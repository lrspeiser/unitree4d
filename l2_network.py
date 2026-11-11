"""Read L2 identity/work mode or explicitly stage a static network configuration.

Packet layout follows the pinned Unitree SDK's protocol structs. Payload-only
CRC, type 100 commands and type 108 IP configuration were checked against the
official SDK library implementation. No documented DHCP/hostname command exists.
"""
import argparse
import ipaddress
import json
from pathlib import Path
import socket
import struct
import time
import zlib

MAGIC = bytes.fromhex('55aa050a')


def encode(kind, payload):
    return (MAGIC + struct.pack('<II', kind, len(payload) + 24) + payload
            + struct.pack('<II2s2s', zlib.crc32(payload), 0, b'\0\0', b'\0\xff'))


def frames(datagram):
    """One UDP datagram can contain a response and ACK concatenated together."""
    position = 0
    while position < len(datagram):
        if len(datagram) - position < 24 or datagram[position:position + 4] != MAGIC:
            raise ValueError('Invalid/truncated L2 frame header')
        kind, size = struct.unpack_from('<II', datagram, position + 4)
        if size < 24 or position + size > len(datagram):
            raise ValueError('Invalid L2 frame length')
        frame = datagram[position:position + size]
        payload = frame[12:-12]
        if frame[-2:] != b'\0\xff' or zlib.crc32(payload) != struct.unpack_from('<I', frame, size - 12)[0]:
            raise ValueError('Invalid L2 CRC/tail')
        yield kind, payload
        position += size


def network_payload(lidar_ip, destination_ip, gateway, mask, lidar_port=6101, destination_port=6201):
    source = ipaddress.IPv4Address(lidar_ip)
    destination = ipaddress.IPv4Address(destination_ip)
    route = ipaddress.IPv4Address(gateway)
    network = ipaddress.IPv4Network(f'{source}/{mask}', strict=False)
    if source in (network.network_address, network.broadcast_address) or source.is_multicast or source.is_unspecified:
        raise ValueError('L2 address must be a unicast host address')
    if destination in (network.network_address, network.broadcast_address) or destination not in network or source == destination:
        raise ValueError('Destination must be a different host on the selected subnet')
    if route != ipaddress.IPv4Address('0.0.0.0') and route not in network:
        raise ValueError('Gateway must be on the selected subnet, or 0.0.0.0')
    if not (1 <= lidar_port <= 65535 and 1 <= destination_port <= 65535):
        raise ValueError('UDP ports must be between 1 and 65535')
    return (source.packed + destination.packed + route.packed + network.netmask.packed
            + struct.pack('<HH', lidar_port, destination_port))


def describe(kind, payload):
    if kind == 101 and len(payload) == 16:
        packet_type, command, value, status = struct.unpack('<IIII', payload)
        return {'type': kind, 'ack_packet_type': packet_type, 'command': command,
                'value': value, 'status': status}
    if kind == 105 and len(payload) >= 40:
        return {'type': kind, 'hardware': '.'.join(map(str, payload[:4])),
                'firmware': '.'.join(map(str, payload[4:8])),
                'name': payload[8:32].split(b'\0', 1)[0].decode('utf-8', 'replace')}
    if kind == 107 and len(payload) == 4:
        return {'type': kind, 'work_mode': struct.unpack('<I', payload)[0]}
    if kind == 108 and len(payload) == 20:
        names = ['lidar_ip', 'destination_ip', 'gateway', 'mask']
        result = {'type': kind}
        result.update({name: str(ipaddress.IPv4Address(payload[i * 4:i * 4 + 4])) for i, name in enumerate(names)})
        result['lidar_port'], result['destination_port'] = struct.unpack_from('<HH', payload, 16)
        return result
    return {'type': kind, 'payload_bytes': len(payload)}


def exchange(sock, current_ip, request, seconds=3):
    sock.sendto(request, (current_ip, 6101))
    deadline = time.monotonic() + seconds
    responses = []
    while time.monotonic() < deadline:
        try:
            data, sender = sock.recvfrom(65535)
        except socket.timeout:
            continue
        if sender != (current_ip, 6101):
            continue
        try:
            for kind, payload in frames(data):
                if kind not in (102, 103, 104):
                    result = describe(kind, payload)
                    responses.append(result)
                    print(json.dumps(result), flush=True)
        except ValueError as error:
            print(json.dumps({'ignored_frame': str(error)}), flush=True)
    return responses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bind-ip', default='192.168.1.2')
    parser.add_argument('--current-ip', default='192.168.1.62')
    parser.add_argument('--query', action='store_true', help='Read version and work mode; no configuration changes')
    parser.add_argument('--lidar-ip')
    parser.add_argument('--destination-ip')
    parser.add_argument('--gateway', default='0.0.0.0')
    parser.add_argument('--mask', default='255.255.255.0')
    parser.add_argument('--apply', action='store_true', help='Send the staged type-108 configuration; otherwise dry run')
    parser.add_argument('--record', default='tmp/l2-network-last-change.json')
    args = parser.parse_args()
    if args.query:
        if args.apply:
            parser.error('--query and --apply cannot be combined')
        request = None
    else:
        if not args.lidar_ip or not args.destination_ip:
            parser.error('Supply --lidar-ip and --destination-ip, or use --query')
        try:
            payload = network_payload(args.lidar_ip, args.destination_ip, args.gateway, args.mask)
        except ValueError as error:
            parser.error(str(error))
        request = encode(108, payload)
        proposed = describe(108, payload)
        print(json.dumps({'current_ip': args.current_ip, 'proposed': proposed, 'apply': args.apply}, indent=2), flush=True)
        if not args.apply:
            return
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((args.bind_ip, 6201))
        sock.settimeout(0.2)
        if args.query:
            for command in (3, 6):
                exchange(sock, args.current_ip, encode(100, struct.pack('<II', command, 0)), 2)
            return
        responses = exchange(sock, args.current_ip, request)
        record = {'current_ip': args.current_ip, 'bind_ip': args.bind_ip,
                  'proposed': proposed, 'responses': responses,
                  'activation_verified': False}
        output = Path(args.record)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(record, indent=2) + '\n')
        # Firmware may report the internal command type rather than legacy type 108.
        success = any(r.get('type') == 101 and r.get('ack_packet_type') == 108
                      and r.get('status') == 1 for r in responses)
        if not success:
            raise SystemExit('No matching type-108 success ACK observed. Do not assume acceptance; inspect the saved response record and verify the new address after restart. Firmware may report an internal command type.')
        print('Success ACK received. The SDK requires a power-cycle after changing IP settings.')
        print('Verify the new address and incoming scan packets after reconnecting to the target network.')


if __name__ == '__main__':
    main()
