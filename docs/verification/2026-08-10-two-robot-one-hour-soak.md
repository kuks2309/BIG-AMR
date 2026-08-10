# Verification — two-robot fleet, one-hour soak

**2026-08-10 · `src/MES/csm` + `src/Sim/trnav_2ws_gazebo` · measured by running, not by inspection**

The baseline the three-robot build must be compared against. amr1 and amr2 were
run for a full hour after the give-way junction deadlock was fixed
(`docs/issues_and_fixes/issues_and_fixes.md`, 2026-08-10), to establish that the
two-robot fleet is sound before amr3 is written.

Two runs are recorded: the same build **before** and **after** the two-line fix
in `SimAcs.who_yields`. Settings are identical, so the columns are comparable.

---

## What was run

```bash
# strays cleared first — leftover bridges fight over the same wheels
pkill -9 -x gzserver; pkill -9 -x gzclient; pkill -9 -x robot_state_publisher
pkill -9 -f 'trnav_2ws_gazebo/lib'; pkill -9 -f 'lib/csm/sim_node'
ps -eo args | grep -E 'gzserver|trnav_2ws_gazebo/lib' | grep -v grep   # empty

source /opt/ros/humble/setup.bash && source install/setup.bash
FLEET_ROBOTS=2 ros2 launch trnav_2ws_gazebo fleet.launch.py gui:=true
ros2 run csm sim_node --robots 2 --batch-seconds 15
```

Both packages are `--symlink-install`, so the source tree is what ran; no
rebuild was needed. Fleet readiness confirmed on `/amr1/joint_states` and
`/amr2/joint_states` before starting the CSM. Segment C has no robot bound to
it in this build — `ROBOT_SEGMENT = {"amr1": "A", "amr2": "B"}`.

Closest approach was measured from `/gazebo/model_states`, which carries every
robot in ONE message so the poses compared are from the same instant. Both
centre-to-centre distance and the capsule **body gap** are reported; the body
gap is the number the traffic rules themselves use (`sim_acs._seg_gap`), and is
the one to judge safety by.

---

## Headline

| | before fix | after fix |
|---|---|---|
| runtime | 1638 s (27 min) | **3711 s (62 min)** |
| jobs created | 33 | 58 |
| delivered | 17 | **49** |
| retired DONE | 17 | 49 |
| **retired FAILED** | **4** | **0** |
| failure rate | **19 %** | **0 %** |

---

## The defect that was fixed

| | before | after |
|---|---|---|
| give-way encounters | 5 | 5 |
| **passes completed** (`road is yours`) | **1** | **5** |
| rejoined | 1 | 5 |
| **deadlock give-ups** (`nobody passed`) | **4** | **0** |

The encounter count is the same in both runs, so this is a like-for-like
comparison of exactly the behaviour that was broken: **1 of 5 resolved before,
5 of 5 after.** Resolution took 8.9–14.8 s per encounter, against a
`YIELD_LIMIT` of 45 s.

---

## Anything wrong at all — after the fix

Counted over the whole hour, not sampled:

| signal | count |
|---|---|
| `WARN` lines in the CSM log | **0** |
| `ERROR` lines in the CSM log | **0** |
| docking failures | 0 |
| `could not clear <station>` | 0 |
| jobs REJECTED / "not a leg" | 0 |
| node deaths | 0 |

The launch log contains 13 error lines, **all benign Gazebo startup noise** and
all before spawn completed: `Sensor.cc:510 Get noise index not valid` (x12, a
Gazebo sensor-config quirk) and one missing `model.config` for gzclient's model
browser. None recurred during the run.

---

## Liveness — the failures that log nothing

"No errors" is not the same as "working". A queue that never drains is silent.

| | |
|---|---|
| jobs created | 58 |
| delivered | 49 |
| never retired | 9 |

Of the nine never retired, **four are `CTR*_ULD -> SLT_LD*`** — segment C, which
has no robot. They queue as BUSY for ever **by design**: `SimAcs.submit_job`
answers BUSY rather than REJECTED when a leg has no robot, so the work waits
instead of dying. This is the direct evidence that binding amr3 to segment C
will pick them up. The remaining five are the newest in-flight batch.

**No servable job starved.** Every segment A and B job created was served.

Throughput is flat to the end — no slow degradation:

```
  0-10 min: 7      30-40 min: 8
 10-20 min: 8      40-50 min: 8
 20-30 min: 8      50-60 min: 9
```

Both robots stayed busy: amr1 31 job legs, amr2 19. The split is expected —
segment A (ASRS -> Gravure LD) feeds four machines from one always-stocked
store, segment B only becomes servable after a gravure has processed.

---

## Proximity — not a safety defect

| | before fix | after fix |
|---|---|---|
| samples | 44 083 | 98 388 |
| closest centre-to-centre | 1.59 m | 1.91 m |
| **closest body gap** | **1.46 m** | **1.90 m** |

Against `CONTACT_GAP` 0.90 m (bodies touch) and `STOP_GAP` 1.20 m (where the
avoidance layer aims to stop). **Neither run came close to either threshold.**

This matters for reading the defect correctly: the deadlock was a **liveness**
failure, not a collision risk. Both robots had already stopped. Enlarging the
world would not have fixed it — the blocker was a reservation held in a dict,
not a lack of space.

The after-fix figure covers the first 53 min of the run; the meter was stopped
to read its summary while the sim continued.

---

## Docking accuracy

54 docks, no failures:

```
mean range   0.679 m     (DOCK_TARGET = ROBOT_HALF_WIDTH 0.45 + DOCK_GAP 0.20 = 0.65 m)
mean |offset| 0.0000 m
```

---

## Unit tests

```
before:  143 passed
after:   151 passed        (+8, src/MES/csm/test/test_traffic.py — new)
```

`test_traffic.py` covers the junction/give-way seam, which had **zero** coverage
before. Confirmed the tests catch the defect rather than merely passing: with
the fix reverted, **4 of 8 fail**, including
`test_the_mutual_hold_that_failed_three_jobs`.

---

## What this does and does not establish

**Establishes.** The two-robot fleet runs an hour with zero failures, zero
warnings, flat throughput, no starvation, and comfortable separation. The
deadlock is fixed at both unit and system level.

**Does not establish.** Five give-way encounters in an hour is a small sample of
the specific case that was broken; the unit test is what pins the mechanism, and
Gazebo confirms it holds in motion. Nothing here exercises segment C, three-robot
traffic, or the south aisle shared between amr2 and amr3 — all of which are new
conditions that amr3 introduces and that this baseline cannot speak to.
