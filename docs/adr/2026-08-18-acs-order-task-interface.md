# ADR 2026-08-18 — The ACS interface becomes orders and task lists

- **Status**: Accepted — 2026-08-18 (model and builder landed with tests; call sites not yet migrated)
- Related: the "THE REAL ACS INTERFACE" comment block in `adapters/base.py` (recorded 2026-08-14),
  ADR [2026-08-07-job-timeout-and-idle-parking](2026-08-07-job-timeout-and-idle-parking.md)

## Context

`adapters/base.py` received the vendor schema on 2026-08-14 and recorded **conclusions
only**. The last line of that comment block is why this ADR exists:

> "COST OF DOING THIS PROPERLY: `AcsAdapter` has two implementations (`mock.py`,
> `sim_acs.py`) and four call sites (`main_cycle.py`, `mes_app.py`,
> `runtime/tasks/job_tracker.py`, `seer_client.py`). Widening the interface is a
> deliberate change across eight files and wants an ADR, not a drive-by edit."

### Fact 1 — our interface is a different shape from the ACS's unit of work

`AcsAdapter` today is `submit_job(job) -> TransportResult`: one move, A to B. The real ACS
takes an **order, which is an ordered list of tasks**. From the schema (held outside this
repository — vendor material, this repository is public — at
`References/local/acs/schema.graphql`):

- `createOrder(input: CreateOrderInput!): SimpleResponse!` — L858
- `input CreateOrderInput { id, tasks: [TaskInput!]!, vehicleId, priority, hotLot, custom,
  requester, requesterDetail, comment }` — L2174
- `enum TaskKind { NONE LOAD UNLOAD STAGE SCAN TURN PORT_CUSTOM CHARGE MAINT MOVE
  NODE_CUSTOM }` — L1081

The six tasks named in the CSM specification (rev01 §5) map onto that enum **exactly**
(MOVE, LOAD, UNLOAD, WAIT→STAGE, SCAN, CHARGE), because §5 was written from this schema.

### Fact 2 — this change removes a concept rather than adding one

Delivering to a port and collecting from it in the same visit is currently a separate
primitive, `TaskType.SWAP`. If an order is a task list, it is just
`MOVE → UNLOAD → STAGE → LOAD` — **one order, one visit**. That is not a new feature; it
is a special case disappearing (base.py comment item 1, gazebo open question B0).

`Carried`'s docstring already states the plant's real shape: every hop here is an
exchange, not a delivery.

### Fact 3 — exactly one thing is blocked, and it must not spread

`type SimpleResponse { errorCode: Int!, message: String }`. Every mutation returns one
integer and **the code table is not in the schema**. Our own analysis calls it "the single
most important thing still owed to us". So the distinction between `TransportResult.BUSY`
and `REJECTED` — the one that decides whether a job is retried forever or failed while it
would have run — has no basis today (specification assumption A7).

If that guess is made independently in several places, receiving the real table means
hunting for all of them.

## Decision

1. **Add the order model to `adapters/base.py`** — `TaskKind` (the schema enum verbatim),
   `AcsTask` (the `TaskInput` fields), `AcsOrder` (the `CreateOrderInput` fields),
   `SimpleResponse`. Field names keep **the vendor's spelling**: a name we have renamed to
   our taste cannot be checked against the live server.
2. **Widen `AcsAdapter`** — `create_order`, `order_state`, `cancel_order`, `abort_order`,
   `pause_order`, `resume_order`, `make_order_fail`, `make_order_success`. Cancel and abort
   are **separate operations**, and abort takes **no drop-off location** — the meeting notes
   said otherwise and the schema settles it. Do not add that parameter.
3. **Do not delete the existing three methods.** `submit_job` keeps working, so the 229
   tests and the four call sites migrate one at a time instead of breaking together.
4. **Confine the errorCode guess to one function** — `classify_error_code(code)`. Codes we
   invented are marked `PROVISIONAL`, and **nothing else in the CSM may interpret an integer
   error code**. A test enforces this. Receiving the real table is then a one-function change.
5. **Keep `TaskType.SWAP`.** The equipment protocol's `MC_Task_Type = 3` ("unload then
   load") is an equipment-side fact and is still needed. Only the ACS-side primitive goes.

## Consequences

- The real ACS arrives behind the same interface — which is what specification §9 requires.
- `sim_acs` executes orders in Gazebo and reports state in the same shape, so what is
  verified in the simulator holds at deployment. That is the whole point of the harness.
- Priority and hot-lot become expressible for the first time (§6: "priority first, then age").
- **Cost**: base.py, two implementations, four call sites. Item 3 means this need not be
  done in one change.
- **Residual risk**: without the errorCode table the retry policy is still a guess. Item 4
  contains that guess; it does not remove it.

## Alternatives rejected

- **Leave the interface alone and build task lists inside `sim_acs`.** What the simulator
  verifies would then differ in shape from what deployment runs, defeating the purpose.
- **Replace the three methods outright.** 229 tests and four call sites break at once, with
  no intermediate state to return to.
- **Guess the errorCode table now.** Scattered guesses cannot be found again when the real
  table arrives. Item 4 exists to prevent this.
