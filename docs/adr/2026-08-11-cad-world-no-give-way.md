# ADR 2026-08-11 — The CAD-derived world has no give-way system

- **Status**: Accepted — 2026-08-11. Decision taken by the project lead on the
  measured lane geometry below. Applies to the `cad-world` branch only; the
  verified simulation on `sim-verified-2026-08-10` keeps give-way and needs it.
- **Rollback**: Reversible — the give-way code still exists on `main` and on the
  tag. Nothing is deleted from the running system by this ADR.

## Context

The give-way system was built over 2026-08-10 and cost most of a day: a
handshake where one robot is chosen to stand aside, drives ~2 m off the lane,
reports clear, waits for the other to pass, then rejoins. It produced four
defects in sequence — a junction held while yielding, a homing robot that could
never yield, a stand-aside aimed along the aisle instead of off it, and a
partner exclusion with no lower bound that let two robots close to 0.116 m.

It exists because `plant.py` models each aisle as a **single lane** — one chain
of nodes down the centre, no width. Two robots meeting on it cannot pass, so
somebody has to leave the road.

**The drawings say the plant is not built that way.**

Measured from `FM2 Front-end layout V7 20260709_0806.dwg`, block `AGV PATH0508`
(49 lanes in the cell area):

| lane width | count |
| --- | --- |
| 2.1 m | 24 |
| 2.4 m | 8 |
| 2.6 m | 17 |

A 3.5T-Big AGV is **1.60 m wide** (system deck slide 2). A 2.1 m lane leaves
**0.25 m per side**. There is nowhere to pull over. The manoeuvre give-way
depends on cannot be performed.

Two-way traffic is handled instead by **parallel lane pairs** — e.g. lanes at
x 250.08..252.18 and x 253.04..255.14, 5.06 m combined, enough for two robots
to pass side by side (3.2 m of body).

And every machine has a **queue position 3.54 m behind its dock** (measured at
the coaters, `BIG& SMALL AGV Layout V1 20260810.dwg`). A robot waiting for a bay
stands off the lane. Our model has no queue, so waiting robots stand *on* the
aisle — which is what produced the deadlocks and the single measured collision.

## Decision

**The CAD-derived world does not implement give-way.** Head-on conflict is
prevented by routing, not resolved by yielding.

Retired for this world:

- `_sidestep_target`, the stand-aside drive, `_stood_aside` handshake
- `who_yields`, `partner_of`, `yielding`, `encounter_over`
- `YIELD_LIMIT` and the give-up path
- `_off_the_road` / "already clear" and `YIELD_FLOOR`

Kept, because they are not give-way and remain necessary:

- **Layer 1** (`_threat`) — a predictive collision guard is required whatever
  the routing. It is the last word before any velocity is published.
- **Junction reservation** — lanes still cross, and layer 1 can only say *stop*,
  never *who goes*.
- **The hold-and-wait fix in `claim_junction`** — a robot refused a junction
  releases its own. That is fundamental to any reservation scheme and was the
  root cause of the worst deadlocks.
- **The true-footprint body model** — `STOP_GAP` as real clearance rather than a
  capsule axis separation.

To be built:

- **One-way routing** over the parallel lane pairs, so two robots are never
  scheduled toward each other on the same lane.
- **Queue positions** at each machine, so a robot waiting for a bay is off the
  lane by construction.

## Consequences

**A simpler system.** Give-way was four interacting rules with a 45 s timeout
and a failure mode that destroyed jobs. Routing has none of that: if two robots
cannot meet head-on, there is nothing to arbitrate.

**A week of work does not carry over**, and that is the correct outcome rather
than a loss. The defects it produced were real and the fixes were right; they
were fixes to a subsystem that models a plant which does not exist.

**Routing becomes load-bearing.** With no yielding, a routing bug is a deadlock
rather than an inefficiency. `roads.py` must encode direction, and the router
must refuse to plan against it.

**Unverified.** No CAD-derived world has been run. Whether one-way routing plus
junction reservation is sufficient at the documented fleet size — six 3.5T AGVs
on segment C, not one — is untested. The claim here is only that give-way cannot
work in a 2.1 m lane, which is arithmetic, not that its replacement is proven.

## Open

- **Are the parallel lanes actually one-way, and in which directions?** The
  `方向箭头` (direction arrow) blocks all sit at x≈390, outside the cell area.
  If the pairs are bidirectional the routing premise weakens. Worth asking the
  customer — a better question than the LD/ULD one.
- Lane connectivity is not yet a graph: 49 rectangles, no nodes or edges.
