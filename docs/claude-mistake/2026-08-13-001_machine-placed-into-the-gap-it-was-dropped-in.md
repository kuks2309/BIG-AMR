---
date: 2026-08-13
id: 2026-08-13-001
type: rule-violation
severity: high
reflected_assets:
  - src/MES/csm/csm/plant_cad.py
  - src/Sim/trnav_2ws_gazebo/scripts/generate_cad_world.py
  - src/Sim/trnav_2ws_gazebo/scripts/audit_cad_world.py
  - docs/gazebo_world/open-questions.md
---

# A 6.9 m machine was drawn 2.82 m wide, because it was sized to the gap it was dropped into

## What the user said

Against a screenshot of the world, with the misplaced body circled in blue and the
correct positions drawn in white:

> 「you place the grv1 in wrong place ... blue grv1 is which you have placed and
> white i have added is the correct place」

## The error

`GRAVURE1_BODY` put the gravure at **x 182.63..185.45** — the 2.82 m gap between
the roads at 182.63 and 185.45. That gap is an **AGV aisle**. The machine belongs
in the corridor at **x 173.19..180.07**, which is what `GRAVURE_X` had said all
along.

## The file already contained the number that disproves it

This is the part that matters. No new measurement was needed:

| | |
| --- | --- |
| `GRAVURE_SIZE` (same file, 80 lines up) | **6.9** m wide |
| body as placed | **2.82** m wide |
| discrepancy | **4.08 m — the body was 41% of its own declared width** |

Two more, both derivable from data already in the file:

* The road structure has exactly **one** gap that fits 6.9 m: x 172.98..180.23,
  **7.25 m**. `GRAVURE_X` (6.88 m) sits in it with ~0.2 m either side.
* **Five AGV positions land inside the body as placed** (183.20, 183.51 ×2,
  184.38, 184.68). A dock cannot be inside the machine it serves.

## Why the reasoning went wrong

The retracted comment justified the move with density: "the box holds 41 drawing
entities; the dense structure is at x 183.3..185.6 with 167,565 vertices."

**Density is not identity.** The x 183.3..185.6 column is the
`凹版1.5T大AGV路线` route artwork and aisle furniture — precisely where a drawing
carries the most detail per square metre. Vertex count was treated as proof of
"machine here", and it only ever showed "drawing detail here".

The 41-entity count was then read as proof of the *negative* — that `GRAVURE_X`
could not be a machine. An area outline having few entities is what an outline is.

## Why no check caught it

`audit_cad_world.py` check 2 tests parking positions against `machines()`, and
`machines()` builds the gravures from `GRAVURE_X`/`GRAVURE_Y`. The body actually
drawn came from `GRAVURE1_BODY`, a separate constant.

**So the one body in the world not built from the audited constants was the one
body the audit could not see.** The five pads sitting inside it were never tested
against it. It survived until a human looked at the screen.

This also means my own report of "6 findings, all pre-existing" was true of the
checks that existed and blind to this.

## Fix

* Gravures drawn from `GRAVURE_X` × `GRAVURE_Y`, all four, at 6.9 × 17.1 m.
* `GRAVURE1_BODY` → `GRAVURE1_BODY_RETRACTED`; `GRAVURE1_CONNECTORS` likewise,
  since they spanned the aisle's roads. **Not re-derived** — the corrected
  connectors need the diagram the correction came from.
* `GRAVURE_STATIONS` moved to the body centreline (x 176.63) at its two ends, LD
  south / ULD north, as the annotation marks.
* New open question **A9**: the gravure's own AGV pads are in the aisle across a
  road from the machine, so they are a queue, not the LD/ULD stations. Recorded,
  not resolved.
* **`audit_cad_world.py` check 6 — drawn body extent vs declared size.** Passes
  now; would have failed the moment the 2.82 m body was written.

## Rule (reflected in assets)

**When you place geometry, check it against the dimension the same file already
declares for it.** A body whose extent is derived from its surroundings — the gap
it fits, the roads either side — is not measured, and the machine's own size
constant is the cheapest possible contradiction test.

**Vertex density locates drawing detail, not machinery.** Where AGV routes,
dimension leaders and aisle furniture live, density is highest and machines are
absent. A claim of the form "the dense structure is here, so the machine is here"
needs a footprint that matches the machine's declared dimensions.

**An invariant that reads a constant cannot audit a body built from a different
constant.** When a special case bypasses the general path (`GRAVURE1_BODY` beside
`machines()`), the checks that cover the general path silently stop applying — so
either route the special case through the same accessor, or add a check that walks
what is actually drawn.

## Relation to earlier entries

Same family as **2026-08-10-005** (speculation overriding a recorded
measurement): there, a threshold with recorded evidence was reversed on a
calculation; here, a width with a recorded measurement was overridden by a
density argument. Both replaced a measured number with an inference and left the
measured number sitting in the file, unreferenced.
