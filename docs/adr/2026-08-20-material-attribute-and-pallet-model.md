# ADR 2026-08-20 — Material attribute, drum type, and what a pallet can hold

- **Status**: Proposed — 2026-08-20. Implemented and tested; the final verdict is not the
  author's to stamp (never-self-approve).
- **Rollback**: Additive. New fields default to None, and None means *unknown* everywhere.
  Nothing already working changes behaviour.

## Context

`Material` records an identifier, a kind, a location, `ready_at` and `expires_at`. Its
docstring justifies the narrowness well:

> THE IDENTIFIER AND ALMOST NOTHING ELSE. Width, weight, grade and coating spec belong to
> the customer's systems; section 7 is explicit that keeping a second copy is how
> mismatches arise.

That reasoning is right for **master data** and wrong for **decision inputs**. CATL's own
system routes material on three attributes we do not hold, and it holds them precisely
because every dispatch decision reads them.

Two independent sources agree on all three — the CCS manual §4.6.5, and the rack PLC
variable table the team lead sent on 2026-08-19:

| | Values | Source |
| --- | --- | --- |
| **material attribute** | 1 bright/CW · 2 bright/CCW · 3 dark/CW · 4 dark/CCW | manual §4.6.5, `Rack_To_PCS[7]` |
| **drum type** | 360 · 430 · 500 · 580 | manual §4, `Rack_To_PCS[8]` |
| **pallet capacity** | **≥500 single-bobbin · <500 dual-bobbin** | both, stated identically |

Without them CSM cannot express any of:

- **§3.6 source matching.** The face must match. The rotation need not — it is fixed by
  turning the pallet 180°, which is a first-class AGV task type (§3.8). Some material
  types are configured **non-rotatable** and must match exactly (§4.6.11).
- **The single-item refusals** (§2.2, §6). A dual-slot pallet holding one roll is not
  auto-transported. A dual pallet with one empty bobbin is not used for return flow. An
  empty pallet is outside the automatic flow entirely — *"中控系统自动流程业务逻辑不含空
  托盘的流转"*.
- **Four of the twelve daily-check items** (§6 items 5–8), which `ui/health.py` currently
  cannot answer at all. They are not four gaps; they are one, and this is it.

## Decision

### D1 — a `material` module owning the vocabulary, not scattered constants

`csm/material.py` holds the enums and the rules. The alternative — integers threaded
through `records.py` and compared inline — is how `1` starts meaning "bright, clockwise"
in one place and "available" in another.

### D2 — `MaterialAttribute` knows how to match, because the rule is not equality

§3.6 is not `a == b`. The face must match; the rotation is negotiable by rotating the
pallet, **unless the material type is configured non-rotatable**. So matching is a method
with a flag, not an operator:

```python
attr.matches(required, rotatable=True)    # face only
attr.matches(required, rotatable=False)   # exact
```

`rotated()` returns the 180° partner, which is what a rotate-feed task produces.

### D3 — pallet capacity is derived, never stored

`≥500 single, <500 dual` is a rule about the drum type, not a second field. Storing both
invites them to disagree. The threshold is a named constant with its source beside it.

The field is an `INT` in their table, not an enum — 360/430/500/580 are the values *in
use*, not the domain. So an unknown drum type still yields a capacity, and only a missing
one yields None.

### D4 — `TrayStatus` is NOT range-checked as an enum

Their table carries two out-of-band values in the same INT: **>900 means rack error** and
**800 is a reset**. A plain `IntEnum` would raise on both, and a range check would accept
900 as a tray state.

So `classify_tray(value)` returns a `(TrayStatus | None, TrayCondition)` pair — the
condition being NORMAL, ERROR or RESET. A caller that ignores the condition gets None for
the status rather than a wrong answer.

### D5 — unknown stays unknown

Every new field defaults to None, and None means *we were not told*, never a default
value. This follows `ready_at`, whose docstring already makes the argument: *"None means
WE DO NOT KNOW — not 'ready now'."*

Consequently `matches()` on an unknown attribute returns **False, not True**. Refusing to
move material we cannot characterise is the conservative direction: the cost is a call
that waits, against the cost of feeding a machine the wrong face.

⚠ This differs from the resting-time default, which treats unknown as READY. That is
deliberate and the asymmetry is real: resting has a documented shipped default of 0
(§4.6.12, *"静置为非标准功能"*), so unknown genuinely means "no resting configured".
Nothing says an unknown attribute means "any attribute will do".

## Scope — what this ADR does NOT do

- **It does not wire matching into source selection.** Choosing a source by attribute
  needs a *requested* attribute per destination, which §4.6.5 says is machine
  configuration and our adapters do not carry yet. The rule is implemented and tested as a
  function; the caller comes next, so this change is additive and provable on its own.
- **It does not model the pallet PAIR.** The manual is emphatic that *"every roll is half
  of a PAIR"* and `rack_slot` holds one `material_ref`. Representing A and B sides is a
  records-schema change and is registered as debt rather than smuggled in here.
- **It does not add the rotate-180 task type.** `TaskType` is the customer's 1/2/3 and a
  fourth member is a protocol claim, not a model change.

## Consequences

- The four unanswerable daily-check items become answerable once the pair model lands;
  this is the half of that work with no schema change.
- `MaterialType` (302/228/125) is carried as an opaque int. It is their model code and we
  have no table for it — carried, never interpreted.
- A new asymmetry exists between "unknown resting" and "unknown attribute". Both are
  defensible and both are documented; anyone changing one should read D5 first.

## Verification

`test_material_model.py` — the four attributes and their faces, the rotation partner,
matching with and without rotation, the capacity threshold at exactly 500, the two
out-of-band tray values, and that unknown never silently passes a match.
