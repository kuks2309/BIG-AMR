"""acs_server — any AcsAdapter, served over the real GraphQL interface.

WHAT THIS IS FOR
================

`acs_client.py` is proven by unit tests against a server that exists only while
those tests run. That leaves the interesting half untested: the client inside a
LIVE system, under real timers, with the job tracker ticking at 4 Hz and the
subscription running on its own thread. Blocking, thread starvation and
subscription lifecycle are exactly the faults unit tests cannot reach, and they
are the ones that will bite on the customer's network.

We cannot reach the customer's ACS. So we put a server in front of the one ACS
we do have:

    CSM ──(GraphQL over a real socket)──> this ──> SimAcs ──> Gazebo

The client in that chain is the real one, the transport is a real socket, and
the timing is the simulator's. Nothing is stubbed except the fleet, which was
always simulated anyway.

⚠ THIS IS A HARNESS, NOT A MODEL OF THE CUSTOMER'S ACS. It answers the
operations we call, with the shapes their schema declares. It says nothing about
their error codes, their result vocabulary, their authentication, or how their
server behaves under load.

WHY IT POLLS
============

`SimAcs` has no change notification — it is asked, it answers. So this server
polls it and publishes what changed. That looks like the thing `acs_client`'s
docstring argues against, and it is, but it is on the RIGHT SIDE of the wire:
the poll is inside the harness standing in for the ACS, and the CSM still
receives pushes. The real ACS pushes for itself and this file goes away.

`strawberry` and `uvicorn` are imported lazily, inside `start()`. They are
test-and-harness dependencies, and nothing that runs in production may need
them present.
"""

import threading
import time

from .base import AcsOrder, AcsTask, TaskKind, TransportResult

#: THIS SERVER'S OWN RESULT VOCABULARY.
#:
#: The schema makes an order's outcome free text and we have never been shown
#: the vendor's words, so `acs_client.RESULT_STATES` is empty and everything
#: unrecognised reads as UNKNOWN. A loopback that inherited that would turn
#: every ARRIVED into UNKNOWN on the way back and no job would ever finish.
#:
#: So the harness declares its own vocabulary and the client is TOLD it, the way
#: `classify_error_code` lets an adapter pass the codes it knows. Inventing
#: words for a server we wrote is honest; inventing them for the vendor's would
#: not be, and this dict is not a guess at theirs.
RESULT_WORDS = {
    TransportResult.ARRIVED: "Arrived",
    TransportResult.FAILED: "Failed",
    TransportResult.REJECTED: "Rejected",
}

#: The same table, as the client reads it: word -> state.
LOOPBACK_RESULT_STATES = {word: state for state, word in RESULT_WORDS.items()}


def _word_for(state):
    """The result string for a state, or "" while the order is still running.

    EMPTY IS MEANINGFUL. `classify_result` reads "no result" as IN_PROGRESS,
    which is what an unfinished order is. Sending a word for it would make every
    in-flight order look like it had an outcome.
    """
    return RESULT_WORDS.get(state, "")


class LoopbackAcsServer:
    """Serves one `AcsAdapter` at `endpoint`, on a background thread.

    :param adapter: the ACS being fronted — `SimAcs` in the simulator
    :param port: 0 picks a free one, which is what tests want
    :param poll: seconds between checks for a changed order

    Start it, read `endpoint`, point an `AcsGraphQLClient` at it, stop it when
    done. Failure to start is raised rather than swallowed: unlike the UI, a
    harness nobody can reach is not a degraded run, it is a broken one.
    """

    def __init__(self, adapter, host="127.0.0.1", port=0, poll=0.2):
        self.adapter = adapter
        self.host = host
        self.port = port
        self.poll = poll

        self._server = None
        self._thread = None
        #: order id -> the last state we published, so only CHANGES go out.
        self._published = {}
        #: order id -> the order as the client will read it.
        self._orders = {}
        self._sequence = 0
        self._listeners = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------- lifecycle

    @property
    def endpoint(self):
        return f"http://{self.host}:{self.port}"

    def start(self, timeout=15.0):
        import uvicorn
        from strawberry.asgi import GraphQL

        if self.port == 0:
            self.port = _free_port(self.host)

        schema = _build_schema(self)
        app = GraphQL(schema, subscription_protocols=["graphql-transport-ws"])
        config = uvicorn.Config(app, host=self.host, port=self.port,
                                log_level="error")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True,
                                        name="acs-loopback")
        self._thread.start()

        deadline = time.monotonic() + timeout
        while not self._server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        if not self._server.started:
            raise RuntimeError(
                f"the loopback ACS did not start on {self.endpoint}")
        return self

    def stop(self, timeout=5.0):
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._server = self._thread = None

    # ---------------------------------------------------------- the ACS side

    def accept(self, payload):
        """`createOrder` — hand the order to the adapter underneath."""
        order = AcsOrder(
            id=payload["id"],
            tasks=[AcsTask(kind=_kind(task.get("kind")),
                           target=task.get("target"))
                   for task in payload.get("tasks", [])],
            priority=payload.get("priority"),
            requester=payload.get("requester"),
            comment=payload.get("comment"),
        )
        response = self.adapter.create_order(order)
        if response.errorCode == 0:
            with self._lock:
                self._orders[order.id] = {"id": order.id, "result": "",
                                          "assignedVehicleId": None,
                                          "timeCompleted": None}
                self._published[order.id] = TransportResult.IN_PROGRESS
        return response

    def snapshot(self, order_id):
        with self._lock:
            return dict(self._orders.get(order_id) or {}) or None

    def known_orders(self):
        with self._lock:
            return [dict(order) for order in self._orders.values()]

    def subscribe(self, queue):
        with self._lock:
            self._listeners.append(queue)

    def unsubscribe(self, queue):
        with self._lock:
            if queue in self._listeners:
                self._listeners.remove(queue)

    def sweep(self):
        """Ask the adapter about every live order and publish what moved.

        ONE REPORT PER CHANGE, not per sweep. Publishing every sweep would make
        the sequence number meaningless and drown the client in reports saying
        nothing happened — which is the coalescing-versus-change distinction
        this whole interface exists to get right.
        """
        changed = []
        with self._lock:
            live = [oid for oid, state in self._published.items()
                    if state is TransportResult.IN_PROGRESS]
        for order_id in live:
            state = self.adapter.order_state(order_id)
            with self._lock:
                if state is self._published.get(order_id):
                    continue
                self._published[order_id] = state
                order = self._orders.setdefault(order_id, {"id": order_id})
                order.update({
                    "result": _word_for(state),
                    "assignedVehicleId": _vehicle_for(self.adapter, order_id),
                    "timeCompleted": None,
                })
                self._sequence += 1
                changed.append((self._sequence, dict(order)))
        for sequence, order in changed:
            self._publish(sequence, order)
        return len(changed)

    def _publish(self, sequence, order):
        with self._lock:
            listeners = list(self._listeners)
        for queue in listeners:
            queue.put_nowait((sequence, order))


def _vehicle_for(adapter, order_id):
    """Which robot took this order, if the adapter can say.

    Optional on purpose: `AcsAdapter` does not require it, and a harness must
    not demand more of an adapter than the interface does.
    """
    for robot in getattr(adapter, "robots", ()):
        if getattr(robot, "job_id", None) == order_id:
            return robot.name
    return None


def _kind(name):
    try:
        return TaskKind(name)
    except ValueError:
        return TaskKind.NONE


def _free_port(host):
    import socket
    with socket.socket() as probe:
        probe.bind((host, 0))
        return probe.getsockname()[1]


def _build_schema(server):
    """The subset of the vendor's schema this harness answers.

    Built inside a function so that `strawberry` is imported only when a
    loopback is actually started — see the module docstring.
    """
    import asyncio
    import typing

    import strawberry

    @strawberry.type
    class SimpleResponseType:
        errorCode: int
        message: typing.Optional[str] = None

    @strawberry.type
    class OrderType:
        id: str
        result: typing.Optional[str] = None
        assignedVehicleId: typing.Optional[str] = None
        timeCompleted: typing.Optional[str] = None

    @strawberry.type
    class ChangedReportOfOrder:
        sequence: int
        new: typing.Optional[OrderType] = None

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

    # Two input types, not one shared one — the vendor's schema declares them
    # separately, so a client written against it names them apart.
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

    @strawberry.type
    class Query:
        @strawberry.field
        def order(self, id: str) -> typing.Optional[OrderType]:
            found = server.snapshot(id)
            return OrderType(**found) if found else None

    @strawberry.type
    class Mutation:
        @strawberry.mutation
        def createOrder(self, input: CreateOrderInput) -> SimpleResponseType:
            response = server.accept(strawberry.asdict(input))
            return SimpleResponseType(errorCode=response.errorCode,
                                      message=response.message or None)

        @strawberry.mutation
        def cancelOrder(self, input: CancelOrderInput) -> SimpleResponseType:
            response = server.adapter.cancel_order(input.id)
            return SimpleResponseType(errorCode=response.errorCode,
                                      message=response.message or None)

        @strawberry.mutation
        def abortOrder(self, input: AbortOrderInput) -> SimpleResponseType:
            response = server.adapter.abort_order(input.id)
            return SimpleResponseType(errorCode=response.errorCode,
                                      message=response.message or None)

    @strawberry.type
    class Subscription:
        @strawberry.subscription
        async def orderChanged(
                self, requestSeed: bool = False
        ) -> typing.AsyncGenerator[ChangedReportOfOrder, None]:
            """Seed first if asked, then a report per change.

            The sweep runs HERE, on the subscription's own task, rather than on
            a timer of its own: with no subscriber there is nobody to tell, and
            a harness that polls a simulator nobody is listening to is just heat.
            """
            queue = asyncio.Queue()
            server.subscribe(queue)
            try:
                if requestSeed:
                    for index, order in enumerate(server.known_orders(), 1):
                        yield ChangedReportOfOrder(sequence=-index,
                                                   new=OrderType(**order))
                    yield ChangedReportOfOrder(sequence=0, new=None)
                while True:
                    try:
                        sequence, order = await asyncio.wait_for(
                            queue.get(), timeout=server.poll)
                        yield ChangedReportOfOrder(sequence=sequence,
                                                   new=OrderType(**order))
                    except asyncio.TimeoutError:
                        # SimAcs cannot tell us; ask it. Off the event loop,
                        # because `order_state` is ordinary blocking code and
                        # running it inline would stall every other socket this
                        # server is holding.
                        await asyncio.get_running_loop().run_in_executor(
                            None, server.sweep)
            finally:
                server.unsubscribe(queue)

    return strawberry.Schema(query=Query, mutation=Mutation,
                             subscription=Subscription)


__all__ = ["LoopbackAcsServer", "LOOPBACK_RESULT_STATES", "RESULT_WORDS"]
