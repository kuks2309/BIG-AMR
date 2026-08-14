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
  5. every station the deck counts is either placed or knowingly short
  6. every machine is drawn at the size its own constant declares

A failure is not necessarily a bug in the plant. It is a place where our reading
of the drawing is incomplete, and it is worth exactly one question to the
customer. Findings go to `docs/gazebo_world/open-questions.md`.

This exists because check 1 failed the first time it was run, on the four
east-west lanes at the coaters — a contradiction that had been sitting in the
extracted data for a day and that nobody would have noticed until a robot drove
into a wall in simulation.

TWO CORRECTIONS, 2026-08-13. Both made check 1 report things that are not
findings, which is worse than reporting nothing: an audit that cries wolf stops
being read.

  * IT AUDITED LANES THE WORLD DOES NOT DRAW. Checks 1 and 4 walked `P.LANES`,
    which still contains the two rectangles in `EXCLUDED_LANES` — known not to be
    roads and filtered out of the world on the project lead's instruction. So the
    audit reported two coater crossings for paint that does not exist. Both checks
    now walk `P.lanes_drawn()`, the same list the generator draws.
  * IT REPORTED A SETTLED QUESTION AS A FAILURE. The four east-west coater lanes
    that this script was written to catch are now explained: `COATER_X` is the
    coater CELL INCLUDING ITS AGV APRON, and a lane reaching x 124.56 is serving
    the LD station at 125.58 (see plant_cad COATER_LD_X). The crossing is real and
    correct. Check 1 now separates a lane inside a coater CELL, which is expected
    and reported as such, from a lane through a machine BODY, which is still a
    finding.

The second one is the reason the count dropped from 9 findings to 2. Nothing about
the plant changed; the audit stopped miscounting its own resolved questions.

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
    lanes = P.lanes_drawn()
    length, width = P.ROBOT_3_5T[1], P.ROBOT_3_5T[0]
    pads = [(i, x, y, r, footprint(x, y, r, length, width))
            for i, (x, y, r) in enumerate(P.AGV_POSITIONS, 1)]
    failures = 0

    print("=" * 70)
    print("1. lane paint crossing a machine body")
    print("=" * 70)
    # A coater is a CELL, not a body — a lane inside it is the spur serving that
    # coater's LD and ULD stations, both of which sit inside the same span. Split
    # rather than suppressed: the crossings are still listed, under a heading that
    # says which of them is a question.
    hits, expected = [], []
    for i, lane in enumerate(lanes, 1):
        for name, x0, y0, x1, y1 in machines:
            a = overlap(lane, (x0, y0, x1, y1))
            if a > 0.5:
                (expected if name.startswith("CTR") else hits).append(
                    (i, name, a, lane))
    for i, name, a, lane in expected:
        print(f"   cell lane {i:02d} x {lane[0]:7.2f}..{lane[2]:7.2f} "
              f"y {lane[1]:7.2f}..{lane[3]:7.2f}  inside {name}, {a:6.1f} m2")
    if expected:
        print(f"   ^ {len(expected)} inside a coater CELL, which is where that "
              f"coater's\n     stations are. Expected, not a finding "
              f"(plant_cad COATER_LD_X).\n")
    if hits:
        for i, name, a, lane in hits:
            print(f"   FAIL lane {i:02d} x {lane[0]:7.2f}..{lane[2]:7.2f} "
                  f"y {lane[1]:7.2f}..{lane[3]:7.2f}  through {name}, {a:6.1f} m2")
        print(f"\n   {len(hits)} crossings of a machine BODY. Either the footprint"
              f"\n   is smaller than its block bounding box, or the lane passes"
              f"\n   under it.")
        failures += len(hits)
    else:
        print("   ok — no lane runs through a machine body")

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
                for x0, y0, x1, y1 in lanes)
        if d > REACH:
            print(f"   FAIL pad {i:02d} ({px:7.2f},{py:7.2f})  {d:5.2f} m from lane")
            bad += 1
    print("   ok — every position is served by a lane" if not bad else "")
    failures += bad

    print()
    print("=" * 70)
    print("5. deck station counts vs what the world places")
    print("=" * 70)
    # Not a contradiction in the drawing — a gap between what the customer says
    # exists and what we have found. It belongs here because it is the same kind
    # of question as the others and because a shortfall that is only in a document
    # gets forgotten, while one printed by the audit does not.
    placed = P.stations_placed()
    short = 0
    for station, want in P.STATION_COUNTS_DECK.items():
        have = placed.get(station, 0)
        if have >= want:
            print(f"   ok   {station:<13} {have}/{want}")
        else:
            print(f"   SHORT {station:<12} {have}/{want}  "
                  f"{want - have} not placed")
            short += 1
    if short:
        print(f"\n   {short} station type(s) short of the deck [S16]. These are"
              f"\n   unlocated, not missing: the deck says they exist and the"
              f"\n   drawing has not told us where. See open-questions A1, A2.")
        failures += short

    print()
    print("=" * 70)
    print("6. drawn body extent vs the machine's declared size")
    print("=" * 70)
    # THE CHECK THAT WOULD HAVE CAUGHT THE GRAVURE. A gravure was placed 2.82 m
    # wide in an AGV aisle while GRAVURE_SIZE, four screens up in the same file,
    # said 6.9 m. Nothing compared the two, so a machine drawn at 41% of its own
    # width survived on screen until a human looked at it.
    #
    # Every machine here has both a declared size and an extent it is drawn at.
    # They are independent readings of the drawing, so making them agree is
    # exactly the kind of contradiction this script exists for.
    declared = {"ASRS": P.ASRS["size"], "GRV": P.GRAVURE_SIZE,
                "CTR": P.COATER_SIZE, "SLT": P.SLITTER_SIZE}
    bad = 0
    for name, x0, y0, x1, y1 in machines:
        want = declared.get(name if name == "ASRS" else name[:3])
        if want is None:
            continue
        got = (x1 - x0, y1 - y0)
        dw, dl = abs(got[0] - want[0]), abs(got[1] - want[1])
        if dw > 0.5 or dl > 0.5:
            print(f"   FAIL {name:5} drawn {got[0]:6.2f} x {got[1]:6.2f} m, "
                  f"declared {want[0]:6.2f} x {want[1]:6.2f}  "
                  f"(off by {dw:.2f} x {dl:.2f})")
            bad += 1
    if bad:
        print(f"\n   {bad} machine(s) drawn at a size their own constant"
              f"\n   contradicts. One of the two readings is wrong.")
        failures += bad
    else:
        print("   ok — every body matches its declared size within 0.5 m")

    print()
    print("=" * 70)
    print(f"{failures} finding(s) across {len(machines)} machines, "
          f"{len(lanes)} lanes, {len(pads)} positions")
    print(f"  flow: " + " | ".join(f"{leg}->{dst}" for leg, _r, _e, _s, dst, _w
                                   in P.FLOW))
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
