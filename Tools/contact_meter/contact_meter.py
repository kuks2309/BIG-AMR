#!/usr/bin/env python3
"""Measure how close the robots actually get, from outside the code under test.

WHY THIS EXISTS, AND WHY IT IS NOT A ROS NODE.

Robot-to-robot contact produces NO LOG LINE. On 2026-08-24 a four-robot run
reported twenty give-ways completing, zero deadlocks and zero errors, and was
described as clean while amr3 and amr4 were overlapping in the south aisle. The
run log was correct and the conclusion drawn from it was wrong, because the log
has nothing to say about the one thing that matters most.

NEVER VERIFY A MODEL WITH AN INSTRUMENT BUILT ON THAT MODEL. On 2026-08-10 the
proximity meter shared the traffic layer's capsule model and reported "no
contact" while two robots overlapped. So this file imports nothing from `csm`.
It reads pose and body size from the HTTP `/state` endpoint the simulation
already serves, and computes the separation of two oriented rectangles with its
own arithmetic. If the traffic layer's idea of a footprint is wrong, this still
sees the truth.

usage:
    python3 contact_meter.py                        # watch, print every 30 s
    python3 contact_meter.py --url http://host:8080/state
    python3 contact_meter.py --interval 0.2 --report 30 --out contact.log

exit status is 1 if contact was ever measured, so a soak script can fail on it.
"""

import argparse
import collections
import json
import math
import sys
import time
import urllib.request

#: Below this the bodies are touching. Not a tolerance to be relaxed — zero
#: separation between two rectangles IS contact.
CONTACT_M = 0.0

#: The gap the traffic layer promises to hold and has never reliably held. A
#: reading between 0 and this is a near miss, and 2026-08-10 recorded 0.101 m
#: being watched by a person who called it a hit. Treat it as a failure.
MARGIN_M = 0.30


def corners(x, y, yaw, length, width):
    """The four corners of a robot, in world coordinates."""
    c, s = math.cos(yaw), math.sin(yaw)
    return [(x + dx * c - dy * s, y + dx * s + dy * c)
            for dx, dy in ((length / 2, width / 2), (length / 2, -width / 2),
                           (-length / 2, -width / 2), (-length / 2, width / 2))]


def _point_to_segment(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    vx, vy = bx - ax, by - ay
    denominator = vx * vx + vy * vy
    t = 0.0 if denominator < 1e-12 else \
        max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / denominator))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def _penetration_depth(pa, pb):
    """How deep two convex polygons overlap, or None if they are apart.

    Separating axis theorem: project both polygons onto each edge normal. One
    axis with no overlap proves they are apart. If every axis overlaps, the
    SMALLEST of those overlaps is how far one would have to move to separate
    them — the honest measure of how bad a hit was.

    The corner-to-edge distance used for the apart case CANNOT do this job.
    Two identical boxes lying on top of each other have every corner sitting
    exactly on an edge, so that measure reads 0.000 — indistinguishable from a
    graze. A meter that reports a total overlap as "just touching" understates
    precisely the case worth knowing about, which is why this is separate.
    """
    smallest = float("inf")
    for poly in (pa, pb):
        for i in range(len(poly)):
            ax, ay = poly[i]
            bx, by = poly[(i + 1) % len(poly)]
            nx, ny = -(by - ay), bx - ax
            length = math.hypot(nx, ny)
            if length < 1e-12:
                continue
            nx, ny = nx / length, ny / length
            a_projected = [nx * px + ny * py for px, py in pa]
            b_projected = [nx * px + ny * py for px, py in pb]
            overlap = min(max(a_projected), max(b_projected)) - \
                max(min(a_projected), min(b_projected))
            if overlap <= 0.0:
                return None                   # a separating axis: they are apart
            smallest = min(smallest, overlap)
    return smallest


def body_gap(a, b, length, width):
    """Metres between two robot footprints. Negative means overlapping.

    `a` and `b` are (x, y, yaw). A positive value is the true Euclidean gap.
    A negative value is the penetration depth — how far apart they would have
    to be pushed to stop touching.
    """
    ca, cb = corners(*a, length, width), corners(*b, length, width)
    depth = _penetration_depth(ca, cb)
    if depth is not None:
        return -depth
    return min(_point_to_segment(p, poly[i], poly[(i + 1) % 4])
               for pts, poly in ((ca, cb), (cb, ca))
               for p in pts for i in range(4))


def sample(url, timeout=3.0):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8080/state")
    parser.add_argument("--interval", type=float, default=0.2,
                        help="seconds between samples (default 0.2 = 5 Hz)")
    parser.add_argument("--report", type=float, default=30.0,
                        help="seconds between running-minimum lines")
    parser.add_argument("--out", default="",
                        help="also append every line to this file")
    args = parser.parse_args()

    log = open(args.out, "a", buffering=1) if args.out else None

    def say(line):
        stamped = f"{time.strftime('%H:%M:%S')} {line}"
        print(stamped, flush=True)
        if log:
            log.write(stamped + "\n")

    worst = {}                  # pair -> smallest gap ever seen
    worst_pose = {}             # pair -> the poses at that moment
    contacts = 0
    margin_breaches = 0
    reported = collections.defaultdict(lambda: "clear")   # pair -> level now
    samples = 0
    next_report = time.time() + args.report

    say(f"contact meter on {args.url} — contact <= {CONTACT_M:.2f} m, "
        f"margin < {MARGIN_M:.2f} m")

    while True:
        try:
            state = sample(args.url)
        except Exception as exc:                      # the sim may not be up yet
            time.sleep(max(args.interval, 1.0))
            if samples == 0:
                say(f"waiting for the simulation ({exc.__class__.__name__})")
            continue

        length, width = state["plant"]["robot_size"]
        robots = [(r["name"], r["position"][0], r["position"][1], r["yaw"])
                  for r in state["fleet"] if r.get("position")]
        samples += 1

        for i in range(len(robots)):
            for j in range(i + 1, len(robots)):
                na, xa, ya, wa = robots[i]
                nb, xb, yb, wb = robots[j]
                gap = body_gap((xa, ya, wa), (xb, yb, wb), length, width)
                pair = (na, nb)

                if pair not in worst or gap < worst[pair]:
                    worst[pair] = gap
                    worst_pose[pair] = ((xa, ya, wa), (xb, yb, wb))

                # WHAT LEVEL THIS PAIR IS AT NOW, not merely "reported before".
                #
                # A single `reported_pairs` set was a real defect in this file:
                # a pair that tripped MARGIN was added to it, so when the same
                # pair went on to TOUCH, the contact was suppressed and never
                # counted. On 2026-08-24 it printed `contacts=0` through an
                # actual collision, and only the running minimum gave it away.
                # An instrument whose headline number hides the worst case is
                # worse than no instrument, because it gets quoted.
                level = "contact" if gap <= CONTACT_M else \
                        ("margin" if gap < MARGIN_M else "clear")
                was = reported[pair]
                if level == "clear":
                    reported[pair] = "clear"
                elif level != was:
                    # Report on entry, and again on ESCALATION margin -> contact.
                    reported[pair] = level
                    if level == "contact":
                        contacts += 1
                        say(f"CONTACT  {na} <-> {nb}  gap {gap:+.3f} m   "
                            f"{na}({xa:+.2f},{ya:+.2f},yaw {wa:+.2f})  "
                            f"{nb}({xb:+.2f},{yb:+.2f},yaw {wb:+.2f})")
                    else:
                        margin_breaches += 1
                        # POSITIONS TOO. CONTACT lines carried them and MARGIN
                        # lines did not, so a near miss could be seen but not
                        # located — on 2026-08-25 that cost a wrong diagnosis
                        # (blamed on dock spacing; it was the shared lay-by).
                        say(f"MARGIN   {na} <-> {nb}  gap {gap:.3f} m "
                            f"(< {MARGIN_M:.2f})   "
                            f"{na}({xa:+.2f},{ya:+.2f},yaw {wa:+.2f})  "
                            f"{nb}({xb:+.2f},{yb:+.2f},yaw {wb:+.2f})")

        if time.time() >= next_report:
            next_report = time.time() + args.report
            closest = sorted(worst.items(), key=lambda kv: kv[1])[:3]
            summary = "  ".join(f"{a}<->{b} {g:+.2f}" for (a, b), g in closest)
            say(f"[{samples} samples] contacts={contacts} "
                f"margin_breaches={margin_breaches}  closest: {summary}")

        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    sys.exit(0)
