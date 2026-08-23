"""The OPC-UA client, against a real OPC-UA server.

Not a mock. `asyncua` runs an actual server in-process, exposing the customer's
own variable names, and the adapter connects to it over opc.tcp and subscribes.
What is proven here is the client and the subscription semantics — NOT the
customer's server, its node ids, or its security policy.

The test that matters is the last one: two requests raised inside one cycle
must arrive as two. That is the hole polling cannot close, and the reason this
adapter exists.
"""

import asyncio

import pytest

asyncua = pytest.importorskip("asyncua")

from asyncua import Server, ua                                   # noqa: E402

from csm.adapters.base import (DockingAxis, MaterialPresence, StationStatus,
                               TaskProcessing, TaskType)          # noqa: E402
from csm.adapters.opcua_client import (QUEUE_SIZE, OpcUaEquipmentClient,
                                       variable_name)             # noqa: E402

ENDPOINT = "opc.tcp://127.0.0.1:48401/csm/test/"
STATION = "GRV1_LD"
OBJECT = "2:Gravure1"


class Machine:
    """A gravure, as an OPC-UA server. Flipped by the test the way a PLC would."""

    def __init__(self):
        self.server = None
        self.vars = {}

    async def start(self):
        self.server = Server()
        await self.server.init()
        self.server.set_endpoint(ENDPOINT)
        idx = await self.server.register_namespace("csm-test")

        obj = await self.server.nodes.objects.add_object(idx, "Gravure1")
        # The customer's names, unwind side.
        booleans = ("MC_HeartBeat", "MC_Ready_UW", "MC_Alarm_UW",
                    "MC_Rolling_Full_UW", "MC_Roll_Null_UW", "MC_Roll_IN_UW",
                    "MC_Enter_Permitted_UW", "AGV_Task_Recive_UW")
        for name in booleans:
            var = await obj.add_variable(idx, name, False)
            await var.set_writable()
            self.vars[name] = var
        for name, initial in (("MC_Task_Type_UW", 0),
                              ("AGV_Task_Processing_UW", 0)):
            var = await obj.add_variable(idx, name, ua.Variant(initial, ua.VariantType.Int32))
            await var.set_writable()
            self.vars[name] = var
        var = await obj.add_variable(idx, "MC_Num", "2A01")
        await var.set_writable()
        self.vars["MC_Num"] = var

        await self.server.start()

    async def stop(self):
        if self.server is not None:
            await self.server.stop()

    #: Nodes declared Int32. A bare Python int is rejected with
    #: BadTypeMismatch, so the write has to carry the variant type — the same
    #: strictness a real PLC server applies.
    INT_VARS = ("MC_Task_Type_UW", "AGV_Task_Processing_UW")

    async def set(self, name, value):
        if name in self.INT_VARS:
            value = ua.Variant(int(value), ua.VariantType.Int32)
        await self.vars[name].write_value(value)


async def _connected():
    machine = Machine()
    await machine.start()
    client = OpcUaEquipmentClient(ENDPOINT, {STATION: OBJECT},
                                  axis=DockingAxis.UNWIND_A)
    await client.connect()
    return machine, client


async def _settle(seconds=0.6):
    """Let the server sample and publish. Real transport, so real latency."""
    await asyncio.sleep(seconds)


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# -- naming -----------------------------------------------------------------

def test_signals_are_suffixed_by_docking_axis():
    assert variable_name("MC_Ready", DockingAxis.UNWIND_A) == "MC_Ready_UW"
    assert variable_name("MC_Ready", DockingAxis.REWIND_B) == "MC_Ready_RW"


def test_per_machine_signals_are_not_suffixed():
    """A heartbeat belongs to the machine, not to one of its four axes."""
    assert variable_name("MC_HeartBeat", DockingAxis.REWIND_A) == "MC_HeartBeat"
    assert variable_name("MC_Num", DockingAxis.UNWIND_B) == "MC_Num"


# -- against a live server ---------------------------------------------------

@pytest.mark.timeout(60)
def test_it_connects_and_reads_the_machine_number():
    async def go():
        machine, client = await _connected()
        try:
            await _settle()
            assert str(client.machine_number(STATION)) == "2A01"
            assert client.station_map() == {STATION: "2A01"}
        finally:
            await client.disconnect()
            await machine.stop()
    run(go())


@pytest.mark.timeout(60)
def test_presence_comes_from_the_three_booleans():
    async def go():
        machine, client = await _connected()
        try:
            await machine.set("MC_Roll_Null_UW", True)
            await _settle()
            assert client.presence(STATION) is MaterialPresence.NOTHING

            await machine.set("MC_Roll_Null_UW", False)
            await machine.set("MC_Roll_IN_UW", True)
            await _settle()
            assert client.presence(STATION) is MaterialPresence.EMPTY_BOBBIN
        finally:
            await client.disconnect()
            await machine.stop()
    run(go())


@pytest.mark.timeout(60)
def test_a_request_arrives_as_a_call():
    async def go():
        machine, client = await _connected()
        try:
            await _settle()
            client.poll_calls()                       # drain the initial values
            await machine.set("MC_Task_Type_UW", 1)   # 0 -> 1: the request
            await _settle()

            calls = client.poll_calls()
            assert len(calls) == 1
            assert calls[0].station_id == STATION
            assert calls[0].task_type is TaskType.LOAD
        finally:
            await client.disconnect()
            await machine.stop()
    run(go())


@pytest.mark.timeout(60)
def test_the_level_alone_does_not_raise_a_second_call():
    """A request is the TRANSITION. A value that stays 1 is still one request."""
    async def go():
        machine, client = await _connected()
        try:
            await _settle()
            client.poll_calls()
            await machine.set("MC_Task_Type_UW", 1)
            await _settle()
            assert len(client.poll_calls()) == 1
            await _settle()
            assert client.poll_calls() == [], "the level is not a new request"
        finally:
            await client.disconnect()
            await machine.stop()
    run(go())


@pytest.mark.timeout(60)
def test_two_requests_in_one_cycle_arrive_as_two():
    """THE REASON THIS ADAPTER EXISTS.

    A station finishes a job and raises another of the same type before the CSM
    looks again. Reading the level shows 1 both times and the second job is
    never created — that is the hole polling cannot close, and it is still
    xfail against the polling stand-in.

    Here the server QUEUES the changes (QueueSize > 1), so both transitions
    arrive.
    """
    async def go():
        machine, client = await _connected()
        try:
            await _settle()
            client.poll_calls()

            await machine.set("MC_Task_Type_UW", 1)    # request one
            await asyncio.sleep(0.15)
            await machine.set("MC_Task_Type_UW", 0)    # acknowledged
            await asyncio.sleep(0.15)
            await machine.set("MC_Task_Type_UW", 1)    # request two
            await _settle()

            calls = client.poll_calls()
            assert len(calls) == 2, (
                f"both requests must survive; got {len(calls)}. "
                f"QueueSize is {QUEUE_SIZE}")
        finally:
            await client.disconnect()
            await machine.stop()
    run(go())


# -- the server is allowed to say no -----------------------------------------

@pytest.mark.timeout(60)
def test_the_server_reports_what_queue_size_it_actually_granted():
    """QueueSize is a REQUEST. The server returns a RevisedQueueSize.

    asyncua does not surface it — create_monitored_items reads it off the
    response and keeps only the item id, storing the REQUESTED size in its own
    bookkeeping. So the library will happily let us believe we are protected.
    """
    async def go():
        machine, client = await _connected()
        try:
            await _settle()
            assert client.revised_queue_sizes, "nothing was read back"
            assert client.coalescing_protected is True
            assert all(v > 1 for v in client.revised_queue_sizes.values())
        finally:
            await client.disconnect()
            await machine.stop()
    run(go())


@pytest.mark.timeout(60)
def test_a_server_that_caps_the_queue_is_detected_not_believed():
    """The failure this guards against is silent, so the detection must not be.

    Many PLC OPC-UA servers cap QueueSize at 1. If ours does, change
    notifications coalesce exactly as polling does — the same bug one layer
    down, and harder to find because the code says QUEUE_SIZE = 10 and looks
    correct.
    """
    async def go():
        machine, client = await _connected()
        try:
            await _settle()

            # Stand in for a server that will only ever grant one slot.
            real = client._client.uaclient.modify_monitored_items

            async def capped(params):
                results = await real(params)
                for r in results:
                    r.RevisedQueueSize = 1
                return results

            client._client.uaclient.modify_monitored_items = capped
            await client.verify_queueing()

            assert client.coalescing_protected is False
            assert set(client.revised_queue_sizes.values()) == {1}
        finally:
            await client.disconnect()
            await machine.stop()
    run(go())


@pytest.mark.timeout(60)
def test_protection_is_unknown_before_we_have_asked():
    """None, not True. Not having checked is not the same as being safe."""
    client = OpcUaEquipmentClient(ENDPOINT, {STATION: OBJECT},
                                  axis=DockingAxis.UNWIND_A)
    assert client.coalescing_protected is None
