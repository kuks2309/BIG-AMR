# live_view — animated system explainer

A single self-contained HTML page showing how work flows through the whole
system: a machine finishes a batch, the Mini MES creates a job, the ACS assigns
a robot, the robot crosses the floor, the job completes — and when every robot
is busy, new jobs visibly queue.

Built for showing the system to people who do not read code. No build step, no
server, no dependencies.

## Open it

```bash
xdg-open Tools/live_view/index.html
```

Or drag the file into a browser. That is the whole procedure — it is one file.

## What it shows

| Region | What it is |
|---|---|
| Top strip | The four layers. Each travelling dot is one message: a finished batch reported, a job handed to the ACS, a robot given a destination |
| Inside a robot | Which brain holds the wheel. Seer for the transit; the gate engages and the Jetson takes over for the precise approach |
| Centre canvas | The 12 × 12 m hall, same stations and obstacles as `warehouse.world` |
| Job board | The Mini MES's view — every job and its FSM state |
| Fleet panel | The ACS's view — which robot holds which job |
| Event log | Colour-coded by which layer spoke |

Job states use the same names as the real FSM in
[`src/MES/mini_mes/mini_mes/job_fsm.py`](../../src/MES/mini_mes/mini_mes/job_fsm.py):
`WAITING → ASSIGNED → RUNNING → DONE`.

**Waiting is the point.** Stations deliberately produce faster than three robots
can clear, so a backlog forms on its own. It is not scripted — the ACS simply has
no free robot to give, which is the same condition that makes the real Python
return `BUSY`.

## It is a re-implementation, not the real thing

The page runs its own small simulation in JavaScript so it works anywhere, with
nothing installed. It mirrors the real logic but is **not** connected to ROS 2 or
Gazebo. Treat it as an explainer, not as evidence.

Faithful to the real system:

- job lifecycle and state names
- a busy fleet queues work instead of discarding it
- the source station is freed on collection, so it can produce again
- crab motion — the body never rotates, and the steering angle is folded into
  ±90° exactly as `qd_inverse_kinematics` normalises it
- the two-brain handover: Seer drives the transit, the gate engages for the
  final approach and the Jetson takes over while Seer is shown a frozen snapshot
- obstacle avoidance bounded below the attraction, so a robot deflects around
  something without being driven by it
- station and obstacle positions match `warehouse.world`

Simplified:

- straight-line travel, no obstacle avoidance and no scan data
- no failures, so the `FAILED` branch and the timeout never appear
- three robots; the Gazebo simulation currently has one

## Changing it

Everything is in `index.html`. The parts you are most likely to touch are near
the top of the `<script>` block:

| Want to change | Edit |
|---|---|
| Station positions | `STATIONS` |
| Pallets and pillar | `OBSTACLES` |
| Number of robots | the `for (let i = 1; i <= 3; i++)` loop |
| How fast batches appear | `s.period` in the `STATIONS.filter(...)` block — lower means a longer queue |
| Robot speed | `speed: 1.05` in the robot definition |
| Colours | the CSS custom properties on `:root` |

Reload the browser to see a change. There is nothing to rebuild.

## Recording it for a presentation

Use any screen recorder on the browser window. The page loops forever, so a
30–60 second capture shows several complete jobs and at least one queued one.
Press **Speed ×4** first if you want more to happen in less footage, and
**Add rush order** a few times to force a backlog immediately rather than
waiting for one to build.
