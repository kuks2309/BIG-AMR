#!/usr/bin/env python3
"""Plan view of cad_plant.world, drawn to be laid beside the CAD on screen.

Same coordinates, same colours as the Gazebo world, plus a labelled grid so a
point can be found in both. Output goes to the gitignored working directory —
it is derived from confidential drawings.
"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow

from csm import plant_cad as P

OUT = "References/local/gazebo-world/extracted/cad_world_plan.png"

fig, ax = plt.subplots(figsize=(20, 22), dpi=140)

# ---- hall
(wx0, wx1), (wy0, wy1) = P.HALL_X, P.HALL_Y
ax.add_patch(Rectangle((wx0, wy0), wx1 - wx0, wy1 - wy0,
                       fc="#f7f7f5", ec="#333", lw=2.5, zorder=0))

# ---- lanes
for i, (x0, y0, x1, y1) in enumerate(P.LANES, 1):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0,
                           fc="#c3ccd8", ec="#8d9cb0", lw=0.6, zorder=1))

# ---- machines
CL = {"ASRS": "#f2bf26", "GRV": "#4d8ce6", "CTR": "#d95a4d", "SLT": "#73cc66"}
for name, x0, y0, x1, y1 in P.machines():
    key = "ASRS" if name == "ASRS" else name[:3]
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0,
                           fc=CL[key], ec="#333", lw=1.4, alpha=0.9, zorder=3))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, name, ha="center", va="center",
            fontsize=11, weight="bold", zorder=6)

# ---- lane-through-machine conflicts, in warning red
def ov(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None

nconf = 0
for lane in P.LANES:
    for name, mx0, my0, mx1, my1 in P.machines():
        r = ov(lane, (mx0, my0, mx1, my1))
        if r and (r[2] - r[0]) * (r[3] - r[1]) > 0.5:
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1],
                                   fc="none", ec="#e0004d", lw=2.2,
                                   hatch="xxx", zorder=7))
            nconf += 1

# ---- AGV positions
L, W = P.ROBOT_3_5T[1], P.ROBOT_3_5T[0]
for px, py, rot in P.AGV_POSITIONS:
    yaw = math.radians(rot)
    c, s = abs(math.cos(yaw)), abs(math.sin(yaw))
    hw, hh = (c * L + s * W) / 2, (s * L + c * W) / 2
    ax.add_patch(Rectangle((px - hw, py - hh), 2 * hw, 2 * hh,
                           fc="#3fb35a", ec="#14501f", lw=0.8, zorder=4))
    ax.add_patch(FancyArrow(px, py, math.cos(yaw) * 1.6, math.sin(yaw) * 1.6,
                            width=0.18, head_width=0.7, head_length=0.6,
                            fc="#0d3d16", ec="none", zorder=5))

# ---- junctions
for jx, jy in P.JUNCTIONS:
    ax.add_patch(Rectangle((jx - 0.6, jy - 0.6), 1.2, 1.2,
                           fc="#f28c1e", ec="none", alpha=0.95, zorder=5))

# ---- charging
cw, ch = P.CHARGING_BAY_SIZE
for group, bays in P.CHARGING.items():
    for bx, by in bays:
        ax.add_patch(Rectangle((bx - cw / 2, by - ch / 2), cw, ch,
                               fc="#3f73d9", ec="#16306b", lw=1.0, zorder=4))
        ax.text(bx, by - ch / 2 - 1.6, "CHG", ha="center", fontsize=7,
                color="#16306b", zorder=6)

# ---- grid, labelled in absolute CAD metres
for gx in range(int(wx0 // 10 * 10), int(wx1) + 10, 10):
    ax.axvline(gx, color="#b9b9b9", lw=0.4, ls=":", zorder=0)
for gy in range(int(wy0 // 10 * 10), int(wy1) + 10, 10):
    ax.axhline(gy, color="#b9b9b9", lw=0.4, ls=":", zorder=0)

ax.set_xlim(wx0 - 6, wx1 + 6)
ax.set_ylim(wy0 - 6, wy1 + 6)
ax.set_aspect("equal")
ax.set_xticks(range(int(wx0 // 20 * 20), int(wx1) + 20, 20))
ax.set_yticks(range(int(wy0 // 20 * 20), int(wy1) + 20, 20))
ax.tick_params(labelsize=9)
ax.grid(False)
ax.set_xlabel("CAD x  [m]  — absolute, same number as in the DWG", fontsize=12)
ax.set_ylabel("CAD y  [m]  — absolute, same number as in the DWG", fontsize=12)
ax.set_title(f"cad_plant.world — FM2 cathode cell, {wx1-wx0:.0f} x {wy1-wy0:.0f} m\n"
             f"{len(P.machines())} machines · {len(P.LANES)} lanes · "
             f"{len(P.JUNCTIONS)} junctions · {len(P.AGV_POSITIONS)} AGV positions · "
             f"{nconf} lane/machine conflicts (red hatch)",
             fontsize=15, weight="bold")
fig.tight_layout()
fig.savefig(OUT, bbox_inches="tight")
print("wrote", OUT, f"({nconf} conflicts marked)")

# ---- second view: the cathode cell only, at a readable scale
ax.set_xlim(105, 225)
ax.set_ylim(160, 290)
ax.set_xticks(range(110, 230, 10))
ax.set_yticks(range(160, 300, 10))
ax.set_title("cad_plant.world — cathode cell detail  (x 105-225, y 160-290 m)",
             fontsize=15, weight="bold")
fig.set_size_inches(18, 19)
OUT2 = OUT.replace(".png", "_cell.png")
fig.savefig(OUT2, bbox_inches="tight")
print("wrote", OUT2)
