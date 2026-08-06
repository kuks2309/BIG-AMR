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

# ---------------------------------------------------------------- geometry

HALL_W, HALL_E = -23.0, 20.0     # hall extent in x (assumption A1)
HALL_S, HALL_N = -13.0, 13.0     # hall extent in y
WALL_T = 0.2

MACHINE_W, MACHINE_D = 3.0, 2.0        # A5
MACHINE_PITCH = 6.0                    # A4
PORT_OFFSET = 1.2                      # A4: LD/ULD either side of centre

ROW_N_Y = 8.0                          # north machine row centre
ROW_S_Y = -8.0                         # south machine row centre
DOCK_INSET = 2.2                       # A6: dock this far in front of the face
AISLE_N_Y = 3.0                        # north aisle
AISLE_S_Y = -3.0                       # south aisle
AISLE_W_X = -20.0                      # west cross aisle
AISLE_E_X = 16.0                       # east cross aisle
PARK_X = [-21.5, 17.5]                 # parking spurs, off the cross aisles

#: Machine face y (the side the robot approaches from).
_FACE_N = ROW_N_Y - MACHINE_D / 2.0
_FACE_S = ROW_S_Y + MACHINE_D / 2.0

#: Where the machines stand, west to east along each row.
_GRV_X = [-10.0, -4.0, 2.0, 8.0]       # Gravure 1..4, north row
_CTR_X = [-10.0, -4.0, 2.0, 8.0]       # Coater 1..4, south row
_ASRS_X = -17.0                        # west end, north row (A3)
_SLT_X = -17.0                         # west end, south row (A3)


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
_add("SLT", "MACHINE", (_SLT_X, ROW_S_Y), _dock_s(_SLT_X))
for i in range(1, 5):
    _add(f"SLT_LD{i}", "LD", (_SLT_X, ROW_S_Y),
         _dock_s(_SLT_X + (i - 2.5) * 1.3), machine=False)

# WIP buffer racks — optional overflow when the destination is full [S16][TR].
# Each sits at the east end of its own row, so a robot diverting to a buffer
# stays in its own segment's aisle and never queues in front of a machine.
_WIP_X = 13.0
_add("WIP_GRV", "MACHINE", (_WIP_X, ROW_N_Y), _dock_n(_WIP_X))
for i in (1, 2):
    _add(f"WIP_GRV{i}", "BUFFER", (_WIP_X, ROW_N_Y),
         _dock_n(_WIP_X + (i - 1.5) * 2 * PORT_OFFSET), machine=False)
_add("WIP_CTR", "MACHINE", (_WIP_X, ROW_S_Y), _dock_s(_WIP_X))
for i in (1, 2):
    _add(f"WIP_CTR{i}", "BUFFER", (_WIP_X, ROW_S_Y),
         _dock_s(_WIP_X + (i - 1.5) * 2 * PORT_OFFSET), machine=False)

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
        "buffer": ["WIP_GRV1", "WIP_GRV2"],
    },
    {
        "name": "B",                       # 1.5T-Big AGV B
        "payload": 1.5,
        "from": [f"GRV{i}_ULD" for i in range(1, 5)],
        "to": [f"CTR{i}_LD" for i in range(1, 5)],
        "buffer": ["WIP_CTR1", "WIP_CTR2"],
    },
    {
        "name": "C",                       # 3.5T-Big AGV
        "payload": 3.5,
        "from": [f"CTR{i}_ULD" for i in range(1, 5)],
        "to": [f"SLT_LD{i}" for i in range(1, 5)],
        "buffer": [],
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
ROBOT_SEGMENT = {"amr1": "A", "amr2": "B", "amr3": "C"}


def segment_of(robot_name):
    return next((s for s in SEGMENTS
                 if s["name"] == ROBOT_SEGMENT.get(robot_name)), None)


def segment_for_job(from_station, to_station):
    for s in SEGMENTS:
        if from_station in s["from"] and to_station in s["to"]:
            return s
    return None


#: Where idle robots park — on a spur OFF a cross aisle, never on the aisle
#: itself. An idle robot standing on a lane is a road block, which is exactly
#: what stranded the fleet before this rewrite.
PARKING = {
    "A": (PARK_X[0], 1.5),          # west end, north side  — segment A's end
    "B": (PARK_X[1], 1.5),          # east end, north side
    "C": (PARK_X[1], -1.5),         # east end, south side
}
#: Where each parking spur meets its cross aisle.
PARKING_JOIN = {
    "A": (AISLE_W_X, 1.5),
    "B": (AISLE_E_X, 1.5),
    "C": (AISLE_E_X, -1.5),
}
