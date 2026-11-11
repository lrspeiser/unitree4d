import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('l2_network', Path(__file__).parents[1] / 'l2_network.py')
network = importlib.util.module_from_spec(spec)
spec.loader.exec_module(network)


class NetworkProtocolTests(unittest.TestCase):
    def test_real_coalesced_response(self):
        # Real response to read-only user command 6, captured from this L2.
        raw = bytes.fromhex('55aa050a6b0000001c000000050000002e2f9a1600000000000000ff')
        # The first frame is captured exactly; construct the ACK tail through the
        # already hardware-verified encoder because SDK tail reserve bytes vary.
        first = raw
        ack = network.encode(101, struct.pack('<IIII', 2000, 6, 0, 1))
        result = list(network.frames(first + ack))
        self.assertEqual([x[0] for x in result], [107, 101])
        self.assertEqual(network.describe(*result[0])['work_mode'], 5)

    def test_config_wire_layout(self):
        payload = network.network_payload('192.168.0.62', '192.168.0.34', '192.168.0.1', '255.255.255.0')
        self.assertEqual(payload.hex(), 'c0a8003ec0a80022c0a80001ffffff00d5173918')
        frame = network.encode(108, payload)
        self.assertEqual(len(frame), 44)
        self.assertEqual(struct.unpack_from('<II', frame, 4), (108, 44))
        self.assertEqual(list(network.frames(frame)), [(108, payload)])

    def test_reject_bad_inputs_and_corruption(self):
        for source, destination in [('0.0.0.0', '192.168.0.34'),
                                    ('192.168.0.255', '192.168.0.34'),
                                    ('192.168.0.62', '192.168.1.34'),
                                    ('192.168.0.62', '192.168.0.62')]:
            with self.assertRaises(ValueError):
                network.network_payload(source, destination, '192.168.0.1', '255.255.255.0')
        good = network.encode(100, struct.pack('<II', 6, 0))
        corrupt = bytearray(good); corrupt[12] ^= 1
        for raw in [good[:-1], corrupt, b'bad']:
            with self.assertRaises(ValueError):
                list(network.frames(raw))


if __name__ == '__main__':
    unittest.main()
