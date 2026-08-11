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

### Correction, 2026-08-11 — the network is mixed, not uniformly paired

The first version of this ADR said two-way traffic is handled by **parallel lane
pairs**, generalising from a single example (x 250.08..252.18 alongside
253.04..255.14). Grouping all 20 north-south lanes into corridors shows that is
true of some and false of others:

**Two-lane corridors** — side-by-side rectangles spanning the *same* y-range, so
two robots can run abreast:

| corridor x | width | |
| --- | --- | --- |
| 157.94..162.64 | 4.70 m | two lanes, both y 227..274 |
| 185.45..190.48 | 5.03 m | two lanes y 172..220, two more y 220..267 |
| 213.25..216.95 | 3.70 m | two lanes y 175..271 / 175..283 |
| 257.53..261.23 | 3.70 m | two lanes, both y 174..196 |

**Single-lane corridors** — one rectangle, or two covering *different* stretches
of y (the same lane drawn in segments):

| corridor x | width | |
| --- | --- | --- |
| 170.55..172.98 | 2.43 m | y 170..217, then y 230..278 |
| 180.23..182.63 | 2.40 m | y 170..220, then y 230..280 |
| 209.04..211.14 | 2.10 m | single |
| 239.61..241.71 | 2.10 m | single |
| 136.01..138.61 | 2.60 m | two short segments |

So the plant uses **wide two-lane spines for the main runs and single lanes for
spurs and links**.

This does not change the decision — a 2.1 m single lane cannot hold the
stand-aside manoeuvre either, so give-way is impossible there too. It does change
the *replacement*: routing over parallel pairs covers only part of the network.
The single-lane sections need their own answer (see "To be built").

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

To be built — and the two corridor kinds need different answers:

- **Two-lane corridors** (4.70, 5.03, 3.70, 3.70 m): assign a direction per lane
  so the pair carries opposing flows. Two robots never meet head-on because they
  are never on the same lane travelling toward each other.
- **Single-lane corridors** (2.10–2.60 m): a direction alone is not enough,
  because two robots routed the *same* way still queue nose-to-tail and a robot
  entering against the flow has nowhere to go. These need **segment reservation**
  — the whole lane between two junctions held by one robot at a time, not just
  the junction. That is the bay interlock's shape applied to a length of lane,
  and the interlock has been faultless.
- **Queue positions** at each machine, so a robot waiting for a bay is off the
  lane by construction.

Segment reservation on a single lane is the piece with no precedent in the
current code. Junction reservation holds a point; this must hold a span, which
means a robot has to acquire the next segment before leaving the current one, or
release-then-acquire and risk being stranded mid-corridor.

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

- **Are the two-lane corridors one-way, and in which directions?** The
  `方向箭头` (direction arrow) blocks all sit at x≈390, outside the cell area,
  so the drawing does not say. If those corridors are bidirectional instead, the
  routing premise weakens and more of the network falls back on segment
  reservation. Worth asking the customer — a better question than the LD/ULD one.
- **Deadlock under segment reservation is unproven.** Two robots approaching a
  single-lane corridor from opposite ends, each holding the segment behind them,
  is a circular wait — the same shape as the junction hold-and-wait that caused
  the worst failures on 2026-08-10. The fix there was to release on a failed
  claim; whether that is sufficient for spans rather than points is untested.
- Lane graph now exists: 49 rectangles reduced to 11 corridors with **51
  junctions** (`References/local/gazebo-world/extracted/lane_graph.json`).
  Direction of travel is still absent.

## Record of correction

The first version of this ADR generalised "parallel lane pairs" from one
measured example to the whole network. Grouping all 20 north-south lanes showed
four corridors are genuinely two-lane and five are single. The decision stands —
give-way does not fit a 2.1 m lane either way — but the replacement design was
wrong for half the network, and single-lane segment reservation is a harder
problem than the paired-lane routing originally proposed.
