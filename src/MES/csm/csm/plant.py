"""plant — the factory, as the customer documents describe it.

SINGLE SOURCE OF TRUTH. The station list, the material flow and the AGV class
assignment all live here; roads.py builds lanes from it, sim_acs drives to it,
sim_node raises jobs against it, and the Gazebo world is generated from it. When
the plant changes, this file changes and everything else follows.

=============================================================================
SOURCES  (meeting_files/)
=============================================================================
[S7]   system deck slide 7    — process chain
[S16]  system deck slide 16   — Big AGV material flow, AGV classes, port counts
[S39]  system deck slide 39   — AGV route map: long aisles, perpendicular spurs
[IP]   "IP Address Summary for the Entire Line_20260506_KR.xlsx",
       sheet "FM2 Front-end" — every PLC-connected docking port on the line
[PROT] "AGV与主机设备对接流程及协议.xlsx" — one sheet per LD / ULD station:
       凹版机上料工位 (gravure LOADING), 凹版机下料工位 (gravure UNLOADING),
       涂布机上料工位 / 下料工位 (coater loading / unloading), 冷压机 (cold press)
[TR]   meeting-20260804-165629.txt — WIP buffers are optional overflow;
       gluing is a 30 s step the CSM must know about and the ACS must not

=============================================================================
WHAT IS DOCUMENTED
=============================================================================
Process chain [S7]:

    ASRS -> Gravure Print -> Coating -> Slitting -> Calendering
         -> Cold Press -> Ear Forming -> Winding

Every machine has SEPARATE loading and unloading ports [IP][PROT]. Gravure and
Coater are listed as "Unwinder / Rewinder" pairs; Slitter, Calendering, Pressing
and Ear Forming are listed as explicit LD / ULD ports.

Big AGV material flow [S16] — robots are segmented, NOT a shared pool:

    1.5T-Big AGV A  x2 :  ASRS         -> Gravure LD    (WIP Gravure optional)
    1.5T-Big AGV B  x2 :  Gravure ULD  -> Coater LD     (WIP Coater optional)
    3.5T-Big AGV    x6 :  Coater ULD   -> Slitter LD    (WIP Slitter optional)

Port counts [S16][IP]: ASRS 1, Gravure 4 (LD+ULD each), Coater 4 (LD+ULD each),
Slitter 4 LD, WIP Gravure 2, WIP Coater 4.

=============================================================================
WHAT IS ASSUMED, AND WHY
=============================================================================
The documents give topology, inventory and flow. They do NOT give metric
coordinates in any form recoverable from the decks — the layouts are dense CAD
images without a legible scale. Everything geometric below is therefore an
assumption, chosen to match the SHAPE the route map [S39] shows: long parallel
aisles with perpendicular docking spurs, not a loop around an open floor.

  A1  Two machine rows facing one another across a central aisle pair. [S39]
      shows exactly this comb-on-a-corridor arrangement.
  A2  Gravure on the north row, Coater on the south row, so the AGV B segment
      (Gravure ULD -> Coater LD) crosses between them and the A and C segments
      each stay on one side. This keeps the three AGV classes apart, which is
      what [S16] achieves by assigning classes to segments at all.
  A3  ASRS at the west end of the north row, Slitter at the west end of the
      south row — chain order runs west to east and back.
  A4  6.0 m between machine centres; LD and ULD ports 1.2 m either side of the
      machine centre. Big enough for a 1.6 x 0.9 m AGV to dock without fouling
      its neighbour.
  A5  Machine footprint 3.0 x 2.0 m. Roll-handling equipment; no dimension is
      given anywhere in the files.
  A6  Aisle 5.0 m clear of the machine faces, dock points 2.2 m in front of the
      face. Two AGVs must be able to pass while a third is docked.

  SCOPE: only the Big AGV segment of the line is modelled — ASRS through
  Slitter LD. Calendering, Pressing, Ear Forming and Winding are served by the
  Small AGV fleet (64 units, [S16][TR]) and are out of scope for a 3-robot
  simulation. Anode is omitted; the front end is duplicated cathode/anode [IP]
  and one side is enough to exercise the logic.
"""

import math
import re

# ---------------------------------------------------------------- geometry

#: UNIFORM PLANT SCALE. Multiplies every PLANT dimension and leaves the ROBOT
#: alone, so a bigger hall means more room per robot rather than a bigger robot
#: in the same room.
#:
#: WHY IT EXISTS. On 2026-08-24 the slitter's four docking ports were measured
#: at a 2.00 m pitch while every other LD/ULD pair in the plant uses 2.40 m. A
#: 1.6 x 0.9 m robot turning to dock beside a parked one needs 2.02 m
#: (half-diagonal 0.918 + half-length 0.80 + the 0.30 margin), so two adjacent
#: slitter docks could not both be used: measured body gap 0.19 m, and layer 1
#: stopped the arriving robot 0.8 m short of its goal for 72 seconds.
#:
#: WHAT SCALES AND WHAT DOES NOT. Everything below this line that is a distance
#: in the building scales. `ROBOT_L`/`ROBOT_W` and everything derived from them
#: — PARK_SPUR, PARK_PITCH, ROW_MIN_GAP, the docking tolerances — do not, and
#: neither do the traffic clearances in sim_acs.py (STOP_GAP, SIDESTEP,
#: PATH_CLEARANCE, PASSING_GAP). Those are properties of the vehicle and of the
#: margin we refuse to close; scaling them would move the goalposts with the
#: pitch and measure nothing.
#:
#: 1.20 is not a guess: it lifts the slitter's 2.00 m pitch to 2.40 m, which is
#: the spacing the rest of the plant already uses and already works at.
#:
#: THE COST IS TRAVEL. Every route grows by this factor, and route length is
#: what broke the one-way-aisle change of 2026-08-07 — segment B went from 12
#: to 24 waypoints and its robot never arrived. Expect deliveries per minute to
#: fall by roughly (SCALE - 1). Judge a scaled run on deliveries/min, not on
#: deliveries.
SCALE = 1.20


def _s(value):
    """Scale one plant dimension. Lists and tuples scale element-wise."""
    if isinstance(value, (list, tuple)):
        return type(value)(_s(v) for v in value)
    return value * SCALE

HALL_W, HALL_E = _s(-27.0), _s(26.2)     # hall extent in x (assumption A1)
#: West edge moved out from -25.0 on 2026-08-21, by the SAME 1.6 m the west
#: aisle moved. Parking hangs off the aisle (`PARK_X = AISLE_W_X - PARK_SPUR`),
#: so a wall that moved less would fix the corner by squeezing the bays; at
#: -26.6 a parked robot keeps the 1.50 m of wall clearance it had before.
HALL_S, HALL_N = _s(-15.0), _s(13.0)     # hall extent in y
#: South edge moved out from -13.0 on 2026-08-18. Leg C has six 3.5T robots
#: (specification fleet table) and its queue runs south from the east cross
#: aisle; the sixth slot landed 0.25 m inside the wall's robot-radius pad. The
#: alternative was to shave the clearance between slots until six fitted, which
#: is fitting the robot to the drawing rather than the drawing to the robot.
#: North is unchanged: leg B has two robots and needs 3.65 m.
WALL_T = _s(0.2)

MACHINE_W, MACHINE_D = _s(3.0), _s(2.0)        # A5
MACHINE_PITCH = _s(6.0)                    # A4
PORT_OFFSET = _s(1.2)                      # A4: LD/ULD either side of centre

ROW_N_Y = _s(8.0)                          # north machine row centre
ROW_S_Y = _s(-8.0)                         # south machine row centre
#: A6: how far in front of the machine face the lane network hands over to
#: docking. This is a THROUGHPUT number, not a clearance one.
#:
#: The crab closes from here to DOCK_TARGET at 0.10 m/s under a P law, so the
#: distance sets the dock time directly: 2.2 m took ~30 s, and a job has to fit
#: TWO docks inside its 120 s budget plus the travel between them. It did not —
#: every delivery dock was still closing when the job timed out, so no job ever
#: completed, no gravure ever produced output, and amr2 and amr3 were starved of
#: work entirely. Measured: 3 successful collections, ZERO deliveries.
#:
#: 1.5 m closes in ~23 s and still leaves 0.58 m of clearance for the robot to
#: square up at the hand-over, against a 0.918 m half-diagonal.
DOCK_INSET = _s(1.5)
AISLE_N_Y = _s(3.0)                        # north aisle
AISLE_S_Y = _s(-3.0)                       # south aisle
#: Moved west from -20.0 on 2026-08-21, together with `_SLT_PORT_X0` below.
#: NEITHER CHANGE WORKS ALONE and both were tried that way first:
#:   moving only the road   — the slitter ports are measured FROM the road, so
#:                            they move with it and the corner gap is unchanged
#:   moving only the offset — the ports slide east into CTR1_LD, and the gap
#:                            at that end drops to 0.30 m
#: The south row between the corner and CTR1_LD needs 9.80 m — four ports at a
#: 2.0 m pitch, plus 1.90 m of clearance at each end — and at -20.0 it had
#: 8.80 m. It did not fit. This is the metre it was short.
AISLE_W_X = _s(-22.0)                      # west cross aisle
#: Moved east from 22.0 on 2026-08-21: `WIP_SLT_2` sat 1.80 m from the corner
#: and two robots need 1.90 m. The same fault as the west end, mirrored, and
#: found only because `_check_row` was written to look for it.
AISLE_E_X = _s(22.2)                       # east cross aisle
#: THE ROBOT ITSELF, because the layout has to be big enough for it.
#: 1.6 x 0.9 m is the simulated chassis. (The deck gives 1.3 x 1.9 m for the
#: 1.5T and 1.6 x 2.0 m for the 3.5T; the sim models one body for all three,
#: and this is that body. If the sim ever carries three, take the largest.)
ROBOT_L, ROBOT_W = 1.6, 0.9

#: HOW FAR A PARKING BAY SITS OFF ITS CROSS AISLE.
#:
#: DERIVED, NOT CHOSEN — and it must exceed the robot's own length. It was
#: 1.5 m against a 1.6 m robot, so a robot parked correctly in its own bay
#: still had its tail 0.70 m from the aisle centreline. It was not in the way
#: by accident; parked properly it COULD NOT be out of the way.
#:
#: What that cost, measured 2026-08-18: amr2 drove its own lane west, turned
#: south down the east aisle toward the coater row as its job required, and
#: came within 1.8 m of amr3 sitting in the neighbouring bay. Layer 1 stopped
#: it — correctly, since continuing would have closed the gap below STOP_GAP.
#: amr3 could not move aside because it was already parked. Layer 1 "only ever
#: says stop: it cannot say who goes", so both sat frozen for four minutes with
#: seven jobs queued behind them. Twice, and once they touched.
#:
#: The clearance below is the gap between a PASSING robot's flank and a PARKED
#: robot's tail, both bodies included — not centre to centre.
PARK_CLEARANCE = 1.25
PARK_SPUR = ROBOT_L / 2.0 + ROBOT_W / 2.0 + PARK_CLEARANCE      # 2.5 m

PARK_X = [AISLE_W_X - PARK_SPUR, AISLE_E_X + PARK_SPUR]

#: Machine face y (the side the robot approaches from).
_FACE_N = ROW_N_Y - MACHINE_D / 2.0
_FACE_S = ROW_S_Y + MACHINE_D / 2.0

#: Where the machines stand, west to east along each row.
_GRV_X = _s([-10.0, -4.0, 2.0, 8.0])       # Gravure 1..4, north row
_CTR_X = _s([-10.0, -4.0, 2.0, 8.0])       # Coater 1..4, south row
_ASRS_X = _s(-17.0)                        # west end, north row (A3)
_SLT_X = _s(-17.0)                         # west end, south row (A3)


def _dock_n(x):
    """Dock point in front of a north-row machine."""
    return (x, _FACE_N - DOCK_INSET)


def _dock_s(x):
    return (x, _FACE_S + DOCK_INSET)


# ---------------------------------------------------------------- stations

#: kind: SOURCE (never called, only supplies) | LD (material goes IN here)
#:       ULD (material comes OUT here)       | BUFFER (WIP overflow rack)
STATIONS = {}


def _add(name, kind, machine_xy, dock_xy, machine=True):
    STATIONS[name] = {
        "kind": kind,
        "machine": machine_xy,      # solid body, robots must never drive here
        "dock": dock_xy,            # where the robot stands to be served
        "solid": machine,
    }


# ASRS — one port, the source of every roll [S16][IP]
_add("ASRS", "SOURCE", (_ASRS_X, ROW_N_Y), _dock_n(_ASRS_X))

# Gravure 1..4, north row. Unwinder = LD, Rewinder = ULD [IP][PROT]
for i, x in enumerate(_GRV_X, 1):
    _add(f"GRV{i}", "MACHINE", (x, ROW_N_Y), _dock_n(x))
    _add(f"GRV{i}_LD", "LD", (x, ROW_N_Y), _dock_n(x - PORT_OFFSET), machine=False)
    _add(f"GRV{i}_ULD", "ULD", (x, ROW_N_Y), _dock_n(x + PORT_OFFSET), machine=False)

# Coater 1..4, south row
for i, x in enumerate(_CTR_X, 1):
    _add(f"CTR{i}", "MACHINE", (x, ROW_S_Y), _dock_s(x))
    _add(f"CTR{i}_LD", "LD", (x, ROW_S_Y), _dock_s(x - PORT_OFFSET), machine=False)
    _add(f"CTR{i}_ULD", "ULD", (x, ROW_S_Y), _dock_s(x + PORT_OFFSET), machine=False)

# Slitter: one machine at the west end of the south row with 4 LD ports [S16].
# Its ULD is served by the Small AGV fleet and is out of scope.
#: SLITTER PORT SPACING. The four ports were pitched 1.3 m apart — closer than
#: the robot is LONG (1.6 m) — so two robots docked at neighbouring slitter
#: ports overlapped by 0.30 m. The entry interlock is per station and happily
#: permits both, so four ports existed that could never all be used. Measured
#: 2026-08-07; harmless only because a single robot serves this segment today,
#: and a real fault at the documented fleet size of six.
#:
#: 2.0 m is what fits. The westmost port must clear the west cross aisle at
#: x = -20 and the eastmost must stay clear of CTR1_LD at x = -11.2, which
#: leaves 6.0 m of span for four ports. That gives 0.4 m between docked robots —
#: less than the 0.8 m the gravure and coater LD/ULD pairs enjoy, but positive,
#: which 1.3 m was not.
_SLT_PITCH = _s(2.0)
#: THE PORTS BELONG TO THE MACHINE, NOT TO THE ROAD.
#:
#: This was `AISLE_W_X + 0.7` — the first port defined as an offset from the
#: west aisle. Two things were wrong with that.
#:
#: It could not be fixed. The gap between the corner and the first port WAS
#: this number, by construction, so widening the hall moved the ports with the
#: road and changed nothing. That was tried, on 2026-08-21, and the hall grew
#: 1.8 m for no effect before anyone re-measured the gap rather than the road.
#:
#: And it was backwards. `_SLT_X` comes from the customer's drawing; where we
#: put a road does not. A machine's own docking ports sliding about because we
#: moved a road is not something that can happen in a factory.
#:
#: So the four ports are centred on the machine, and the ROAD is placed to
#: clear them — which is the direction the dependency should run. `_check_row`
#: below then verifies the clearance instead of defining it, so a layout that
#: does not fit fails loudly rather than silently guaranteeing 0.7 m.
_SLT_PORT_X0 = _SLT_X - (3 * _SLT_PITCH) / 2.0

_add("SLT", "MACHINE", (_SLT_X, ROW_S_Y), _dock_s(_SLT_X))
for i in range(1, 5):
    _add(f"SLT_LD{i}", "LD", (_SLT_X, ROW_S_Y),
         _dock_s(_SLT_PORT_X0 + (i - 1) * _SLT_PITCH), machine=False)

# WIP buffer racks — optional overflow when the destination is full [S16][TR].
# Each sits at the east end of its own row, so a robot diverting to a buffer
# stays in its own segment's aisle and never queues in front of a machine.
# Ports are named "<machine>_<n>", the SAME convention the machines use, so a
# port can be matched to the machine it belongs to. They were "WIP_GRV1", which
# does not start with "WIP_GRV_", so roads._owner_of never recognised them and
# the buffer spurs were never exempt from their own rack. Harmless at the old
# hand-over distance and an instant build failure once it shortened.
_WIP_X = _s(13.0)
_add("WIP_GRV", "MACHINE", (_WIP_X, ROW_N_Y), _dock_n(_WIP_X))
for i in (1, 2):
    _add(f"WIP_GRV_{i}", "BUFFER", (_WIP_X, ROW_N_Y),
         _dock_n(_WIP_X + (i - 1.5) * 2 * PORT_OFFSET), machine=False)
_add("WIP_CTR", "MACHINE", (_WIP_X, ROW_S_Y), _dock_s(_WIP_X))
for i in (1, 2):
    _add(f"WIP_CTR_{i}", "BUFFER", (_WIP_X, ROW_S_Y),
         _dock_s(_WIP_X + (i - 1.5) * 2 * PORT_OFFSET), machine=False)

#: Leg C's rack — the WIP Slitter. Added 2026-08-18; segment C had none, so a
#: coater whose slitter was full had nowhere to put its output and the divert
#: branch was untestable on a third of the line.
_WIP_SLT_X = _s(19.0)
_add("WIP_SLT", "MACHINE", (_WIP_SLT_X, ROW_S_Y), _dock_s(_WIP_SLT_X))
for i in (1, 2):
    _add(f"WIP_SLT_{i}", "BUFFER", (_WIP_SLT_X, ROW_S_Y),
         _dock_s(_WIP_SLT_X + (i - 1.5) * 2 * PORT_OFFSET), machine=False)

#: HOW MUCH EACH RACK HOLDS — not how many docks it has.
#:
#: The deck counts WIP Gravure Print 2EA, WIP Coater 13EA and WIP Slitter 30EA.
#: Those are SLOTS, not access points: the customer layout puts only a handful of
#: AGV positions at each rack, and a rack plainly holds more rolls than it has
#: places to stand. Modelling 30 docks would be wrong as well as unbuildable.
#:
#: So each rack has two access ports and a capacity. The divert decision asks
#: "is the rack full?", which is a capacity question, and the robot asks "where
#: do I stand?", which is a dock question. They are not the same number.
BUFFER_CAPACITY = {"WIP_GRV": 2, "WIP_CTR": 13, "WIP_SLT": 30}

#: Solid bodies robots must never drive through.
OBSTACLES = {n: s["machine"] for n, s in STATIONS.items() if s["solid"]}

#: Every place a robot can be sent.
DOCKS = {n: s["dock"] for n, s in STATIONS.items() if s["kind"] != "MACHINE"}

#: THE DOCKING MARKER on each machine face — the QR/ArUco square the robot
#: watches to close the last couple of metres. One per port, directly in line
#: with that port, so the robot centres on its OWN port rather than the machine.
#:
#: (x, y, outward_normal). The normal points into the aisle: that is the
#: direction the robot must arrive from.
#:
#: This is what makes docking independent of the map. The lane network is only
#: accurate to wherever we drew it; the marker is fixed to the real machine, so
#: closing on the marker absorbs any error in where the machine actually stands.
MARKERS = {}
for _n, _s in STATIONS.items():
    if _s["kind"] == "MACHINE":
        continue
    _dx, _dy = _s["dock"]
    if _dy > 0:                      # north row: face looks south, into the aisle
        MARKERS[_n] = (_dx, ROW_N_Y - MACHINE_D / 2.0, -math.pi / 2.0)
    else:
        MARKERS[_n] = (_dx, ROW_S_Y + MACHINE_D / 2.0, math.pi / 2.0)

#: INSIDE THIS RANGE OF A MARKER the robot is in the bay and must not turn.
#:
#: Docked, it presents its flat side — half-width 0.45 m — leaving 0.229 m to
#: the machine face. Rotating swings the corner out to the half-diagonal,
#: hypot(0.8, 0.45) = 0.918 m: an extra 0.468 m of sweep into a 0.229 m gap, so
#: a corner cuts about 0.24 m INTO the machine. Reversing out the way it came in
#: is not tidiness, it is the only motion that fits.
#:
#: A marker is 4.0 m from its spur junction, the dock 2.2 m, and the docked
#: robot 0.65 m. Three metres therefore covers the whole bay and releases the
#: robot to turn only once it is within a metre of the aisle.
BAY_RADIUS = abs((ROW_N_Y - MACHINE_D / 2.0) - AISLE_N_Y) - 1.0

#: EVERY MARKER IS DIFFERENT, and a robot checks the one it can see before it
#: enters. A marker is not just something to aim at — it says WHICH port this
#: is, so arriving at the wrong station is detectable rather than silent.
#:
#: Without it, a robot pointed at the wrong bay docks perfectly against the
#: wrong machine and reports success; the CSM then believes material is
#: somewhere it is not. With it, the mismatch stops the approach.
#:
#: Stable and sorted, so an id belongs to a port for good and does not shuffle
#: when the plant gains a machine.
MARKER_IDS = {name: i for i, name in enumerate(sorted(DOCKS), start=1)}

#: Robot half-width. It crabs sideways into the dock, so this is the face that
#: ends up against the machine.
ROBOT_HALF_WIDTH = 0.45
#: Clear gap between robot and machine when docked.
DOCK_GAP = 0.20
#: Range from the robot CENTRE to the marker that counts as docked. The source
#: project's 0.45 m is a lidar reading from the sensor; measured from the centre
#: the equivalent is half the robot plus the gap.
DOCK_TARGET = ROBOT_HALF_WIDTH + DOCK_GAP
#: Closer than this is an over-approach fault. Same margin below target as the
#: source project used (0.45 -> 0.28).
DOCK_MIN = DOCK_TARGET - 0.17

#: Where a dock's spur meets its aisle — straight back from the dock, onto the
#: road. This is where a robot waits after backing out, and it is ON the network
#: by construction. The previous model put wait spots at a sideways offset that
#: belonged to no lane at all, so every job ended with the robot leaving the road
#: and driving cross-country to an unmapped point.
JOINS = {n: (d[0], AISLE_N_Y if d[1] > 0 else AISLE_S_Y) for n, d in DOCKS.items()}


# ------------------------------------------------------------ material flow

#: The Big AGV segments [S16]. Each is (name, sources, destinations, buffer).
#: A robot class serves exactly one segment — that is the design, and it is why
#: the real line does not have every robot roaming the whole floor.
SEGMENTS = [
    {
        "name": "A",                       # 1.5T-Big AGV A
        "payload": 1.5,
        "from": ["ASRS"],
        "to": [f"GRV{i}_LD" for i in range(1, 5)],
        "buffer": ["WIP_GRV_1", "WIP_GRV_2"],
    },
    {
        "name": "B",                       # 1.5T-Big AGV B
        "payload": 1.5,
        "from": [f"GRV{i}_ULD" for i in range(1, 5)],
        "to": [f"CTR{i}_LD" for i in range(1, 5)],
        "buffer": ["WIP_CTR_1", "WIP_CTR_2"],
    },
    {
        "name": "C",                       # 3.5T-Big AGV
        "payload": 3.5,
        "from": [f"CTR{i}_ULD" for i in range(1, 5)],
        "to": [f"SLT_LD{i}" for i in range(1, 5)],
        "buffer": ["WIP_SLT_1", "WIP_SLT_2"],
    },
]

#: WHICH PORT SUPPLIES WHICH, paired by machine.
#:
#: Derived per index, not per segment. An earlier version took the segment's
#: FIRST source for every destination, so all four coaters were fed from
#: GRV1_ULD alone: gravure 2, 3 and 4's output was never collected and four
#: machines queued behind one port.
FEEDS = {}
for _i in range(1, 5):
    FEEDS[f"GRV{_i}_LD"] = "ASRS"
    FEEDS[f"CTR{_i}_LD"] = f"GRV{_i}_ULD"
    FEEDS[f"SLT_LD{_i}"] = f"CTR{_i}_ULD"

def sources_for(destination):
    """Every station that could supply this destination, BEST FIRST.

    FEEDS answers "which port is paired with this one". That is not the same
    question as "where should this material come from", and treating it as if it
    were is why a coater whose own gravure was empty would wait while the other
    three gravures held finished material it could have taken.

    The order encodes two decisions, both cheap to change:

      1. **The rack first.** Material already parked on a WIP rack is preferred
         over fresh material upstream. Otherwise parked rolls accumulate: the
         rack only ever fills, because there is always something newer to take.
      2. **Then the paired machine, then its siblings.** FEEDS' pairing is a
         sensible default — it spreads four destinations across four sources
         instead of everybody queueing at the first one — but it is a preference
         now, not a constraint.

    Returns candidates only. Whether a candidate can actually supply right now
    is a separate question, asked by the caller against live station status, and
    whether the MATERIAL matches is a third question we cannot yet answer at all
    (the customer has not given us the matching rules).
    """
    seg = segment_of_station(destination)
    if seg is None:
        return [FEEDS[destination]] if destination in FEEDS else []
    out = list(seg["buffer"])                       # 1. clear the rack first
    paired = FEEDS.get(destination)
    if paired and paired not in out:                # 2. its own pair next
        out.append(paired)
    for src in seg["from"]:                         # 3. then any sibling
        if src not in out:
            out.append(src)
    return out


def bobbin_return_for(station):
    """Where the EMPTY BOBBIN goes when this station has finished with it.

    Specification jobs 3, 7 and 11 — the three returns that had no
    implementation at all, and assumption A5 which gives their destinations:

        leg A   Gravure LD  -> ASRS                (back to the store)
        leg B   Coater LD   -> Gravure ULD         (one process upstream)
        leg C   Slitter LD  -> Coater ULD          (one process upstream)

    Read from SEGMENTS rather than written out, because the rule IS the segment
    reversed: a bobbin goes back the way its roll came. Writing the three pairs
    as a literal table would be a second place for the plant to be described,
    and the last time this file had two descriptions of one thing the launch
    spawned robots six metres from where the CSM believed they were.

    Every hop here is an exchange, not a delivery (see `Carried`), so this is
    the return half of every material job, not a special case.

    Returns None for a station that is not a segment destination — the ASRS and
    the WIP racks do not hand bobbins back.
    """
    for seg in SEGMENTS:
        if station in seg["to"]:
            # The bobbin goes to the station that supplied the roll. Where a
            # segment has several sources, the paired one is the natural
            # partner; FEEDS holds that pairing.
            paired = FEEDS.get(station)
            if paired and paired in seg["from"]:
                return paired
            return seg["from"][0]
    return None


def is_bobbin_return(from_station, to_station):
    """True if this pair is a bobbin going back upstream, not a roll going on.

    Useful to callers that have a job and want to know which direction it runs
    without re-deriving the segment.
    """
    return bobbin_return_for(from_station) == to_station


def buffer_for(source):
    """The WIP rack that stranded material from this source should go to.

    A rack buffers the INPUT of the process it serves — WIP_GRV feeds the
    gravures, so material bound for a gravure parks there. That is why the
    diversion runs from the upstream source to the rack of the DESTINATION's
    leg, not to a rack beside the source.

    Returns the rack's access ports, or [] if the source has no leg.
    """
    for seg in SEGMENTS:
        if source in seg["from"]:
            return list(seg["buffer"])
    return []


def segment_of_station(station):
    """Which leg a station belongs to, by any of its roles. None if unknown.

    Distinct from `segment_of(robot_name)` below, which answers the same
    question for a ROBOT. Naming them alike shadowed one with the other.
    """
    for seg in SEGMENTS:
        if (station in seg["from"] or station in seg["to"]
                or station in seg["buffer"]):
            return seg
    return None


#: A machine's material goes in one port and comes out the other — the line IP
#: summary lists these as "Unwinder / Rewinder" pairs. Without the link the two
#: ports are unrelated stations and the line cannot fill past its first stage:
#: material delivered to a gravure's load port is never collectable from its
#: unload port, so no coater job is ever servable and two thirds of the fleet
#: never moves.
PORT_LINKS = [(f"GRV{i}_LD", f"GRV{i}_ULD") for i in range(1, 5)]
PORT_LINKS += [(f"CTR{i}_LD", f"CTR{i}_ULD") for i in range(1, 5)]

#: Which segment each robot serves. Three robots, three segments — the real line
#: runs 2 + 2 + 6 [S16], so this is one of each rather than the full fleet.
#:



def parking_for(robot_name):
    """The slot THIS robot parks in — its own, not its leg's.

    A leg's slots are handed out in name order, so the assignment is stable
    across restarts: amr1 always gets leg A's first slot whether or not amr4
    exists. It has to be stable, because a robot drives home to it.

    Returns None for a robot with no leg, and None for a robot whose leg has
    more robots than slots. Both are real states and neither should be papered
    over with a default — a default would mean sending two robots to the same
    coordinates, which is what this replaced.
    """
    segment, index = parking_index(robot_name)
    if segment is None:
        return None
    slots = PARKING_SLOTS[segment]
    return slots[index] if index < len(slots) else None


def parking_index(robot_name):
    """Which leg this robot parks on, and its place in that leg's queue.

    Split out of `parking_for` because two things need it and they need
    different answers from it: the coordinates to drive to, and the ROAD NODE
    with those coordinates. Deriving the queue position twice is how the two
    would eventually disagree about which slot a robot owns.

    Returns (None, None) for a robot on no leg.
    """
    segment = ROBOT_SEGMENT.get(robot_name)
    if segment is None:
        return None, None
    # Numerically, not alphabetically — see `robot_number`.
    peers = sorted((n for n, s in ROBOT_SEGMENT.items() if s == segment),
                   key=lambda n: (robot_number(n) is None, robot_number(n), n))
    if robot_name not in peers:
        return None, None
    return segment, peers.index(robot_name)


def segment_of(robot_name):
    return next((s for s in SEGMENTS
                 if s["name"] == ROBOT_SEGMENT.get(robot_name)), None)


def segment_for_job(from_station, to_station):
    """Which leg a job belongs to — and therefore which AGV class carries it.

    Matches BOTH directions along a segment, because a leg's robots carry the
    roll forward and the empty core back. The specification says so directly:
    jobs 5 and 7 are both LOWBIGB, 9 and 11 are both HIGHBIG, 1 and 3 are both
    LOWBIGA. The bobbin is not a different leg, it is the return half of one.

    This used to match the forward direction only. Every bobbin return was then
    rejected by the ACS with "no segment", because CTR1_LD -> GRV1_ULD is
    segment B read backwards and matched nothing — visible in the simulator as
    five bobbin jobs created and five failed.
    """
    for s in SEGMENTS:
        if from_station in s["from"] and to_station in s["to"]:
            return s
        if from_station in s["to"] and to_station in s["from"]:
            return s                      # the return half of the same leg
    return None


#: Where idle robots park — on a spur OFF a cross aisle, never on the aisle
#: itself. An idle robot standing on a lane is a road block, which is exactly
#: what stranded the fleet before this rewrite.
#: HOW MANY ROBOTS EACH LEG HAS, from the specification's fleet table
#: (cathode). Legs A and B carry two 1.5T robots each; leg C carries six 3.5T.
#: The simulator usually runs one per leg, which is why one bay per leg was
#: enough until now — and why it stopped being enough the moment anyone asked
#: what a second robot would do.
FLEET = {"A": 2, "B": 2, "C": 6}

#: SPACING BETWEEN QUEUE SLOTS, measured across the robots, not centre to
#: centre. Slots sit side by side along the cross aisle, so what has to clear
#: is the robot's WIDTH.
PARK_PITCH = ROBOT_W + PARK_CLEARANCE

#: Which end of the plant each leg parks at, and which way its queue grows.
#: Away from y=0 in both cases, so the two east legs open out rather than
#: growing into one another.
_PARK_SIDE = {"A": (0, +1), "B": (1, +1), "C": (1, -1)}


def parking_slots(segment):
    """Every queue slot for this leg, the one nearest the aisle first.

    A QUEUE, NOT A BAY PER ROBOT. The customer's own layout works this way —
    the surveyed drawing has a dock column and a separate queue column 3.6 m
    behind it, with 51 positions in the cell area, not one reserved bay per
    vehicle. Robots take the next free slot.

    This replaces one bay per LEG, which silently assumed one robot per leg.
    With two, both were sent home to identical coordinates: two robots aiming
    at the same point, which is the collision this file spent 2026-08-18
    designing out at the bays.

    Slots grow outward from the aisle centre. Each one hangs off the cross
    aisle on its own short spur, which is why `roads` needs no new lane type —
    it already chains everything sitting on an aisle in order, so a spur
    further out simply extends that aisle.
    """
    which, direction = _PARK_SIDE[segment]
    x = PARK_X[which]
    y0 = 1.5 * direction
    return [(x, y0 + i * PARK_PITCH * direction) for i in range(FLEET[segment])]


def parking_join_slots(segment):
    """Where each of this leg's queue slots meets its cross aisle."""
    which, _ = _PARK_SIDE[segment]
    aisle = AISLE_W_X if which == 0 else AISLE_E_X
    return [(aisle, y) for _, y in parking_slots(segment)]


#: Every slot, per leg. Index 0 is the one nearest the aisle.
PARKING_SLOTS = {seg: parking_slots(seg) for seg in _PARK_SIDE}
PARKING_JOIN_SLOTS = {seg: parking_join_slots(seg) for seg in _PARK_SIDE}

#: The leg's FIRST slot, under the name callers have always used. Keeping this
#: means nothing that only ever needed "where does leg B park" has to change.
PARKING = {seg: slots[0] for seg, slots in PARKING_SLOTS.items()}
#: Where each parking spur meets its cross aisle.
PARKING_JOIN = {seg: joins[0] for seg, joins in PARKING_JOIN_SLOTS.items()}


#: WHICH QUEUE SLOTS HAVE POWER.
#:
#: A CHARGER IS A PARKING SLOT WITH A CABLE, not a separate place. That is how
#: the real plant works — a robot waiting and a robot charging are in the same
#: row — and it means charging needs no new geometry at all.
#:
#: Every second slot is powered, which is not a guess: deck slide 30 marks
#: "Charger 5EA" for the Big AGV fleet on each polarity, and the cathode fleet
#: is 2 + 2 + 6 = ten robots. One charger per two robots gives A:1 + B:1 + C:3
#: = 5 — the deck's own number.
#:
#: ⚠ The real bays are 5.2 x 2.2 m against a 1.6 x 0.9 m robot, so a real
#: charging bay is much larger than a parking slot. We do not model that: it
#: matters for the floor plan and not for deciding who charges when.
CHARGER_EVERY = 2


def charging_slots(segment):
    """Indices of this leg's queue slots that can charge."""
    return list(range(0, FLEET[segment], CHARGER_EVERY))


#: leg -> [(x, y)] of its charging positions.
CHARGERS = {seg: [PARKING_SLOTS[seg][i] for i in charging_slots(seg)]
            for seg in _PARK_SIDE}


def robot_number(robot_name):
    """The digits in `amr7`, or None.

    Needed because robots must sort NUMERICALLY. Plain string order puts
    `amr10` before `amr3`, which would hand leg C's first parking slot to the
    tenth robot and quietly shuffle everyone else's — a fault that cannot
    appear below ten robots and is invisible above it until two robots drive to
    one bay.
    """
    found = re.search(r"\d+", robot_name or "")
    return int(found.group()) if found else None


def assign_legs(count, fleet=None):
    """Hand `count` robots to legs in the deck's own proportions.

    THE RULE: each robot goes to the leg that is furthest from its full
    complement, measured as a FRACTION of that complement, with ties broken in
    deck order. Fractions rather than absolute shortfall, so a leg entitled to
    six does not swallow the first four robots before the two-robot legs get
    one each.

    It lands on the sensible answer at every size we actually run:

        3 robots -> A 1, B 1, C 1     one per leg, which is what we have today
        5 robots -> A 1, B 1, C 3     leg C is the busy one, so it gets the spare
       10 robots -> A 2, B 2, C 6     exactly the deck's fleet [S6]

    Stops at the deck's total: there are only that many parking slots and that
    many chargers, and a robot with nowhere to park is not a robot.
    """
    fleet = FLEET if fleet is None else fleet
    legs = list(fleet)
    taken = {leg: 0 for leg in legs}
    out = {}
    for i in range(1, count + 1):
        # Full legs are not candidates. When every leg is full we stop rather
        # than overflow: the shortage is real and hiding it would put two
        # robots in one bay.
        free = [leg for leg in legs if taken[leg] < fleet[leg]]
        if not free:
            break
        leg = min(free, key=lambda l: (taken[l] / fleet[l], legs.index(l)))
        taken[leg] += 1
        out[f"amr{i}"] = leg
    return out


#: THIS DICT IS THE WHOLE BINDING. A robot is tied to one leg of the material
#: flow by naming a segment here; the segment names its pickup and delivery
#: ports above, and those ports name the markers, the roads and the parking bay.
#: Nothing else in the system knows one robot from another — driving, docking,
#: traffic and the job FSM all key off station ids.
#:
#: So amr3 is amr2 with a different string, and that is the design working
#: rather than a coincidence. If a robot ever needs code the others do not, the
#: leg abstraction has leaked and the fix belongs here, not in a special case.
#:
#: A leg with no robot is legal: SimAcs.submit_job answers BUSY, not REJECTED,
#: so its jobs queue until somebody can serve them. That is what let amr3 be
#: removed and rewritten without touching anything else — measured over an hour
#: with segment C unserved, in docs/verification/2026-08-10-two-robot-one-hour-soak.md
#:
#: Generated for the DECK'S FULL FLEET, not for however many happen to be
#: running. A three-robot run is amr1..amr3 of the same table, so a robot's leg
#: and parking slot do not move when the fleet grows — and it has to be stable,
#: because a robot drives home to its slot.
ROBOT_SEGMENT = assign_legs(sum(FLEET.values()))


def chargers_for(robot_name):
    """Every charger this robot may use, nearest to its own slot first.

    A LIST, not one place. The deck gives 5 chargers to 10 robots and
    `CHARGER_EVERY` says so: two robots share each one. `charger_for` naming a
    single slot was true only while every leg had one robot, and it stopped
    being true the moment leg C had three — two of them would be sent to the
    same plug with nothing arbitrating it, and neither the code nor any test
    would have noticed.

    Its OWN leg's chargers, because a robot is bound to one leg and driving it
    across the plant to another leg's charger would cross every lane it is
    meant to stay out of.
    """
    segment = ROBOT_SEGMENT.get(robot_name)
    if segment is None or not CHARGERS.get(segment):
        return []
    home = parking_for(robot_name)
    if home is None:
        return list(CHARGERS[segment])
    return sorted(CHARGERS[segment],
                  key=lambda c: (c[0] - home[0]) ** 2 + (c[1] - home[1]) ** 2)


def charger_for(robot_name):
    """The charger this robot would prefer, or None if its leg has none.

    ⚠ PREFERENCE, NOT A RESERVATION. Another robot may be on it. Anything that
    actually sends a robot to charge must ask the fleet for a free one — see
    `SimAcs.claim_charger` — and this is only the first choice.
    """
    chargers = chargers_for(robot_name)
    return chargers[0] if chargers else None


def is_charger(position, tolerance=0.3):
    """Is this position one of the charging slots?"""
    for slots in CHARGERS.values():
        for x, y in slots:
            if abs(x - position[0]) <= tolerance and abs(y - position[1]) <= tolerance:
                return True
    return False



#: What two robots need between two points on a road: one body length, plus the
#: gap layer 1 refuses to close. Below this, two robots meeting there have
#: nowhere to resolve it and no traffic rule can help them.
ROW_MIN_GAP = ROBOT_L + 0.30


def row_gaps(north):
    """Every gap along one row, west to east, corners included.

    (gap, from_name, to_name), in metres.
    """
    side = 1 if north else -1
    points = sorted((st["dock"][0], name) for name, st in STATIONS.items()
                    if st.get("dock")
                    and (1 if st["dock"][1] > 0 else -1) == side
                    and st.get("kind") in ("LD", "ULD", "BUFFER", "SOURCE"))
    out, prev, prev_name = [], AISLE_W_X, "west corner"
    for x, name in points:
        out.append((x - prev, prev_name, name))
        prev, prev_name = x, name
    out.append((AISLE_E_X - prev, prev_name, "east corner"))
    return out


def check_rows():
    """Refuse a layout where two robots could meet with nowhere to go.

    WHY THIS EXISTS. The slitter's first port was written as `AISLE_W_X + 0.7`
    — 0.7 m from the corner, with a comment calling it "clear of the cross
    aisle". A robot is 1.60 m long. It was not clear of anything, and nothing
    said so: the number DEFINED the clearance, so it could never be wrong.

    It surfaced as a three-robot jam on 2026-08-21 — amr2 came round the corner
    as amr3 came out of the spur, and neither could give way because there was
    no road between them. Then the same fault turned up mirrored at the east
    end, `WIP_SLT_2` 1.80 m from its corner, which nobody had noticed either.

    So the clearance is CHECKED rather than assumed. A layout that does not fit
    raises here, at import, instead of being discovered by two robots meeting
    in it.
    """
    bad = []
    for north in (False, True):
        for gap, a, b in row_gaps(north):
            # A hair under the minimum and exactly the minimum are the same
            # thing to a float, and neither is a layout anybody should ship.
            # The tolerance is there so the message is about the geometry
            # rather than about binary representation.
            if gap < ROW_MIN_GAP - 1e-9:
                bad.append(f"{a} -> {b}: {gap:.2f} m, needs {ROW_MIN_GAP:.2f}")
    if bad:
        raise ValueError(
            "layout leaves nowhere for two robots to pass:\n  "
            + "\n  ".join(bad))


check_rows()


def declare_locations(records):
    """Tell a records store every place material can legitimately be.

    THE PLANT IS THE SOURCE OF TRUTH, THE TABLE IS ONLY THE INDEX. `records.py`
    deliberately knows nothing about this plant — it is a generic store — so
    the knowledge flows one way, from here into it, the same way rack sizes do.

    Why the table exists at all: `materials.location` is a free string that may
    name a machine port, a buffer rack or the store, and before 2026-08-21 only
    the first had a table behind it. A reader joining materials to stations
    lost every roll sitting in the ASRS and was not told.
    """
    from .records import LocationKind

    for dock in DOCKS:
        segment = segment_of_station(dock)
        records.define_location(
            dock,
            LocationKind.STORE if dock == "ASRS" else LocationKind.PORT,
            segment=segment["name"] if isinstance(segment, dict) else segment)

    for name, station in STATIONS.items():
        if station.get("kind") == "BUFFER":
            segment = segment_of_station(name)
            records.define_location(
                name, LocationKind.RACK,
                segment=segment["name"] if isinstance(segment, dict)
                else segment)
