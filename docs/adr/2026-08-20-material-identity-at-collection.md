# ADR 2026-08-20 — Material gets its identity at collection, not at diversion

- **Status**: Proposed — 2026-08-20. Implemented and tested; the final verdict is not the
  author's to stamp (never-self-approve).
- **Rollback**: Reversible. Jobs already carry an optional `material_ref`; this fills it
  in on a path that previously left it None.

## Context

Measured on a running fleet, 2026-08-20:

```
jobs_created 19   bobbins_returned 11   materials 1   diverted_to_rack 0
jobs with a material_ref: 0 of 19
```

The single material is a legacy row seeded by hand to test a migration. **CSM gave an
identity to nothing it moved.**

`register_material` is reachable from exactly one place in the running system —
`equipment_monitor.py`, inside `_divert_stranded`:

> THE MATERIAL GETS AN IDENTITY HERE, because this is where it stops being "whatever the
> machine had" and starts being a thing sitting on a rack that somebody will later ask for
> by name.

That reasoning is sound for the rack. It is the wrong *only* place, because the divert
path fires when every destination of a leg is full — which in four measured runs never
happened once.

The consequence is that four functions the inventory marks ✅ are, in the running system,
dead code:

| | What it should answer | Reality |
| --- | --- | --- |
| B1 location tracking | where is this roll | one row, never updated |
| B2 movement history | where has it been | `job_store.py:237` guards on `job.material_ref`, never true |
| B3 LOT tracking | the customer's `yyyymmddhhmmssfff` | issued once, by a test |
| B4 traceability | falls out of B1–B3 | nothing to trace |

It also leaves the fields added earlier today — attribute, drum type, material type, state
— describing a record almost nothing creates.

## Decision

### D1 — a job claims its material when the job is created

Both job-creating paths in `EquipmentMonitorTask` — the material path and the bobbin
return — resolve a `material_ref` before calling `store.create`.

The monitor is the right place because it is where a source is chosen, and the source is
what is holding the thing. The alternative, minting at actual pickup, would put records
work inside the job FSM, which does not know about material at all.

### D2 — claim the material already there before minting a new one

```
ready_materials(source, now)  ->  oldest, FIFO
   found     -> use it
   not found -> register_material(kind, at=now, location=source)
```

**THIS IS THE WHOLE POINT.** Minting unconditionally would give a roll a new LOT id at
every hop, and three hops would be three unrelated records. Traceability — B4, "where has
this roll been" — is exactly the question that cannot survive that.

Reusing also makes two existing mechanisms real for the first time:

- `ready_materials` is **FIFO by `created_at`**, which is specification A2 and manual
  §3.1's core selection rule. It has existed and never been called by the running system.
- `is_ready` increments `unrested_decisions` when it accepts material whose resting state
  we do not know. That counter has sat at 0 not because we never decided blind, but
  because we never decided at all.

### D3 — `kind` comes from what the job carries

`Carried.ROLL` -> `kind="roll"`, `Carried.BOBBIN` -> `kind="bobbin"`. An empty core is a
tracked object in their model too: the return flow is specified in terms of pallets
carrying double empty bobbins (§1.2.2), and `TrayStatus` distinguishes them.

### D4 — the divert path keeps its own mint, unchanged

It already resolves a material and parks it. It now goes through the same claim-then-mint
helper, so a stranded roll that was already known keeps its identity instead of acquiring
a second one — the same bug as D2, on the path that previously did the minting.

### D5 — a job whose source has nothing is still created

If `ready_materials` returns nothing and minting is not appropriate, the job is created
with `material_ref=None` exactly as today. **This must not become a new way for a job to
fail.** The monitor already decides whether a source can supply, before this; adding a
second, quieter gate here would be a way to lose work for a records reason.

## Consequences

- `materials` grows by roughly one per new roll entering the line, not one per job. That
  is the same shape as the real system, where every roll is a record.
- `move_material` starts firing on DONE, so `material_moves` fills up and B2 becomes
  answerable.
- `unrested_decisions` will start rising, because we will start deciding. That is a
  counter doing its job, not a regression — and it makes the size of customer open
  decision #6 visible for the first time.
- The four routing fields now describe records that exist. Nothing populates them yet
  (that needs the PDA supplement or the rack PLC), so they stay honestly None.

## Not in scope

- **Where attribute and drum type come from.** Registering a material does not invent
  them. They arrive from the PDA supplement (§3.4) or `Rack_To_PCS`, and inventing a
  plausible value would be worse than None.
- **The pallet pair** — `debt-115`. One material per job here; A and B sides later.
- **Consuming material at a machine.** A roll fed into a gravure is transformed, and
  whether that ends its identity or continues it is a customer question, not ours. Today
  it simply keeps its identity and its location becomes the destination.

## Verification

`test_material_identity.py` — a job carries the material it collects; a second job from
the same place reuses the same LOT id rather than minting a second; the history of one
roll across two hops is one chain; a bobbin job registers a bobbin; and a source with
nothing still produces a job.

Plus a live re-run of `fleet.launch.py robots:=3`, comparing `materials` and
`jobs with a material_ref` against the baseline above.
