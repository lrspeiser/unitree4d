"""Run the real offline viewer without opening a LiDAR socket."""

import json
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


class ViewerHTTPTests(unittest.TestCase):
    def test_offline_page_and_fresh_replay(self):
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        process = subprocess.Popen(
            [
                sys.executable,
                "point_viewer.py",
                "--port",
                str(port),
                "--replay",
                "tests/fixtures/l2-scan.bin",
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 8
            while True:
                try:
                    with urlopen(f"http://127.0.0.1:{port}/api", timeout=1) as response:
                        state = json.load(response)
                    if state["points"]:
                        break
                except OSError:
                    pass
                self.assertIsNone(process.poll(), "Viewer exited before serving data")
                if time.monotonic() >= deadline:
                    self.fail("Viewer did not serve a decoded replay")
                time.sleep(0.05)
            self.assertEqual(state["mode"], "replay")
            self.assertEqual(state["invalid"], 0)
            self.assertEqual(state["error"], "")
            self.assertLess(state["age_s"], 0.6)
            self.assertEqual(len(state["points"][0]), 4)
            with urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
                page = response.read().decode("utf-8")
            self.assertIn("Mark empty scene", page)
            self.assertIn("toUpperCase()", page)
            self.assertNotIn("\ufffd", page)
        finally:
            process.terminate()
            process.communicate(timeout=5)

    def test_unbounded_recording_argument_rejected(self):
        result = subprocess.run(
            [sys.executable, "point_viewer.py", "--record-seconds", "nan"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("finite positive", result.stderr)


if __name__ == "__main__":
    unittest.main()
