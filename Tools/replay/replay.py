#!/usr/bin/env python3
"""Put the traffic rules back through a recorded moment, without Gazebo.

WHY THIS EXISTS
===============
On 2026-08-31 two jams took 28.5 and 47 minutes of wall clock to appear, and
neither was reproducible on demand. Every attempt to test a fix cost half an
hour and might not reproduce at all. Meanwhile the STATE log could not answer
"which rule stopped this robot" — it samples every 3.5 s and, for a robot
driving home, printed nothing but the word `idle`.

So `SimAcs` now writes `Log/trace_*.jsonl`, one line per control cycle,
carrying every field the rules read. This loads any window of that file and
asks each rule what it decides, tick by tick.

    # what was every rule saying in the ten seconds before amr3 stopped?
    python3 Tools/replay/replay.py --at 1788152934 --window 10

    # just two robots, and only the ticks where something changed
    python3 Tools/replay/replay.py --at 1788152934 --only amr2,amr3 --changes

    # where did the fleet first stop and stay stopped?
    python3 Tools/replay/replay.py --find-jam

IT IS THE REAL RULES. Nothing is reimplemented here: the recorded fields are
put back onto real `SimRobot` objects and the real methods are called. A rule
that changes changes here too, which is the whole point — edit a rule, replay
the same ten seconds, see whether the robot still stops.

WHAT IT CANNOT DO. It does not re-simulate. Positions are what they were, so
this answers "what did the rules decide about this situation", not "what would
have happened next". For the second question, change the rule and run the sim.
"""
import argparse
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "src", "MES", "csm"))

try:
    from csm import plant                                    # noqa: E402,F401
    from csm.adapters.sim_acs import SimAcs, SimRobot        # noqa: E402
except ModuleNotFoundError as exc:
    # sim_acs imports the ROS message types, so the workspace has to be on the
    # path. Saying so beats a bare ImportError, because the fix is one line and
    # nothing about "No module named trnav_msgs" suggests it.
    sys.exit(f"{exc}\n\nSource the workspace first:\n"
             "    source /opt/ros/humble/setup.bash\n"
             "    source install/setup.bash")


class Fleet:
    """Only what the rules ask of a fleet: who else is out there."""

    def __init__(self, robots):
        self.robots = robots


def rebuild(row, fleet):
    """A SimRobot carrying exactly what was recorded, and nothing invented.

    Built without __init__ on purpose — the real one needs a live ROS node,
    publishers and subscriptions, none of which a rule reads.
    """
    r = object.__new__(SimRobot)
    r.name = row["name"]
    r.pose = tuple(row["pose"])
    r.vel = tuple(row["vel"])
    r.fleet = fleet
    r.node = None
    for f in SimAcs.TRACE_FIELDS:
        v = row.get(f)
        if f in ("_goal", "_pause_goal", "_exit_goal") and v is not None:
            v = tuple(v)
        if f in ("_waypoints", "_home_waypoints") and v is not None:
            v = [tuple(p) for p in v]
        setattr(r, f, v)
    r._stall_ref = r._stall_since = None
    r._noted_hold = False
    return r


#: What to ask, and in what order. Each entry is (label, callable) and every
#: one of them is a REAL method — see the module docstring.
def verdicts(r):
    out = {}
    try:
        out["on_spur"] = r._on_a_spur()
    except Exception as exc:                     # a rule that raises is news
        out["on_spur"] = f"!{type(exc).__name__}"
    try:
        c = r._crossing()
        out["crossing"] = round(c[1], 2) if c else None
    except Exception as exc:
        out["crossing"] = f"!{type(exc).__name__}"
    try:
        out["held_r2"] = bool(r._held_for_a_leaver())
    except Exception as exc:
        out["held_r2"] = f"!{type(exc).__name__}"
    try:
        station = r._target_station()
        leaver = r._neighbour_leaving(station)
        out["rule7"] = leaver.name if leaver else None
    except Exception as exc:
        out["rule7"] = f"!{type(exc).__name__}"
    try:
        t = r._threat()
        out["layer1"] = t.name if t else None
    except Exception as exc:
        out["layer1"] = f"!{type(exc).__name__}"
    try:
        g = r._goal
        if g is not None:
            f = r._ahead_in_my_lane(r.pose[0], r.pose[1],
                                    g[0] - r.pose[0], g[1] - r.pose[1])
            out["follow3m"] = f.name if f else None
        else:
            out["follow3m"] = None
    except Exception as exc:
        out["follow3m"] = f"!{type(exc).__name__}"
    return out


def load(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass                  # a half-written last line is normal
    return rows


def newest_trace():
    logs = [os.path.join("Log", f) for f in os.listdir("Log")
            if f.startswith("trace_") and f.endswith(".jsonl")]
    if not logs:
        sys.exit("no Log/trace_*.jsonl — run the sim with CSM_TRACE unset")
    return max(logs, key=os.path.getmtime)


#: Halt reasons that mean TRAFFIC — one robot waiting on another.
#:
#: The discriminator that matters. A robot dwelling at a port, waiting in a
#: dock for its next job, or charging is motionless for twenty seconds at a
#: time and is perfectly healthy; without this the first "jam" found is always
#: a robot doing its job properly.
TRAFFIC_HALTS = ("3 m rule", "layer 1", "rule 7", "rule 3",
                 "pausing before the road", "holding —", "holding -",
                 "entry refused", "machine has not granted entry",
                 "homing: robot ahead")


def is_traffic_halt(reason):
    return bool(reason) and any(h in reason for h in TRAFFIC_HALTS)


def find_jam(ticks, still=0.03, seconds=10.0):
    """The first moment two or more robots are stopped ON EACH OTHER.

    Three conditions, and all three are needed:

      1. the robot has somewhere to go  — a parked one is not stuck
      2. it is not moving                — `still` is m/s; 0.01 m/s is stuck
      3. its halt reason is a TRAFFIC one — see `TRAFFIC_HALTS`

    Without (3) this fires on every robot dwelling at a port, which is most of
    them, most of the time.
    """
    frozen_since = {}
    for tick in ticks:
        t = tick["t"]
        stopped = set()
        for row in tick["fleet"]:
            # A ROBOT WITH NOWHERE TO GO IS NOT STUCK. Ten robots parked in
            # their bays at startup are motionless for minutes, and without
            # this the first "jam" found is always t=0.
            trying = row.get("busy") or row.get("_homing")
            if not trying or not is_traffic_halt(row.get("_halt_reason")):
                frozen_since.pop(row["name"], None)
                continue
            if math.hypot(*row["vel"]) <= still:
                stopped.add(row["name"])
                frozen_since.setdefault(row["name"], t)
            else:
                frozen_since.pop(row["name"], None)
        held = [n for n in stopped
                if t - frozen_since.get(n, t) >= seconds]
        if len(held) >= 2:
            return min(frozen_since[n] for n in held), sorted(held)
    return None, []


def watch(path, window, poll, hold, out_dir):
    """Follow a running trace and report each jam as it forms.

    WHY. A jam takes 20-45 minutes of wall clock to appear and nobody can sit
    watching Gazebo for that. This reads the trace as it is written, and the
    moment two robots have been stopped on each other for `hold` seconds it
    prints the replay and saves it. Leave it running and read the report.

    Reports are written to `out_dir` so a jam found overnight is still there
    in the morning.
    """
    os.makedirs(out_dir, exist_ok=True)
    offset, ticks, seen = 0, [], set()
    print(f"watching {path}\n  jam = 2+ robots stopped on each other for "
          f"{hold:.0f}s\n  reports -> {out_dir}/\n")
    while True:
        with open(path) as fh:
            fh.seek(offset)
            fresh = fh.read()
            offset = fh.tell()
        if fresh:
            # A partial last line is normal on a live file: keep it for the
            # next pass rather than dropping the cycle.
            lines = fresh.split("\n")
            if not fresh.endswith("\n"):
                offset -= len(lines[-1].encode())
                lines = lines[:-1]
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        ticks.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            ticks = ticks[-60000:]              # roughly the last hour

        at, who = find_jam(ticks, seconds=hold)
        key = (round(at, 1), tuple(who)) if at is not None else None
        if key is not None and key not in seen:
            seen.add(key)
            stamp = time.strftime("%H%M%S")
            report = os.path.join(out_dir, f"jam_{stamp}.txt")
            lines = render(ticks, at, window, 2.0, set(who))
            head = (f"JAM at t={at:.1f}  {', '.join(who)}"
                    f"   (found {time.strftime('%H:%M:%S')})")
            with open(report, "w") as fh:
                fh.write(head + "\n" + "\n".join(lines) + "\n")
            print("\n" + head)
            for ln in lines:
                print(ln)
            print(f"  -> {report}\n")
        time.sleep(poll)


def render(ticks, at, window, after, want, changes=True):
    """The replay table, as a list of lines. Shared by --at and --watch."""
    lo, hi = at - window, at + after
    out = [f"{'t':>8}  {'robot':6} {'pos':>16} {'v':>5}  "
           f"spur cross held_r2 rule7      layer1     follow3m   halt"]
    last = {}
    for tick in ticks:
        t = tick["t"]
        if not lo <= t <= hi:
            continue
        robots = []
        fleet = Fleet(robots)
        allr = {row["name"]: rebuild(row, fleet) for row in tick["fleet"]}
        robots.extend(allr.values())
        for row in tick["fleet"]:
            if want is not None and row["name"] not in want:
                continue
            r = allr[row["name"]]
            v = verdicts(r)
            key = (tuple(sorted(v.items())), r._halt_reason)
            if changes and last.get(row["name"]) == key:
                continue
            last[row["name"]] = key
            out.append(f"{t:8.1f}  {r.name:6} "
                       f"({r.pose[0]:+6.2f},{r.pose[1]:+6.2f}) "
                       f"{math.hypot(*r.vel):5.2f}  "
                       f"{str(v['on_spur']):5} {str(v['crossing']):5} "
                       f"{str(v['held_r2']):7} {str(v['rule7']):10} "
                       f"{str(v['layer1']):10} {str(v['follow3m']):10} "
                       f"{r._halt_reason or ''}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--trace", help="default: the newest Log/trace_*.jsonl")
    ap.add_argument("--at", type=float, help="centre of the window")
    ap.add_argument("--window", type=float, default=10.0,
                    help="seconds BEFORE --at to replay (default 10)")
    ap.add_argument("--after", type=float, default=2.0,
                    help="seconds after --at as well (default 2)")
    ap.add_argument("--only", help="comma-separated robot names")
    ap.add_argument("--changes", action="store_true",
                    help="print a robot only when a verdict changes")
    ap.add_argument("--find-jam", action="store_true",
                    help="locate the first sustained multi-robot stop")
    ap.add_argument("--watch", action="store_true",
                    help="follow a running trace and report jams as they form")
    ap.add_argument("--poll", type=float, default=10.0,
                    help="seconds between passes while watching")
    ap.add_argument("--hold", type=float, default=15.0,
                    help="seconds stopped before it counts as a jam")
    ap.add_argument("--reports", default="Log/jams",
                    help="where --watch saves its reports")
    args = ap.parse_args()

    path = args.trace or newest_trace()
    if args.watch:
        return watch(path, args.window, args.poll, args.hold, args.reports)
    ticks = load(path)
    if not ticks:
        sys.exit(f"{path} is empty")
    print(f"{path}: {len(ticks)} cycles, "
          f"{ticks[-1]['t'] - ticks[0]['t']:.0f} s"
          + (f", wall {ticks[0].get('wall', 0):.0f}..{ticks[-1].get('wall', 0):.0f}"
             if ticks[0].get("wall") else ""))

    at = args.at
    if args.find_jam or at is None:
        at, who = find_jam(ticks)
        if at is None:
            sys.exit("no sustained multi-robot stop found")
        print(f"first jam at {at:.1f} — {', '.join(who)}")
        if args.find_jam and args.at is None and not args.only:
            args.only = ",".join(who)

    want = set(args.only.split(",")) if args.only else None
    print(f"\nreplaying {at - args.window:.1f} .. {at + args.after:.1f}"
          + (f"  ({args.only})" if args.only else ""))
    for line in render(ticks, at, args.window, args.after, want, args.changes):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
