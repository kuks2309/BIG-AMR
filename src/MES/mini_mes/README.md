# mini_mes

Job planning and tracking, one layer above the ACS.

Something notices a machine has finished a batch, decides that material must move,
and follows that job until it arrives. That is all a Mini MES is.

See [`ARCHITECTURE.md`](../../../ARCHITECTURE.md) §5 for the design and
[`WORKFLOW.md`](../../../WORKFLOW.md) for one order followed end to end.

---

## Run it

```bash
# no hardware, no ROS — a fake factory, instant, deterministic
python3 -m mini_mes.demo --jobs 5 --fail-one

# the same factory under the real Supervisor, on wall-clock timers
python3 -m mini_mes.supervised_demo --seconds 20 --robots 1

# against the Gazebo simulation
bash ../../Sim/trnav_2ws_gazebo/scripts/start_sim.sh
ros2 run mini_mes sim_node

# read the real robot's status (READ-ONLY by construction)
ros2 run mini_mes seer_client --host 192.168.44.82
```

```bash
python3 -m pytest test/ -q          # 76 tests, ~2 s
```

---

## Two drivers, one system

The same job store and the same job FSM are driven two ways. This is deliberate,
and neither is a legacy of the other.

| | `MainCycle` | `build_mes` + `Supervisor` |
|---|---|---|
| Shape | one loop, one thread, one tick | independent FSMs, own periods |
| Clock | injected — a 600 s timeout verifies instantly | wall clock, asyncio |
| Failure | one domain — an exception stops everything | isolated and recorded per FSM |
| Dispatch | each job asks the ACS for itself | a Dispatcher decides whose turn |
| Used by | `demo`, most tests, and as the reference | `supervised_demo`, `sim_node` |

`MainCycle` is kept because a driver you can step by hand with a fake clock is
what makes the job FSM's behaviour provable. Every bug found in this package was
found that way. `test_mes_app.py` runs both over the same scenario and asserts
they reach the same outcome — the concurrent runtime is checked *against* the
sequential one.

---

## Layout

```
mini_mes/
  job.py            Job (plain data) + JobContext (what guards may see)
  job_fsm.py        IDLE → ASSIGNED → RUNNING → DONE / FAILED
  fsm/              the tiny engine: State, Transition, StateMachine
  main_cycle.py     the sequential driver
  runtime/
    supervisor.py   holds a list of FSMs, starts them, watches the exit flag
    fsm_task.py     one FSM as an asyncio task — the Active Object pattern
    job_store.py    the bookkeeping both drivers share
    mes_app.py      build_mes() — the one place the FSMs are wired together
    tasks/
      equipment_monitor.py   notices finished batches      1 Hz
      dispatcher.py          decides whose turn it is      0.5 s + on event
      job_tracker.py         steps every job FSM           4 Hz
  adapters/
    base.py         EquipmentAdapter / AcsAdapter — the interfaces
    mock.py         a fake factory and fleet
    sim_acs.py      drives the Gazebo robot
  seer_client.py    read-only Seer status reader
```

---

## Why adapters

The two things this package talks to are both unavailable:

- the **equipment protocol** is unknown, blocked on CATL
- the **MES → ACS interface** is undecided — it may be JSON path files, a new
  API, or Seer's own

Behind an ABC, neither blocks development. The FSMs are written and tested today
against mocks, and when the answers arrive only one new class is written per
interface. Precedent in this repository: `Tools/Kinematics/can_transport.py`
puts a `CanTransport` ABC in front of socketcan / pcan / mock so the drive logic
never learns which CAN hardware is underneath. This is the same move, one layer
up.

---

## Three things that are not obvious

**A busy fleet means wait, not give up.** `TransportResult.BUSY` is distinct from
`REJECTED`. Collapsing them destroyed every job created while another was
travelling — with one robot, the line produced work and the MES threw it away.

**Completing a job must free the SOURCE station, not only the destination.** A
source left marked finished never produces again, and the line goes quiet after
two or three jobs while batches keep completing.

**`RUNNING` has three exits — success, failure, and timeout.** While the Panda
gate is engaged every layer above is blind by design; if the Jetson dies
mid-dock, Seer still reports "parked, normal". The timeout is the only thing
that ends such a job. A waiting state with only a success arrow is a place the
system can hang for ever.

---

## Safety note

`seer_client.py` is read-only **by construction**, not by convention: it accepts
only port 19204 (status) and refuses the control and navigation ports at
construction time. No command API numbers appear in the file. Writing to a
production robot's controller is not something a status reader should be one
typo away from.
