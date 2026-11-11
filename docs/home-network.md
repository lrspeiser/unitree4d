# Home-network commissioning and a discoverable name

The connected L2 identifies as `YS-L2`, hardware `2.2.1.1`, firmware `2.8.11.1`.
Those values were read through the actual sensor's version command.

## Current commissioning state (2026-11-11)

**5090 continuation update:** the L2 at `192.168.0.250:6101` now sends to
`192.168.0.36:6201` (the Windows PC), following an acknowledged sensor-only write.
Native Windows live reception was verified. No Windows network settings were
changed. `unitree.localdomain` resolved and the sensor returned YS-L2 identity.
Use [the current README](../README.md) and
[the electrical commissioning worksheet](electrical-team-build-guide.md#commission-the-robot-network).

The following bullets document the preceding Mac commissioning step, including
its former destination `192.168.0.34`. They are history, not settings to reapply.


- UniFi reserved `192.168.0.250` for the L2 and named it `unitree`.
- UniFi's local DNS record `unitree.localdomain` resolves to `192.168.0.250`.
  Both the full name and short `unitree` resolved through this Mac's normal OS
  resolver, using its existing `localdomain` search domain and gateway DNS.
- This Mac's existing Wi-Fi lease `192.168.0.34` is now reserved as the receiver.
- The L2 acknowledged a type-108 configuration write with status `1` for
  `192.168.0.250:6101`, destination `192.168.0.34:6201`, gateway `192.168.0.1`,
  mask `255.255.255.0`. After the user moved Ethernet to the home LAN and
  power-cycled the L2, its new address answered all three ping requests.
- A live Java probe over the Mac's Wi-Fi (`en0`) decoded 2,171 scans / 641,497
  points in 10.057 seconds, with zero invalid packets, sequence gaps or
  discontinuities. Data remained fresh at every one-second check. The disconnected
  direct Ethernet adapter was inactive during this test.
- Read-only identity/work-mode queries also succeeded at the new address:
  firmware `2.8.11.1`, hardware `2.2.1.1`, name `YS-L2`, work mode `5`.
- The previous direct-link settings were L2 `192.168.1.62:6101` and receiver
  `192.168.1.2:6201`. The Mac's dedicated Ethernet adapter was restored to DHCP
  after disconnecting it. Wi-Fi supplies the home connection.

The source/destination settings survived the power cycle and actual LAN reception
was verified, beyond the saved DNS/reservation and sensor ACK. See
[`results/home-network-2026-11-11`](../results/home-network-2026-11-11) for the
probe output and health record. The local configuration reply record and UniFi
screenshots are kept under ignored `tmp/`; no router login/session information
is committed.

Unitree's published manual and SDK expose a static LiDAR IP, destination IP,
gateway, subnet mask and UDP ports. They do not document a DHCP-client or hostname
setting. Do not try to enable DHCP by writing `0.0.0.0` as the LiDAR address.
Absence of a documented setting is not a claim about every possible firmware.

For a UniFi LAN, the practical supported arrangement is a fixed address on the
correct LAN plus a DNS name supplied by the gateway. A DHCP reservation excludes
the address from reassignment but does not turn the sensor into a DHCP client.

## Commissioning order

1. Keep the powered L2 directly connected to a computer that can reach the old
   address. Read its current identity and record the MAC from that link.
2. In UniFi, inspect the actual LAN subnet, DHCP pool, reservations and DNS/search
   domain. Select an unused address and reserve/exclude it before configuring the L2.
3. Give the receiving computer a stable address too, using a UniFi DHCP reservation
   if it remains a DHCP client. The L2 sends to a configured destination; it does
   not discover the receiver by hostname.
4. Stage and inspect the new sensor configuration. Apply it once, record replies,
   then follow Unitree's restart/power-cycle requirement.
5. Move the L2's Ethernet cable to a LAN switch/router LAN port. Verify reachability
   and actual incoming scans from the selected receiver before declaring success.
6. Name the device `unitree` in UniFi. Create a corresponding local DNS Host (A)
   record, using the LAN's configured domain. Verify both gateway DNS and normal
   OS name resolution. A client display alias alone is not a DNS record.

Choose a unicast DNS name such as `unitree.home.arpa` or one within the existing
LAN domain. Do not assume `unitree.local` works: `.local` is used for multicast
DNS/Bonjour, and no L2 mDNS implementation has been verified. UniFi's DNS records
resolve only for clients using the gateway's DNS service.

## Read-only identity query and staged configuration

The native Python helper works on the Mac without the SDK's Linux-only binary:

```sh
python3 l2_network.py --query
```

It requests version and work mode, not a factory reset or network change. One
UDP datagram may contain several response frames; the helper validates each
frame separately. The pinned SDK's type-108 network packet is 44 bytes, including
the 20-byte configuration payload and its payload CRC. Some size comments in
the upstream header are stale; the actual struct/library implementation is used.

Example dry run for a `192.168.0.0/24` LAN, **only after checking these addresses**:

```sh
python3 l2_network.py \
  --lidar-ip 192.168.0.250 \
  --destination-ip 192.168.0.34 \
  --gateway 192.168.0.1
```

This only prints the proposal. To send it, add `--apply`; that is a real sensor
configuration write. The helper does not restart the sensor or change the router.
It records replies under ignored `tmp/l2-network-last-change.json`. An unmatched
or absent ACK is reported as uncertain, because firmware may echo an internal
command type. A confirmed new IP and received scan stream after restart are the
decisive verification. Preserve the old/new settings for recovery.

For a receiver already on the LAN, with the above example addresses:

```sh
java -cp build/java unitree4d.L2Probe 0.0.0.0 192.168.0.250 10
```

Do not run another receiver on UDP port 6201 at the same time. No network change
or UniFi DNS entry is implied merely by the presence of these examples; the
commissioning state above records what was actually applied. Read the sensor's
identity after the move with:

```sh
python3 l2_network.py --query --bind-ip 192.168.0.34 --current-ip 192.168.0.250
```

Changing the receiver to the 5090 or Jetson requires configuring the L2's
destination IP again. Reserve that machine's real LAN address first. Merely
cloning this repository or resolving `unitree` does not retarget the data stream.
On another network, inspect that network's subnet and address availability before
using the helper; the home LAN addresses are not robot deployment settings.

Sources: [Unitree IP configuration example](https://github.com/unitreerobotics/unilidar_sdk2/blob/0e3c51f512e6b8ff60b8c32f160b412cb48445c2/unitree_lidar_sdk/examples/set_ip_address.cpp),
[Unitree protocol structs](https://github.com/unitreerobotics/unilidar_sdk2/blob/0e3c51f512e6b8ff60b8c32f160b412cb48445c2/unitree_lidar_sdk/include/unitree_lidar_protocol.h),
[UniFi DNS records and local hostnames](https://help.ui.com/hc/en-us/articles/15179064940439-UniFi-DNS-Records-and-Local-Hostnames).
