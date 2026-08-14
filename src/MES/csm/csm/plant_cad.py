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
  * WIP rack ENVELOPES. We have eight access positions (WIP_ACCESS_X) but not the
    racks themselves, and not which of the four groups is which family.
  * the SLITTER LD/ULD stations. The coaters' and gravures' are settled (see
    COATER_LD_X and GRAVURE_STATIONS) and they do NOT share a pattern — the
    coater separates LD/ULD in x, the gravure in y — so the slitter must be
    worked out on its own evidence, not assumed from either.
  * the ASRS docking stations — one position found for a 57 m machine (A1).

WHAT THE MACHINES ARE FOR is in the `flow` section at the end: the three Big AGV
legs, their robot classes and fleet sizes, the WIP rack option on each, and how
many of each station the deck says exist against how many we have placed. That
section is sourced from the deck's own text and the 2026-08-04 meeting, and it is
what `audit_cad_world.py` check 5 measures our geometry against.
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
#:
#: THE FOOTPRINT IS MEASURED. What is inside it is not — see ASRS_AISLE_W.
ASRS = {"x": (129.95, 140.88), "y": (166.35, 223.09), "size": (10.9, 56.7)}

#: THE ASRS IS A CRANE-AISLE RACK, NOT A SOLID BLOCK.
#:
#: Corrected 2026-08-13 on the project lead's instruction, against the reference
#: render `References/local/gazebo-world/extracted/factory_visual_flow.png`. That
#: image shows the foil ASRS as an automated store: TWO multi-level racking walls
#: running the full 56.7 m length, a CENTRAL AISLE between them, and a stacker
#: crane in the aisle. It was drawn here as one solid 10.9 x 56.7 x 3.0 m slab,
#: which is wrong in kind — it presents a store as a monolith and makes the crane
#: aisle a wall.
#:
#: WHAT IS MEASURED: the outer footprint above, from block `foil ASRS` [D1].
#:
#: WHAT IS NOT: the split between rack depth and aisle width, the number of
#: levels, and the height. Attempts to measure the split from the drawing on
#: 2026-08-13 FAILED and are recorded so the next attempt starts further along:
#:
#:   * `cathode_cell_trimmed.dxf` contains NO ASRS geometry. trim_dxf.py flattens
#:     the block tree one level and this equipment is nested deeper — consistent
#:     with sources.md's note that the equipment layers are "not reachable from
#:     BIG&SMALL-AGV-TR at depth 1 or 2".
#:   * In [D1], block `foil ASRS` has ONE placement, inside block `reuse
#:     equipment` at scale 25.4 (drawn in inches). It contains ~30 distinct
#:     `FOIL ASRS_CATHODE$0$...` sub-blocks re-inserted at scale 0.0393701
#:     (= 1/25.4), rotations 0/90/180/270. Their local x values fall in two
#:     clusters, around +100,570..+100,850 and -100,569..-100,602, which LOOKS
#:     like two mirrored rack walls — but the implied separation is ~201,000 local
#:     units and no unit interpretation makes that 10.9 m. The transform chain
#:     through the mixed 25.4 / 1/25.4 scales is not resolved.
#:   * A scan for blocks matching /asrs|foil/i also returns `cathode ASRS` and
#:     `anode ASRS`, both on layer `_POWDER ASRS`, whose extents (310 x 6.25 m)
#:     are plainly not a machine footprint. Do not measure the largest match.
#:
#: SO THE SPLIT BELOW IS A DRAWING CONVENTION, exactly like MACHINE_H, and it is
#: named so that nothing mistakes it for plant data. A 2.5 m clear aisle is at the
#: generous end for a stacker crane and leaves 4.215 m of rack each side.
#:
#: COST OF BEING WRONG: cosmetic only today — nothing routes into the ASRS, and
#: the AGV never enters it (it docks outside, see ASRS_DOCK_FOUND). It becomes real
#: the moment anyone measures roll capacity off the rack depth, so it is on the
#: open-questions list as A10 rather than left as a comment.
ASRS_AISLE_W = 2.50          # CONVENTION, not measured

#: HEIGHT IS 3.0 m — THE SAME DRAWING CONVENTION AS EVERY OTHER MACHINE.
#:
#: Set to 12.0 m on 2026-08-13 to reflect the multi-level rack in the render, then
#: put back to 3.0 the same day on the project lead's instruction, because of where
#: the default camera happens to sit.
#:
#: The camera is parked at (94.4, 160.8, 95) looking north-east, and its ground
#: aim point is (128.2, 219.7) — 1.75 m off the ASRS west face and inside its y
#: span. So the ASRS stands directly between the viewer and the rest of the plant.
#: At 12 m, with only a 2.5 m aisle splitting it, the two walls read as one block
#: and occlude the gravure and slitter rows entirely. The view was unusable.
#:
#: WHAT THIS DOES NOT UNDO: the ASRS is still two racking walls with a crane aisle
#: between them, which was the actual correction. Only the height went back.
#:
#: The real height is unknown either way — the drawings are plan views with no
#: heights (A8), and this is asked for in A10. If it turns out to matter, raise this
#: AND move the camera in the same change, or the view breaks again.
ASRS_HEIGHT = 3.0            # CONVENTION, = MACHINE_H. Real height unknown (A10)
ASRS_MEASURED_INTERNALS = False


def asrs_racks():
    """The two racking walls as (name, x0, y0, x1, y1), aisle left empty.

    Outer footprint measured; the aisle width that divides them is
    `ASRS_AISLE_W`, a convention. Returned as two bodies rather than one so the
    world shows a store with an aisle instead of a solid block.
    """
    (x0, x1), (y0, y1) = ASRS["x"], ASRS["y"]
    xm = (x0 + x1) / 2.0
    half = ASRS_AISLE_W / 2.0
    return [("ASRS_rack_w", x0, y0, xm - half, y1),
            ("ASRS_rack_e", xm + half, y0, x1, y1)]


def asrs_aisle():
    """The crane aisle as (x0, y0, x1, y1). The crane's, not the AGV's."""
    (x0, x1), (y0, y1) = ASRS["x"], ASRS["y"]
    xm = (x0 + x1) / 2.0
    half = ASRS_AISLE_W / 2.0
    return (xm - half, y0, xm + half, y1)

#: Gravure x4 — blocks `FDVCXVCX` / `FDSAFVDSVCS` [D2], found via the GRAVURE
#: area label at (174.20, 224.89) lying on them, not by name.
#:
#: THIS IS THE MACHINE. Corrected 2026-08-13 on the project lead's instruction,
#: after the world was put on screen and the gravures were in the wrong corridor.
#: The previous version of this comment called the box "AN AREA OUTLINE, NOT THE
#: MACHINE" and moved the body east to x 182.63..185.45. That was wrong, and the
#: file already contained the number that disproves it:
#:
#:   * GRAVURE_SIZE is 6.9 m wide. The body placed at 182.63..185.45 is 2.82 m
#:     wide — 4.08 m narrower than the machine it claimed to be. It had been
#:     sized to fill the gap it was dropped into, not to its own dimension.
#:   * The road structure has exactly one gap that fits 6.9 m: between the
#:     north-south roads at x 172.98 and x 180.23, a span of 7.25 m. GRAVURE_X
#:     (6.88 m) sits in it with ~0.2 m either side. The 2.82 m gap between the
#:     roads at 182.63 and 185.45 is an AGV aisle — a 3.5T body is 1.60 m wide.
#:   * Five AGV positions from the gravure's own layer land INSIDE the body as it
#:     was placed (183.20, 183.51 x2, 184.38, 184.68). A dock cannot be inside the
#:     machine it serves. `audit_cad_world.py` never caught this because check 2
#:     tests pads against `machines()`, which returns these GRAVURE_X boxes — so
#:     the one body that was NOT built from them was the one body never audited.
#:     Check 6 now compares every drawn body against its declared size.
#:
#: The "dense structure at x 183.3..185.6, 167,565 vertices" that the retracted
#: reading leaned on is real, but density is not identity: that column is the
#: `凹版1.5T大AGV路线` route artwork and the AGV aisle furniture, which is exactly
#: where you would expect the most drawing detail per square metre.
#:
#: Note the y centres are NOT evenly pitched: gaps are 26.7, 31.2, 26.7 m. The
#: 17.10 m length is corroborated by GRV1's own AGV pair spanning 17.11 m, but
#: GRV4's measured positions span 13.17 m and GRV2's 8.35 m, so the LENGTH is
#: less certain than the width. Bodies are drawn at 17.10 m and that is flagged.
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

# ------------------------------------------------------- gravure stations
#
# ALL FOUR GRAVURE BODIES ARE PLACED, from GRAVURE_X x GRAVURE_Y above.
#
# Corrected 2026-08-13 on the project lead's instruction, given against the world
# on screen: the gravures were in the AGV aisle at x 182.63..185.45 and belong in
# the machine corridor at x 173.19..180.07. See the GRAVURE_X comment for the
# three numbers that disprove the old placement — the decisive one is that a
# machine declared 6.9 m wide had been drawn 2.82 m wide.
#
#     road  x 170.55..172.95 ────────────────────────────
#                        [ ULD  GRV_n  LD ]                  body x 173.19..180.07
#     road  x 180.23..182.63 ────────────────────────────
#                                  · · · ·                   AGV aisle x 182.63..185.45
#     road  x 185.45..187.55 ────────────────────────────
#
#   * two roads run ALONG the row, one on each side of the machine corridor
#   * each machine carries LD at one end and ULD at the other, along its long
#     axis, which is what deck slide 19 draws — Unwinder at one end of the
#     gravure, Rewinder at the other, and what the project lead's annotation of
#     the world shows (ULD at high y, LD at low y).
#
# WHAT IS STILL NOT SETTLED — the STATIONS, not the bodies.
#
# Taking positions from the gravure's own layer `凹版1.5T大AGV路线` — not the
# x 185.62 line, which is `涂布-3.5T大AGV` and belongs to amr3 — only GRV1 has
# both ends:
#
#     GRV1   173.76 .. 190.87   span 17.11 m   against a 17.10 m body   OK
#     GRV2   199.17 .. 207.52   span  8.35 m                            no
#     GRV3   239.97 only                                                no
#     GRV4   259.85 .. 273.02   span 13.17 m                            no
#
# The three incomplete ones are NOT filled in by symmetry. An earlier version of
# this section did exactly that — took GRV1's south position and its MIDDLE one
# as the pair, got a 9.34 m separation, and generated six more stations from it.
# Nine metres for a pair at the two ends of a seventeen metre machine should have
# stopped that on its own.
#
# AND THOSE PADS ARE AT x 183.2..184.7 — IN THE AISLE, NOT ON THE MACHINE. With
# the body corrected to x 173.19..180.07, the gravure's own AGV positions sit
# across the road at 180.23..182.63 from the machine they serve, 3.1-4.6 m east of
# its face. So they are a queue or approach line in the aisle rather than the
# LD/ULD stations themselves. This is a REAL open question and it is why only
# GRV1's stations are placed, on the body's own centreline where the project
# lead's annotation puts them — see open-questions A9.
GRAVURE_BODY_LENGTH = GRAVURE_SIZE[1]

#: RETRACTED 2026-08-13 — the body in the aisle. Kept inert so that anything still
#: reading it fails loudly on a name that says what happened, rather than getting a
#: plausible rectangle. Nothing reads it today.
GRAVURE1_BODY_RETRACTED = (182.63, 173.76, 185.45, 190.87)

#: RETRACTED 2026-08-13 with the body above. These spanned the two roads either
#: side of the AISLE (x 180.23..187.55); with the machine in the corridor to the
#: west they connect the wrong pair of roads. What the connectors should be has
#: NOT been re-derived — that needs the same diagram the correction came from.
GRAVURE1_CONNECTORS_RETRACTED = (
    (180.23, 171.26, 187.55, 173.66),
    (180.23, 190.97, 187.55, 193.37),
)

#: ALL FOUR GRAVURES CARRY LD AND ULD — extended from GRV1 alone on 2026-08-13,
#: on the project lead's observation that "grv1 have ld and uld but other gvr does
#: not have".
#:
#: THIS IS NOT THE RETRACTED SYMMETRY DERIVATION. That one (commit 550547c) took
#: GRV1's south AGV pad and its MIDDLE pad as a pair, got a 9.34 m separation for
#: the two ends of a 17.1 m machine, and generated six stations from that single
#: bad measurement. The difference now is that nothing is derived from GRV1 at all
#: — each machine's stations come from ITS OWN measured body, and three independent
#: sources agree on the count and the arrangement:
#:
#:   1. the bodies are measured — GRAVURE_X x GRAVURE_Y, four of them
#:   2. the deck [S16] counts "Gravure Print LD 1Set x 4EA" and "ULD 1Set x 4EA",
#:      i.e. one set per machine, which is STATION_COUNTS_DECK
#:   3. the project lead's annotation of the world drew the pattern on every
#:      gravure identically — ULD at the high-y end, LD at the low-y end
#:
#: SO THE ORDER DOES NOT ALTERNATE. An earlier version of this section said
#: adjacent machines MIRROR ("LD ULD | ULD LD | LD ULD | ULD LD"), from the same
#: diagram reading that put the body in the aisle. The annotation shows three
#: gravures side by side with LD south and ULD north on all of them, so the
#: mirroring claim is dropped with the rest of that reading.
#:
#: STILL SOFT: the 17.10 m body LENGTH, which sets where the ends are. GRV2's
#: measured AGV pads span 8.35 m and GRV4's 13.17 m against it (see GRAVURE_X). If
#: the length is wrong the stations move along y with it — they stay on their own
#: machine's ends, which is why this is a bounded error rather than a wrong place.
GRAVURE_STATION_INSET = 1.2      # from each end; a drawing choice, not measured

#: How big a station marker is drawn, square. A drawing choice — but the connector
#: road has to start at its edge, so the number is shared rather than hardcoded in
#: the generator, where it was 2.4 in one place and the connector would have
#: guessed it in another.
STATION_MARKER = 2.4


def gravure_stations():
    """Every gravure LD/ULD as (name, x, y, kind) — eight in total.

    LD at each body's low-y end, ULD at its high-y end, on the body centreline.
    """
    cx = sum(GRAVURE_X) / 2.0
    h = GRAVURE_SIZE[1] / 2.0
    out = []
    for i, cy in enumerate(GRAVURE_Y, 1):
        out.append((f"GRV{i}", cx, cy - h + GRAVURE_STATION_INSET, "LD"))
        out.append((f"GRV{i}", cx, cy + h - GRAVURE_STATION_INSET, "ULD"))
    return out


#: GRV1's pair, kept as a name for anything that wants just the one machine.
GRAVURE_STATIONS = tuple((x, y, k) for _n, x, y, k in gravure_stations()[:2])


def gravure_bodies():
    """The four gravure machines as (name, x0, y0, x1, y1), all measured.

    Same extents `machines()` reports, exposed on their own because the world
    generator draws these as solid bodies and used to skip them entirely.
    """
    h = GRAVURE_SIZE[1] / 2.0
    return [(f"GRV{i}", GRAVURE_X[0], cy - h, GRAVURE_X[1], cy + h)
            for i, cy in enumerate(GRAVURE_Y, 1)]


#: THE GRAVURE ROAD STRUCTURE — CROSS-ROADS IN THE GAPS, SHORT SPURS OFF THEM.
#:
#: Described by the project lead, 2026-08-13, against the world on screen:
#:
#:   "1 rectangle (this is actually a road) connects two roads which is middle
#:    gvr1 and gvr2, then from that rectangle two short roads connect with gvr2 ld
#:    and gvr1 uld. there are two more, 1 connected two roads and one connect with
#:    gvr1 ld"
#:
#:     road 170.55..172.95  ║              ║  road 180.23..182.63
#:                          ║   [ULD]      ║
#:                          ║    GRV2      ║
#:                          ║   [ LD]      ║
#:                          ║      ║       ║      <- spur to GRV2 LD
#:                          ╠══════╩═══════╣      <- CROSS-ROAD, in the gap
#:                          ║      ║       ║      <- spur to GRV1 ULD
#:                          ║   [ULD]      ║
#:                          ║    GRV1      ║
#:                          ║   [ LD]      ║
#:                          ║      ║       ║
#:                          ╠══════╩═══════╣      <- CROSS-ROAD, south of GRV1
#:
#: So per BOUNDARY (not per station): one cross-road spanning road to road, and a
#: short spur off it to each station facing that boundary. Five boundaries for four
#: machines — south of GRV1, the three gaps, north of GRV4 — giving 5 cross-roads
#: and 8 spurs.
#:
#: WHY NOT BESIDE THE STATION. A first attempt copied `coater_connectors()`
#: literally and ran each road east from its station's edge. That works at the
#: coater because COATER_X is a 24.83 m CELL drawn as an outline with open floor
#: inside. The gravure body is SOLID and 6.88 m of a 7.28 m corridor, leaving
#: 0.20 m each side, so 93% of every connector was buried under the machine and
#: 0.16 m showed. The gaps — 9.61, 14.06, 9.61 m — are the only free floor in the
#: row, which is why the structure has to reach the end of the machine first.
#:
#: A SPUR STOPS AT THE BODY EDGE, not at the station centre. Stations sit
#: GRAVURE_STATION_INSET (1.2 m) inside their end, so running the spur to the
#: station would bury that last 1.2 m in the machine — the same mistake smaller.
#: The remaining 1.2 m is the machine's own port, not road.
#:
#: DERIVED, NOT MEASURED — same standing as the coater's eight. Drawn at reduced
#: opacity for that reason.
GRAVURE_ROAD_WEST_X = (170.55, 172.95)
GRAVURE_ROAD_EAST_X = (180.23, 182.63)

#: Where to put an END cross-road, measured out from the body end. Matches the
#: ~3.5 m clearance the 9.61 m gaps give their centred cross-roads.
GRAVURE_END_CLEARANCE = 3.5


def _gravure_roads_span_y(y):
    """Do BOTH north-south gravure roads exist at this y? [D2] LANES.

    They do not run the whole length: both are interrupted between roughly
    y 217 and y 230, so a cross-road placed at the centre of the GRV2-GRV3 gap
    would join nothing. Checked rather than assumed.
    """
    def has(col):
        return any(abs(L[0] - col[0]) < 0.1 and abs(L[2] - col[1]) < 0.1
                   and L[1] <= y <= L[3] for L in LANES)
    return has(GRAVURE_ROAD_WEST_X) and has(GRAVURE_ROAD_EAST_X)


def _spur_band():
    """The x band a spur occupies — the body centreline, station width."""
    cx = sum(GRAVURE_X) / 2.0
    return cx - STATION_MARKER / 2.0, cx + STATION_MARKER / 2.0


def _lanes_across_spur():
    """(y0, y1) of every DRAWN lane that already crosses the spur band.

    Three of them do: y 220.14..222.74, 227.42..230.02 and 277.71..280.11. The
    first two also span both north-south roads on their own, so the drawing
    already provides a cross-road in the GRV2-GRV3 gap and we must not add one.
    """
    sx0, sx1 = _spur_band()
    return sorted((L[1], L[3]) for L in lanes_drawn()
                  if L[0] <= sx0 and L[2] >= sx1)


def _boundaries():
    """(free_floor_lo, free_floor_hi, [stations served]) for each of the five."""
    h = GRAVURE_SIZE[1] / 2.0
    ends = [(cy - h, cy + h) for cy in GRAVURE_Y]
    n = len(GRAVURE_Y)
    out = [(ends[0][0] - 2 * GRAVURE_END_CLEARANCE, ends[0][0], ["GRV1:LD"])]
    for i in range(1, n):
        out.append((ends[i - 1][1], ends[i][0],
                    [f"GRV{i}:ULD", f"GRV{i + 1}:LD"]))
    out.append((ends[-1][1], ends[-1][1] + 2 * GRAVURE_END_CLEARANCE,
                [f"GRV{n}:ULD"]))
    return out


def gravure_cross_roads():
    """Cross-roads as (name, x0, y0, x1, y1, [stations served]).

    ONE PER BOUNDARY THAT DOES NOT ALREADY HAVE A ROAD. Corrected 2026-08-14 —
    the first version built one at every boundary, including the GRV2-GRV3 gap
    where the drawing already carries two east-west lanes that span both
    north-south roads. That put a cross-road on top of a measured lane.

    Where one IS needed it spans the OUTER edges of both north-south roads, so the
    junction is unambiguous, and sits at the middle of the free floor — shifted if
    the roads are interrupted there (they are, between y 217 and 230).
    """
    half = CONNECTOR_WIDTH / 2.0
    lanes = _lanes_across_spur()
    out = []
    for i, (lo, hi, serves) in enumerate(_boundaries()):
        # Already a road in this boundary's free floor? Then it is the cross-road.
        if any(ly1 > lo and ly0 < hi for ly0, ly1 in lanes):
            continue
        want = (lo + hi) / 2.0
        cy = want
        if not _gravure_roads_span_y(cy):
            best, k = None, 0.1
            while k <= (hi - lo):
                for cand in (want - k, want + k):
                    if lo + half <= cand <= hi - half \
                       and _gravure_roads_span_y(cand):
                        best = cand
                        break
                if best is not None:
                    break
                k += 0.1
            cy = best if best is not None else want
        out.append((f"cross{i}", GRAVURE_ROAD_WEST_X[0], cy - half,
                    GRAVURE_ROAD_EAST_X[1], cy + half, serves))
    return out


def gravure_spurs():
    """The eight spurs as (name, x0, y0, x1, y1, kind).

    A SPUR STOPS AT THE FIRST ROAD IT MEETS, which is what a road does — it does
    not run through one junction to reach another. Corrected 2026-08-14 on the
    project lead's observation that GRV2's ULD spur "crossed over all the road to
    connect gravure3": it was 10.63 m long and ran straight through both lanes in
    that gap to reach a cross-road that should not have existed.

    Candidate stopping edges are every drawn lane crossing the spur band plus every
    cross-road; the nearest one in the direction of travel wins.
    """
    h = GRAVURE_SIZE[1] / 2.0
    sx0, sx1 = _spur_band()
    stops = list(_lanes_across_spur())
    stops += [(c[2], c[4]) for c in gravure_cross_roads()]
    out = []
    for i, cy in enumerate(GRAVURE_Y, 1):
        for kind in ("LD", "ULD"):
            edge = cy - h if kind == "LD" else cy + h
            if kind == "LD":                       # runs south, stop at the top
                cands = [b for _a, b in stops if b <= edge + 1e-6]
                y0, y1 = (max(cands) if cands else edge), edge
            else:                                  # runs north, stop at the bottom
                cands = [a for a, _b in stops if a >= edge - 1e-6]
                y0, y1 = edge, (min(cands) if cands else edge)
            out.append((f"GRV{i}", sx0, y0, sx1, y1, kind))
    return out


def gravure_road_notes():
    """Anything about the gravure roads a reader should not have to rediscover."""
    notes = []
    for name, _x0, y0, _x1, y1, serves in gravure_cross_roads():
        cy = (y0 + y1) / 2.0
        if not _gravure_roads_span_y(cy):
            notes.append(f"{name} at y {cy:.2f} touches NEITHER north-south road "
                         f"— they are interrupted here; serves {', '.join(serves)}")
    for name, _x0, y0, _x1, y1, kind in gravure_spurs():
        if y1 - y0 < 0.05:
            notes.append(f"{name} {kind} spur has zero length — a road already "
                         f"reaches the body edge at y {y0:.2f}")
    return notes


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

#: EACH STATION HAS ITS OWN SHORT CONNECTOR, IMMEDIATELY EAST OF IT.
#:
#: From the project lead's sketch of the coater row. Per coater: the spur runs
#: east-west, and each of its two stations has a SHORT road of its own running
#: from the spur to the station, placed hard against the station's east side.
#:
#:     spur ═══════════════════════════════════
#:            ║              ║
#:          [LD][R]        [ULD][R]
#:
#: Three things this gets right that the previous version did not:
#:
#:   * the connector is BESIDE the station, not on top of it. Station and road
#:     share an edge; a robot on the road has the station on its left, which is
#:     why the station symbols face across the road (rot 0 / rot 180) rather than
#:     along it.
#:   * it is SHORT — the height of the station plus the reach to the spur, about
#:     3.7 m. Not a road crossing the gap to the next coater.
#:   * there is one per station, so two per spur, eight in the row.
#:
#: I PREVIOUSLY CALLED TWO LANES 'MEASURED CONNECTORS'. They are not:
#:
#:     x 136.01..138.61  y 243.10..253.47   10.4 m long
#:     x 136.01..138.61  y 260.00..271.65   11.7 m long
#:
#: Both run from one coater's spur past the NEXT coater's station, which is not
#: what a connector does. They are north-south link roads between coater rows,
#: and they are recorded as such below. The coincidence that drew me in — that
#: ULD_X falls 0.57 m inside their west edge — is because they run along the same
#: column, not because they are the connector.
#:
#: SO ALL EIGHT CONNECTORS ARE DERIVED. None is measured. The drawing does not
#: appear to contain them at all, which is consistent with the other
#: single-layer gaps in this file, but it means the whole set is our
#: construction from the sketch and must be labelled that way.
CONNECTOR_WIDTH = 2.60

#: Clearance between the station's east edge and the connector's west edge.
#: Zero — the sketch shows them touching.
CONNECTOR_GAP = 0.0

#: TWO LANE RECTANGLES IN THE COATER AREA THAT ARE NOT ROADS.
#:
#:     x 136.01..138.61  y 243.10..253.47   10.4 m
#:     x 136.01..138.61  y 260.00..271.65   11.7 m
#:
#: Both are in the drawing's lane data (blocks *U2937 and *U2939), and I first
#: mistook them for the station connectors — ULD_X falls 0.57 m inside their west
#: edge, which is a coincidence of sharing a column, not a relationship.
#:
#: EXCLUDED FROM THE WORLD on the project lead's instruction: there are no such
#: roads in the coater area. Kept here rather than deleted because they ARE in
#: the drawing, so the record should show what was measured and why it was left
#: out — not silently lose it. If they turn out to be something else (a cable
#: tray, a maintenance access, a lane from an older revision), this is where that
#: gets written down.
#:
#: The world generator filters these out of LANES as well as skipping them
#: directly, since they appear in both.
EXCLUDED_LANES = (
    (136.01, 243.10, 138.61, 253.47),
    (136.01, 260.00, 138.61, 271.65),
)


#: THE TWO-LANE ROADS — TWO OF THEM IN THE CELL, AND ONLY TWO.
#:
#: Identified by the project lead, 2026-08-14: "there are two roads has two lane
#: one for go another for come." Confirmed against the extraction: exactly two
#: corridors are made of a pair of lanes lying side by side over the same span.
#:
#:     Road 1 (spine)  x 157.94..160.54 + 160.04..162.64  = 4.70 m  y 227.02..274.25
#:     Road 2 (east)   x 213.25..215.35 + 214.85..216.95  = 3.70 m  y 175.35..271.48
#:
#: Everything else in the cell is single-file at 2.10-2.60 m.
#:
#: WHY THIS MATTERS more than it looks. A 3.5T AGV is 1.60 m wide, so a 2.10 m lane
#: leaves 0.25 m per side and two robots CANNOT pass. On these two roads they never
#: have to — opposing flows get a lane each. That is the first real answer to open
#: question A6, and it means the give-way manoeuvre our model uses (step ~2 m
#: sideways off the lane) is neither possible nor needed here.
#:
#: STILL UNKNOWN: WHICH lane is which direction. "One for go, another for come" is
#: the structure, not the assignment. Nothing below assigns a direction, and the
#: divider is drawn undirected for exactly that reason.
#:
#: Note the pairs OVERLAP rather than abut — Road 1's lanes share x 160.04..160.54.
#: The divider is placed at the centre of the whole corridor, which for Road 1 is
#: also the centre of that overlap (160.29).
TWO_LANE_MIN_COMBINED = 3.0      # below this it is one lane, not a pair


def two_lane_roads():
    """The paired-lane corridors as (name, axis, a, b, divider, lo, hi).

    `axis` is 'ns' or 'ew'; `divider` is the x (ns) or y (ew) of the centre line;
    `lo`/`hi` are the shared extent along the road. Detected from the lane
    rectangles rather than listed, so a lane edit cannot leave this stale.
    """
    out = []
    lanes = lanes_drawn()
    for axis, i0, i1, j0, j1 in (("ns", 0, 2, 1, 3), ("ew", 1, 3, 0, 2)):
        # i = across the road, j = along it
        band = sorted((L for L in lanes
                       if (L[i1] - L[i0]) < (L[j1] - L[j0])),
                      key=lambda L: L[i0])
        for a, b in zip(band, band[1:]):
            gap = b[i0] - a[i1]
            lo, hi = max(a[j0], b[j0]), min(a[j1], b[j1])
            combined = b[i1] - a[i0]
            if -1.0 < gap < 1.0 and hi > lo and combined >= TWO_LANE_MIN_COMBINED:
                out.append((f"road{len(out) + 1}", axis, a, b,
                            (a[i0] + b[i1]) / 2.0, lo, hi))
    return out


#: WHICH LANE GOES WHICH WAY — AN ASSUMPTION, NOT A MEASUREMENT.
#:
#: The project lead asked for direction to be marked on 2026-08-14. We do not have
#: it. Open question A6 has been unanswered since the world was first built: the
#: drawing paints drivable area and never says which way traffic runs, and all 42
#: arrow glyphs in the cell are on EQUIPMENT layers (machine-internal material
#: flow), none on an AGV layer.
#:
#: So this applies the ordinary right-hand-traffic rule — keep right, as road
#: vehicles do in Korea and China — and says so on screen by drawing the arrows in
#: a colour of their own rather than as road paint.
#:
#:     north-south road:  travelling +y (north) you keep right -> EAST lane
#:                        travelling -y (south)                -> WEST lane
#:     east-west road:    travelling +x (east)  you keep right -> SOUTH lane
#:                        travelling -x (west)                 -> NORTH lane
#:
#: COST OF BEING WRONG: every arrow reverses. That is a one-line change here and
#: nothing else in the file depends on it — no route, no reservation, no station
#: assignment reads this. It is a drawing aid until the customer answers A6.
#:
#: ⚠ CONTRADICTED 2026-08-14, THE SAME DAY IT WAS WRITTEN.
#:
#: The ACS meeting says lanes are **bidirectional** and that a blocked robot
#: waits then reroutes, and that **traffic control is the ACS's job, not ours**. If that
#: holds, assigning a direction per lane models a rule the plant does not have, and the
#: chevrons drawn from this constant are asserting something false.
#:
#: KEPT, NOT DELETED, for two reasons: the evidence is weak (the audio was deleted, the
#: bidirectional claim sits in a degraded repeated-line stretch, and the English
#: traffic-control exchange is not in the surviving transcript at all — see
#: open-questions A6), and the two-lane pairs still need explaining. Two-way flow on one
#: 2.10 m lane is impossible for a 1.60 m body, so the pairs must carry the two
#: directions somewhere.
#:
#: Do NOT build anything on this. It is a drawing aid whose premise is in doubt.
#:
#: Set to "left" to flip the whole network, or "none" to stop drawing chevrons.
LANE_DIRECTION_RULE = "right"


def two_lane_directions(road):
    """(lane_a_heading, lane_b_heading) in degrees for one `two_lane_roads()` row.

    `a` is the lower lane on the across-axis (west for ns, south for ew).
    Headings are 0 = +x (east), 90 = +y (north), 180 = west, 270 = south.
    """
    _name, axis, _a, _b, _div, _lo, _hi = road
    if axis == "ns":
        west, east = 270.0, 90.0            # keep right: north on the east lane
        return (west, east) if LANE_DIRECTION_RULE == "right" else (east, west)
    south, north = 0.0, 180.0               # keep right: east on the south lane
    return (south, north) if LANE_DIRECTION_RULE == "right" else (north, south)


def lanes_drawn():
    """LANES minus the rectangles that are known not to be roads."""
    out = []
    for L in LANES:
        if any(abs(L[0]-e[0]) < 0.5 and abs(L[1]-e[1]) < 0.5
               and abs(L[2]-e[2]) < 0.5 and abs(L[3]-e[3]) < 0.5
               for e in EXCLUDED_LANES):
            continue
        out.append(L)
    return tuple(out)


def coater_connectors():
    """Every station's connector as (x0, y0, x1, y1, coater, kind).

    ALL DERIVED from the sketch — none is in the drawing. A connector hugs the
    station's east edge and runs from the far side of the station pair to the
    spur, so a robot turns off the spur onto it and stops with the station
    alongside.
    """
    out = []
    half_len = ROBOT_3_5T[1] / 2.0          # station x half-extent, facing +/-x
    half_wid = ROBOT_3_5T[0] / 2.0          # station y half-extent
    span = COATER_STATION_PAIR / 2.0 + half_wid
    for i, ((sy0, sy1, side), sty) in enumerate(zip(COATER_SPUR, COATER_STATION_Y)):
        for kind, cx in (("ld", COATER_LD_X), ("uld", COATER_ULD_X)):
            x0 = cx + half_len + CONNECTOR_GAP
            x1 = x0 + CONNECTOR_WIDTH
            if side == "north":             # spur above: road runs up to it
                y0, y1 = sty - span, sy0
            else:                           # spur below: road runs down to it
                y0, y1 = sy1, sty + span
            out.append((x0, y0, x1, y1, i + 1, kind))
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
#: marks both in this area, so two rack families may share these columns. The
#: counts themselves are now reconciled — see WIP_COUNTS_DECK, where slide 20's
#: "3SET(13)" shows the 9EA and 4EA coater entries are one family of 13 counted in
#: two places. That fixes the totals but not the group-to-family mapping.
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

#: CHARGING — THREE SOURCES, THREE ANSWERS. Only the measured one is drawn.
#:
#:   * this file used to carry FOUR positions, from an early extraction never
#:     reconciled with anything since. Two of them sit at y ~132, in the ANODE
#:     cell, which we do not model — so the world drew blue pads on empty floor
#:     100 m south of the cathode line.
#:   * searching [D1] for charging blocks finds ONE type, `大AGV充电站双`
#:     ("Big AGV charging station, DOUBLE"), 3 placements in the whole drawing
#:     and exactly ONE in the cathode cell: (193.61, 242.31).
#:   * the system deck [S15][S30] says FIVE chargers for the cathode Big AGV
#:     fleet, five more for the anode.
#:
#: The world draws the one we can point at. The gap between one and five stays
#: visible as a question rather than being padded out — a wrong charger is worse
#: than a missing one, because a missing one looks like a question and a wrong
#: one looks like an answer.
#:
#: This is not tidiness. Ten cathode Big AGVs sharing five chargers at 2 hours
#: per 30% [S15] is a real limit on fleet availability, and it is contention we
#: have never simulated.
CHARGING_BAY_SIZE = (5.2, 2.2)

#: The single charging block actually found in the cathode cell.
CHARGING_MEASURED = ((193.61, 242.31),)

#: Deck [S15][S30].
CHARGING_EXPECTED_CATHODE = 5

#: The old unreconciled set. Kept so the numbers are not lost. NOT DRAWN.
CHARGING_UNRECONCILED = {
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

#: FLEET SIZE PER CLASS, cathode cell — deck slide 6, "1.1 System Configuration".
#: Ten Big AGVs on the cathode side, not three. The anode side has its own
#: 2 / 2 / 7 = 11, which we do not model (see open question B3).
#:
#: The charging note above already assumed ten; this is where the number comes
#: from, split by class. Our simulation runs three robots (B2).
FLEET_CATHODE = {"1.5T-Big AGV A": 2, "1.5T-Big AGV B": 2, "3.5T-Big AGV": 6}
FLEET_ANODE = {"1.5T-Big AGV A": 2, "1.5T-Big AGV B": 2, "3.5T-Big AGV": 7}

# ------------------------------------------------------------------- flow
#
# THE THREE BIG AGV LEGS — DECK SLIDE 16, THE MASTER "Big AGV Material flow"
# SLIDE FOR THE CATHODE CELL. Slides 17, 20 and 22 then repeat one leg each with
# its own station counts. Read off the slide XML (`<a:t>` runs) directly, because
# the slide images in `extracted/` are 1071x856 and their text is not legible —
# the same reason `sources.md` gives for not trusting the PNGs.
#
#     leg  robot            EA   from                 to             WIP option
#     A    1.5T-Big AGV A   2    ASRS                 Gravure Print LD   WIP Gravure Print
#     B    1.5T-Big AGV B   2    Gravure Print ULD    Coater LD          WIP Coater
#     C    3.5T-Big AGV     6    Coater ULD           Slitter LD         WIP Slitter
#
# CONFIRMED INDEPENDENTLY by the project lead in the 2026-08-04 meeting
# (`meeting_files/meeting-20260804-165629.txt` lines 174-176): "ASRS는 그래비로
# 가야 되고 / 그래비는 코트로 가야 되고 / 코트는 슬리터로 가야 되는 게 딱 정해져
# 있어요" — the chain is FIXED. Only the machine INDEX is free (line 177: "몇 번째로
# 가라는 거는 정해져 있진 않거든요"), and choosing it is CSM's job (line 341).
#
# THE WIP RACK IS AN ALTERNATE DESTINATION ON EVERY LEG, NOT AN EXCEPTION PATH.
# Slide 16 marks it "(Option)" on all three legs. The meeting explains the rule
# (lines 320-337): if the destination machine has no free port the robot puts the
# roll on the rack and it is fetched from there later. So a leg is
# `source -> (destination | rack)` and a fourth movement `rack -> destination`
# exists that no leg covers. Our job model has neither.
#
# EVERY HOP IS AN EXCHANGE, NOT A DELIVERY. Both load types appear on all three
# legs: "Roll Pallet" AND "Bobbin Pallet" [S16]. Slide 19 makes it concrete at the
# gravure — "Unwinder (AGV) bobbin Loading - roll Unloading" at one end,
# "Rewinder Roll (AGV) Roll Loading - bobbin unloading" at the other. The meeting
# gives the same shape (line 333): after dropping the roll the robot takes the
# empty core back to the ASRS. A job is therefore two transfers at each end, and
# there is a return flow of empties the model does not represent.
#
#: (leg, robot class, EA, from station, to station, WIP option).
FLOW = (
    ("A", "1.5T-Big AGV A", 2, "ASRS",              "GRAVURE_LD",  "WIP_GRAVURE"),
    ("B", "1.5T-Big AGV B", 2, "GRAVURE_ULD",       "COATER_LD",   "WIP_COATER"),
    ("C", "3.5T-Big AGV",   6, "COATER_ULD",        "SLITTER_LD",  "WIP_SLITTER"),
)

#: Both load types ride every leg [S16]. Bobbin = the empty core.
LOAD_TYPES = ("Roll Pallet", "Bobbin Pallet")

#: HOW MANY OF EACH STATION THE DECK SAYS EXIST [S16], against how many we have
#: actually placed in the world. The deck writes each as "1Set x 4EA" — one set
#: per machine, four machines.
#:
#: This table is the point of the section: it turns "the drawing is silent" into a
#: number we are short by, per station, and it is checked by
#: `audit_cad_world.py`. Placed counts come from the constants above.
STATION_COUNTS_DECK = {
    "ASRS":        1,     # "ASRS 1EA"
    "GRAVURE_LD":  4,     # "Gravure Print LD  1Set x 4EA"
    "GRAVURE_ULD": 4,     # "Gravure Print ULD 1Set x 4EA"
    "COATER_LD":   4,     # "Coater LD  1Set x 4EA"
    "COATER_ULD":  4,     # "Coater ULD 1Set x 4EA"
    "SLITTER_LD":  4,     # "Slitter LD 1Set x 4EA"
}

#: WIP RACK COUNTS [S16][S20][S22] — AND THE 9 + 4 = 13 THAT WAS OPEN.
#:
#: The WIP note at WIP_ACCESS_X said the deck marks "WIP Coater 4EA and 9EA" and
#: left the relation open. Slide 16 lists both entries and slide 20 gives the
#: total as "WIP Coater 13 | 3SET(13)" — so 9 + 4 = 13 is one family counted in
#: two places, not two conflicting readings. Sets: gravure 1SET(2),
#: coater 3SET(13), slitter 5SET(30).
#:
#: STILL OPEN: which of the four WIP_GROUP_Y groups belongs to which family. The
#: counts do not settle it — 8 access positions cannot be 13 or 30 slots either
#: way, which is the inference behind "access points, not slots".
WIP_COUNTS_DECK = {"WIP_GRAVURE": 2, "WIP_COATER": 13, "WIP_SLITTER": 30}

#: SLITTER LD IS 4EA — SO THE EIGHT-POSITION LINE AT x 185.62 IS NOT IT.
#:
#: SLITTER_DOCK_Y holds eight positions on one line and this file reads them as a
#: shared queue for the row. The deck says Slitter LD is "1Set x 4EA", one per
#: machine, like every other station in the plant. Eight is not four, so the line
#: is EITHER the queue (and the four LD stations are somewhere we have not found)
#: OR four LD stations plus four queue slots interleaved.
#:
#: This does not resolve open question A2, it sharpens it: we are now looking for
#: FOUR stations, one per slitter, and we know how many to expect. Nothing here is
#: placed on the strength of it — the slitter stations stay unplaced.
SLITTER_LD_EXPECTED = 4


def flow_summary():
    """One line per leg, for a generator or audit to print."""
    return [f"{leg}  {robot:<16} {ea} EA   {src} -> {dst}  (or {wip})"
            for leg, robot, ea, src, dst, wip in FLOW]


def stations_placed():
    """How many of each deck station we have actually put in the world.

    Deliberately derived from the geometry constants rather than hard-coded, so
    that placing a station updates this and the audit's shortfall shrinks on its
    own. `gravure_stations()` carries four LD and four ULD; the coaters carry four
    of each (CTR4's ULD inferred, counted because it IS drawn); the slitters and
    the ASRS carry none we can name.
    """
    grv = {"LD": 0, "ULD": 0}
    for _name, _sx, _sy, kind in gravure_stations():
        grv[kind] += 1
    return {
        "ASRS":        0,                       # one dock FOUND, not a station (A1)
        "GRAVURE_LD":  grv["LD"],
        "GRAVURE_ULD": grv["ULD"],
        "COATER_LD":   len(COATER_STATION_Y),
        "COATER_ULD":  len(COATER_STATION_Y),
        "SLITTER_LD":  0,                       # not placed — see SLITTER_LD_EXPECTED
    }


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
