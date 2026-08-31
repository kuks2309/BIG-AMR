#!/usr/bin/env python3
"""Render a recorded run as a top-down video, so a run can be WATCHED back.

WHY THIS EXISTS
===============
A jam takes 20-45 minutes of wall clock to appear and nobody can sit in front
of Gazebo waiting for it. `replay.py` answers "which rule stopped this robot",
which is the right question once you know where to look — but it is a table of
numbers, and it cannot show you a robot slowly rotating in place, or a queue
forming, or the shape of a manoeuvre going wrong.

This draws the plant and the robots from the same trace and writes an mp4. No
Gazebo, no waiting: an hour of run renders in a couple of minutes and can be
scrubbed, paused and shared.

    # the whole run
    python3 Tools/replay/render.py

    # the 60 s around a jam the watchdog reported
    python3 Tools/replay/render.py --at 1039 --window 40 --after 20

    # slower, for a manoeuvre you want to study
    python3 Tools/replay/render.py --at 1039 --window 20 --speed 0.25

WHAT IS DRAWN. Machines as solid blocks, both lane rings with direction
arrows, spurs, every robot as a body-shaped rectangle at its true heading,
with its name and — when it is stopped — the rule that stopped it. A robot
halted by a traffic rule is drawn red, one that is simply working is green.

It is the SAME trace `replay.py` reads, so what you watch and what the rule
table says cannot disagree.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "src", "MES", "csm"))

import matplotlib                                            # noqa: E402
matplotlib.use("Agg")
import matplotlib.patches as mpatches                        # noqa: E402
import matplotlib.pyplot as plt                              # noqa: E402

from csm import plant                                        # noqa: E402
from csm.adapters import roads                               # noqa: E402

#: The same words `replay.py` calls traffic, kept in step by importing them.
sys.path.insert(0, HERE)
from replay import TRAFFIC_HALTS, is_traffic_halt            # noqa: E402,F401

def agv(text):
    """Rewrite `amr8` as `1C4` wherever it appears.

    The halt reasons are built in `sim_acs` and name ROS nodes, which is right
    for a log line and wrong for anything a person reads.
    """
    if not text:
        return text
    for name in sorted(plant.ROBOT_SEGMENT, key=len, reverse=True):
        num = plant.agv_number(name)
        if num:
            text = text.replace(name, num)
    return text


BG, INK, DIM = "#11151c", "#e6edf3", "#3d4757"
INNER, OUTER, SPUR = "#4f9dfb", "#e8a33d", "#4caf6d"
BUSY, STUCK, IDLE = "#4caf6d", "#e05252", "#7d8899"


def _wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def load(path, lo=None, hi=None):
    out = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if lo is not None and d["t"] < lo:
                continue
            if hi is not None and d["t"] > hi:
                break
            out.append(d)
    return out


def newest_trace():
    logs = [os.path.join("Log", f) for f in os.listdir("Log")
            if f.startswith("trace_") and f.endswith(".jsonl")]
    if not logs:
        sys.exit("no Log/trace_*.jsonl")
    return max(logs, key=os.path.getmtime)


def draw_plant(ax):
    """Everything that never moves: machines, lanes, docks."""
    net = roads.build()
    for a, b in net.lanes:
        (x1, y1), (x2, y2) = net.nodes[a], net.nodes[b]
        spur = a.startswith(("dock_", "park_")) or b.startswith(("dock_", "park_"))
        # The two rings run at fixed y; anything else is a spur or a ring change.
        colour = SPUR if spur else (INNER if abs(y1 - y2) < 1e-6 and
                                    abs(y1 - plant.AISLE_S_Y) > 1e-6 else OUTER)
        ax.plot([x1, x2], [y1, y2], color=colour, lw=0.8, alpha=0.5, zorder=1)

    for name, st in plant.STATIONS.items():
        if not st["solid"]:
            continue
        mx, my = st["machine"]
        ax.add_patch(mpatches.Rectangle(
            (mx - plant.MACHINE_W / 2, my - plant.MACHINE_D / 2),
            plant.MACHINE_W, plant.MACHINE_D,
            facecolor="#242c38", edgecolor=DIM, lw=0.8, zorder=2))
        ax.text(mx, my, name, color="#8b97a8", fontsize=5.5,
                ha="center", va="center", zorder=3)

    for name, (dx, dy) in plant.DOCKS.items():
        ax.plot(dx, dy, "o", ms=2.0, color=DIM, zorder=3)


def body(ax, x, y, yaw, colour, label, reason, row=0,
         on_lane=True):
    """One robot, at its true size and heading."""
    L, W = plant.ROBOT_L, plant.ROBOT_W
    c, s = math.cos(yaw), math.sin(yaw)
    # corners of the body in the world, so the drawing is the footprint the
    # contact meter measures -- not a dot that hides overlap.
    ax.add_patch(mpatches.Rectangle(
        (x - (L / 2) * c + (W / 2) * s, y - (L / 2) * s - (W / 2) * c),
        L, W, angle=math.degrees(yaw),
        facecolor=colour, edgecolor="white", lw=0.6, alpha=0.9, zorder=5))
    # a nose mark, so a rotating robot is obvious
    ax.plot([x, x + c * L * 0.62], [y, y + s * L * 0.62],
            color="white", lw=0.9, zorder=6)
    ax.text(x, y + W * 0.9, label, color=INK, fontsize=5.5,
            ha="center", va="bottom", zorder=6)
    if reason:
        # STAGGERED, and on a dark plate. Two robots stopped on each other are
        # by definition close together, so their reasons land on top of one
        # another exactly when both need reading.
        ax.text(x, y - W * 0.9 - 1.5 * (row % 3), reason[:38],
                color="#ffc4c4", fontsize=4.6, ha="center", va="top", zorder=7,
                bbox=dict(boxstyle="square,pad=0.15", facecolor=BG,
                          edgecolor="none", alpha=0.85))

    # HOW FAR OFF ITS LANE THIS ROBOT IS POINTING.
    #
    # A robot stopped at an angle across a lane blocks it, and nothing in the
    # halt reason says so. Measured 2026-08-31: amr8 sat at yaw 123 deg on the
    # inner lane, 57 deg off the direction of travel, with `_turning` False --
    # so no rule knew it was lying across the road, and amr3 queued behind it.
    off = min(abs(_wrap(yaw)), abs(_wrap(yaw - math.pi)))
    if on_lane and off > math.radians(25.0):
        ax.text(x, y + W * 0.9 + 1.2, f"{math.degrees(off):.0f}deg off lane",
                color="#ffd479", fontsize=4.6, ha="center", va="bottom",
                zorder=7)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--trace")
    ap.add_argument("--at", type=float, help="centre the window here")
    ap.add_argument("--window", type=float, default=40.0, help="seconds before")
    ap.add_argument("--after", type=float, default=10.0, help="seconds after")
    ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--speed", type=float, default=1.0,
                    help="1.0 = real time, 0.25 = quarter speed")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    path = args.trace or newest_trace()
    lo = hi = None
    if args.at is not None:
        lo, hi = args.at - args.window, args.at + args.after
    ticks = load(path, lo, hi)
    if not ticks:
        sys.exit("nothing in that window")

    span = ticks[-1]["t"] - ticks[0]["t"]
    # Take only as many cycles as the frame rate needs, so an hour of trace at
    # 30 Hz does not become 100,000 frames.
    want = max(1, int(span * args.fps / max(args.speed, 1e-6)))
    step = max(1, len(ticks) // want)
    frames = ticks[::step]
    out = args.out or os.path.join(
        "Log", os.path.basename(path).replace("trace_", "run_")
                                     .replace(".jsonl", ".mp4"))
    print(f"{path}: {len(ticks)} cycles over {span:.0f}s "
          f"-> {len(frames)} frames -> {out}")

    tmp = tempfile.mkdtemp(prefix="render_")
    try:
        for i, tick in enumerate(frames):
            fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100)
            fig.patch.set_facecolor(BG)
            ax.set_facecolor(BG)
            draw_plant(ax)
            halted = 0
            for r in tick["fleet"]:
                x, y, yaw = r["pose"]
                reason = r.get("_halt_reason") or ""
                v = math.hypot(*r["vel"])
                if v < 0.03 and is_traffic_halt(reason):
                    colour, halted = STUCK, halted + 1
                elif r.get("busy") or r.get("_homing"):
                    colour = BUSY
                else:
                    colour = IDLE
                body(ax, x, y, yaw, colour,
                     plant.agv_number(r["name"]) or r["name"],
                     agv(reason) if v < 0.03 else "",
                     on_lane=bool(r.get("busy") or r.get("_homing")),
                     row=len(tick["fleet"]) and
                     [q["name"] for q in tick["fleet"]].index(r["name"]))
            ax.set_xlim(plant.HALL_W - 1, plant.HALL_E + 1)
            ax.set_ylim(plant.HALL_S - 1, plant.HALL_N + 1)
            ax.set_aspect("equal")
            ax.axis("off")
            ax.set_title(f"t = {tick['t']:8.1f} s     "
                         f"{halted} robot(s) stopped by a traffic rule",
                         color=INK, fontsize=10, loc="left")
            fig.savefig(os.path.join(tmp, f"f{i:06d}.png"),
                        facecolor=BG, bbox_inches="tight", pad_inches=0.1)
            plt.close(fig)
            if i % 50 == 0:
                print(f"  {i}/{len(frames)}", flush=True)

        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(args.fps),
             "-i", os.path.join(tmp, "f%06d.png"),
             "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", out],
            check=True)
        print(f"wrote {out}  ({os.path.getsize(out) / 1e6:.1f} MB)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
