# CAD world — what we do not know

`cad_plant.world` is generated from `src/MES/csm/csm/plant_cad.py`, which is
measured from two customer drawings. This file lists **everything the drawings do
not tell us**, so that the gaps are visible rather than quietly filled in with a
guess.

Written 2026-08-11, after generating the world for the first time and running
`audit_cad_world.py` against it. Several of these were found BY building the
world — they were invisible in the extracted numbers and obvious on screen.

**Rule for this file: nothing here gets an invented answer.** Where we have taken
an assumption in order to keep moving, it is recorded under "Assumptions we took"
with the cost of being wrong, and it stays on this list until someone confirms it.

## How to read the priority

| | meaning |
| --- | --- |
| **BLOCKING** | we cannot lay out that part of the plant at all |
| **HIGH** | we can build it, but a wrong answer means rebuilding |
| **MEDIUM** | affects behaviour or realism, not layout |
| **LOW** | cosmetic, or we can measure it ourselves later |

---

## A. For the customer (Motion Device / CATL)

### A1. Where do AGVs dock at the ASRS? — **BLOCKING**

The ASRS is the source of every roll. Its body spans **y 166.35 to 223.09**
(56.7 m long) at x 129.95..140.88. In the whole cathode cell we found **one**
AGV position anywhere near it: **(151.85, 219.43)**, at its extreme northern end
and 9.9 m off its face.

One position cannot serve a 57 m machine that feeds the entire line.

Either the ASRS is served from a face this drawing does not cover, or its
positions are on a layer we have not found.

**Until this is answered, segment A (ASRS → Gravure LD) cannot be laid out.**
That is one of our three robot legs. We will not invent the positions.

> **Ask:** Can you send the AGV loading/unloading positions for the foil ASRS —
> which face, how many stations, and their coordinates?

### A2. Where do AGVs dock at slitters 1, 2 and 3? — **BLOCKING**

> **Sharpened 2026-08-13 by the deck, not answered.** Slide 16 says
> **"Slitter LD 1Set x 4EA"** — four stations, one per slitter, the same pattern as
> every other machine in the plant. The eight-position line at x 185.62 is
> therefore **not** the LD stations: eight is not four. So this question now has a
> target number, and the line is either a shared queue with the four stations still
> unfound, or four stations with four queue slots interleaved. The world draws
> those eight pads in magenta rather than as ordinary positions
> (`generate_cad_world.py`), and `plant_cad.SLITTER_LD_EXPECTED` records the four.

Same shape of problem. Nearest-machine assignment over all 45 measured positions:

| machine | positions within 12 m |
| --- | --- |
| SLT1 (y 220.23..227.83) | **none** |
| SLT2 (y 230.01..237.61) | **none** |
| SLT3 (y 243.73..251.33) | **none** |
| SLT4 (y 253.51..261.11) | 2, at 6.0 and 6.1 m |

There **is** a line of eight positions at x 185.62 running y 233..260, which is
why `plant_cad.py` currently records them as `SLITTER_DOCK_Y`. But see A3 — that
reading is not safe, and if it is wrong then three of four slitters are unserved.

> **Ask:** Which AGV positions serve slitters 1-4?

### A3. Does the x 183-186 corridor serve the gravures, the slitters, or both? — **HIGH**

This corridor runs between the gravure row (east face x **180.07**) and the
slitter row (west face x **191.64**). The positions in it are almost exactly
between the two:

| position line | to gravure face | to slitter face |
| --- | --- | --- |
| x 183.5 | 3.43 m | 8.14 m |
| x 185.62 | **5.55 m** | **6.02 m** |

The x 185.62 line is **0.47 m** from being nearer the slitters than the gravures.
`plant_cad.py` assigns it to the slitters by reasoning, not measurement, and says
so. A 0.47 m margin is not a measurement.

This is also the busiest part of the network — one corridor, two machine rows,
eight positions on one line — so getting it wrong is expensive.

> **Ask:** In the corridor between the gravures and the slitters, which side does
> each row of AGV positions serve?

### A4. What does the AGV symbol's rotation mean? — **HIGH**

Every position carries a rotation, and we read it as the direction the robot
faces when parked. **The evidence does not support that reading**, which matters
because the rot 0 / rot 180 pairing is the only thing suggesting which port is
loading and which is unloading.

Positions in the gravure/slitter corridor at rot 0 (which we read as facing +x,
i.e. east):

| position | faces | what is there |
| --- | --- | --- |
| (183.65, 239.97) | east | the gap between SLT2 and SLT3 — no machine |
| (184.38, 207.52) | east | open floor |
| (184.68, 190.87) | east | open floor |
| (184.65, 266.88) | east | open floor |

Four positions pointing at nothing. So either the robots **reverse** into these
positions (block +x is the rear), or the block's local axis is not the robot's
forward axis at all.

> **Ask:** In the AGV layout drawing, does the symbol's arrow show the direction
> of travel, or the direction the robot faces when parked? Do the AGVs reverse
> into any station?

> **Partial answer 2026-08-14 — reversing in is real.** The ACS schema makes reversing
> into a station a first-class per-task option, so backing in is supported behaviour
> rather than an oddity. That makes the
> "robots reverse into these positions" reading of the four rot-0 positions
> plausible, though it still does not say which positions do it.

### A5. Do AGV lanes pass through the coaters? — **HIGH**

> **Evidence for the drive-in reading, 2026-08-14 ACS meeting.** They twice described
> the robot **entering the equipment** — a permission request before entry, a named
> permit signal without which entry is refused, and the fork raised **before** entry
> rather than after. Record: `References/local/meetings/2026-08-14-acs/`.
>
> That supports reading 1 (the coater is entered by AGVs and these lanes are drive-in
> bays) over reading 2 (bounding-box artefact). **Not proof for the coaters
> specifically** — they were describing equipment generally — but if it holds,
> `DOCK_STANDOFF` moves from 6.90 m to roughly 20.4 m. Worth confirming per machine
> type rather than assuming across the row.

The audit's first check failed on this, at all four coaters:

| lane | y span | runs into |
| --- | --- | --- |
| 1 | 233.53..236.13 | CTR1, 35.2 m² |
| 2 | 240.68..243.28 | CTR2, 18.4 m² |
| 3 | 257.40..260.00 | CTR3, 35.2 m² |
| 4 | 265.06..267.66 | CTR4, 20.1 m² |

Each of these lanes runs west from the main spine at x 157.94 to **x 124.56** —
which is **13.5 m inside** the coater's block extent of x 113.25..138.08.

We checked the drawing geometry directly. Inside the region where the lane
crosses CTR2 there are 44 equipment vertices on layer `C-EQU`; in a control
region on the same coater with no lane there are 33. **The density is the same**,
so the drawing does not show a notch or an opening there — the lane and the
equipment are simply drawn on top of each other.

Two readings, and we cannot choose between them:

1. the coater is **entered** by AGVs and these lanes are drive-in bays; or
2. the coater's real floor footprint is narrower than its block bounding box,
   with the machine at the west end and the east ~13.5 m being apron.

Reading 2 would move the coater's east face from 138.08 to about 124.56, which
changes `DOCK_STANDOFF` from 6.90 m to about 20.4 m — so this is not a detail.

> **Ask:** Is the coater block in the drawing the machine itself, or the whole
> coater cell including the AGV apron? Do AGVs drive inside it?

### A6. Which way does traffic run on each lane? — **HIGH**

> **Reframed 2026-08-14 by the ACS meeting — and it moves this OFF our plate.**
> Record: `References/local/meetings/2026-08-14-acs/`.
>
> Two statements from the ACS team change what this question is for:
>
> 1. **Traffic control is the ACS's**, not ours. Corridor routing and deadlock
>    avoidance are theirs to build. Confirms the assumption `ARCHITECTURE.md` §10 Q7
>    carried for months.
> 2. **Lanes are bidirectional**, and a blocked robot **waits, then reroutes** —
>    around five minutes was mentioned as the threshold.
>
> So the answer to "which way does traffic run" is apparently **both ways, and the
> ACS sorts it out.** That means we should NOT be assigning a direction per lane at
> all — doing so would model a rule the plant does not have.
>
> ⚠ **Caveats, and they are real.** The audio was deleted at the end of the meeting;
> a rough room-mic transcript is all that survives. The bidirectional claim sits in a
> degraded, repeated-line stretch (four consecutive identical lines at ~54:33), and
> the English exchange that establishes traffic-control-is-theirs is **not in the
> surviving transcript at all** — that stretch was re-transcribed separately and the
> output was not kept. Consistent with everything else in the meeting, but not
> provable. Needs the written follow-up.
>
> **Consequence for the world today:** `plant_cad.LANE_DIRECTION_RULE` and the
> direction chevrons drawn on the two-lane roads assert one-way flow under a
> keep-right assumption. That now contradicts the customer. They should come out, or
> be re-labelled as "structure only, direction unknown" — see the note at
> `TWO_LANE_MIN_COMBINED`.
>
> **Still genuinely open:** the two-lane corridors exist (Road 1 spine 4.70 m, Road 2
> east 3.70 m). If lanes are bidirectional, what are the *pairs* for? Two-way flow on
> a single 2.10 m lane is physically impossible for a 1.60 m body, so the pairs must
> carry the two directions somewhere. Which lane, on which corridor, is still unsaid.

Carried over from
[the give-way ADR](../adr/2026-08-11-cad-world-no-give-way.md), and now the main
thing standing between us and a router.

The cell has 37 lane rectangles and 30 crossings. Four corridors are genuinely
two-lane (widths 4.70, 5.03, 3.70, 3.70 m) and five are single (2.10-2.60 m). The
`方向箭头` (direction arrow) blocks all sit at x≈390, **outside the cell area**,
so the drawing does not say.

This decides the whole traffic design. With directions, two-lane corridors carry
opposing flows and robots never meet head-on. Without them, every corridor needs
segment reservation, which is a harder problem and a deadlock risk.

#### Correction, 2026-08-11 — arrows DO exist in the cell, but not on AGV layers

Overlaying the drawing on the world put arrow glyphs on screen inside the cell,
which contradicted the sentence above. Extracting them settles it, and the
original claim was wrong in its reason though right in its conclusion:

**42 thick arrow glyphs exist in the cathode cell.** Every single one is on an
EQUIPMENT layer — `_COATER CATHODE` (36), `_MIXING EQ_CATHODE` (5),
`FOIL ASRS_CATHODE` (1). They are machine-internal material-flow arrows, 0.5-5 m
long, several of them double-headed. A further 36 thin glyphs on layer `4` are
dimension leaders, 2-3 cm thick.

**None is on an AGV layer, and none annotates a lane rectangle.** So the answer
does not change — the drawing still does not say which way AGV traffic runs — but
"no arrows lie inside the cell area" was false, and anyone re-checking this would
have found them and concluded the search had been careless.

Worth noting for A5: the densest cluster of these equipment arrows sits at
x 134-137, the coater's east end, which is exactly where the lanes penetrate the
coater bounding box.

> **Ask:** Are the AGV lanes one-way? For the two-lane corridors, which lane runs
> which way?

### A7. Which port of each pair is loading and which is unloading? — **MEDIUM**

Each machine face has two positions 4.10 m apart, one at rot 0 and one at rot
180. The protocol workbook confirms 上料工位 (loading) and 下料工位 (unloading)
are separate stations with separate handshakes. **Neither says which physical
position is which.**

We assume the lower-y position is LD, because material flows north. **Cost of
being wrong: 4.10 m of driving per job.** It does not invert the job model.

Lowest-value question on this list — ask it last, or not at all.

### A9. The gravure's own AGV positions are in the aisle, not at the machine — **HIGH**

Raised 2026-08-13, by correcting the gravure bodies. The bodies are now at
x 173.19..180.07 (the machine corridor, 7.25 m wide); the five positions on the
gravure's own layer `凹版1.5T大AGV路线` are at x 183.20..184.68, which is the AGV
aisle **on the far side of the road at x 180.23..182.63**:

| position | x from gravure east face (180.07) | what lies between |
| --- | --- | --- |
| (183.20, 199.17) | 3.13 m | the 2.40 m road |
| (183.51, 173.76) | 3.44 m | the 2.40 m road |
| (183.51, 182.51) | 3.44 m | the 2.40 m road |
| (184.38, 207.52) | 4.31 m | the 2.40 m road |
| (184.68, 190.87) | 4.61 m | the 2.40 m road |

A robot parked there cannot reach the machine without crossing a road, so these
are **not** the LD/ULD stations — most likely a queue or approach line. Note the
y values still line up with the machine ends (173.76 and 190.87 bracket GRV1's
173.76..190.87 span), which is why they were read as end stations before.

`GRAVURE_STATIONS` therefore places GRV1's LD and ULD on the **body's own
centreline** at x 176.63, where the project lead's annotation marks them, and the
aisle pads stay drawn as measured positions with no name attached.

> **Ask:** In the gravure row, where does the AGV physically stand to load and
> unload — in the aisle at x ~183.5, or against the machine at x ~180? And are the
> five positions on the gravure layer stations or a queue?

### A10. What is inside the foil ASRS? — **MEDIUM**

Raised 2026-08-13. The project lead's render
(`extracted/factory_visual_flow.png`) shows the foil ASRS as a crane-aisle store:
**two multi-level racking walls** the full 56.7 m, a **central aisle**, and a
**stacker crane** in it. The world had it as one solid 10.9 × 56.7 × 3.0 m slab —
wrong in kind, and it made the crane aisle a wall.

The footprint is measured. The inside is not, and two attempts to measure it
failed — both recorded at `plant_cad.ASRS_AISLE_W` so the next attempt starts
further along:

* `cathode_cell_trimmed.dxf` holds **no** ASRS geometry — `trim_dxf.py` flattens
  one block level and this equipment is nested deeper.
* In [D1], `foil ASRS` is placed once inside `reuse equipment` at scale 25.4, and
  re-inserts ~30 `FOIL ASRS_CATHODE$0$…` sub-blocks at scale 0.0393701. Their
  local x values form two mirrored clusters (+100,570..+100,850 and
  −100,569..−100,602) that *look* like two rack walls, but the implied separation
  is ~201,000 local units and no unit reading makes that 10.9 m.

So `ASRS_AISLE_W = 2.50` and `ASRS_HEIGHT = 12.0` are **conventions**, named as
such, like `MACHINE_H`. Cosmetic today — nothing routes inside the ASRS and the
AGV docks outside it — but it stops being cosmetic the moment anyone reads roll
capacity off the rack depth.

> **Ask:** For the foil ASRS — how deep is each racking wall, how wide is the
> crane aisle, how many levels, and how tall overall? And which end does the
> stacker crane hand off to (that is A1 from the other side)?

### A8. Machine heights and door positions — **LOW**

The drawings are plan views with no heights. Every machine in the world stands
3.0 m tall, which is a drawing convention so the layout reads in 3-D. Fine until
something needs to pass over or under.

---

## B. For the professor / internal

### B0. The job model is one-way; the plant exchanges and buffers — **HIGH**

> **Confirmed 2026-08-14 — the exchange is a physical button.** The ACS team described
> **three buttons on the machine**: bring material, take material away, and one that
> does both at once. That third one is `TaskType.SWAP`. The exchange is not a modelling
> idea we invented; an operator presses it. They also confirmed both roll and bobbin
> move on every hop, matching the capacity deck.
>
> **RESOLVED IN SHAPE 2026-08-14 by the ACS GraphQL schema** (analysis held at
> `References/local/acs/`). An order is an ordered **list of tasks**, with load and
> unload among the task kinds. So a deliver-and-collect visit is **one order, two
> tasks**.
> The exchange needs no new primitive; `TaskType.SWAP` maps to a two-task order.
> The empty-bobbin return is a second task, not a second job.
>
> That closes the *modelling* half of B0. The **routing** half — who diverts to the
> WIP rack when the destination is full — is still open and still ours.
>
> **And they have thought about the buffer where we have not.** Carrier identity
> *vanishes* at equipment stations but *persists* at the buffer — our WIP rack. That is
> the `rack → destination` branch we still have no job type for, and it is now the
> largest hole in our job model. Nobody in the meeting claimed it, and everything else
> they declined landed on us.

Added 2026-08-13 from the deck's own material-flow slides and the 2026-08-04
meeting. This is not a layout gap — the geometry is fine — it is the **shape of a
job** being wrong, and it is the largest single gap between our model and the
plant. Recorded in `plant_cad.py`'s `flow` section with sources.

The deck [S16] defines three legs, and every one of them is
`source -> (destination | WIP rack)` carrying **two** load types:

| leg | robot | EA | from | to | option |
| --- | --- | --- | --- | --- | --- |
| A | 1.5T-Big AGV A | 2 | ASRS | Gravure Print LD | WIP Gravure Print |
| B | 1.5T-Big AGV B | 2 | Gravure Print ULD | Coater LD | WIP Coater |
| C | 3.5T-Big AGV | 6 | Coater ULD | Slitter LD | WIP Slitter |

Three things follow that we do not model:

1. **Each hop is an exchange, not a delivery.** Both `Roll Pallet` and
   `Bobbin Pallet` ride every leg [S16], and slide 19 spells it out at the
   gravure: bobbin loading / roll unloading at the Unwinder, roll loading /
   bobbin unloading at the Rewinder. The meeting says the same (transcript 333):
   after dropping the roll the robot returns the empty core to the ASRS. Our job
   moves one item one way.
2. **The WIP rack is a routing branch on every leg, marked "(Option)".** If the
   destination has no free port the roll goes to the rack (transcript 320-337).
   That also implies a fourth movement — `rack -> destination` — that no leg
   covers and no job type exists for.
3. **Ten robots, not three, in three classes with fixed legs.** Slide 6 gives
   cathode 2 / 2 / 6. A robot is bound to a leg, so the fleet is not
   interchangeable — which is a different scheduling problem from the one
   `sim_acs.py` solves.

The chain itself is confirmed twice over and is **fixed**: transcript 174-176,
"ASRS는 그래비로 가야 되고 / 그래비는 코트로 가야 되고 / 코트는 슬리터로 가야 되는
게 딱 정해져 있어요". Only the machine *index* is free (line 177), and choosing it
is CSM's job (line 341).

### B1. Do we simulate two robot types or one? — **HIGH**

The system deck specifies two machines:

| model | documented | simulated now |
| --- | --- | --- |
| 1.5T-Big AGV A/B (amr1, amr2) | 1,300 × 1,900 mm | 900 × 1,600 |
| 3.5T-Big AGV (amr3) | 1,600 × 2,000 mm | 900 × 1,600 |

We model all three as one undersized body. In the verified 5.0 m aisle world that
was survivable. In a **2.1 m lane** it is not: a 1.60 m body in a 2.1 m lane
leaves 0.25 m per side, and we have been testing 0.90 m bodies with 0.60 m.

The URDF change is straightforward. What it breaks is every clearance constant in
`sim_acs.py`, all of which were tuned against the small body.

### B2. How many robots does this plant actually run? — **HIGH**

We simulate three. The drawing has **51 AGV positions** and the deck describes
six 3.5T AGVs on the coating leg alone. Our traffic layer has never been run with
more than three robots, and every deadlock we found appeared at two or three.

### B3. Do we model the anode cell? — **MEDIUM**

The hall is 306 × 209 m and contains both cells; we model only the cathode side
(y > 160). The anode cell at y 27..72 has 26 AGV positions of its own. The world
currently draws the full hall shell with half of it empty, which is honest but
means the walls are further away than anything we simulate.

### B4. Is Gazebo usable at this scale? — **MEDIUM, and testable today**

188 static models over 306 × 209 m, versus roughly 100 over 43 × 26 m in the
verified world. Travel times go up by about 10× — a job that took 90 s will take
minutes — so a one-hour soak covers far fewer jobs than it used to.

This is the one question on the page **we can answer ourselves**, by launching
the world and watching the real-time factor. It should be answered before any
robot is put in it.

---

## Assumptions we took, and what they cost

These are in the code today. Each one is a guess with a stated price.

| # | assumption | where | if wrong |
| --- | --- | --- | --- |
| 1 | lower-y port is LD | `PORT_ORDER_LD_FIRST` | 4.10 m of driving per job |
| 2 | x 185.62 line serves the slitters | `SLITTER_DOCK_Y` | three slitters unserved (A2) |
| 3 | block rotation = robot facing | `AGV_POSITIONS` | docking approach reversed (A4) |
| 4 | coater body = block bounding box | `COATER_X` | dock standoff 6.90 m vs ~20.4 m (A5) |
| 5 | machine height 3.0 m | `generate_cad_world.py` | cosmetic only |
| 6 | coater centre = area label + 1.15 m | `COATER_Y` | up to ~1 m of machine position |

## Things we found ourselves and do not need to ask

Recorded so they are not asked twice:

- **Coater count and pitch** — 4 machines at 12.0 m pitch, matching the deck's
  "Coater 4 EA". An earlier reading of 23.96 m was measuring alternate machines.
- **Coater width** — 24.83 m, the `Cathode Coater template` variant. The 27.75 m
  figure was the union of two different block variants, one of them the anode
  line's.
- **Dock columns at the coaters** — three, not two: dock at x 144.98, queues at
  148.51 and 152.05, uniform 3.54 m pitch. The first reading found two because it
  searched one layer.
- **CTR1 and CTR4 LD/ULD pairs** — present. Their apparent absence was an
  extraction miss.
- **The 26 "orphan" positions at y 27..70** — the anode cell, not an anomaly.
- **WIP Coater 9EA and 4EA are one family of 13**, not two conflicting readings.
  Slide 20 gives the total as "WIP Coater 13 | 3SET(13)", and slide 16 lists the
  9 and the 4 separately — so it is 13 slots counted in two places. Sets are
  gravure 1SET(2), coater 3SET(13), slitter 5SET(30). Recorded in
  `plant_cad.WIP_COUNTS_DECK`. **Which of the four `WIP_GROUP_Y` groups belongs to
  which family is still open** — the counts do not settle that.
- **The station counts are all "1Set x 4EA"** [S16]: Gravure Print LD/ULD, Coater
  LD/ULD and Slitter LD are four each, ASRS is 1EA. So the plant has one station
  set per machine everywhere, and `audit_cad_world.py` check 5 now prints what we
  are short of that: ASRS 0/1, GRAVURE_LD 1/4, GRAVURE_ULD 1/4, SLITTER_LD 0/4.
- **Which robot runs which leg** — the deck states it outright on slides 17, 20 and
  22, one leg per slide. This was very nearly written down as a derivation; it is
  not one. See B0.
- **Two positions overlap**: (183.51, 266.82) and (184.65, 266.88) share 1.06 m²
  when both are occupied by a 3.5T body. They are 1.14 m apart with different
  headings, so they are alternatives rather than two simultaneous stations — or
  one belongs to the smaller 1.5T AGV. Not worth a question.

## Where to look before asking

- `plant_cad.py` — every number with its derivation
- `docs/gazebo_world/sources.md` — which drawing, which layer, how converted
- `References/local/gazebo-world/extracted/` — the extraction output and the
  plan renders (gitignored; the drawings are confidential and this repo is public)
- `ros2 run trnav_2ws_gazebo audit_cad_world.py` — re-runs the four consistency
  checks that produced A2 and A5
