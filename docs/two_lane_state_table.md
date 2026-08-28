# AMR state / action / result — the two-lane road

Every cycle, `SimRobot.drive()` asks these questions **in this order** and stops
at the first one that answers. The order is the priority: a row can only fire if
every row above it declined.

Read the "result" column as what actually happens, measured — not what was
intended. Where the two differ the row says so.

Source: [`sim_acs.py`](../src/MES/csm/csm/adapters/sim_acs.py). Written
2026-08-27 on branch `two_lane`, 863 tests passing, nothing committed.

## The two rules

1. **Every robot follows the lines.** The road graph is the only path.
2. **Crossing the road, a robot pauses before it.** It stops `ROAD_EDGE`
   = 1.55 m short of the lane, tells the robots near it to stand still, and
   goes when its path is clear.

Everything below is either one of those two, or one of the four things kept
that are *not* rules: layer 1, the station interlock, robot-ahead queueing, and
the rotation guard.

## The table

| # | State | Action | Result |
|---|---|---|---|
| 1 | No pose yet | return, command nothing | Never commands blind. Costs one cycle. |
| 2 | Battery 0% | `_stop("battery flat")` | Stops where it stands, for good. Something has to come and get it. `can_move` keeps the dispatcher from giving it work. |
| 3 | **Any robot within `HOLD_RADIUS` 6 m is pausing at the road edge, and the crossing is still ahead of us** | `_stop("holding — a robot is coming out of a dock")` | RULE 2. Stands still until that robot is across. A robot that has *passed* the spur, or is off the road, is exempt — see `_could_still_reach`. |
| 4 | **We are crossing a lane and something is in our path** | `_stop("pausing before the road — X in the way")` | RULE 2. Waits `ROAD_EDGE` short of the lane, body clear of it, holding everyone near. Goes when the path clears. |
| 5 | **We are crossing and the path is clear** | hold the flag, drive on, turn pinned | Crosses in one move. The hold runs until the body is clear on the far side, so the lane is never released mid-crossing. |
| 6 | On course to touch another robot inside `STOP_GAP` 0.30 m | `_stop("layer 1: …")` | LAYER 1. The last physical stop. **It only ever says stop — it can never say who goes.** Two robots inside 0.30 m both freeze and neither recovers. |
| 7 | Backing out of a bay (`_exit_goal` set) | `_drive_to_exit` | RULE 2 the other way. Holds from the moment it starts backing out until it has arrived outside and released the bay. |
| 8 | No job and no goal | `_go_home` | Drives to its parking bay **on the lanes**. A robot that simply stopped where it finished would be a road block. |
| 9 | Docking already started | `_run_docking` | Owns the cycle. Closes on the marker, not the map, so map error does not reach the machine face. |
| 10 | Final leg, within 2.2 m, **bay occupied** | `_stop("entry refused: bay occupied")` | Station interlock — one robot per bay, because the machine protocol carries one "AGV inside" bit. **Waits ON the outer lane**, blocking it. See Known-wrong below. |
| 11 | Final leg, within 2.2 m, machine not permitting | `_stop("machine has not granted entry")` | `MC_Enter_Permitted` must have been continuous for longer than the comm-alarm time. Asked every cycle; a flickering signal never satisfies it. |
| 12 | Loading or unloading | `_stop("dwelling at the port")` | Real time at a real port. Not a stall — the stall clock is held off. |
| 13 | Reached an intermediate waypoint | pop it, carry on the same cycle | Corners are directions, not destinations. Tolerance 0.60 m — but only 0.175 m where the route **turns**, or the cut becomes a diagonal across the aisle. |
| 14 | Reached the dock approach point | `_square_up`, then dock | Turns parallel to the machine face first. Crabbing in tilted costs reach: at 11.4° the corner reaches 0.599 m into a 0.229 m gap. |
| 15 | Not moving for 8 s while driving | fail the job | It is raised again. A robot that cannot arrive must not drive at the goal for ever. |
| 16 | Otherwise | drive: goal attraction + bounded avoidance | Avoidance is capped below attraction on purpose — it nudges, it never halts. Halting is layer 1's job. |

### The turn rule, inside row 16

| State | Action | Result |
|---|---|---|
| Final leg, in a bay, on a spur, or crossing | `angular.z = 0` — hold heading, crab | Rotating sweeps the half-diagonal 0.918 m against 0.450 m held flat. There is not room for that beside a machine or over a live lane. |
| Anywhere else, heading error < 29° | turn toward the goal, full speed | Keeps the wheel angle away from the ±90° fold where the kinematics has two answers and flips between them. |
| Anywhere else, heading error > 29° | turn, and multiply speed by `cos(error)` | **Known-wrong.** At 171° that is a speed of zero, so the robot must complete a 171° turn before it may move — a turn the fold problem never required. See below. |

## Known-wrong, measured 2026-08-27 with ten robots

These three rows do not do what the rule intends. Each is a live defect, not a
tuning question.

| # | What happens | Measured | Why |
|---|---|---|---|
| 10 | A robot refused a bay waits **standing in the outer lane**, blocking everything behind it | amr1 at (-20.36, +4.49) — exactly `join_ASRS_outer` — refused, while amr6 held the ASRS bay | The interlock is gated on `_final_leg`, and the final leg begins **at** the outer junction. The earliest a robot can ask is already on the road. It should ask at the pause point, 1.55 m short. |
| — | **No following distance on a job leg at all** | amr1 closed from 2.4 m to **0.26 m** behind amr2 with nothing telling it to slow | `_robot_ahead` and its 2.4 m corridor are wired only into the homing path. On a job the robot has the avoidance nudge, then layer 1 at 0.30 m — the one distance from which neither robot recovers. |
| — | A robot's heading is inherited from **how it last docked** and nothing reconciles it with where it must go next | amr2 left GRV1_ULD nose-east and had to travel west: 171° error, commanded speed 0, and it could not turn because rotating needed 0.918 m and it had 0.26 m | Docking takes the *nearer* of the two parallel headings and deliberately never turns 180°. Arrive on the inner lane (eastbound), leave on the outer lane (westbound), and the robot is backwards. |

## Where a robot may wait, and why this is hard

There is **nowhere between the two lanes to stand.** They are `LANE_GAP`
= 1.80 m apart and a robot crossing presents 0.90 m of width, so a robot
stopped anywhere between them is inside 0.30 m of one lane or the other. The
only clear places are:

- **on the inner lane** — queueing, which is normal traffic, but it stalls a
  one-way ring behind it;
- **past the outer lane on the spur** — 2.1 m long, so no room behind a robot
  already in the bay.

That is why row 10 is a decision and not a patch.
