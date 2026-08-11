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

### A5. Do AGV lanes pass through the coaters? — **HIGH**

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

### A8. Machine heights and door positions — **LOW**

The drawings are plan views with no heights. Every machine in the world stands
3.0 m tall, which is a drawing convention so the layout reads in 3-D. Fine until
something needs to pass over or under.

---

## B. For the professor / internal

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
