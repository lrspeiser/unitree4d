"""Export bounded raw L2 recordings for offline/COS algorithm development."""

import argparse
import json
from pathlib import Path

import numpy as np

from point_viewer import decode

ap = argparse.ArgumentParser()
ap.add_argument("recording", type=Path)
ap.add_argument("output", type=Path)
args = ap.parse_args()
points = []
offsets = [0]
metadata = []
with args.recording.open() as f:
    for line in f:
        row = json.loads(line)
        p, meta = decode(bytes.fromhex(row["packet_hex"]))
        points.append(p)
        offsets.append(offsets[-1] + len(p))
        metadata.append({k: v for k, v in row.items() if k != "packet_hex"})
if not points:
    raise SystemExit("No valid slices")
np.savez_compressed(
    args.output,
    xyzi=np.concatenate(points).astype("float32"),
    slice_offsets=np.array(offsets),
    metadata_json=json.dumps(metadata),
)
print(f"Exported {len(points)} slices, {offsets[-1]} points to {args.output}")
