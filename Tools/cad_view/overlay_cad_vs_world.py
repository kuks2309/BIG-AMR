#!/usr/bin/env python3
"""Draw the real CAD geometry and our Gazebo world on ONE image.

    python3 Tools/cad_view/overlay_cad_vs_world.py

This is the check that matters. Everything else compares numbers to numbers;
this puts the customer's lines and our boxes in the same picture, in the same
absolute coordinates, so a machine we placed wrongly is visible as a box that
does not sit on its outline.

    thin grey lines   the drawing, straight from the trimmed DXF
    coloured boxes    cad_plant.world, from plant_cad.py
    red hatch         where a painted lane crosses a machine body

Output is gitignored — it contains the customer's drawing.
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle, FancyArrow

import ezdxf

from csm import plant_cad as P

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.normpath(os.path.join(
    HERE, "..", "..", "References", "local", "gazebo-world", "extracted"))
DXF = os.path.join(EXTRACT, "cathode_cell_trimmed.dxf")

#: The area worth looking at. The hall is 305 x 209 m but half of it is the
#: anode cell, which we do not model — including it just shrinks everything.
VIEW = (105, 160, 225, 290)


def cad_segments(path):
    """Every line in the drawing as a ((x0,y0),(x1,y1)) pair, in METRES.

    The DXF is in millimetres, which is the drawing's own unit and the reason
    plant_cad's numbers are 1/1000 of what a viewer shows.
    """
    doc = ezdxf.readfile(path)
    segs = []
    for e in doc.modelspace():
        t = e.dxftype()
        try:
            if t == "LINE":
                a, b = e.dxf.start, e.dxf.end
                segs.append(((a.x / 1000, a.y / 1000), (b.x / 1000, b.y / 1000)))
            elif t == "LWPOLYLINE":
                pts = [(p[0] / 1000, p[1] / 1000) for p in e.get_points()]
                segs += list(zip(pts, pts[1:]))
                if e.closed and len(pts) > 2:
                    segs.append((pts[-1], pts[0]))
        except Exception:
            pass
    return segs


def main():
    if not os.path.exists(DXF):
        print(f"missing {DXF}", file=sys.stderr)
        print("Run Tools/cad_view/trim_dxf.py first — see docs/gazebo_world/sources.md",
              file=sys.stderr)
        return 1

    print("reading the drawing ...")
    segs = cad_segments(DXF)
    x0, y0, x1, y1 = VIEW
    segs = [s for s in segs
            if x0 - 5 < s[0][0] < x1 + 5 and y0 - 5 < s[0][1] < y1 + 5]
    print(f"  {len(segs):,} line segments in view")

    fig, ax = plt.subplots(figsize=(19, 20), dpi=150)
    ax.set_facecolor("white")

    # The drawing underneath, thin and pale — it is the reference, not the
    # subject. Drawn first so our boxes sit on top of it.
    ax.add_collection(LineCollection(segs, colors="#9aa3ad", linewidths=0.28,
                                     zorder=1))

    # Our world on top, unfilled so the drawing shows through. A filled box
    # would hide exactly the outline we are checking against.
    CL = {"ASRS": "#e0a800", "GRV": "#1f5fd0", "CTR": "#c62828", "SLT": "#2e9e3f"}
    for name, mx0, my0, mx1, my1 in P.machines():
        key = "ASRS" if name == "ASRS" else name[:3]
        ax.add_patch(Rectangle((mx0, my0), mx1 - mx0, my1 - my0, fc="none",
                               ec=CL[key], lw=2.6, zorder=4))
        ax.text((mx0 + mx1) / 2, (my0 + my1) / 2, name, ha="center", va="center",
                fontsize=13, weight="bold", color=CL[key], zorder=6,
                bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.5))

    for lx0, ly0, lx1, ly1 in P.LANES:
        ax.add_patch(Rectangle((lx0, ly0), lx1 - lx0, ly1 - ly0, fc="#4a90d9",
                               ec="none", alpha=0.20, zorder=2))

    L, W = P.ROBOT_3_5T[1], P.ROBOT_3_5T[0]
    for px, py, rot in P.AGV_POSITIONS:
        yaw = math.radians(rot)
        c, s = abs(math.cos(yaw)), abs(math.sin(yaw))
        hw, hh = (c * L + s * W) / 2, (s * L + c * W) / 2
        ax.add_patch(Rectangle((px - hw, py - hh), 2 * hw, 2 * hh, fc="#2fb355",
                               ec="#12461f", lw=1.0, alpha=0.85, zorder=5))
        ax.add_patch(FancyArrow(px, py, math.cos(yaw) * 1.5, math.sin(yaw) * 1.5,
                                width=0.16, head_width=0.65, head_length=0.55,
                                fc="#0c3312", ec="none", zorder=6))

    for jx, jy in P.JUNCTIONS:
        ax.add_patch(Rectangle((jx - 0.6, jy - 0.6), 1.2, 1.2, fc="#f28c1e",
                               ec="none", zorder=5))

    # Where our own audit says the world contradicts itself.
    nconf = 0
    for lane in P.LANES:
        for name, mx0, my0, mx1, my1 in P.machines():
            ox0, oy0 = max(lane[0], mx0), max(lane[1], my0)
            ox1, oy1 = min(lane[2], mx1), min(lane[3], my1)
            if ox1 > ox0 and oy1 > oy0 and (ox1 - ox0) * (oy1 - oy0) > 0.5:
                ax.add_patch(Rectangle((ox0, oy0), ox1 - ox0, oy1 - oy0,
                                       fc="none", ec="#e0004d", lw=2.4,
                                       hatch="xxx", zorder=7))
                nconf += 1

    for gx in range(int(x0 // 10 * 10), int(x1) + 10, 10):
        ax.axvline(gx, color="#dcdcdc", lw=0.4, zorder=0)
    for gy in range(int(y0 // 10 * 10), int(y1) + 10, 10):
        ax.axhline(gy, color="#dcdcdc", lw=0.4, zorder=0)

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xlabel("CAD x  [m]", fontsize=12)
    ax.set_ylabel("CAD y  [m]", fontsize=12)
    ax.set_title(
        "CAD drawing (grey)  vs  cad_plant.world (coloured)\n"
        f"same absolute coordinates · {len(segs):,} drawing segments · "
        f"{len(P.machines())} machines · {len(P.AGV_POSITIONS)} AGV positions · "
        f"{nconf} lane/machine conflicts (red)",
        fontsize=15, weight="bold")
    fig.tight_layout()

    out = os.path.join(EXTRACT, "overlay_cad_vs_world.png")
    fig.savefig(out, bbox_inches="tight")
    print("wrote", out)

    # A close-up of the coaters, where the biggest unresolved question is.
    ax.set_xlim(108, 165)
    ax.set_ylim(225, 280)
    ax.set_title("Coater row — do the lanes really run into the machines?\n"
                 "grey = drawing · red boxes = our coater bodies · "
                 "red hatch = lane inside the body",
                 fontsize=15, weight="bold")
    fig.set_size_inches(17, 17)
    out2 = os.path.join(EXTRACT, "overlay_coaters.png")
    fig.savefig(out2, bbox_inches="tight")
    print("wrote", out2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
