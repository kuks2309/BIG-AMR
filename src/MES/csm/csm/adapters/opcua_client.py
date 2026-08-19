"""The equipment link, over real OPC-UA.

Everything else in `adapters/` is a stand-in. This one talks to a server.

WHY SUBSCRIPTIONS AND NOT POLLING
=================================

A transport request is a TRANSITION — `MC_Task_Type` changing 0 -> 1, 2 or 3 —
and the machine returns it to 0 once it sees our `AGV_Task_Recive`. Reading the
level on a timer cannot tell one request from two: a station that finishes a
job and raises another of the same type between two reads presents an unchanged
value, and the second job is never created.

An OPC-UA subscription reports CHANGES, and with `QueueSize > 1` the server
queues them instead of overwriting. Two rapid transitions arrive as two
notifications. That is the whole reason this exists.

⚠ THE CUSTOMER SAID POLLING. In the 2026-08-04 review they said the interaction
is not event-driven and that the CSM should scan continuously. We read that as
being about their application logic — both sides raise bits in a shared block —
rather than about the OPC-UA transport, which can still deliver change
notifications on those same tags. It is their statement and it has not been
withdrawn, so customer question Q17a asks them to confirm. Building this does
not commit them to it: `EquipmentAdapter` is the boundary, and a polling
implementation would sit behind the identical interface.

⚠ NOT YET RUN AGAINST CUSTOMER EQUIPMENT. It is tested against a local server
that exposes the documented variable names, which proves the client and the
subscription semantics — not the customer's server, its node ids, or its
security policy.

NAMES
=====

Variables are the customer's, from `AGV与主机设备对接流程及协议.xlsx`, sheet
主机与AGV交互变量表. Every signal exists twice, `_UW` (unwind) and `_RW`
(rewind), and `DockingAxis` decides which half is meant.
"""

import asyncio

from .base import (EquipmentAdapter, MachineNumber, MaterialPresence,
                   StationStatus, TaskProcessing, TaskType, TransportCall)

#: The machine's half of the block. Suffixed `_UW` or `_RW` per docking axis.
MC_TO_AGV = (
    "MC_HeartBeat", "MC_Num", "MC_Task_Type", "MC_Ready", "MC_Alarm",
    "MC_Auto", "MC_Enter_Permitted", "MC_Door_O", "MC_Door_C",
    "MC_Pos_A", "MC_Pos_B", "MC_Take_OK", "MC_Put_OK",
    "MC_Rolling_Full", "MC_Roll_Null", "MC_Roll_IN", "MC_Task_Delete",
)

#: Ours.
AGV_TO_MC = (
    "AGV_HeartBeat", "AGV_MC_Num", "AGV_Task_Recive", "AGV_Task_ongoing",
    "AGV_Enter_Request", "AGV_Entering", "AGV_Exit", "AGV_Take_OK",
    "AGV_Put_OK", "AGV_Task_Type", "AGV_Task_Processing", "AGV_Num",
)

#: Unsuffixed signals — one per machine rather than one per docking axis.
UNSUFFIXED = frozenset({"MC_HeartBeat", "MC_Num", "AGV_HeartBeat",
                        "AGV_MC_Num"})

#: HOW MANY CHANGES THE SERVER KEEPS FOR US.
#:
#: The one number that makes this better than polling. At 1 — the OPC-UA
#: default — the server overwrites a pending notification and two rapid
#: transitions arrive as one, which is the same coalescing that polling
#: suffers, just at a different layer.
QUEUE_SIZE = 10

#: How often the server samples the variable, in milliseconds. Must be shorter
#: than the machine's re-raise gap; that gap is customer question Q17a and we
#: do not have it, so this is a starting value and not a justified one.
SAMPLING_MS = 50.0
PUBLISH_MS = 100.0


def variable_name(signal, axis=None):
    """`MC_Ready` + REWIND_A -> `MC_Ready_RW`. Unsuffixed signals stay bare."""
    if signal in UNSUFFIXED or axis is None:
        return signal
    return signal + axis.suffix


class _SignalCache:
    """Latest value per variable, and a QUEUE of the transitions that matter.

    A subscription hands us changes. Most are only interesting as a current
    value, but `MC_Task_Type` going 0 -> 1/2/3 IS the request, so those are
    kept in order rather than collapsed into "the value is 1 now".
    """

    def __init__(self):
        self.values = {}
        self.requests = []          # (station_id, TaskType), oldest first

    def update(self, station_id, name, value):
        key = (station_id, name)
        previous = self.values.get(key)
        self.values[key] = value
        if name.startswith("MC_Task_Type") and previous in (None, 0) and value:
            # The edge, not the level. This is the request.
            self.requests.append((station_id, TaskType(value)))

    def get(self, station_id, name, default=None):
        return self.values.get((station_id, name), default)

    def take_requests(self):
        out, self.requests = self.requests, []
        return out


class OpcUaEquipmentClient(EquipmentAdapter):
    """`EquipmentAdapter` over OPC-UA. One server, many stations.

    Deliberately holds no CSM logic. It turns variables into the vocabulary the
    rest of the CSM already speaks — calls, presence, status codes — and
    nothing above it learns that OPC-UA exists.
    """

    def __init__(self, endpoint, stations, axis=None, namespace_uri=None):
        """
        :param endpoint:  e.g. "opc.tcp://192.168.1.10:4840"
        :param stations:  {our name: node-id prefix or object browse name}
        :param axis:      which `DockingAxis` this client speaks for, or None
                          for the unsuffixed signals only.
        """
        self.endpoint = endpoint
        self.stations = dict(stations)
        self.axis = axis
        self.namespace_uri = namespace_uri

        self._client = None
        self._subscription = None
        self._handles = []
        self._cache = _SignalCache()
        self._acknowledged = []

    # -- connection ------------------------------------------------------

    async def connect(self):
        """Open the session and subscribe. Idempotent."""
        from asyncua import Client

        if self._client is not None:
            return
        self._client = Client(url=self.endpoint)
        await self._client.connect()

        handler = _ChangeHandler(self)
        self._subscription = await self._client.create_subscription(
            PUBLISH_MS, handler)

        for station_id in self.stations:
            for signal in MC_TO_AGV:
                node = await self._node(station_id, signal)
                if node is None:
                    continue
                # queuesize is the point — see the constant. asyncua's
                # default is 0, which the server reads as "one", and one is
                # the coalescing this adapter exists to avoid.
                handle = await self._subscription.subscribe_data_change(
                    node, queuesize=QUEUE_SIZE,
                    sampling_interval=SAMPLING_MS)
                self._handles.append((handle, station_id, signal, node))

    async def disconnect(self):
        if self._subscription is not None:
            await self._subscription.delete()
            self._subscription = None
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    async def _node(self, station_id, signal):
        """Resolve one variable on one station, or None if the server lacks it.

        Missing variables are tolerated rather than fatal: a real line will not
        expose every signal on every station — the cold press has `MC_Shift`
        and nothing else does — and refusing to start over one absent tag would
        make the adapter useless against the real plant.
        """
        name = variable_name(signal, self.axis)
        try:
            return await self._client.nodes.root.get_child(
                ["0:Objects", f"{self.stations[station_id]}", f"2:{name}"])
        except Exception:
            return None

    # -- EquipmentAdapter ------------------------------------------------

    def poll_calls(self):
        """Requests seen since the last call, in the order they were raised.

        These come from the subscription's QUEUE, not from reading a level, so
        two requests raised inside one cycle are two entries here.
        """
        return [TransportCall(station_id, task_type, source="machine")
                for station_id, task_type in self._cache.take_requests()]

    def acknowledge_call(self, call):
        """Set `AGV_Task_Recive`, which is what makes the machine stop asking.

        The write is deliberately not awaited here: `EquipmentAdapter` is a
        synchronous interface and the CSM's tasks are not. The pending write is
        drained by `flush`, called from the same loop that owns the client.
        """
        self._acknowledged.append(call)

    async def flush(self):
        """Perform the writes queued by the synchronous interface."""
        pending, self._acknowledged = self._acknowledged, []
        for call in pending:
            node = await self._node(call.station_id, "AGV_Task_Recive")
            if node is not None:
                await node.write_value(True)

    def get_station_status(self, station_id):
        """Our five-value view, derived from the machine's real signals."""
        if station_id not in self.stations:
            return StationStatus.UNKNOWN
        if self._cache.get(station_id, variable_name("MC_Alarm", self.axis)):
            return StationStatus.FAULT
        if not self._cache.get(station_id, variable_name("MC_Ready", self.axis)):
            return StationStatus.BUSY
        presence = self.presence(station_id)
        if presence is MaterialPresence.FULL_ROLL:
            return StationStatus.FINISHED
        return StationStatus.IDLE

    def presence(self, station_id):
        """The three booleans. None if the server has not reported them yet."""
        names = [variable_name(n, self.axis) for n in
                 ("MC_Rolling_Full", "MC_Roll_Null", "MC_Roll_IN")]
        got = [self._cache.get(station_id, n) for n in names]
        if any(v is None for v in got):
            return None                  # not "nothing" — not yet known
        return MaterialPresence.from_signals(*got)

    def task_processing(self, station_id):
        value = self._cache.get(
            station_id, variable_name("AGV_Task_Processing", self.axis))
        return TaskProcessing(value) if value else None

    def machine_number(self, station_id):
        raw = self._cache.get(station_id, "MC_Num")
        return MachineNumber.parse(raw) if raw else None

    def station_map(self):
        out = {}
        for station_id in self.stations:
            mc = self.machine_number(station_id)
            if mc is not None:
                out[station_id] = str(mc)
        return out

    def send_station_command(self, station_id, command):
        """Accepted for sending only.

        There is no acknowledgement on this link, so True here means the write
        was queued and NOTHING about whether the machine acted. Confirmation is
        `send_and_confirm` plus a read-back of `presence`.
        """
        return station_id in self.stations

    def list_stations(self):
        return list(self.stations)


class _ChangeHandler:
    """asyncua calls this on every queued value change."""

    def __init__(self, client):
        self._client = client

    def datachange_notification(self, node, value, data):
        for handle, station_id, signal, known in self._client._handles:
            if known == node:
                self._client._cache.update(
                    station_id, variable_name(signal, self._client.axis), value)
                return
