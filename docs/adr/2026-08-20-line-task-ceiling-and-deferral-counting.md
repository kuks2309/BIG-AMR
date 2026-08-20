# ADR 2026-08-20 — A per-line task ceiling, and counting deferrals as calls

- **Status**: Proposed — 2026-08-20. Implemented and regression-tested; the final
  verdict is not the author's to stamp (never-self-approve).
- **Rollback**: Reversible. The ceiling is off unless a `LineCapacity` is injected,
  and the deferral change is internal to `EquipmentMonitorTask`.

## Context

A six-minute run of `fleet.launch.py robots:=3` on 2026-08-20 produced:

```
jobs_created      14      active_jobs       9     (3 robots)
finished_jobs      5      open calls       14     climbing
calls_deferred   759      diverted_to_rack  0
retried            0      abandoned         0     commands_lost 0
```

Two separate defects are visible in those numbers.

### 1. `calls_deferred` counts polls, not calls

`EquipmentMonitorTask.step()` iterates `equipment.poll_calls()`, which returns the
**latched outstanding** calls — the same objects, every poll, until acknowledged. A call
that cannot be served increments `deferred` on *every* pass. The task wakes at 1 Hz, so
the counter climbs at roughly one per second per unservable call, indefinitely.

Measured directly: 219 → 234 → 249 → 264 over three five-second samples, dead steady,
while the number of open calls held at 5.

`ui/health.py:_supply` then compares that number against `jobs_created` and reports
*"759 calls deferred against 14 served — a supply problem upstream"*. The two quantities
have different units: one is a rate integrated over wall-clock, the other is a count.
The check therefore crosses into WARN on every run of any length and never recovers.

**This is the only warning the dashboard raises.** An acceptance instrument whose sole
alarm is always on is worse than one with no alarm, because it teaches the reader to
ignore it.

### 2. There is no ceiling on work in flight

`ui/health.py:179` already says so in its own source: *"CCS manual §2.15 (no ceiling
implemented yet)"*. Nothing bounds how much work may be outstanding against one leg.
Calls arrive about every 27 s; a job takes about 86 s; each leg has one robot. Jobs
created outran jobs finished for the whole run and the open-call list grew monotonically.

CATL's own system does bound it, and the rule is written down — `ccs-manual-notes.md`
§5, from manual §2.15:

```
max_tasks = (turntables assigned) + (buffer racks assigned) + redundancy

stop posting when
    AGV tasks in flight
  + material at turntable entrances
  + material on the line's buffer racks
  + material posted to this line awaiting transport
 >= max_tasks
```

and §3.2 gives the companion rule for *which* line is served next:

```
shortfall = (max_tasks - current_tasks) / max_tasks     -- highest wins
```

A percentage, not an absolute, so a small line and a big line compete fairly.

We are not inventing a policy here. We are implementing one the customer already runs.

## Decision

### D1 — `deferred` counts distinct calls; a separate gauge counts the outstanding ones

`EquipmentMonitorTask` keeps the set of calls currently deferred, keyed by
`(station_id, task_type)`. On each step it recomputes that set and increments the
cumulative counter **only for keys that were not deferred on the previous pass**.

Two numbers result, and they answer different questions:

| | meaning | shape |
| --- | --- | --- |
| `deferred` | distinct calls that could not be served at least once | cumulative, monotonic |
| `deferred_now` | calls that cannot be served **right now** | gauge |

`_supply` moves to the gauge plus the cumulative count, and stops comparing a rate
against a count.

### D2 — a `LineCapacity` implementing §2.15, injected rather than assumed

A new `csm/runtime/capacity.py` owns the formula. It is constructed from
`plant.SEGMENTS` — whose `to` list is the leg's destination ports (the manual's
turntables) and whose `buffer` list is the leg's WIP racks — plus a per-leg
`redundancy`.

`EquipmentMonitorTask` consults it before creating a job. A call for a leg at its
ceiling is **left outstanding and counted once**, exactly as an unservable call already
is. It is never acknowledged, so the machine keeps asking and nothing is silently
dropped — the property this layer exists to preserve.

**Injected, defaulting to `None`, which disables the ceiling entirely.** Every existing
caller and every existing test behaves exactly as before unless it opts in. This is the
same pattern `divert_for` and `return_for` already use in this task.

### D3 — shortfall breaks ties, it does not outrank priority

`DispatcherTask` sorts candidates by `(-priority, -shortfall, created_at)`.

Priority stays first because the 2026-08-14 ACS meeting put ordering of competing jobs
squarely on CSM, and priority is the field that expresses it. Shortfall enters below it,
which is where it belongs: the manual's rule decides *which line to post to*, not
whether an urgent job waits behind a routine one. Age still breaks the final tie, so
nothing starves.

With no `LineCapacity` injected every shortfall is equal and the sort is byte-for-byte
the previous behaviour.

### D4 — the ceiling is loose at the documented capacities, and that is recorded, not hidden

With `redundancy = 0` the formula gives:

| leg | ports | rack slots | ceiling |
| --- | --- | --- | --- |
| A | 4 | 1 + 1 | 6 |
| B | 4 | 7 + 6 | 17 |
| C | 4 | 15 + 15 | 34 |

One robot per leg will rarely reach 17 or 34, so on legs B and C the ceiling will not
bind in a three-robot sim. That is the honest consequence of implementing the customer's
formula rather than a number that makes our graph look calm.

**`redundancy` is the knob, and it accepts negatives** — the manual says so explicitly:
negative means the line's buffer is deliberately kept that many pallets short. The
simulator can therefore drive the ceiling into binding and prove the deferral path
without altering the formula:

```bash
ros2 launch trnav_2ws_gazebo fleet.launch.py robots:=3 line_redundancy:=-3
```

The launch argument is joined (`--line-redundancy=`) for the reason the charging
thresholds already document in `fleet.launch.py`: launch drops an empty two-token
argument and the next flag eats the value. `sim_node._redundancy` therefore has to accept
an empty string, which is what the default path produces.

We do **not** invent a tighter rule. If the ceiling turns out to be the wrong shape for a
three-robot cell, that is a question for the customer, not a constant for us to pick.

## Consequences

- The dashboard's only alarm becomes meaningful. `_supply` compares like with like, and a
  quiet line reports quiet.
- CSM stops posting to a saturated leg, which is the behaviour the customer's system has.
- A new number exists that nobody has given us: `redundancy`. It defaults to 0 and is
  recorded as a debt, not treated as known.
- The ceiling counts material on the leg's racks toward the limit, so as the divert path
  starts being exercised the ceiling tightens on its own — which is the manual's intent.
- **Not addressed here**: whether "material at turntable entrances" has an analogue in our
  model. We count in-flight jobs and parked material; the entrance term has no equivalent
  because we do not model turntables. Registered as debt rather than approximated.

## Verification

- `test_line_capacity.py` — the formula, the gauge, the deferral-counted-once property,
  and that an unserved call is never acknowledged.
- Full suite green before and after; the ceiling is inert without injection, so no
  existing test changes behaviour.
- Re-run of `fleet.launch.py robots:=3` with the ceiling active, comparing
  `calls_deferred` growth against the previous run.

## Open

- `redundancy` per leg is unspecified by the customer → new debt entry.
- The "material at turntable entrances" term of §2.15 has no analogue → new debt entry.
- Whether a three-robot cell should use the plant's ceiling at all, or a scaled one →
  question for CATL, recorded in the inventory rather than answered here.
