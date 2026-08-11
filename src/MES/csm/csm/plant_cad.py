"""plant_cad — the FM2 Cell area as the customer's drawings actually describe it.

NOT YET WIRED IN. `plant.py` still drives the simulation. This module holds the
CAD-derived geometry so it can be checked against the drawings before anything
depends on it, and so the switch-over is one deliberate change rather than a
rewrite with no way back.

=============================================================================
WHERE THESE NUMBERS COME FROM
=============================================================================
Two drawings from the project NAS, converted with LibreDWG 0.14 (`dwg2dxf`) and
read with ezdxf. Working copies and the full extraction live in
`References/local/gazebo-world/` (gitignored — the drawings are Motion Device
confidential and this repository is public). The audit trail is
`docs/gazebo_world/sources.md`.

  [D1]  BIG& SMALL AGV Layout V1 20260810.dwg
        51 AGV positions, coater and ASRS bodies, charging bays
  [D2]  FM2 Front-end layout V7 20260709_0806.dwg
        process area labels, gravure and slitter bodies, the AGV lane network,
        building walls and columns

SCALE — verified three ways, not assumed:
  * DXF header `$INSUNITS = 4` (millimetres), `$MEASUREMENT = 1` (metric)
  * equipment blocks measure 2-3 m, plausible only in mm
  * symbol blocks `zw$CB5A` / `zw$FACA` are 1.845 m deep, matching the
    documented 1800 mm roll length (system deck slide 2, "Load Dimensions")

FRAME — one world frame, verified by containment. The architect base block
`Architect20260620` is placed at scale 25.4 (drawn in inches), and
`world = (insert + local * 25.4) / 1000` lands in the same frame as [D1]'s
equipment. Proof: all four COATER (C) labels fall inside the `_COATER CATHODE`
extent and all four COATER (A) labels inside `_COATER OVEN`, with no offset;
applying an offset puts all eight outside.

Coordinates below are ABSOLUTE CAD coordinates in metres. Nothing is shifted,
so any point here can be typed into the drawing and found.

=============================================================================
WHAT IS MEASURED AND WHAT IS NOT
=============================================================================
Measured: every machine footprint and position, the lane widths, the AGV dock
and queue columns, the dock standoff, the charging bays, the building shell.

NOT measured, and flagged at each site below:
  * which port of a pair is LD and which is ULD (see PORT_ORDER)
  * lane connectivity — the drawing gives 49 lane rectangles, not a graph
  * WIP rack envelopes
"""

# ---------------------------------------------------------------- building

#: Hall extent from 1933 wall segments on layers A-WALL / I-WALL in the cell
#: area [D2]. Roughly 306 x 209 m — the world we have been simulating is
#: 43 x 26 m, about a tenth of this in each direction.
HALL_X = (30.17, 335.58)
HALL_Y = (84.74, 293.63)

#: Structural columns sit on a ~10-12 m grid (3651 column marks on A-COLS
#: [D2]). Recorded because columns are obstacles; individual positions are not
#: yet extracted.
COLUMN_PITCH_X = (10.0, 11.8)

# ---------------------------------------------------------------- machines
#
# Each entry is (x_min, x_max) for the body and a list of y centres. Bodies are
# axis-aligned rectangles in the drawing.

#: ASRS — one unit, the source of every roll. Block `foil ASRS` [D1].
ASRS = {"x": (129.95, 140.88), "y": (166.35, 223.09), "size": (10.9, 56.7)}

#: Gravure x4 — blocks `FDVCXVCX` / `FDSAFVDSVCS` [D2]. The block names are
#: meaningless CAD identifiers; these were identified by the GRAVURE area label
#: at (174.20, 224.89) lying on them, not by name.
#:
#: Note the y centres are NOT evenly pitched: gaps are 26.7, 31.2, 26.7 m.
GRAVURE_X = (173.19, 180.07)
GRAVURE_SIZE = (6.9, 17.1)
GRAVURE_Y = (182.90, 209.61, 240.77, 267.48)

#: Coater x4 — `Cathode Coater type1` / `Cathode Coater template` [D1], with
#: positions taken from the COATER (C) area labels [D2] because only two of the
#: four bodies survived extraction (the rot-180 placements have a mirrored
#: bounding box spanning 256 m and were filtered out as composites).
#:
#: PITCH 12.0 m, four machines — matching the deck's "Coater 4 EA". An earlier
#: reading of 23.96 m was this author measuring alternate machines; both
#: numbers were real, one was of the wrong thing.
COATER_X = (113.25, 141.00)
COATER_SIZE = (24.0, 7.6)
COATER_Y = (232.87, 244.63, 256.83, 268.88)

#: Slitter x4 — blocks `BLOCK5_1` / `BLOCK6_1` inside block `Slitting` [D2].
#: Paired spacing: gaps of 9.78, 13.72, 9.78 m.
SLITTER_X = (191.64, 204.69)
SLITTER_SIZE = (13.05, 7.6)
SLITTER_Y = (224.03, 233.81, 247.53, 257.31)

# ------------------------------------------------------------------- AGV
#
# THE DRAWING HAS TWO DOCK COLUMNS PER MACHINE ROW, NOT ONE.
#
# At every coater there is a 2x2 arrangement: an inner column where the robot
# docks and an outer column 3.54 m behind it. The outer column is a QUEUE
# position — a robot waits there, off the lane, rather than on it.
#
# Our current model has no queue position, so a waiting robot stands on the
# aisle. That is exactly the behaviour that produced the deadlocks and the one
# measured collision this week. The real plant designed the problem out.

#: Distance from a machine face to the inner (docking) column [D1].
DOCK_STANDOFF = 4.71
#: Inner and outer column x at the coater row [D1].
COATER_DOCK_X = 145.7
COATER_QUEUE_X = 149.3
#: Gravures are served from their EAST face at x ~183.5 [D1], a 3.4 m standoff.
GRAVURE_DOCK_X = 183.5

#: Two ports on the same machine face, this far apart, facing opposite ways
#: (rot 0 and rot 180 in the drawing) [D1].
PORT_SEPARATION = 4.10
#: Adjacent AGV positions along a face.
POSITION_PITCH = 3.54

#: WHICH OF THE PAIR IS LD — A CONVENTION, NOT A MEASUREMENT.
#:
#: The drawing shows two positions per machine face 4.10 m apart, one at rot 0
#: and one at rot 180, and the protocol workbook confirms 上料工位 (loading) and
#: 下料工位 (unloading) are separate stations with separate handshakes. Neither
#: says which physical position is which.
#:
#: Taken: the lower-y position is LD. Material flows north through the cell
#: (ASRS south, slitter north), so a machine's input sits on its upstream side.
#:
#: THE COST OF BEING WRONG IS 4.10 m OF DRIVING. It does not invert the job
#: model: that lives in plant.FEEDS, which is material flow and already correct
#: independently of geometry. Flip this one constant if a photograph or the
#: handshake spec says otherwise.
PORT_ORDER_LD_FIRST = True

# ------------------------------------------------------------------ lanes

#: Lane widths in the cell area [D2]: 24 lanes at 2.1 m, 8 at 2.4 m, 17 at
#: 2.6 m. A 3.5T AGV is 1.60 m wide, so a 2.1 m lane leaves 0.25 m per side.
#:
#: THESE ARE SINGLE-FILE LANES. Our model uses a 5.0 m aisle and a give-way
#: rule where a robot steps ~2 m sideways off the lane to let another past.
#: That manoeuvre does not fit here.
#:
#: The drawing solves two-way traffic differently: lanes run in PARALLEL PAIRS
#: (e.g. x 250.08..252.18 alongside 253.04..255.14, 5.06 m combined). Whether
#: the give-way subsystem should exist at all is therefore an open design
#: question, not a tuning problem.
LANE_WIDTHS = (2.1, 2.4, 2.6)
LANE_COUNT_CELL_AREA = 49

#: Charging bays — block `大AGV充电站双` ("Big AGV charging station, double")
#: [D1]. These are the real parking positions.
CHARGING_BAY_SIZE = (5.2, 2.2)
CHARGING = {
    "gravure_1_5T": ((177.22, 131.99), (197.12, 241.21)),
    "coating_3_5T": ((226.22, 131.96), (192.36, 241.37)),
}

# ------------------------------------------------------------------ robots
#
# From the system deck slide 2, "1.1 AGV model". We currently simulate every
# robot as 1.600 x 0.900 m, which is 31% too narrow for the 1.5T and 44% too
# narrow for the 3.5T, and models two distinct machines as one.

ROBOT_1_5T = (1.300, 1.900)      # 1.5T-Big AGV A and B  (amr1, amr2)
ROBOT_3_5T = (1.600, 2.000)      # 3.5T-Big AGV          (amr3)
ROBOT_SPEED = 0.5                # m/s, deck slide 15 (we run 0.6)


def machines():
    """Every modelled machine as (name, x_min, y_min, x_max, y_max) in metres."""
    out = [("ASRS", ASRS["x"][0], ASRS["y"][0], ASRS["x"][1], ASRS["y"][1])]
    for i, cy in enumerate(GRAVURE_Y, 1):
        h = GRAVURE_SIZE[1] / 2.0
        out.append((f"GRV{i}", GRAVURE_X[0], cy - h, GRAVURE_X[1], cy + h))
    for i, cy in enumerate(COATER_Y, 1):
        h = COATER_SIZE[1] / 2.0
        out.append((f"CTR{i}", COATER_X[0], cy - h, COATER_X[1], cy + h))
    for i, cy in enumerate(SLITTER_Y, 1):
        h = SLITTER_SIZE[1] / 2.0
        out.append((f"SLT{i}", SLITTER_X[0], cy - h, SLITTER_X[1], cy + h))
    return out
