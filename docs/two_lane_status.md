# two_lane — status, 2026-08-26

Branch `two_lane`, **nothing committed yet**. 836 tests pass — source the
workspace first or `csm` and `trnav_msgs` will not import:

    source /opt/ros/humble/setup.bash && source install/setup.bash
    cd src/MES/csm && python3 -m pytest -p no:anyio test -q

## What this branch is

The single-lane give-way road was replaced with **two one-way lanes** per aisle,
same rectangle. Every station and parking bay has a junction on **both** lanes,
and a spur crosses both to reach its dock or bay.

## The rules — there are only two (user, 2026-08-26)

1. **Every robot follows the lines.** The road graph is the only path.
2. **Crossing the road, a robot pauses before it.** It stops `ROAD_EDGE`
   = 1.55 m short of the lane, tells every robot within `HOLD_RADIUS` = 6 m to
   stand still, and goes when nothing blocks its path onto the road.

   Rule 2 now runs BOTH WAYS — see the section below. The user stated it as
   "leaving a dock", and going in is the same manoeuvre backwards.

Everything else was **deleted**: the whole give-way system (sidestep, lay-bys,
yield partners, head-on detection, the old Rules 1–5), the junction reservation
red-light system, the merge give-way rule. `sim_acs.py` went 3385 -> 2382 lines.

**Kept, and not as rules:**
- **Layer 1** (`_threat`, `STOP_GAP` 0.30 m) — the last physical stop before two
  bodies touch. It only ever says stop; it never decides who goes.
- **Station interlock** (`request_entry`) — one robot per machine bay, because
  the machine protocol carries exactly one "AGV is inside" bit.
- **Robot-ahead stop** — queueing, part of following the line.
- **Rotation guard** — no rotating on a final approach, in a bay, on a spur,
  or while crossing a lane onto one.

## FIXED 2026-08-26 — rule 2 now runs both ways

**Rule 2 covered a robot coming OUT of a dock. Nothing covered one going IN.**

All 27 docks and all 10 parking bays sit outside both lanes, so every approach
crosses a live lane. Measured 2026-08-26 15:36:24:

    amr2 (-20.69,-4.50) eastbound on the south OUTER lane, dead straight 4 m
    amr3 (-19.09,-4.85) crossing that lane on the SLT_LD3 spur, going IN
    CONTACT, gap -0.007 m

Both robots obeyed both rules. The rule was missing a half.

**What was added.** `SimRobot._crossing` / `_pause_before_crossing`
(`sim_acs.py`), hooked into `drive()` just before the `_held_for_a_leaver`
check, and `plant.outer_lane_beyond`. Same `ROAD_EDGE`, same `HOLD_RADIUS`,
same `_blocks_path`, and the hold rides on the same flag the way out uses —
`_held_for_a_leaver` now watches `_pausing`, which is out-or-in.

Three things fell out of it that were not in the plan:

- **The hold outlasts the pause.** It is set from the moment the robot stops
  short until its body is clear on the far side, not just while it is waiting.
  A hold that ended the instant the robot moved would release the lane into
  the one moment the robot is standing in it.
- **The turn is pinned while crossing.** The crossing hop is not the final
  leg, not in a bay and not yet on the spur, so the rotation guard did not
  cover it and the robot turned from its aisle heading toward the junction
  with its body over a live lane. Rotating reaches the half-diagonal 0.918 m
  against 0.450 m held flat, which turns the 0.65 m of air `ROAD_EDGE` leaves
  into 0.18 m — inside layer 1's own stop distance. The turn is waste as well
  as hazard: the final leg holds the aisle heading and crabs in anyway.
- **A robot standing IN the pauser's way is no longer held.** Otherwise the
  pause is the deadlock it exists to prevent — the pauser waits for its path
  to clear and the only robot that could clear it has just been told to stand
  still. `HOLD_RADIUS` is 6 m and the corridor is 2.4 m, so this only bites
  when the other robot was already inside the corridor when the pause began,
  which is exactly the case that never resolves on its own.

**A robot arriving ALONG the outer lane holds nobody.** It turns off the lane
it is already on and crosses nothing; the rule engages only for a robot that
starts at least half a robot width short of the line.

**Measured.** `Log/contact_2026-08-26_160625.log`, five robots:

    16:11:25 [1428 samples] contacts=0 margin_breaches=0
             closest: amr4<->amr5 +0.90  amr3<->amr4 +0.91  amr3<->amr5 +0.93

49 new tests in `test/test_crossing_in.py`; 836 pass in total (was 787).

### Found while measuring it — a robot waits for the machine IN the lane

`request_entry` and `_machine_permits` are gated on `_final_leg`, which begins
AT the outer junction — so a robot refused entry stops dead in the lane it has
just crossed into. Observed repeatedly in the 16:04 run:

    amr3 (-19.10,-4.65) "machine has not granted entry"   south outer lane
    amr4 ( -3.56,-4.75) "machine has not granted entry"   south outer lane
    amr2 ( -6.40,-4.98) "machine has not granted entry"   south outer lane

It is a few seconds each time, not minutes, and the crossing hold covers it —
`_pausing_in` is still set at those positions, so everything within 6 m is
standing still. So it is not currently a contact, and it is a road block.

**There is nowhere good to send it, which is why this is a decision and not a
patch.** The lanes are `LANE_GAP` = 1.80 m apart and a crabbing robot is
0.90 m wide, so a robot standing anywhere between them has 0.00 m to one lane
or the other. The only clear places to wait are ON the inner lane (queueing,
which stalls a one-way ring behind it) or PAST the outer lane on the spur
(2.1 m long — no room behind the robot already in the bay). Ask before
choosing.

## THE OPEN PROBLEM — the diagonal off a spur

**A robot leaving a spur cuts diagonally across the aisle instead of turning
onto its line.** Observed 2026-08-26, amr4 leaving CTR2_ULD:

    it backed straight up its spur to (-3.40,-4.60) — 0.11 m from
    join_CTR2_ULD_outer — correctly, dead straight.

    straight up its own spur:  join_CTR2_ULD_inner (-3.36,-2.70)  1.90 m DUE NORTH
    what entry_node_for chose: join_CTR2_LD_inner  (-6.24,-2.70)  3.42 m at 146 deg

    via the diagonal       : hop 3.42 + road 14.5 = 17.9 m
    via its own spur north : hop 1.80 + road 17.3 = 19.1 m

It saves 1.2 m. `entry_node_for` minimises the WHOLE trip and the first hop is
the one leg exempt from the graph, so 1.2 m buys a diagonal across a live lane.
Under RULE 1 the 1.2 m should lose.

### Why the two obvious fixes failed, and what to try instead

- Restricting a robot on a lane to rejoin only on that lane: **196 of 270**
  routes stopped converging.
- Lowering `MAX_ONRAMP`: re-swept on the current graph, only 6.0 converges
  (2.0 -> 120, 3.0 -> 88, 5.0 -> 88, 6.0 -> 0).

Both failed the same way, and the cause is almost certainly not the constraint
itself but **the driver re-planning from scratch every single step**. Any
constraint whose truth flips as the robot moves — "am I on a lane", "is that
node ahead of me" — makes the chosen on-ramp flip with it, and the robot
alternates between two answers for ever.

**Try hysteresis first, before any new constraint.** Remember the entry node
once chosen and keep it until the robot reaches it, or until it becomes
unreachable. That removes oscillation by construction rather than by tuning a
tolerance, and it is probably what `TIE_BREAK` and the `MAX_ONRAMP` sweep have
been approximating all along. With the plan stable, a lane-following constraint
can then be added and actually measured.

Verify with the harness already in the tests: replan every 0.5 m from every
parking bay to every dock, 270 routes, and count how many arrive.

## Geometry changed this session (plant.py)

- `PARK_SPUR` is measured from the **outer lane**, not the aisle centreline.
  Splitting each aisle moved the lane 0.90 m toward the bays and nothing
  compensated: the constant promised 1.25 m of clearance and delivered 0.35 m.
- Parking bays turned **90 degrees** (nose along the aisle). Nose-in cannot fit —
  it needs x >= 30.34 and the hall wall allows 30.22.
- `PARK_PITCH` = `ROBOT_L + PARK_CLEARANCE` = 2.85 m (was `ROBOT_W + ...` = 2.15).
- `PARK_YAW` derived from `RING`: west outer runs south, east outer runs north,
  so leg A parks nose-south and legs B and C nose-north.
- `LANE_GAP` = 1.80 m. Lane constants moved above `PARK_X` so it can use them.

## Road graph changed this session (roads.py)

- **Each spur's two junctions are joined to each other.** They sit on the same
  line `LANE_GAP` apart and were unlinked, which made the outer junction a trap:
  25.4 m to reach a node 1.80 m away. Now 12.7 m.
- **The eight corner cross-links were removed.** Redundant once every spur joins
  both rings — all 702 dock-to-dock routes identical without them, road still
  strongly connected. Ring changes now happen only on spurs (37 of them).
- **`spur_joins` measures the spur to the MARKER, not the dock node.** A robot
  docks 1.15 m past the dock node, so every docked robot used to read as "not on
  a spur" and "leave by your own junction" never fired.
- **`entry_node_for` avoids other robots on the on-ramp hop** (`avoid` argument,
  fed by `sim_acs._others()`), with a fallback to the best hop if none is clear.

## Things measured, so don't re-derive them

- `MAX_ONRAMP` **must stay 6.0**. Re-swept on the current graph: 2.0 -> 120
  failures, 3.0 -> 88, 5.0 -> 88, **6.0 -> 0**. This is the cost of the cap: the
  first hop is off-graph and can cut across a lane.
- Forcing a robot on a lane to rejoin only on that lane **broke routing** —
  196 of 270 routes stopped converging. Backed out.
- Replacing `spur_joins`' distance test with a projection test also broke it —
  88 of 270. Backed out; the conservative distance test is load-bearing.

## Instruments

- `Tools/contact_meter/contact_meter.py` — independent footprint measurement,
  imports nothing from `csm`. **This is the arbiter, not the CSM's own view.**
- The world can paint the road graph: `generate_world.py --roads`.
  blue = inner ring, orange = outer ring, green = spurs,
  pink = ring changes (all on spurs now), chevrons show direction.

## Known-open, not touched this session

- `PARK_PITCH` fixed the parking jam, but adjacent slitter docks are 2.40 m apart
  and a robot parked sideways-on presents 1.60 m — 0.80 m of air.
- A dead robot still blocks whatever it is standing on for ever. Layer 1 stops
  and nothing restarts.
- `segment_for_job` ignores each segment's `buffer` list.
- Dispatcher head-of-line blocking starves idle robots.
