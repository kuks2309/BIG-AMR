# ADR 2026-08-07 — Job timeout, and idle robots must go home

- **Status**: Accepted — 2026-08-07 (**SIL only**. No hardware verification.)
- **Scope**: `csm/sim_node.py`, `csm/adapters/sim_acs.py`. Simulation and the
  CSM's own job model. No equipment protocol change.

## Context

Two faults with one shared root: **the simulation was given timing numbers that
nobody chose, and no rule about where a robot waits.**

### (1) The 120 s job timeout has no source

A job that spends longer than `job_timeout_s` in one state is failed. `sim_node`
sets it to **120 s**. That number appears nowhere in the customer documents and
contradicts the CSM's own default:

| where | value |
|---|---|
| `csm/job.py` | **600 s** |
| `csm/runtime/mes_app.py` | **600 s** |
| `csm/demo.py` | 60 s (a scripted demo with an injected clock) |
| `csm/sim_node.py` | **120 s** ← the outlier |

The meeting files were searched for anything that could justify it. They give
**process** times only:

- 30 s — the gluing step a bobbin pallet passes through
- 65 s / 130 s / 260 s — station cycle times
- 6–10 h — curing

The only minute-scale figures in the transcript are `10분 쉬죠? 5분?` — someone
proposing a coffee break. **There is no documented transport timeout.**

### Why 120 s could not work

It has to cover a whole job, and a job is two docks plus the travel between:

```
travel to source  +  DOCK  +  load 3 s  +  travel to destination  +  DOCK
```

Docking closes the last stretch at 0.10 m/s under a P law, so it took ~30 s per
dock from a 2.2 m hand-over. Two docks alone are ~60 s, and amr2's route crosses
the hall from the north row to the south row — 12 waypoints, over 40 m.

Measured: **3 successful collections and ZERO deliveries.** Every delivery dock
was still closing when the job was guillotined. Because no delivery completed, no
gravure ever produced output; because no gravure produced output, no coater job
was ever servable; so **amr2 and amr3 never moved at all.** A timing constant
nobody chose was starving two thirds of the fleet.

### (2) An idle robot stops where it finished, in the middle of the road

Nothing sends a robot anywhere when it has no job. It stops on the spot, and
"the spot" is a lane. Measured:

```
STATE amr1(-17.0,+2.6) idle | amr2(-18.6,+2.6) idle
[amr2] waiting — amr1 is in the way
job_0005: PATH BLOCKED — moved 0.05 m in 8s. Giving up.
```

amr1 finished a job and stopped on the north aisle. amr2 came along, its
protective field correctly refused to drive into it — and then the stall
detector failed amr2's job eight seconds later. Both ended idle, 1.6 m apart,
on the through-lane, blocking it for everyone.

The protective stop sits deliberately AFTER the stall check so two robots facing
each other cannot wait on one another for ever. That is the right trade against a
collision, but it means **standing still on a lane converts into a failed job for
somebody else.** The lane network exists to make traffic predictable; parking on
it defeats that.

## Decision

**1. Take the job timeout from the CSM's own default: 600 s.**

Not tuned to make a particular run pass — matched to the value `job.py` and
`mes_app.py` already use, so there is one number instead of two. A transport
crossing a 43 m hall with two docks legitimately takes minutes; 120 s was never
justified by anything and is removed rather than adjusted.

The stall detector (8 s without motion) and the docking timeout (60 s) are
unchanged. They are the guards that catch a *stuck* robot; the job timeout only
catches a *lost* one, and it should be generous.

**2. An idle robot returns to its parking bay.**

Parking bays are already off the aisles, on spurs off the cross aisles — one per
AGV class, at the end of that class's own run. A robot with no job drives home
and waits there, so a lane is never blocked by a robot that has nothing to do.

## Consequences

- The timeout no longer hides a throughput problem. If a job takes minutes, the
  log says so instead of failing it.
- Dock time still matters and is now visible rather than fatal. The hand-over was
  separately brought from 2.2 m to 1.5 m (~30 s → ~23 s per dock); shortening it
  further is a throughput decision, not a correctness one.
- Going home costs travel. Accepted: a blocked aisle costs another robot its
  whole job, which is worse.
- Not verified on hardware. Everything here is measured in Gazebo.

## Alternatives rejected

- **Raise the timeout to whatever makes the run pass.** That is fitting a
  constant to a symptom. If 600 s proves wrong, the fix is to find what is slow.
- **Let idle robots stay put and route around them.** The lanes are single file;
  there is nowhere to route. Passing needs a lay-by, which is a larger design
  question and is not required if robots simply do not park on the road.
- **Drop the stall detector so a waiting robot is not failed.** It is the only
  thing that catches a genuinely wedged robot, and losing it makes a jam silent.
