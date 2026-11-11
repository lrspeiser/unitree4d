import unittest
from pathlib import Path

import numpy as np

from point_viewer import State, decode


class ViewerTests(unittest.TestCase):
    def test_cpp_parity(self):
        p, _ = decode(Path("tests/fixtures/l2-scan.bin").read_bytes())
        ref = np.loadtxt("build/reference.csv", delimiter=",")
        np.testing.assert_allclose(p[:, :3], ref[:, :3], atol=1e-4, rtol=0)
        np.testing.assert_array_equal(p[:, 3], ref[:, 3])

    def test_corruption(self):
        d = bytearray(Path("tests/fixtures/l2-scan.bin").read_bytes())
        d[200] ^= 1
        for bad in [bytes(d), bytes(d[:100]), b""]:
            with self.assertRaises(ValueError):
                decode(bad)

    def test_bounded(self):
        s = State()
        d = Path("tests/fixtures/l2-scan.bin").read_bytes()
        for _ in range(310):
            s.add(d)
        self.assertEqual(len(s.batches), 300)
        self.assertLessEqual(len(s.snapshot()["points"]), 25000)


if __name__ == "__main__":
    unittest.main()
