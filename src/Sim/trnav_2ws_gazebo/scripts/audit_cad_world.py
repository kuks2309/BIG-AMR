#!/usr/bin/env python3
"""audit_cad_world.py — does the CAD-derived plant contradict itself?

    ros2 run trnav_2ws_gazebo audit_cad_world.py

Every number in `plant_cad.py` was measured off a drawing independently of every
other number, so nothing has ever forced them to agree. This checks the ones that
MUST agree if the extraction is right:

  1. no painted lane runs through a machine body
  2. no parking position sits inside a machine
  3. no two parking positions overlap when both are occupied
  4. every parking position is within reach of a painted lane

A failure is not necessarily a bug in the plant. It is a place where our reading
of the drawing is incomplete, and it is worth exactly one question to the
customer. Findings go to `docs/gazebo_world/open-questions.md`.

This exists because check 1 failed the first time it was run, on the four
east-west lanes at the coaters — a contradiction that had been sitting in the
extracted data for a day and that nobody would have noticed until a robot drove
into a wall in simulation.

Exit code is 0 always: this reports, it does not gate. There is no CI in this
repository to gate with (see CLAUDE.md).
"""

import math
import sys

from csm import plant_cad as P

#: A parking position is "served" if it is this close to painted lane. Generous
#: on purpose — the question is whether a lane reaches the position at all, not
#: whether the final approach is tidy.
REACH = 3.0

#: Below this, an overlap is two rectangles sharing an edge, not a conflict.
AREA_EPS = 0.05


def overlap(a, b):
    """Shared area of two (x0, y0, x1, y1) rectangles."""
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    return (x1 - x0) * (y1 - y0) if x1 > x0 and y1 > y0 else 0.0


def footprint(px, py, rot_deg, length, width):
    """Axis-aligned extent of a body parked at (px, py) facing rot_deg.

    Axis-aligned rather than the true OBB because every position in the drawing
    is at a multiple of 90 degrees, where the two are identical. If a diagonal
    position ever appears this over-reports and should be replaced with the OBB
    test in sim_acs._footprint.
    """
    c, s = abs(math.cos(math.radians(rot_deg))), abs(math.sin(math.radians(rot_deg)))
    hw = (c * length + s * width) / 2
    hh = (s * length + c * width) / 2
    return (px - hw, py - hh, px + hw, py + hh)


def main():
    machines = P.machines()
    length, width = P.ROBOT_3_5T[1], P.ROBOT_3_5T[0]
    pads = [(i, x, y, r, footprint(x, y, r, length, width))
            for i, (x, y, r) in enumerate(P.AGV_POSITIONS, 1)]
    failures = 0

    print("=" * 70)
    print("1. lane paint crossing a machine body")
    print("=" * 70)
    hits = []
    for i, lane in enumerate(P.LANES, 1):
        for name, x0, y0, x1, y1 in machines:
            a = overlap(lane, (x0, y0, x1, y1))
            if a > 0.5:
                hits.append((i, name, a, lane))
    if hits:
        for i, name, a, lane in hits:
            print(f"   FAIL lane {i:02d} x {lane[0]:7.2f}..{lane[2]:7.2f} "
                  f"y {lane[1]:7.2f}..{lane[3]:7.2f}  through {name}, {a:6.1f} m2")
        print(f"\n   {len(hits)} crossings. Either the machine footprint is smaller"
              f"\n   than its block bounding box, or the lane passes under it.")
        failures += len(hits)
    else:
        print("   ok — no lane runs through a machine")

    print()
    print("=" * 70)
    print("2. parking position inside a machine body")
    print("=" * 70)
    bad = 0
    for i, px, py, rot, fp in pads:
        for name, x0, y0, x1, y1 in machines:
            a = overlap(fp, (x0, y0, x1, y1))
            if a > AREA_EPS:
                print(f"   FAIL pad {i:02d} ({px:7.2f},{py:7.2f}) rot {rot:+6.1f} "
                      f"inside {name} by {a:.2f} m2")
                bad += 1
    print("   ok — every position is clear of the machines" if not bad else "")
    failures += bad

    print()
    print("=" * 70)
    print("3. parking positions that overlap each other")
    print("=" * 70)
    bad = 0
    for a in range(len(pads)):
        for b in range(a + 1, len(pads)):
            o = overlap(pads[a][4], pads[b][4])
            if o > AREA_EPS:
                ia, xa, ya, ra, _ = pads[a]
                ib, xb, yb, rb, _ = pads[b]
                print(f"   FAIL pad {ia:02d} ({xa:7.2f},{ya:7.2f}) rot {ra:+6.1f} and "
                      f"pad {ib:02d} ({xb:7.2f},{yb:7.2f}) rot {rb:+6.1f}"
                      f"  share {o:.2f} m2")
                bad += 1
    if bad:
        print(f"\n   {bad} pair(s). A 3.5T body ({width:.2f} x {length:.2f} m) cannot"
              f"\n   occupy both at once — so they are alternatives, or one of them"
              f"\n   belongs to the smaller 1.5T AGV.")
    else:
        print("   ok — all positions can be occupied simultaneously")
    failures += bad

    print()
    print("=" * 70)
    print(f"4. parking positions further than {REACH:.0f} m from any painted lane")
    print("=" * 70)
    bad = 0
    for i, px, py, rot, _ in pads:
        d = min(math.hypot(max(x0 - px, 0, px - x1), max(y0 - py, 0, py - y1))
                for x0, y0, x1, y1 in P.LANES)
        if d > REACH:
            print(f"   FAIL pad {i:02d} ({px:7.2f},{py:7.2f})  {d:5.2f} m from lane")
            bad += 1
    print("   ok — every position is served by a lane" if not bad else "")
    failures += bad

    print()
    print("=" * 70)
    print(f"{failures} finding(s) across {len(machines)} machines, "
          f"{len(P.LANES)} lanes, {len(pads)} positions")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
