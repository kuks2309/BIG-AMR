"""The ACS client, against a real GraphQL server.

Not a mock. `strawberry` serves an actual schema over HTTP and WebSocket on a
real port, and the adapter connects, submits orders and subscribes for
outcomes. What is proven here is this client and the subscription semantics —
NOT the customer's ACS, its error codes, or its authentication.

The server below exposes only the operations we call, with the field names and
shapes taken from the vendor schema (held outside this repository). It is a
STAND-IN FOR THE PROTOCOL, not a model of their fleet: it accepts orders,
remembers them, and pushes changes.

The test that matters is the seed one. A CSM that reconnects without recovering
the orders that finished while it was away leaves those jobs open for ever, and
nothing reports it — see `acs_client`'s module docstring.
"""

import asyncio
import json
import socket
import threading
import time

import pytest

strawberry = pytest.importorskip("strawberry")
uvicorn = pytest.importorskip("uvicorn")
pytest.importorskip("websockets")
# strawberry.asgi needs it, and a missing one must SKIP rather than error the
# whole module — the same courtesy asyncua gets above.
pytest.importorskip("starlette")

import typing                                                     # noqa: E402

from csm.adapters.acs_client import (AcsGraphQLClient, SeedGate,  # noqa: E402
                                     classify_result, order_input, task_input)
from csm.adapters.base import (AcsOrder, AcsTask, TaskKind,       # noqa: E402
                               TransportResult)


# --------------------------------------------------------------- the server


@strawberry.type
class SimpleResponse:
    errorCode: int
    message: typing.Optional[str] = None


@strawberry.type
class Order:
    id: str
    result: typing.Optional[str] = None
    assignedVehicleId: typing.Optional[str] = None
    timeCompleted: typing.Optional[str] = None


@strawberry.type
class ChangedReportOfOrder:
    sequence: int
    new: typing.Optional[Order] = None


@strawberry.input
class TaskInput:
    kind: str
    target: typing.Optional[str] = None
    vehicleSlot: typing.Optional[int] = None
    amount: typing.Optional[int] = None
    carrierId: typing.Optional[str] = None
    carrierModel: typing.Optional[str] = None
    independent: typing.Optional[bool] = None
    enterReverse: typing.Optional[bool] = None
    chargeTo: typing.Optional[int] = None
    expectedDuration: typing.Optional[int] = None
    noBlockingTime: typing.Optional[int] = None
    waitTimeout: typing.Optional[int] = None
    turnAngle: typing.Optional[float] = None


@strawberry.input
class CreateOrderInput:
    id: str
    tasks: typing.List[TaskInput]
    vehicleId: typing.Optional[str] = None
    priority: typing.Optional[int] = None
    hotLot: typing.Optional[int] = None
    requester: typing.Optional[str] = None
    requesterDetail: typing.Optional[str] = None
    comment: typing.Optional[str] = None


#: TWO INPUT TYPES, NOT ONE SHARED ONE. The vendor schema declares
#: `CancelOrderInput` and `AbortOrderInput` separately even though their fields
#: are identical today, and a client written against the real schema names them
#: apart. Collapsing them here made this server accept a document the real
#: server would reject — which is exactly the class of difference a stand-in is
#: supposed to catch, so it is kept faithful rather than tidy.
@strawberry.input
class CancelOrderInput:
    id: str
    requester: typing.Optional[str] = None
    requesterDetail: typing.Optional[str] = None
    comment: typing.Optional[str] = None


@strawberry.input
class AbortOrderInput:
    id: str
    requester: typing.Optional[str] = None
    requesterDetail: typing.Optional[str] = None
    comment: typing.Optional[str] = None


class Fleet:
    """The ACS's own state. One instance, shared by the whole schema.

    `received` keeps every CreateOrderInput verbatim so a test can assert what
    actually went over the wire, rather than what we believe we sent.
    """

    def __init__(self):
        self.orders = {}
        self.received = []
        self.sequence = 0
        self.listeners = []
        #: What createOrder answers. A test flips it to exercise a refusal.
        self.next_code = 0

    def create(self, payload):
        self.received.append(payload)
        if self.next_code == 0:
            self.orders[payload["id"]] = {"id": payload["id"], "result": None,
                                          "assignedVehicleId": None,
                                          "timeCompleted": None}
        return self.next_code

    def finish(self, order_id, result, vehicle="amr1"):
        """The ACS completing an order, and telling everyone."""
        order = self.orders.setdefault(order_id, {"id": order_id})
        order.update({"result": result, "assignedVehicleId": vehicle,
                      "timeCompleted": "2026-08-20T12:00:00Z"})
        self.sequence += 1
        self._publish(ChangedReportOfOrder(
            sequence=self.sequence, new=Order(**order)))

    def _publish(self, report):
        for queue in list(self.listeners):
            queue.put_nowait(report)


FLEET = Fleet()


@strawberry.type
class Query:
    @strawberry.field
    def order(self, id: str) -> typing.Optional[Order]:
        found = FLEET.orders.get(id)
        return Order(**found) if found else None


@strawberry.type
class Mutation:
    @strawberry.mutation
    def createOrder(self, input: CreateOrderInput) -> SimpleResponse:
        code = FLEET.create(strawberry.asdict(input))
        return SimpleResponse(errorCode=code,
                              message=None if code == 0 else "refused")

    @strawberry.mutation
    def cancelOrder(self, input: CancelOrderInput) -> SimpleResponse:
        return SimpleResponse(errorCode=0 if input.id in FLEET.orders else 1)

    @strawberry.mutation
    def abortOrder(self, input: AbortOrderInput) -> SimpleResponse:
        return SimpleResponse(errorCode=0 if input.id in FLEET.orders else 1)


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def orderChanged(
            self, requestSeed: bool = False
    ) -> typing.AsyncGenerator[ChangedReportOfOrder, None]:
        """The vendor's seed protocol, as the schema describes it.

        Seed reports carry a NEGATIVE sequence, then one dummy at sequence 0
        ends the seed, then live traffic. Reproduced here so the client's
        handling of it is exercised against the shape it will actually meet.
        """
        queue = asyncio.Queue()
        FLEET.listeners.append(queue)
        try:
            if requestSeed:
                for index, order in enumerate(FLEET.orders.values(), start=1):
                    yield ChangedReportOfOrder(sequence=-index,
                                               new=Order(**order))
                yield ChangedReportOfOrder(sequence=0, new=None)   # the dummy
            while True:
                yield await queue.get()
        finally:
            FLEET.listeners.remove(queue)


SCHEMA = strawberry.Schema(query=Query, mutation=Mutation,
                           subscription=Subscription)


def _free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    """A real ASGI server on a real port, for the module's lifetime."""
    from strawberry.asgi import GraphQL

    port = _free_port()
    app = GraphQL(SCHEMA, subscription_protocols=["graphql-transport-ws"])
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    running = uvicorn.Server(config)
    thread = threading.Thread(target=running.run, daemon=True)
    thread.start()

    deadline = time.time() + 15.0
    while not running.started and time.time() < deadline:
        time.sleep(0.05)
    if not running.started:
        pytest.skip("the local GraphQL server did not start")

    yield f"http://127.0.0.1:{port}"

    running.should_exit = True
    thread.join(timeout=5.0)


@pytest.fixture(autouse=True)
def clean_fleet():
    FLEET.orders.clear()
    FLEET.received.clear()
    FLEET.sequence = 0
    FLEET.next_code = 0
    yield


def _wait_for(predicate, timeout=10.0):
    """Poll a condition the subscription thread will eventually satisfy."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


# ------------------------------------------------- the shape of what we send


def test_order_input_drops_absent_fields_rather_than_nulling_them():
    """Absent is not null. Sending an explicit null asks the ACS to UNSET."""
    payload = order_input(AcsOrder(id="job_1", tasks=[]), requester="CSM")
    assert payload == {"id": "job_1", "tasks": [], "requester": "CSM"}
    assert "vehicleId" not in payload
    assert "priority" not in payload


def test_order_input_carries_comment_and_requester_detail():
    """`build_order` puts what the job carries in `comment`; it must survive."""
    payload = order_input(AcsOrder(id="job_2", tasks=[], comment="roll",
                                   requesterDetail="line A"))
    assert payload["comment"] == "roll"
    assert payload["requesterDetail"] == "line A"


def test_task_input_serialises_the_enum_by_value():
    payload = task_input(AcsTask(kind=TaskKind.STAGE, target="GRV1_LD"))
    assert payload == {"kind": "STAGE", "target": "GRV1_LD"}


# ---------------------------------------------------------------- the seed


def test_seed_gate_admits_seed_and_swallows_the_dummy():
    gate = SeedGate(expect_seed=True)
    assert gate.admit(-2) is True
    assert gate.admit(-1) is True
    assert gate.admit(0) is False          # the dummy carries no order
    assert gate.seeding is False
    assert gate.admit(1) is True


def test_seed_gate_survives_a_server_that_sends_no_seed():
    """`orderChanged` does not document the seed protocol. Tolerate its absence."""
    gate = SeedGate(expect_seed=True)
    assert gate.admit(7) is True
    assert gate.seeding is False


def test_seed_gate_counts_a_hole_in_the_live_sequence():
    gate = SeedGate(expect_seed=False)
    gate.admit(1)
    gate.admit(2)
    assert gate.gaps == 0
    gate.admit(9)
    assert gate.gaps == 1


def test_seed_reports_do_not_disturb_live_continuity():
    """A seed replay must not be read as a jump in the live run."""
    gate = SeedGate(expect_seed=True)
    gate.admit(5)
    gate.admit(-3)
    gate.admit(6)
    assert gate.gaps == 0


# ------------------------------------------------------- the outcome tables


def test_an_order_with_no_result_is_still_running():
    assert classify_result(None) is TransportResult.IN_PROGRESS
    assert classify_result("") is TransportResult.IN_PROGRESS


def test_an_unknown_result_word_is_unknown_not_failed():
    """We have never been shown the vocabulary. Guessing ends jobs wrongly."""
    assert classify_result("Whatever") is TransportResult.UNKNOWN


# ---------------------------------------------------------- against a server


def test_create_order_reaches_the_server_with_its_task_list(server):
    client = AcsGraphQLClient(server)
    order = AcsOrder(id="job_10", tasks=[
        AcsTask(kind=TaskKind.MOVE, target="ASRS"),
        AcsTask(kind=TaskKind.LOAD, target="ASRS"),
    ])
    response = client.create_order(order)

    assert response.errorCode == 0
    assert len(FLEET.received) == 1
    sent = FLEET.received[0]
    assert sent["id"] == "job_10"
    assert [task["kind"] for task in sent["tasks"]] == ["MOVE", "LOAD"]
    assert sent["requester"] == "CSM"


def test_a_refused_order_is_busy_not_rejected(server):
    """Until the vendor's code table arrives, unknown means retryable."""
    FLEET.next_code = 42
    client = AcsGraphQLClient(server)
    response = client.create_order(AcsOrder(id="job_11", tasks=[]))

    assert response.errorCode == 42
    from csm.adapters.base import classify_error_code
    assert classify_error_code(42) is TransportResult.BUSY


def test_order_state_falls_back_to_a_query_when_unsubscribed(server):
    client = AcsGraphQLClient(server)
    client.create_order(AcsOrder(id="job_12", tasks=[]))

    assert client.order_state("job_12") is TransportResult.IN_PROGRESS
    assert client.order_state("nobody") is TransportResult.UNKNOWN


def test_a_change_is_pushed_without_being_polled(server):
    """The whole reason this client exists instead of a 4 Hz poll."""
    client = AcsGraphQLClient(server)
    client.create_order(AcsOrder(id="job_13", tasks=[]))

    seen = {}
    client.start(on_change=lambda oid, state: seen.__setitem__(oid, state))
    try:
        assert _wait_for(lambda: "job_13" in client._orders), "no seed arrived"
        FLEET.finish("job_13", "Whatever")
        assert _wait_for(lambda: seen.get("job_13") is TransportResult.UNKNOWN)
    finally:
        client.stop()


def test_reconnecting_recovers_what_finished_while_we_were_away(server):
    """The reconcile question, answered by `requestSeed`.

    An order completes while nothing is subscribed. A fresh subscription must
    learn about it from the seed — otherwise the job stays open for ever and
    nothing reports it.
    """
    client = AcsGraphQLClient(server)
    client.create_order(AcsOrder(id="job_14", tasks=[]))
    FLEET.finish("job_14", "done-while-away")     # nobody is listening

    client.start()
    try:
        assert _wait_for(lambda: "job_14" in client._orders), "seed lost the order"
        assert client._orders["job_14"]["result"] == "done-while-away"
    finally:
        client.stop()


def test_cancel_reports_only_that_the_request_was_taken(server):
    """`cancelOrder` is a REQUEST; the true outcome arrives on the order."""
    client = AcsGraphQLClient(server)
    client.create_order(AcsOrder(id="job_15", tasks=[]))

    assert client.cancel_job("job_15") is True
    assert client.cancel_job("never-existed") is False
