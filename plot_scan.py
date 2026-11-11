"""Render the genuine L2 capture; no demo or simulated points."""
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

folder = Path(sys.argv[1])
with (folder / 'scan.ply').open() as stream:
    while True:
        line = stream.readline()
        if not line:
            raise ValueError('PLY has no end_header')
        if line.strip() == 'end_header':
            break
    data = np.loadtxt(stream)
if data.ndim != 2 or data.shape[0] == 0:
    raise ValueError('The scan contains no points')
shown = data[::max(1, len(data) // 30000)]
# Keep the full extent visible; equal scale prevents misleading proportions.
minimum, maximum = data[:, :3].min(axis=0), data[:, :3].max(axis=0)
centre = (minimum + maximum) / 2
radius = max(maximum - minimum) / 2 * 1.05
fig = plt.figure(figsize=(15, 7), layout='constrained', facecolor='#10191e')
ax = fig.add_subplot(121, projection='3d', facecolor='#10191e')
sc = ax.scatter(shown[:, 0], shown[:, 1], shown[:, 2], c=shown[:, 2],
                cmap='viridis', s=0.45, linewidths=0, alpha=0.75)
for k, setter in enumerate([ax.set_xlim, ax.set_ylim, ax.set_zlim]):
    setter(centre[k] - radius, centre[k] + radius)
ax.set_box_aspect((1, 1, 1))
ax.view_init(elev=22, azim=-45)
ax.set(xlabel='X (m)', ylabel='Y (m)', zlabel='Z (m)', title='3D view')
ax.scatter([0], [0], [0], color='#ffb65b', s=20)
for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
    axis.set_pane_color((0.07, 0.11, 0.13, 1))
    axis.label.set_color('#dce8eb')
    axis._axinfo['grid']['color'] = (0.28, 0.38, 0.42, 0.4)
ax.tick_params(colors='#dce8eb')
ax.title.set_color('#dce8eb')
top = fig.add_subplot(122, facecolor='#10191e')
top.scatter(shown[:, 0], shown[:, 1], c=shown[:, 2], cmap='viridis', s=0.5,
            linewidths=0, alpha=0.75)
top.scatter([0], [0], color='#ffb65b', marker='x', s=45, label='L2 position')
top.set(xlabel='X (m)', ylabel='Y (m)', title='Top view')
top.set_aspect('equal', adjustable='box')
top.grid(alpha=0.15, color='#a0bcc5')
top.tick_params(colors='#dce8eb')
for spine in top.spines.values():
    spine.set_color('#50636b')
for label in [top.xaxis.label, top.yaxis.label, top.title]:
    label.set_color('#dce8eb')
legend = top.legend(facecolor='#10191e', edgecolor='#50636b', labelcolor='#dce8eb')
cbar = fig.colorbar(sc, ax=[ax, top], shrink=0.65, pad=0.02)
cbar.set_label('Height Z (m)', color='#dce8eb')
cbar.ax.tick_params(colors='#dce8eb')
fig.suptitle(f'Unitree L2 · captured on this Mac · {len(data):,} points over approximately 1 second', color='#dce8eb')
fig.savefig(folder / 'scan-preview.png', dpi=150, facecolor=fig.get_facecolor())
print('XYZ bounds (metres):', minimum.tolist(), maximum.tolist())
print(folder / 'scan-preview.png')
