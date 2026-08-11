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
  * lane DIRECTION. Deck slide 16 carries direction arrows over the cell; they
    have not been read off into a direction per lane yet.
  * lane connectivity — the drawing gives 49 lane rectangles, not a graph
  * WIP rack envelopes. The deck counts 2 gravure, 13 coater, 30 slitter; we
    have the position of none of them.
  * the gravure and slitter LD/ULD stations. The coaters' are settled (see
    COATER_LD_X); whether the other rows follow the same pattern is NOT checked.
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

#: Coater x4 — `Cathode Coater template` [D1], positioned from the COATER (C)
#: area labels [D2] because only two of the four bodies survived extraction (the
#: rot-180 placements have a mirrored bounding box spanning 256 m and were
#: filtered out as composites).
#:
#: PITCH 12.0 m, four machines — matching the deck's "Coater 4 EA". An earlier
#: reading of 23.96 m was this author measuring alternate machines; both numbers
#: were real, one was of the wrong thing.
#: CORRECTED 2026-08-11. This was (113.25, 141.00), 27.75 m — which is the UNION
#: of two different block variants, not a machine:
#:
#:     Cathode Coater type1     x 116.98..141.00  24.02 m  bodies at y 40..72
#:     Cathode Coater template  x 113.25..138.08  24.83 m  bodies at y 242..274
#:
#: y < 100 is the ANODE cell and y > 200 the CATHODE cell, so the cathode line
#: uses the TEMPLATE variant. Merging the two inflated the width by 3.7 m and
#: put the east face 2.9 m too far out, which would have made every dock
#: standoff wrong.
COATER_X = (113.25, 138.08)
COATER_SIZE = (24.83, 7.72)
#: Area-label anchors. Body centres sit ~1.15 m north of them (measured at the
#: two coaters whose bodies survived extraction: label 244.63 -> centre 245.72,
#: label 268.88 -> centre 270.11), so machine centres are label + 1.15.
COATER_LABEL_Y = (232.87, 244.63, 256.83, 268.88)
COATER_Y = tuple(round(y + 1.15, 2) for y in COATER_LABEL_Y)

#: Slitter x4 — blocks `BLOCK5_1` / `BLOCK6_1` inside block `Slitting` [D2].
#: Paired spacing: gaps of 9.78, 13.72, 9.78 m.
SLITTER_X = (191.64, 204.69)
SLITTER_SIZE = (13.05, 7.6)
SLITTER_Y = (224.03, 233.81, 247.53, 257.31)

# ------------------------------------------------------------------- AGV
#
# A MACHINE'S STATIONS SIT INSIDE ITS CELL, AND ITS SPUR REACHES THEM.
#
# Settled at the coaters on 2026-08-11 (below). A coater cell spans x 113-138;
# its ULD station is at x 136.58 and its LD at 125.58, both INSIDE that span,
# and the spur runs west from the spine to x 124.56 to serve them.
#
# An earlier version of this section described "two dock columns per machine
# row" with an inner dock and an outer queue 3.54 m behind. That model was built
# from the positions at x 145-152, which are now known NOT to be the coater
# stations. It is removed rather than corrected, because none of it survived.

#: THE COATER LD AND ULD STATIONS — CORRECTED 2026-08-11 FROM THE SYSTEM DECK.
#:
#: The deck [S16] marks eight white boxes at the coater row: "Coater LD 1Set x
#: 4EA" on the LEFT column and "Coater ULD 1Set x 4EA" on the RIGHT. Two columns
#: of four, one box per coater. The project lead read them off the slide; block
#: `zw$4E78` in [D1] then confirms it, repeating per coater row:
#:
#:     x 125.58   pair 1.61 m apart, rot 0 and rot 180   ->  Coater LD
#:     x 136.58   SAME y as the LD pair, rot 0 / rot 180 ->  Coater ULD
#:
#: LD AND ULD DIFFER IN x, NOT IN y. Both stations of a coater sit at the same
#: y; only their x differs, by 11.0 m. Everything below the previous version of
#: this section assumed the opposite — that the pair 4.10 m apart in y was
#: LD/ULD — and picked between them with PORT_ORDER_LD_FIRST. That constant was
#: answering a question the plant does not ask.
#:
#: THIS ALSO EXPLAINS THE LANE-THROUGH-COATER CONTRADICTION. `audit_cad_world`
#: reported four lanes running up to 13.5 m into the coater bounding box, and it
#: was read as either drive-in bays or a wrong footprint. Neither: COATER_X is
#: the coater CELL INCLUDING ITS AGV APRON, and a lane reaching x 124.56 is
#: simply serving the LD station at 125.58. The audit finding stands as drawn;
#: its interpretation was wrong.
COATER_LD_X = 125.58
COATER_ULD_X = 136.58

#: One station per coater, at the midpoint of its rot-0 / rot-180 pair. Same y
#: for LD and ULD.
COATER_STATION_Y = (231.47, 245.14, 255.45, 269.76)

#: The two symbols of a station, this far apart in y, facing each other. Read as
#: the roll position and the bobbin position of one exchange.
COATER_STATION_PAIR = 1.61

#: CTR4's ULD IS INFERRED, NOT MEASURED. `zw$4E78` has 22 placements; CTR1-3
#: carry both LD and ULD, CTR4 carries only LD. The deck says ULD is 4EA, so the
#: fourth exists — this is the same single-layer extraction gap that hid the CTR1
#: and CTR4 port pairs before. Taken at the symmetric position and flagged here
#: rather than silently filled.
COATER_ULD_MEASURED = (True, True, True, False)

#: EACH COATER OWNS ONE SPUR — the road structure at the coater row.
#:
#: Described by the project lead and confirmed against the lane rectangles: the
#: row reads CTR1 · road · CTR2 CTR3 · road · CTR4, and the two roads in each
#: gap are NOT a pair serving the gap — one belongs to each coater.
#:
#:     CTR1  station 231.47   spur y 233.53..236.13   from the north
#:     CTR2  station 245.14   spur y 240.68..243.28   from the south
#:     CTR3  station 255.45   spur y 257.40..260.00   from the north
#:     CTR4  station 269.76   spur y 265.06..267.66   from the south
#:
#: Spur centre to station centre is 3.16-3.40 m in every case, and road edge to
#: the near position of the station pair is 1.05-1.29 m. So a robot runs west
#: along its coater's spur and steps off it into the station — the station is
#: perpendicular to the road, not alongside it.
#:
#: This is why the station y values are unevenly spaced (gaps 13.67, 10.31,
#: 14.31): the spurs are interleaved between them, and CTR2/CTR3 have no
#: coater-reaching road between them at all — the lanes there stop at x 145.57.
#:
#: Each entry is (spur_y_min, spur_y_max, approach) with approach the side the
#: spur lies on relative to the station.
COATER_SPUR = (
    (233.53, 236.13, "north"),
    (240.68, 243.28, "south"),
    (257.40, 260.00, "north"),
    (265.06, 267.66, "south"),
)

#: The spurs run from the main north-south spine at x 157.94 west to x 124.56 —
#: past the ULD station at 136.58 and terminating just past the LD at 125.58. So
#: one spur serves BOTH of its coater's stations, ULD first then LD.
COATER_SPUR_X = (124.56, 157.94)

#: EACH SPUR HAS TWO CONNECTORS — one down to LD, one down to ULD.
#:
#: Described by the project lead: "that road has two small connector roads, one
#: for coater LD and another for coater ULD, x 125-130 and 135-140". The geometry
#: demands it — a station sits 3.16-3.40 m off its spur, so something has to join
#: them — and two of the eight are in the lane data already:
#:
#:     x 136.01..138.61  y 243.10..253.47   contains ULD_X, reaches CTR2 station
#:     x 136.01..138.61  y 260.00..271.65   contains ULD_X, reaches CTR4 station
#:
#: Both are 2.60 m wide and both sit on the ULD column (136.58 falls inside
#: 136.01..138.61). So the described structure is confirmed where the drawing
#: shows it; the other six are an extraction gap of exactly the kind that has hit
#: this file before — one layer mined, the rest missed.
#:
#: THE OTHER SIX ARE DERIVED, NOT MEASURED. They are generated from the spur and
#: station geometry by `coater_connectors()` below, and `CONNECTOR_MEASURED` says
#: which two are real. Do not quote a derived connector as a drawing fact.
CONNECTOR_WIDTH = 2.60

#: (coater index 0-3, "ld"|"uld") for the connectors the drawing actually shows.
CONNECTOR_MEASURED = ((1, "uld"), (3, "uld"))


def coater_connectors():
    """Every spur-to-station connector as (x0, y0, x1, y1, coater, kind, measured).

    A connector runs along the station's own column, from the near edge of the
    spur to just past the far position of the station pair, so a robot leaves the
    spur, covers the connector and is at the station.
    """
    out = []
    half = CONNECTOR_WIDTH / 2.0
    reach = COATER_STATION_PAIR / 2.0 + 0.6      # clear the far position
    for i, ((sy0, sy1, side), sty) in enumerate(zip(COATER_SPUR, COATER_STATION_Y)):
        for kind, cx in (("ld", COATER_LD_X), ("uld", COATER_ULD_X)):
            if side == "north":                  # spur above the station
                y0, y1 = sty - reach, sy0
            else:                                # spur below the station
                y0, y1 = sy1, sty + reach
            out.append((cx - half, y0, cx + half, y1, i + 1, kind,
                        (i, kind) in CONNECTOR_MEASURED))
    return out


#: THE WIP RACKS — x 148.51 AND 152.05, FOUR GROUPS ALIGNED WITH THE COATERS.
#:
#: Identified by the project lead as the WIP Slitter racks: "4 WIP slitters
#: almost align with LD and CTR, same road structure between them." The geometry
#: agrees to a degree that is not coincidence — each column carries four PAIRS
#: 4.10 m apart, and the pair centres sit on the coater stations:
#:
#:     pair centre 231.48  vs CTR1 station 231.47   off by 0.01 m
#:     pair centre 245.34  vs CTR2 station 245.14   off by 0.20 m
#:     pair centre 255.35  vs CTR3 station 255.45   off by 0.10 m
#:     pair centre 269.71  vs CTR4 station 269.76   off by 0.05 m
#:
#: and one position of every pair lies ON that coater's spur. So a rack group is
#: reached from the same road as its coater's stations — the spur serves ULD,
#: then LD, then the rack, all on one run.
#:
#: THESE ARE ACCESS POINTS, NOT SLOTS. The deck counts WIP Slitter 30EA and WIP
#: Coater 13EA, and there are nowhere near that many positions here. Read as: a
#: rack holds many rolls and the AGV positions are where a robot stands to reach
#: it. That reading is an INFERENCE from the count mismatch, not something the
#: drawing states — the rack envelopes themselves are still not extracted.
#:
#: Which groups are WIP Slitter and which WIP Coater is NOT settled. The deck
#: marks both in this area (WIP Coater 4EA and 9EA, WIP Slitter 30EA), so two
#: rack families may share these columns.
WIP_ACCESS_X = (148.51, 152.05)
WIP_GROUP_Y = ((229.43, 233.53), (243.29, 247.39),
               (253.30, 257.40), (267.66, 271.76))
WIP_PAIR_SEPARATION = 4.10

#: A third column at x 145.0-145.3, 10 positions, on layers `涂布-3.5T大AGV` and
#: `AGV接机需求`. Six sit at the WIP pair y-values and four at rot +/-90 near the
#: station y-values. Not identified. Recorded so it is not silently dropped.
UNIDENTIFIED_X145 = 145.0

#: THE CORRIDOR AT x 183..186 SERVES MACHINES ON BOTH SIDES.
#:
#: Gravure east face is at x 180.07 and slitter west face at x 191.64, so a
#: position at x 185.6 is 5.5 m from one and 6.0 m from the other — nearest
#: machine cannot tell them apart. The two sub-columns do:
#:
#:     x ~183.5  serves the GRAVURES (their east face)
#:     x ~185.6  serves the SLITTERS (their west face)
#:
#: This is the busiest part of the network: one corridor, two machine rows.
GRAVURE_DOCK_X = 183.5
SLITTER_DOCK_X = 185.62

#: THE SLITTERS ARE SERVED DIFFERENTLY FROM THE COATERS.
#:
#: A coater has its own dock and two queue positions on its own face. The four
#: slitters share ONE north-south line of eight positions at x 185.62, pitched
#: 3.54 m, covering y 233..260 — a queue line for the whole row rather than a
#: dock per machine. Rotations are all +/-90, i.e. facing across the corridor.
#:
#: That matters for traffic: eight positions on one line, on the corridor that
#: also serves the gravures from its other side, is the densest conflict point
#: in the network.
SLITTER_DOCK_Y = (233.15, 236.69, 240.22, 245.73,
                  249.27, 252.80, 256.56, 260.10)

#: THE ASRS IS ESSENTIALLY UNSERVED IN THIS DRAWING — one position found, at
#: (151.85, 219.43). The ASRS body spans y 166..223, so a single position at its
#: northern end is not a full docking arrangement. Either the ASRS is served on
#: a face this drawing does not cover, or its positions are on a layer not yet
#: found. Do not invent them: segment A (ASRS -> Gravure LD) cannot be laid out
#: from the drawing until this is resolved.
ASRS_DOCK_FOUND = ((151.85, 219.43),)

#: EVERY AGV POSITION IN THE CATHODE CELL, AS DRAWN — (x, y, heading_deg).
#:
#: The 45 placements of the AGV symbol blocks inside the cell, verbatim from the
#: extraction, ungrouped and unrounded beyond 2 decimals. The named constants
#: above (COATER_DOCK_X, SLITTER_DOCK_Y, ...) are groupings OF this list; this is
#: the measurement, they are the reading of it. When the two disagree, this wins.
#:
#: Heading is the block rotation in the drawing. It is the direction the AGV
#: symbol points, which we take as the robot's facing when parked. 0 = +x,
#: 90 = +y. Nothing in the drawing confirms that reading, but the rot 0/180 pairs
#: on a shared machine face only make sense as two robots facing each other.
AGV_POSITIONS = (
    (144.97, 233.53,  +180.0),
    (144.98, 243.29,    +0.0),
    (144.98, 247.39,    -0.0),
    (144.98, 253.30,    +0.0),
    (144.98, 257.40,  +180.0),
    (144.98, 267.66,    +0.0),
    (145.22, 231.56,   +90.0),
    (145.23, 245.41,   -90.0),
    (145.23, 255.43,   +90.0),
    (145.31, 269.64,   +90.0),
    (148.51, 229.43,    +0.0),
    (148.51, 233.53,  +180.0),
    (148.51, 243.29,    +0.0),
    (148.51, 247.39,  +180.0),
    (148.51, 253.30,    +0.0),
    (148.51, 257.40,  +180.0),
    (148.51, 267.66,    +0.0),
    (148.51, 271.76,  +180.0),
    (151.85, 219.43,   +90.0),
    (152.05, 229.43,    +0.0),
    (152.05, 233.53,  +180.0),
    (152.05, 243.29,    +0.0),
    (152.05, 247.39,  +180.0),
    (152.05, 253.30,    +0.0),
    (152.05, 257.40,  +180.0),
    (152.05, 267.66,    +0.0),
    (152.05, 271.76,  +180.0),
    (183.20, 199.17,   -90.0),
    (183.51, 173.76,   -90.0),
    (183.51, 182.51,   -90.0),
    (183.51, 266.82,   -90.0),
    (183.51, 273.02,   -90.0),
    (183.65, 239.97,    -0.0),
    (183.65, 259.85,  +180.0),
    (184.38, 207.52,    +0.0),
    (184.65, 266.88,    -0.0),
    (184.68, 190.87,    +0.0),
    (185.62, 233.15,   +90.0),
    (185.62, 236.69,   +90.0),
    (185.62, 240.22,   +90.0),
    (185.62, 245.73,   +90.0),
    (185.62, 249.27,   +90.0),
    (185.62, 252.80,   +90.0),
    (185.62, 256.56,   +90.0),
    (185.62, 260.10,   -90.0),
)

#: Two ports on the same machine face, this far apart, facing opposite ways
#: (rot 0 and rot 180 in the drawing) [D1].
PORT_SEPARATION = 4.10
#: Adjacent AGV positions along a face.
POSITION_PITCH = 3.54

#: RETIRED 2026-08-11 — LD AND ULD ARE NOT RESOLVED BY y.
#:
#: This constant answered "of the two positions 4.10 m apart in y, which is LD?"
#: and took the lower one, reasoning that material flows north. At the coaters
#: the deck [S16] and block `zw$4E78` both show LD and ULD at the SAME y, 11.0 m
#: apart in x (see COATER_LD_X / COATER_ULD_X). The question this answered is not
#: the question the plant asks.
#:
#: Kept as False rather than deleted so that any code still reading it gets the
#: inert value instead of a plausible-looking True. Nothing reads it today.
#:
#: Whether the gravures and slitters follow the coaters' x-separated pattern is
#: NOT yet checked — do not generalise this correction to them without going back
#: to the drawing.
PORT_ORDER_LD_FIRST = False

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

# ------------------------------------------------------------------ lane map
#
# The 37 lane rectangles of the CATHODE cell, from the 49 in [D2] (the rest are
# the anode side and the east yard). Each is (x_min, y_min, x_max, y_max) — a
# RECTANGLE, not a centreline. The drawing paints drivable area; it does not say
# which way traffic runs on it, and no direction arrow lies inside the cell.
#
# These are here so the Gazebo world can be drawn from the same numbers the
# router will eventually use. Painting them makes a wrong lane visible on screen
# instead of only in a log.

LANES = (
    (124.56, 233.53, 157.94, 236.13),  # x  w 2.60
    (124.56, 240.68, 157.94, 243.28),  # x  w 2.60
    (124.56, 257.40, 157.94, 260.00),  # x  w 2.60
    (124.56, 265.06, 157.94, 267.66),  # x  w 2.60
    (141.13, 219.72, 158.97, 222.12),  # x  w 2.40
    (141.13, 221.62, 158.97, 224.02),  # x  w 2.40
    (145.57, 247.21, 157.94, 249.81),  # x  w 2.60
    (145.57, 250.87, 157.94, 253.47),  # x  w 2.60
    (148.63, 226.83, 157.94, 229.43),  # x  w 2.60
    (148.63, 271.73, 157.94, 274.33),  # x  w 2.60
    (158.97, 215.92, 170.58, 218.32),  # x  w 2.40
    (159.48, 220.14, 185.78, 222.74),  # x  w 2.60
    (162.64, 227.42, 185.78, 230.02),  # x  w 2.60
    (170.69, 277.71, 179.99, 280.11),  # x  w 2.40
    (189.15, 171.65, 261.00, 173.75),  # x  w 2.10
    (189.15, 173.25, 250.16, 175.35),  # x  w 2.10
    (189.15, 186.86, 213.25, 188.96),  # x  w 2.10
    (189.15, 208.32, 238.31, 210.42),  # x  w 2.10
    (190.48, 237.53, 200.01, 240.13),  # x  w 2.60
    (216.95, 185.39, 238.54, 187.49),  # x  w 2.10
    (216.95, 271.71, 238.31, 273.81),  # x  w 2.10
    (217.18, 229.65, 238.76, 231.75),  # x  w 2.10
    (136.01, 243.10, 138.61, 253.47),  # y  w 2.60
    (136.01, 260.00, 138.61, 271.65),  # y  w 2.60
    (157.94, 227.02, 160.54, 274.25),  # y  w 2.60
    (160.04, 227.02, 162.64, 274.25),  # y  w 2.60
    (170.55, 230.02, 172.95, 277.61),  # y  w 2.40
    (170.58, 169.83, 172.98, 217.41),  # y  w 2.40
    (180.23, 169.95, 182.63, 220.14),  # y  w 2.40
    (180.23, 230.02, 182.63, 280.20),  # y  w 2.40
    (185.45, 171.66, 187.55, 219.87),  # y  w 2.10
    (185.78, 220.14, 188.38, 267.38),  # y  w 2.60
    (187.05, 171.66, 189.15, 219.87),  # y  w 2.10
    (187.88, 220.14, 190.48, 267.38),  # y  w 2.60
    (209.04, 219.28, 211.14, 265.29),  # y  w 2.10
    (213.25, 175.35, 215.35, 271.48),  # y  w 2.10
    (214.85, 175.35, 216.95, 282.76),  # y  w 2.10
)

#: Lane crossings — where an x-lane rectangle overlaps a y-lane rectangle.
#: Computed in the extraction, not eyeballed. These are the points a reservation
#: scheme has to arbitrate.
JUNCTIONS = (
    (137.31, 243.19),
    (137.31, 260.00),
    (137.31, 266.36),
    (157.94, 228.23),
    (157.94, 234.83),
    (157.94, 241.98),
    (157.94, 248.51),
    (157.94, 252.17),
    (157.94, 258.70),
    (157.94, 266.36),
    (157.94, 272.99),
    (162.64, 228.72),
    (170.58, 216.66),
    (171.75, 230.02),
    (181.43, 220.14),
    (181.43, 230.02),
    (185.78, 221.44),
    (185.78, 228.72),
    (189.15, 172.70),
    (189.15, 174.30),
    (189.15, 187.91),
    (189.15, 209.37),
    (190.48, 238.83),
    (213.25, 187.91),
    (214.30, 175.35),
    (214.30, 209.37),
    (215.90, 175.35),
    (215.90, 209.37),
    (216.95, 186.44),
    (216.95, 272.76),
)

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
