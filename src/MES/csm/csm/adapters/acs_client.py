"""The fleet link, over the ACS's real GraphQL interface.

`mock.py` and `sim_acs.py` are stand-ins. This one talks to a server.

WHY A SUBSCRIPTION AND NOT A POLL
=================================

`job_tracker` asks `get_job_result` at 4 Hz because the old `AcsAdapter` had no
other way to learn an outcome. The real ACS pushes: `orderChanged` delivers a
report per change, carrying BOTH the old and the new order and a monotonic
`sequence`. Polling a level at 4 Hz cannot see a state that was entered and left
between two reads; a change stream can. This is the same argument
`opcua_client.py` makes for `QueueSize`, one layer up, and it is what `debt-033`
tracks.

RECONNECTING IS PART OF THE PROTOCOL, NOT AN AFTERTHOUGHT
=========================================================

ARCHITECTURE.md §10 asks "what does reconcile return after a dropped
subscription?". The schema answers it: `orderChanged(requestSeed: Boolean!)`.
Subscribe with it true and the server replays current state as SEED reports
before going live, so a reconnect recovers the orders that finished while we
were away instead of leaving them open for ever.

⚠ THE SEED PROTOCOL IS DOCUMENTED, BUT NOT ON THIS SUBSCRIPTION. Two of the
schema's twenty-three subscriptions carry the description

    "If 'requestSeed' is true, the server always sends more than one seed data.
     The end of the seed is always dummy data, the sequence of seed is less than
     0, and the sequence of dummy is 0."

`orderChanged` is not one of the two. Assuming it behaves the same way is a
reasonable inference and nothing more, so `SeedGate` below TOLERATES a server
that never sends a seed rather than waiting for one that is not coming.

⚠ NOT YET RUN AGAINST THE CUSTOMER'S ACS. It is tested against a local
Strawberry server built from the operations we call, which proves this client
and the subscription semantics — not their server, its error codes, or its
authentication.

WHAT THIS CANNOT DECIDE
=======================

Every mutation returns `SimpleResponse { errorCode: Int!, message: String }`,
and an order's outcome is free text. Nothing in the schema separates "busy,
retry later" from "rejected, give up". That distinction is the whole reason
`TransportResult.BUSY` and `.REJECTED` both exist, and it lives in an error-code
table we have asked for and not received.

So this module does not guess it. Codes go to `base.classify_error_code`, which
already owns that decision and says it is the only place allowed to make it;
free-text outcomes go to `RESULT_STATES` here, which is empty on purpose. What
neither table covers is COUNTED — `unmapped_codes` and `unmapped_results` — so
the size of what we do not know is visible rather than assumed. That is the same
choice `records.is_ready` makes for resting.

The schema itself stays in `References/local/acs/`. It is vendor material and
this repository is public.
"""

import asyncio
import json
import threading

from .base import (AcsAdapter, AcsOrder, AcsTask, SimpleResponse,
                   TransportResult, classify_error_code)

# --------------------------------------------------------------- the documents
#
# Written out rather than generated. There are four of them, they change only
# when the vendor's schema does, and a generated client would put a code
# generator between a reader and the request that actually goes over the wire.

CREATE_ORDER = """
mutation CreateOrder($input: CreateOrderInput!) {
  createOrder(input: $input) { errorCode message }
}
"""

CANCEL_ORDER = """
mutation CancelOrder($input: CancelOrderInput!) {
  cancelOrder(input: $input) { errorCode message }
}
"""

ABORT_ORDER = """
mutation AbortOrder($input: AbortOrderInput!) {
  abortOrder(input: $input) { errorCode message }
}
"""

#: The fields of `Order` this client reads. Deliberately a SUBSET: an order
#: carries thirty-odd fields, most of them timing statistics that section 7 puts
#: on the "not retained" list. Asking for only what we use keeps the payload
#: small and makes it obvious what a change here would affect.
ORDER_FIELDS = """
    id
    result
    assignedVehicleId
    timeCompleted
"""

ORDER_QUERY = """
query Order($id: String!) {
  order(id: $id) { %s }
}
""" % ORDER_FIELDS

ORDER_CHANGED = """
subscription OrderChanged($requestSeed: Boolean!) {
  orderChanged(requestSeed: $requestSeed) {
    sequence
    new { %s }
  }
}
""" % ORDER_FIELDS


# ----------------------------------------------------------- the result table
#
# INTEGER ERROR CODES ARE NOT INTERPRETED HERE. `base.classify_error_code` says
# it is "THE ONLY PLACE THAT MAY", and it already carries the reasoning, the
# provisional table and the busy-by-default rule. This client calls it and adds
# nothing, so the vendor's table remains a one-function change.
#
# What base does NOT cover is the other half of the same gap: an order's outcome
# is free text, not a code. That table belongs here because it is only reachable
# through this transport.

#: An order's free-text `result` -> the state it means. EMPTY ON PURPOSE. We
#: have never been shown the vocabulary, and a plausible-looking guess
#: ("Success", "Failed") that turns out to be wrong either retires a job that is
#: still running or fails one that finished.
RESULT_STATES = {}

#: What an unrecognised order `result` is taken to mean. UNKNOWN rather than
#: FAILED: the job tracker treats UNKNOWN as "keep waiting, the timeout still
#: applies", which is right for a word we have not been taught. Calling it
#: FAILED would end a job on the strength of a string we cannot read.
#:
#: Same asymmetry `classify_error_code` argues for codes: of the two available
#: mistakes, the recoverable one is the default.
UNMAPPED_RESULT = TransportResult.UNKNOWN


def classify_result(result, table=None):
    """What an order's free-text `result` means.

    An order that has not finished has no result — empty string or null — and
    that is IN_PROGRESS, not an unrecognised word. Distinguishing the two
    matters: only the second is evidence of a vocabulary we are missing, and
    only the second should be counted as such.

    :param table: the result vocabulary of the server being talked to. A server
        that KNOWS its own words — the loopback in `acs_server.py` invents its
        own, so it does — passes them here. Without one, only "no result" is
        understood.

    The parameter exists for the same reason `classify_error_code` has one, and
    works the same way: it lets a server we control be understood completely
    without pretending we can read the vendor's vocabulary.
    """
    if not result:
        return TransportResult.IN_PROGRESS
    table = RESULT_STATES if table is None else table
    return table.get(result, UNMAPPED_RESULT)


# ------------------------------------------------------------------- the seed


class SeedGate:
    """Tells seed reports from live ones, and notices a hole in the stream.

    THE SEQUENCE RULES, as the schema states them for the two subscriptions it
    documents: seed reports carry `sequence < 0`, a dummy at `sequence == 0`
    ends the seed, live reports follow. `orderChanged` does not carry that
    description, so this class is written to survive a server that does none of
    it — see the module docstring.

    A dummy is NOT data. Its `new` is null and feeding it to the cache would
    write an order with no id.
    """

    def __init__(self, expect_seed):
        self.expect_seed = expect_seed
        #: False once the seed has ended, or immediately if none was asked for.
        self.seeding = bool(expect_seed)
        self.last_sequence = None
        self.gaps = 0

    def admit(self, sequence):
        """Should the report's payload be applied? Also tracks continuity.

        Returns True for anything carrying real data, seed or live. Returns
        False only for the end-of-seed dummy.
        """
        if sequence is None:
            # A server that does not sequence its reports at all. Take the data
            # and give up on gap detection rather than dropping the report.
            return True

        if sequence < 0:
            # Seed. It arrives in no guaranteed order relative to live traffic
            # and must never move `last_sequence`, which tracks the LIVE run.
            self.seeding = True
            return True

        if sequence == 0:
            # The dummy that ends the seed. No payload.
            self.seeding = False
            return False

        if self.last_sequence is not None and sequence > self.last_sequence + 1:
            self.gaps += 1
        self.seeding = False
        self.last_sequence = sequence
        return True


# ----------------------------------------------------------------- the client


class AcsGraphQLClient(AcsAdapter):
    """The ACS, over GraphQL. Mutations synchronous, outcomes pushed.

    THE SPLIT IS THE SAME ONE `opcua_client.py` MAKES. Reads come from a cache
    that a subscription keeps current, so the caller never blocks on the
    network to ask "what happened to my order?". Writes go over HTTP and return
    an answer, because `job_fsm` has to decide ACCEPTED / BUSY / REJECTED on the
    spot and cannot be handed a promise.

    :param endpoint: the HTTP URL for queries and mutations
    :param ws_endpoint: the WebSocket URL for subscriptions; defaults to
        `endpoint` with the scheme swapped, which is the usual arrangement
    :param requester: goes on every order, so the ACS's own logs can tell our
        traffic from anyone else's
    """

    def __init__(self, endpoint, ws_endpoint=None, requester="CSM",
                 timeout=5.0, http=None, result_states=None):
        self.endpoint = endpoint
        self.ws_endpoint = ws_endpoint or _ws_url(endpoint)
        self.requester = requester
        self.timeout = timeout
        #: The server's own result vocabulary, when it has one we were told.
        #: None means "only the vendor's, which is empty" — see classify_result.
        self.result_states = result_states

        self._http = http                      # injected in tests
        self._orders = {}                      # order id -> the fields we read
        self._lock = threading.Lock()
        self._thread = None
        self._stop = threading.Event()

        #: How often we met something the two tables do not cover. The size of
        #: the missing error-code table, as a number rather than an opinion.
        self.unmapped_codes = 0
        self.unmapped_results = 0
        #: Times the subscription dropped and was re-seeded.
        self.reseeds = 0
        self.gate = SeedGate(expect_seed=True)

    # ---------------------------------------------------------- the transport

    def _client(self):
        if self._http is None:
            import httpx
            self._http = httpx.Client(timeout=self.timeout)
        return self._http

    def _post(self, document, variables):
        """One GraphQL request. Returns the `data` block, or None."""
        response = self._client().post(
            self.endpoint,
            json={"query": document, "variables": variables},
        )
        response.raise_for_status()
        body = response.json()
        # A GraphQL server answers 200 with an `errors` block. Treating that as
        # success is the classic way to lose a failure silently.
        if body.get("errors"):
            raise AcsProtocolError(body["errors"])
        return body.get("data")

    # ------------------------------------------------------- the order surface

    def create_order(self, order):
        """Submit an `AcsOrder`. The schema's `createOrder`."""
        data = self._post(CREATE_ORDER, {"input": order_input(order, self.requester)})
        response = _simple(data, "createOrder")
        # Counted where the code arrives. `classify_error_code` owns what a code
        # MEANS; this only records that we met one the table does not list, so
        # the size of the missing table is a number rather than an impression.
        if response.errorCode != 0 and classify_error_code(
                response.errorCode) is TransportResult.BUSY:
            self.unmapped_codes += 1
        return response

    def cancel_order(self, order_id):
        """Ask for an order to be dropped before a robot has taken it.

        CANCEL AND ABORT ARE DIFFERENT OPERATIONS and this is the gentle one.
        Abort is for an order already under way; per the schema it takes no
        drop-off location, so where the load ends up is the ACS's decision and
        not ours to pass.
        """
        data = self._post(CANCEL_ORDER, {"input": _requested(order_id, self.requester)})
        return _simple(data, "cancelOrder")

    def abort_order(self, order_id):
        """Stop an order already being carried out."""
        data = self._post(ABORT_ORDER, {"input": _requested(order_id, self.requester)})
        return _simple(data, "abortOrder")

    def order_state(self, order_id):
        """What has become of an order.

        Reads the cache the subscription fills. Falls back to a query when the
        subscription has never mentioned this order — which is the case for the
        first moments after submitting, and after a restart with no seed.
        """
        with self._lock:
            order = self._orders.get(order_id)
        if order is None:
            data = self._post(ORDER_QUERY, {"id": order_id})
            order = (data or {}).get("order")
            if order is None:
                return TransportResult.UNKNOWN
            self._remember(order)
        return self._state_of(order)

    def _state_of(self, order):
        state = classify_result(order.get("result"), self.result_states)
        if state is UNMAPPED_RESULT and order.get("result"):
            self.unmapped_results += 1
        return state

    def _remember(self, order):
        if not order or not order.get("id"):
            return
        with self._lock:
            self._orders[order["id"]] = order

    # -------------------------------------------------- the legacy three

    # `submit_job` is NOT overridden. `AcsAdapter` builds the order with
    # `build_order` and calls `create_order` below, which is exactly what this
    # class would have written — and `build_order` owns the specification's
    # job-to-task-list mapping, so a copy here would be a second place for it to
    # drift. (That default was only a comment's promise until 2026-08-20; it is
    # real now.)

    def get_job_result(self, job_id):
        return self.order_state(job_id)

    def cancel_job(self, job_id):
        """⚠ THE SYNCHRONOUS ANSWER THIS RETURNS IS NOT THE REAL OUTCOME.

        `cancelOrder` is a REQUEST. The mutation acknowledges that the request
        was accepted; whether the order actually stopped comes back later on the
        order's own `request` / `requestResult` fields. Returning a bool here is
        the old interface's shape, and it can only honestly report "the ACS took
        the request", which is what it does.

        Call sites that need the true outcome must watch the order, not this.
        """
        response = self.cancel_order(job_id)
        return response.errorCode == 0

    # ---------------------------------------------------------- subscription

    def start(self, on_change=None):
        """Begin watching `orderChanged` on a background thread.

        Failure to connect is not fatal and not silent: the thread retries and
        counts its re-seeds. A CSM that cannot reach the ACS should keep
        running and say so, exactly as `UiServer` does for its port.
        """
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._watch, args=(on_change,), daemon=True,
            name="acs-orderChanged")
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.timeout)
            self._thread = None

    def _watch(self, on_change):
        asyncio.run(self._watch_async(on_change))

    async def _watch_async(self, on_change):
        while not self._stop.is_set():
            try:
                await self._one_subscription(on_change)
            except Exception:                      # noqa: BLE001 - see below
                # ANY failure here is a dropped link, and the answer to every
                # one of them is the same: reconnect and ask for the seed
                # again. Distinguishing them would change nothing we do.
                pass
            if self._stop.is_set():
                break
            self.reseeds += 1
            self.gate = SeedGate(expect_seed=True)
            await asyncio.sleep(1.0)

    async def _one_subscription(self, on_change):
        import websockets
        async with websockets.connect(
                self.ws_endpoint, subprotocols=["graphql-transport-ws"]) as ws:
            await ws.send(json.dumps({"type": "connection_init", "payload": {}}))
            while True:
                message = json.loads(await ws.recv())
                if message.get("type") == "connection_ack":
                    break
            await ws.send(json.dumps({
                "id": "orders",
                "type": "subscribe",
                "payload": {"query": ORDER_CHANGED,
                            "variables": {"requestSeed": True}},
            }))
            while not self._stop.is_set():
                message = json.loads(await ws.recv())
                kind = message.get("type")
                if kind == "next":
                    self._apply(message["payload"], on_change)
                elif kind in ("complete", "error"):
                    return

    def _apply(self, payload, on_change):
        report = ((payload or {}).get("data") or {}).get("orderChanged")
        if report is None:
            return
        if not self.gate.admit(report.get("sequence")):
            return                                 # the end-of-seed dummy
        order = report.get("new")
        if order is None:
            return
        self._remember(order)
        if on_change is not None:
            on_change(order["id"], self._state_of(order))


class AcsProtocolError(RuntimeError):
    """The server answered, and the answer was an `errors` block."""


# ------------------------------------------------------------------- helpers


def order_input(order, requester=None):
    """An `AcsOrder` as the schema's `CreateOrderInput`.

    ABSENT IS NOT NULL. Every optional field in the input is nullable, and
    sending an explicit null is a request to unset it rather than to leave it
    alone. So `None` fields are dropped, not serialised.
    """
    payload = {
        "id": order.id,
        "tasks": [task_input(task) for task in order.tasks],
    }
    optional = {
        "vehicleId": order.vehicleId,
        "priority": order.priority,
        "hotLot": order.hotLot,
        "custom": order.custom,
        "requester": order.requester or requester,
        "requesterDetail": order.requesterDetail,
        # `build_order` puts what the job carries here, so a reader of the ACS's
        # own order list can tell a roll job from a bobbin job without asking
        # us. Dropping it would throw that away at the last step.
        "comment": order.comment,
    }
    payload.update({k: v for k, v in optional.items() if v is not None})
    return payload


def task_input(task):
    """An `AcsTask` as the schema's `TaskInput`. Same absent-is-not-null rule."""
    payload = {"kind": task.kind.value if hasattr(task.kind, "value") else task.kind}
    for name in ("target", "vehicleSlot", "amount", "carrierId", "carrierModel",
                 "carrierCustom", "independent", "enterReverse", "chargeTo",
                 "expectedDuration", "noBlockingTime", "waitTimeout",
                 "turnAngle", "custom"):
        value = getattr(task, name, None)
        if value is not None:
            payload[name] = value
    return payload


def _requested(order_id, requester):
    return {"id": order_id, "requester": requester}


def _simple(data, field):
    """A `SimpleResponse` out of a mutation's data block."""
    body = (data or {}).get(field) or {}
    return SimpleResponse(errorCode=body.get("errorCode", -1),
                          message=body.get("message"))


def _ws_url(endpoint):
    if endpoint.startswith("https://"):
        return "wss://" + endpoint[len("https://"):]
    if endpoint.startswith("http://"):
        return "ws://" + endpoint[len("http://"):]
    return endpoint


__all__ = ["AcsGraphQLClient", "AcsProtocolError", "SeedGate", "classify_result",
           "order_input", "task_input", "AcsOrder", "AcsTask", "RESULT_STATES",
           "UNMAPPED_RESULT"]
