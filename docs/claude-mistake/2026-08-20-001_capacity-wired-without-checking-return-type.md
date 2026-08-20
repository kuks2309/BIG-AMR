---
id: 2026-08-20-001
type: mistake
category: verify-skip
status: closed
reflected_assets:
  - src/MES/csm/csm/sim_node.py
  - src/MES/csm/test/test_line_capacity.py
  - src/Sim/trnav_2ws_gazebo/scripts/stop_sim.sh
---

# The whole equipment monitor was dead for two minutes and the test suite was green

## What happened

While wiring the new `LineCapacity` (ADR 2026-08-20) into `sim_node.py`, I passed
`plant.segment_of_station` as the `leg_of` callback. That function returns the segment
**dict**, not the segment's name. `LineCapacity` keys its per-leg counts by whatever
`leg_of` returns, and a dict is unhashable.

Every `EquipmentMonitorTask.step()` therefore raised
`TypeError: unhashable type: 'dict'` — 73 consecutive failures over about 75 seconds.

Nothing crashed. The Supervisor caught the exception, logged it, and kept the other five
FSMs running exactly as it is designed to. So the only visible symptom was three robots
sitting still in their bays, which looks identical to a navigation problem, a spawn race,
or a dozen other things.

**The user saw it before I did**, and told me: *"robots are not moving yet"*.

## Why the tests did not catch it

I wrote 15 tests for the new module and all 15 passed, including the ones that exercise
the monitor end to end.

They passed because `test_line_capacity.py` defines its own `leg_of`:

```python
def leg_of(station_id):
    for seg in SEGMENTS:
        if station_id in seg["to"]:
            return seg["name"]      # <- a string, because I wrote it that way
    return None
```

Every fixture in the file returns a string. The real plant returns a dict. I tested the
contract I had invented instead of the one the system actually supplies, and the suite
reported 677 passing while the running system was doing nothing at all.

This is the same shape as the repository's most common recorded failure — `verify-skip`,
29 of 62 prior entries. The specific variant is worth naming: **a hand-written fixture
that agrees with the code under test proves only that the two agree.**

## Root cause

I read `segment_of_station`'s name and its one-line summary — *"Which leg a station
belongs to"* — and did not read its `return`. The docstring is accurate; "which leg" is
answered by handing back the leg. I assumed the shape I wanted rather than checking the
shape that exists, then chose a fixture that encoded the same assumption, so nothing
anywhere could contradict me.

Sequence: assume a return type → write a fixture from the assumption → tests agree with
themselves → green suite → wire it into a live system → the live system stops.

## What was done

1. `sim_node._leg_of` — a named helper that unwraps the segment, with the failure recorded
   in its docstring so the next person sees why it is not a lambda.
2. `test_the_real_plant_wires_through_without_blowing_up` — an integration test using the
   **real** `plant.SEGMENTS`, the **real** `_rack_sizes()` and the **real** `_leg_of`. It
   also asserts that `segment_of_station` returns a dict, pinning the trap itself so the
   helper cannot be "simplified" away later.
3. `stop_sim.sh` — its final verification line did not include `robot_state_publisher`
   among the leftovers it checks for, so it could report a clean teardown with publishers
   from earlier runs still alive. Unrelated to this bug, found while chasing it, fixed in
   the same pass. (The script did already *kill* them; it simply never *checked*.)

Full suite after: 678 passed, 1 xfailed. Re-run of `fleet.launch.py robots:=3`: zero step
failures, first job created and driving within seconds.

## Prevention

**A new callback wired into a live system needs one test that uses the real supplier, not
a fixture.** Unit tests with hand-written doubles are the right tool for the logic and are
structurally incapable of finding an interface mismatch, because the double is written by
the same person making the same assumption at the same moment.

Concretely, for this repository: when a task gains an injected callable, the test file
gets one case that imports the production implementation and calls it. It does not need to
assert much — calling it and using the result the way the code does is enough. That single
test would have failed instantly here.

Second, smaller lesson: **a supervised task that fails every step is invisible from the
outside.** The Supervisor keeping siblings alive is correct and was working as designed,
but "one FSM has failed 73 times in a row" is not something a person watching robots can
see. Whether repeated step failures should surface on the dashboard is a separate
question, and is worth asking rather than assuming — the health page exists precisely to
answer "is anything quietly wrong".
