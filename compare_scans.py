"""Compare controlled real captures using labelled 4 cm occupancy differences."""
from pathlib import Path
from collections import Counter
import sys
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

first, second = map(Path, sys.argv[1:3])
clouds = []
for folder in [first, second]:
    with (folder / 'scan.ply').open() as stream:
        while True:
            line = stream.readline()
            if not line:
                raise ValueError('Missing PLY end_header')
            if line.strip() == 'end_header':
                break
        a = np.loadtxt(stream)
    r = np.linalg.norm(a[:, :3], axis=1)
    clouds.append(a[(r > .15) & (r < 1.2) & (a[:, 2] > .1) & (a[:, 2] < 1)])
keys = [Counter(map(tuple, np.floor(a[:, :3] / .04).astype(int))) for a in clouds]
new = {key for key, n in keys[0].items() if n >= 3 and key not in keys[1]}
mask = np.array([tuple(key) in new for key in np.floor(clouds[0][:, :3] / .04).astype(int)])
changed = clouds[0][mask]
fig, axes = plt.subplots(1, 3, figsize=(14, 5), layout='constrained')
for ax, a, title in zip(axes[:2], clouds, ['Hand held in place', 'Hand removed']):
    ax.scatter(a[:, 0], a[:, 2], s=1, color='#315c85', alpha=.5, linewidths=0)
    ax.set_title(title)
axes[2].scatter(clouds[1][:, 0], clouds[1][:, 2], s=.7, color='#aaaaaa', alpha=.2, linewidths=0)
axes[2].scatter(changed[:, 0], changed[:, 2], s=2, color='#bd316a', linewidths=0)
axes[2].set_title('Surface present during hand capture')
for ax in axes:
    ax.scatter([0], [0], marker='x', s=45, color='#c35b00')
    ax.set(xlim=(-1.2, 1.2), ylim=(-.05, 1), xlabel='X (m)', ylabel='Height Z (m)')
    ax.set_aspect('equal'); ax.grid(alpha=.2)
fig.suptitle('Controlled near-field check · real L2 data · side view · sensor at (0, 0)')
fig.savefig(first / 'hand-comparison.png', dpi=150)
summary = {'method': '4 cm voxels, minimum 3 returns in hand capture, absent in comparison',
           'hand_capture_near_points': len(clouds[0]), 'removed_capture_near_points': len(clouds[1]),
           'changed_voxels': len(new), 'changed_points': len(changed),
           'limitation': 'Motion, occlusion and sampling also cause differences; this is not semantic hand detection.'}
(first / 'comparison.json').write_text(json.dumps(summary, indent=2) + '\n')
print(first / 'hand-comparison.png')
