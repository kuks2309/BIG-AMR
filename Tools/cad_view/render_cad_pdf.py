#!/usr/bin/env python3
"""Render the drawing to a PDF that opens in anything.

    python3 Tools/cad_view/render_cad_pdf.py

WHY THIS EXISTS. LibreCAD cost most of an afternoon and never showed the
drawing: it opens our DWGs to a silently empty document, it opens the DXF at the
origin 100 m from the geometry, and it resolves ACI colour 7 to BLACK on its own
black canvas. Each of those alone produces a black window, and a black window
looks the same whichever caused it. A PDF has none of those failure modes — it
is black lines on white paper, at a fixed scale, in whatever viewer is already
installed.

Pages:
    1     the cathode cell, drawing only
    2     the same with cad_plant.world on top
    3..   tiles at ~35 m across, where individual machines are readable

Every page is labelled with its absolute CAD coordinate range, so a feature can
be located in the drawing, in plant_cad.py and in Gazebo from the same numbers.

Output is gitignored — it is the customer's drawing.
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle

import ezdxf

from csm import plant_cad as P

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.normpath(os.path.join(
    HERE, "..", "..", "References", "local", "gazebo-world", "extracted"))
DXF = os.path.join(EXTRACT, "cathode_cell_trimmed.dxf")   # absolute coordinates
OUT = os.path.join(EXTRACT, "cathode_cell.pdf")

CELL = (105, 160, 225, 292)
#: Tile size. 35 m across a landscape A3-ish page puts a coater at about a third
#: of the width, which is where its detail becomes legible.
TILE = 35.0

COLOURS = {"ASRS": "#c8860d", "GRV": "#1f5fd0", "CTR": "#c62828", "SLT": "#2e9e3f"}


def load_segments(path):
    """Every line in the drawing as a segment pair, in metres."""
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


def clip(segs, box, pad=2.0):
    x0, y0, x1, y1 = box
    return [s for s in segs
            if not (max(s[0][0], s[1][0]) < x0 - pad or min(s[0][0], s[1][0]) > x1 + pad
                    or max(s[0][1], s[1][1]) < y0 - pad or min(s[0][1], s[1][1]) > y1 + pad)]


def draw(ax, segs, box, world, lw, title):
    ax.add_collection(LineCollection(segs, colors="#222222", linewidths=lw, zorder=2))
    if world:
        for lx0, ly0, lx1, ly1 in P.lanes_drawn():
            ax.add_patch(Rectangle((lx0, ly0), lx1 - lx0, ly1 - ly0,
                                   fc="#4a90d9", ec="none", alpha=0.18, zorder=1))
        # Spurs in the coater's own colour — a spur belongs to a machine, a lane
        # does not, and routing will have to tell them apart.
        for sy0, sy1, _side in P.COATER_SPUR:
            ax.add_patch(Rectangle((P.COATER_SPUR_X[0], sy0),
                                   P.COATER_SPUR_X[1] - P.COATER_SPUR_X[0],
                                   sy1 - sy0, fc="#d96a5a", ec="none",
                                   alpha=0.30, zorder=1))
        # Connectors are DERIVED, not measured — dashed so the page says so.
        for cx0, cy0, cx1, cy1, _ci, _kind in P.coater_connectors():
            ax.add_patch(Rectangle((cx0, cy0), cx1 - cx0, cy1 - cy0,
                                   fc="#d96a5a", ec="#a03020", lw=0.8, ls="--",
                                   alpha=0.30, zorder=1))
        for name, mx0, my0, mx1, my1 in P.machines():
            key = "ASRS" if name == "ASRS" else name[:3]
            ax.add_patch(Rectangle((mx0, my0), mx1 - mx0, my1 - my0, fc="none",
                                   ec=COLOURS[key], lw=2.0, zorder=4))
            cx, cy = (mx0 + mx1) / 2, (my0 + my1) / 2
            if box[0] < cx < box[2] and box[1] < cy < box[3]:
                ax.text(cx, cy, name, ha="center", va="center", fontsize=11,
                        weight="bold", color=COLOURS[key], zorder=6,
                        bbox=dict(fc="white", ec="none", alpha=0.7, pad=1.5))
        L, W = P.ROBOT_3_5T[1], P.ROBOT_3_5T[0]
        for px, py, rot in P.AGV_POSITIONS:
            yaw = math.radians(rot)
            c, s = abs(math.cos(yaw)), abs(math.sin(yaw))
            hw, hh = (c * L + s * W) / 2, (s * L + c * W) / 2
            ax.add_patch(Rectangle((px - hw, py - hh), 2 * hw, 2 * hh, fc="#9aa8b8",
                                   ec="#4a5560", lw=0.6, alpha=0.7, zorder=4))
        # Named stations on top of the raw pads, so what is identified is
        # distinguishable from what is merely measured.
        for i, sty in enumerate(P.COATER_STATION_Y):
            for kind, sx, col in (("LD", P.COATER_LD_X, "#12b33f"),
                                  ("ULD", P.COATER_ULD_X, "#f08000")):
                inferred = kind == "ULD" and not P.COATER_ULD_MEASURED[i]
                for dy in (-P.COATER_STATION_PAIR / 2, P.COATER_STATION_PAIR / 2):
                    ax.add_patch(Rectangle((sx - L / 2, sty + dy - W / 2), L, W,
                                           fc=col, ec="black", lw=0.8,
                                           alpha=0.35 if inferred else 0.9, zorder=6))
                if box[0] < sx < box[2] and box[1] < sty < box[3]:
                    ax.text(sx, sty, f"{kind}{i+1}", ha="center", va="center",
                            fontsize=7, weight="bold", zorder=8,
                            bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.6))
        for gi, (ya, yb) in enumerate(P.WIP_GROUP_Y, 1):
            for wx in P.WIP_ACCESS_X:
                for wy in (ya, yb):
                    ax.add_patch(Rectangle((wx - L / 2, wy - W / 2), L, W,
                                           fc="#8c59bf", ec="#4a2470", lw=0.7,
                                           alpha=0.85, zorder=6))

    x0, y0, x1, y1 = box
    step = 10 if (x1 - x0) > 60 else 5
    for gx in range(int(x0 // step * step), int(x1) + step, step):
        ax.axvline(gx, color="#d8d8d8", lw=0.4, zorder=0)
    for gy in range(int(y0 // step * step), int(y1) + step, step):
        ax.axhline(gy, color="#d8d8d8", lw=0.4, zorder=0)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xlabel("CAD x  [m]  (absolute)", fontsize=9)
    ax.set_ylabel("CAD y  [m]  (absolute)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title(title, fontsize=13, weight="bold")


def main():
    if not os.path.exists(DXF):
        print(f"missing {DXF}", file=sys.stderr)
        return 1
    print("reading the drawing ...")
    segs = load_segments(DXF)
    print(f"  {len(segs):,} segments")

    cx0, cy0, cx1, cy1 = CELL
    cell = clip(segs, CELL)

    with PdfPages(OUT) as pdf:
        for world, label in ((False, "drawing only"),
                             (True, "with cad_plant.world overlaid")):
            fig, ax = plt.subplots(figsize=(16, 17))
            draw(ax, cell, CELL, world, 0.18,
                 f"FM2 cathode cell — {label}\n"
                 f"x {cx0}..{cx1} m, y {cy0}..{cy1} m")
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

        nx = int(math.ceil((cx1 - cx0) / TILE))
        ny = int(math.ceil((cy1 - cy0) / TILE))
        n = 0
        for j in range(ny):
            for i in range(nx):
                box = (cx0 + i * TILE, cy0 + j * TILE,
                       cx0 + (i + 1) * TILE, cy0 + (j + 1) * TILE)
                tile = clip(segs, box)
                if len(tile) < 40:          # empty floor — not worth a page
                    continue
                fig, ax = plt.subplots(figsize=(14, 14))
                draw(ax, tile, box, True, 0.45,
                     f"tile x {box[0]:.0f}..{box[2]:.0f} m, "
                     f"y {box[1]:.0f}..{box[3]:.0f} m")
                fig.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
                n += 1
        print(f"  {n} detail tiles")

    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
