# Copyright (c) 2024, Unitree Robotics; (c) 2026, Leonard Speiser.
# Calibration math adapted from the pinned Unitree SDK; see LICENSE and THIRD_PARTY.md.
"""Receive-only L2 viewer. Never sends sensor commands or changes networking."""

import argparse
import collections
import json
import math
import socket
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

from l2_network import frames


def decode(data):
    packets = list(frames(data))
    if len(packets) != 1 or packets[0][0] != 102 or len(data) != 1044:
        raise ValueError("Not a 3D slice")

    def u(offset):
        return struct.unpack_from("<I", data, offset)[0]

    if u(16) != 1020 or u(24) >= 1000000000 or u(128) > 300:
        raise ValueError("Invalid metadata")
    f = np.frombuffer(data, dtype="<f4", count=23, offset=36).astype(float)
    if not np.isfinite(f).all():
        raise ValueError("Nonfinite calibration")
    (
        a,
        b,
        tbias,
        abias,
        beta,
        xi,
        bias,
        scale,
        tstart,
        tstep,
        _,
        rmin,
        rmax,
        astart,
        astep,
    ) = f[7:22]
    rmin = max(0.05, rmin)
    if scale <= 0 or rmax < rmin or rmax > 1000:
        raise ValueError("Invalid range")
    n = u(128)
    raw = np.frombuffer(data, dtype="<u2", count=n, offset=132)
    idx = np.arange(n)
    r = scale * (raw.astype(float) + bias)
    ok = (raw != 0) & (r >= rmin) & (r <= rmax)
    alpha = astart + abias + idx * astep
    theta = tstart + tbias + idx * tstep
    pa = (
        -np.cos(beta) * np.sin(xi) + np.sin(beta) * np.cos(xi) * np.sin(alpha)
    ) * r + b
    pb = np.cos(alpha) * np.cos(xi) * r
    pc = (np.sin(beta) * np.sin(xi) + np.cos(beta) * np.cos(xi) * np.sin(alpha)) * r + a
    p = np.column_stack(
        (
            np.cos(theta) * pa - np.sin(theta) * pb,
            np.sin(theta) * pa + np.cos(theta) * pb,
            pc,
            np.frombuffer(data, dtype="u1", count=n, offset=732),
        )
    )[ok]
    if not np.isfinite(p).all():
        raise ValueError("Nonfinite points")
    return p, {
        "sequence": u(12),
        "sensor_seconds": u(20),
        "sensor_nanos": u(24),
        "point_step_seconds": float(struct.unpack_from("<f", data, 104)[0]),
    }


class State:
    def __init__(self, mode="live"):
        self.mode = mode
        self.lock = threading.Lock()
        self.batches = collections.deque(maxlen=300)
        self.scans = 0
        self.invalid = 0
        self.points = 0
        self.last = 0
        self.error = ""
        self.gaps = 0
        self.seq = None

    def add(self, data, record=None):
        p, meta = decode(data)
        now = time.monotonic()
        if record:
            record.write(
                json.dumps(
                    dict(
                        meta,
                        received_monotonic_ns=time.monotonic_ns(),
                        received_unix_ns=time.time_ns(),
                        packet_hex=data.hex(),
                    )
                )
                + "\n"
            )
        with self.lock:
            if self.seq is not None:
                delta = (meta["sequence"] - self.seq) % 1024
                if 1 < delta < 512:
                    self.gaps += delta - 1
            self.seq = meta["sequence"]
            self.scans += 1
            self.points += len(p)
            self.last = now
            self.batches.append((now, p))

    def snapshot(self):
        with self.lock:
            now = time.monotonic()
            b = [p for t, p in self.batches if now - t <= 0.6]
            p = np.concatenate(b) if b else np.empty((0, 4))
            p = p[:: max(1, (len(p) + 24999) // 25000)]
            return dict(
                mode=self.mode,
                points=p.tolist(),
                scans=self.scans,
                total_points=self.points,
                invalid=self.invalid,
                sequence_gaps=self.gaps,
                age_s=round(now - self.last, 3) if self.last else None,
                error=self.error,
            )


def receive(state, args):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2 * 1024 * 1024)
            s.bind((args.bind, 6201))
            s.settimeout(1)
            record = None
            record_start = time.monotonic()
            if args.record:
                Path(args.record).parent.mkdir(parents=True, exist_ok=True)
                record = open(args.record, "x", buffering=1)
            try:
                while True:
                    try:
                        d, addr = s.recvfrom(65535)
                    except socket.timeout:
                        continue
                    if addr != (args.sensor, 6101):
                        continue
                    if len(d) >= 8 and struct.unpack_from("<I", d, 4)[0] != 102:
                        continue
                    if (
                        record
                        and time.monotonic() - record_start >= args.record_seconds
                    ):
                        record.close()
                        record = None
                    try:
                        state.add(d, record)
                    except ValueError:
                        with state.lock:
                            state.invalid += 1
            finally:
                if record:
                    record.close()
    except Exception as e:
        with state.lock:
            state.error = str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="192.168.0.36")
    ap.add_argument("--sensor", default="192.168.0.250")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--record")
    ap.add_argument("--record-seconds", type=float, default=60)
    ap.add_argument("--replay", type=Path)
    args = ap.parse_args()
    if not math.isfinite(args.record_seconds) or args.record_seconds <= 0:
        ap.error("--record-seconds must be a finite positive number")
    if args.replay and not args.replay.is_file():
        ap.error("--replay must name an existing recorded packet file")
    state = State(mode="replay" if args.replay else "live")
    if args.replay:

        def replay():
            data = args.replay.read_bytes()
            while True:
                state.add(data)
                time.sleep(0.05)

        threading.Thread(target=replay, daemon=True).start()
    else:
        threading.Thread(target=receive, args=(state, args), daemon=True).start()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/api":
                body = json.dumps(state.snapshot(), allow_nan=False).encode()
                typ = "application/json"
            elif self.path == "/":
                body = Path(__file__).with_name("viewer.html").read_bytes()
                typ = "text/html"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", typ)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    print(
        f"Viewer: http://127.0.0.1:{args.port} | "
        + ("REPLAY" if args.replay else "LIVE receive only"),
        flush=True,
    )
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
