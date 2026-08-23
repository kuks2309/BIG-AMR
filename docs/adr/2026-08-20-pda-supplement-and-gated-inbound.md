# ADR 2026-08-20 — The PDA supplement, and inbound refusing incomplete material

- **Status**: Proposed — 2026-08-20. Implemented and tested; the final verdict is not the
  author's to stamp (never-self-approve).
- **Rollback**: Contained. Only `csm/pda.py` and its tests; the divert path parks material
  through `records.park` directly and is untouched.

## Context

Earlier today `Material` gained the three fields CATL routes on — attribute, drum type,
material type — and material started getting an identity when a job collects it.

**Nothing populates them.** Every roll in a live run carries `attribute=None`,
`drum_type=None`. The model is correct and describes nothing.

On the real line there is exactly one place a person enters them: the PDA's
`料架查询与补录入库` screen — query a rack, **supplement**, then take it inbound. Ours
cannot:

```python
def register_material(self, kind="roll", location=None):
```

The manual is specific, and the reason is specific too (§3, §3.4):

> Supplement requires type, attribute and bobbin type to be **non-empty and non-zero** —
> because a zero here is what produces the "missing info" rack states.

That is not validation for its own sake. Manual §5.1 and §6 item 5 are both about racks
whose material cannot be used because its information was never completed, and §6 tells a
human to go and find them every day.

## Decision

### D1 — `supplement()` is its own operation, separate from registering

Scanning and describing are two moments on the real line: material is scanned when it
appears, and supplemented when a worker has read the label. `register_material` therefore
still accepts the three fields (a scanner that already knows them) and still allows None.

`supplement(material_ref, attribute, drum_type, material_type)` fills them in afterwards.

### D2 — zero is not a value, it is the missing-info state

The manual singles out zero rather than empty, so `supplement` rejects **both** None and
0 for drum type and material type, and None for attribute. A `drum_type=0` would otherwise
flow into `pallet_capacity(0)` and come back as a dual pallet — a confident wrong answer
derived from a field nobody filled in.

### D3 — inbound REFUSES material that has not been supplemented

`bind_to_rack` is our inbound. It now declines material whose three fields are not all
present, because that is the customer's rule and because the alternative is a rack holding
something CSM cannot route — which is the state their whole §5.1 troubleshooting section
exists to clear up.

**This does not touch the automatic path.** The WIP diversion parks material through
`records.park` directly, not through the PDA, so a robot stranding a roll on a rack is
unaffected. The gate is on the human inbound only, which is where the customer puts it.

### D4 — the two refusals are told apart

`bind_to_rack` returned a slot, or None when the rack was full. There are now two ordinary
reasons to refuse and they need different actions from the worker: **find another rack**
versus **go and read the label**. Returning None for both would collapse them.

So it returns an `Inbound` result carrying `slot`, `ok` and `reason`. The module's existing
argument still holds — *"None rather than an exception because a full rack is an ordinary
answer a worker needs to see, not a fault"* — and a result object is the same argument
taken one step further, because now there are two such answers.

## Consequences

- The four routing fields become populated by the operation that populates them on the
  real line, so §3.6 matching finally has something to match on.
- A worker can no longer take material inbound without describing it. That is a new way
  for a PDA action to be refused, and it is the customer's own rule rather than ours.
- `bind_to_rack`'s return type changes. Only `test_pda.py` calls it.
- Material registered by the automatic path still has no attribute, because nothing has
  read a label. That is honest and stays honest — see "Not in scope".

## Not in scope

- **The reconciliation checklist** (§3.4) — four ways records and reality disagree. The
  CCS notes say plainly *"We have no equivalent. Our records are assumed to be the
  truth."* That assumption starts to matter now that CSM mints identity, but it is its own
  piece of work and is registered as debt rather than half-built here.
- **Wiring the attribute into source selection.** The rule is implemented
  (`attribute_matches`); the caller needs a *requested* attribute per destination, which
  §4.6.5 puts in machine configuration and our adapters do not carry.
- **The rack PLC as a second source** of these fields. `Rack_To_PCS` reports them too, and
  when that adapter exists it populates the same fields by the same rule.

## Verification

`test_pda.py` — supplement stores the three; zero is refused as firmly as None; inbound
declines unsupplemented material and says why; inbound after supplement succeeds; a full
rack and an undescribed roll are distinguishable; and the automatic divert path still
parks without a supplement.
