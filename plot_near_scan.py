"""Inspect nearby surfaces from genuine capture data, with clearly labelled crops."""
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

folder = Path(sys.argv[1])
radius = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
with (folder / 'scan.ply').open() as stream:
    while True:
        line = stream.readline()
        if not line:
            raise ValueError('PLY has no end_header')
        if line.strip() == 'end_header':
            break
    data = np.loadtxt(stream)
distance = np.linalg.norm(data[:, :3], axis=1)
near = data[(distance <= radius) & (distance >= 0.05)]
if not len(near):
    raise ValueError('No points in the selected radius')
fig, axes = plt.subplots(1, 3, figsize=(16, 6), layout='constrained')
for ax, (x, y, title) in zip(axes, [(0, 1, 'Above: X / Y'), (0, 2, 'Side: X / Z'), (1, 2, 'Side: Y / Z')]):
    sc = ax.scatter(near[:, x], near[:, y], c=near[:, 3], s=0.45, linewidths=0,
                    cmap='viridis', vmin=0, vmax=255)
    ax.scatter([0], [0], color='#d65b00', marker='x', s=50, label='L2 position')
    ax.set(xlabel=f'{"XYZ"[x]} (m)', ylabel=f'{"XYZ"[y]} (m)', title=title,
           xlim=(-radius, radius), ylim=(-radius, radius))
    ax.set_aspect('equal'); ax.grid(alpha=0.2)
axes[0].legend(loc='upper right')
fig.colorbar(sc, ax=axes, shrink=0.6, label='Return intensity (0–255; not RGB color)')
fig.suptitle(f'Actual L2 scan · points within {radius:g} m · {len(near):,} points · sensor at origin')
fig.savefig(folder / 'near-preview.png', dpi=150)
print(folder / 'near-preview.png')
print('Near-field points:', len(near))
