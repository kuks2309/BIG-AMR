# Verification — CSM on the Supervisor, against Gazebo

**2026-08-03 · `src/MES/csm` · verified by running, not by inspection**

The CSM had two halves that never met: `MainCycle`, which worked and drove the
simulation, and `runtime/`, which had the shape Dr. Shim drew on the whiteboard but only
ever ran a toy Producer/Consumer demo. This records the evidence that the merged system
does what the old one did.

---

## What was run

```bash
colcon build --packages-select csm --symlink-install
bash src/Sim/trnav_2ws_gazebo/scripts/start_sim.sh    # Gazebo, warehouse.world
ros2 run csm sim_node                            # the supervised MES
```

Gazebo confirmed up before starting the MES — `gzserver` running on `warehouse.world`,
`/odom`, `/odom_truth`, `/scan`, `/imu/data` and the nine `/motion/wheel_cmd/*` topics
present, both controllers loaded.

Run length ~4 minutes of wall clock, ended with `SIGINT`.

---

## Result

```
5 FSMs started: equipment_monitor, dispatcher, job_tracker, ros_spin, drive

  equipment_monitor      244 ticks    0 errors
  dispatcher             496 ticks    0 errors
  job_tracker            978 ticks    0 errors
  drive                4 802 ticks    0 errors
  ros_spin            23 033 ticks    0 errors
                     ─────────────
                      29 553 ticks    0 errors

jobs   created 9   granted 20   completed 8   failed 0   active 1 at exit
ACS    19 submissions — 8 accepted, 11 busy
log    0 warnings, 0 tracebacks, 0 step failures
```

Route followed as configured: `station_3 → station_5 → station_9 → station_out`.
Each job ran as two legs — collect from source, then carry to destination — with the
3 s dwell at the source.

---

## The three things this was run to check

### 1. The line does not stall

The regression this package has hit before: completing a job frees the destination but
not the **source**, the source stays `FINISHED` for ever, the latch keeps it suppressed,
and the line runs two or three jobs and then goes quiet while batches keep completing.

**8 jobs completed across 9 batches from 3 stations, in continuous rotation.** Stations
kept producing throughout. Not stalled.

### 2. Permits are not wasted

`DispatcherTask` grants one permit at a time. If its readiness rule disagreed with t1's
guard, permits would be spent on jobs the guard then refuses to move — silently, with
nothing logged, the queue simply draining slower than it should.

**19 grants, 19 submission attempts. Exactly 1:1.** Every permit produced exactly one
attempt; none was wasted.

The 20 grants against 19 submissions in the final health snapshot is the one permit
outstanding at the moment of shutdown, not a discrepancy.

`granted` (20) exceeding `created` (9) is expected and correct: with a one-robot fleet a
job that is told `BUSY` returns to `IDLE` and must be granted again. 11 of the 19
attempts were answered `BUSY`, and **none of those jobs was lost** — a busy fleet meant
wait, not give up.

### 3. Shutdown releases everything

`SIGINT` → the supervisor's handler → every FSM's `on_stop()`, including `DriveTask`'s,
which stops the wheels. All five reported a clean stop with their tick counts, the
process exited without hanging, and no FSM had to be cancelled for failing to stop in
time.

Moving `acs._stop()` from `main()`'s `finally` into `DriveTask.on_stop()` is what makes
this hold on paths where the old code would have skipped it.

---

## What this does **not** show

- **No failure path was exercised.** 0 jobs failed, so `t4` and `t5` were never taken
  here. Both are covered by tests (`test_task_job_tracker.py`,
  `test_job_lifecycle.py`) against an injected clock, which is the only practical way to
  verify a 120-second timeout.
- **One robot.** Multi-robot behaviour is untested outside the mocks; the Gazebo world
  has a single robot.
- **Simulated ACS.** `SimAcs` drives the Gazebo robot directly. The real MES → ACS
  interface is still undecided (`ARCHITECTURE.md` §10).
- **No equipment protocol.** `MockEquipment` throughout — the CATL specification has not
  arrived.
- **The Panda gate is not in this loop at all.** It sits below the physics boundary and
  is not simulated.

---

## Test suite

```
76 passed in 2.24s
```

Including `test_the_two_drivers_reach_the_same_outcome`, which runs `MainCycle` and the
supervised FSMs over an identical scenario and asserts they retire the same jobs with the
same results — the claim of the merge, checked rather than asserted.

---

## Related

| | |
|---|---|
| [`ARCHITECTURE.md` §5](../../ARCHITECTURE.md) | the design this implements |
| [`src/MES/csm/README.md`](../../src/MES/csm/README.md) | the two drivers and why both exist |
| [`docs/audit/`](../audit/) | known gaps between design and code |
