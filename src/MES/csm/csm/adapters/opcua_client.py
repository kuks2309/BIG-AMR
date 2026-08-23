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

    #: Set False when the server refuses to queue changes — see
    #: `verify_queueing`. Public because it changes what this adapter can
    #: promise, and a caller that cares should be able to ask.
    coalescing_protected = None

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
        #: (station, code) pairs for `AGV_Task_Processing`.
        self._task_processing_writes = []
        #: What the server actually granted, per subscribed variable.
        self.revised_queue_sizes = {}

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

        await self.verify_queueing()

    async def verify_queueing(self):
        """Ask the server what it ACTUALLY granted, and believe that instead.

        THE SERVER IS ALLOWED TO SAY NO. `QueueSize` is a request, not a
        setting: the server returns a RevisedQueueSize and may revise it down.
        Plenty of PLC OPC-UA servers cap it at 1.

        If it does, this adapter's whole advantage over polling is gone —
        two rapid transitions coalesce into one exactly as they would on a
        timer, with no error and nothing in the log. The same bug, one layer
        further down, and harder to find because the code says QUEUE_SIZE = 10
        and looks correct.

        ⚠ asyncua does not expose the revised value: `create_monitored_items`
        reads it off the response and keeps only the item id, storing the
        REQUESTED size in its own bookkeeping. So the library will let us
        believe we are protected. This asks again via ModifyMonitoredItems,
        whose response carries the same field, and requests the parameters we
        already have — so it changes nothing and only reads back.
        """
        from asyncua import ua

        if self._subscription is None or not self._handles:
            return
        items = []
        ordered = []
        # `subscribe_data_change` hands back the SERVER handle, while
        # asyncua keys its own bookkeeping by the CLIENT handle. Looking the
        # first up in the second finds nothing and this check quietly did
        # nothing at all — which is the exact failure mode it exists to
        # prevent, so it is worth naming rather than fixing silently.
        by_server_handle = {
            data.server_handle: client_handle
            for client_handle, data in self._subscription._monitored_items.items()
            if getattr(data, "server_handle", None) is not None
        }
        for handle, station_id, signal, node in self._handles:
            client_handle = by_server_handle.get(handle)
            if client_handle is None:
                continue
            request = ua.MonitoredItemModifyRequest()
            request.MonitoredItemId = handle
            request.RequestedParameters = ua.MonitoringParameters(
                ClientHandle=client_handle,
                SamplingInterval=SAMPLING_MS,
                QueueSize=QUEUE_SIZE,
                DiscardOldest=False,
            )
            items.append(request)
            ordered.append((station_id, signal))

        if not items:
            return
        params = ua.ModifyMonitoredItemsParameters()
        params.SubscriptionId = self._subscription.subscription_id
        params.ItemsToModify = items
        params.TimestampsToReturn = ua.TimestampsToReturn.Both
        results = await self._client.uaclient.modify_monitored_items(params)

        smallest = QUEUE_SIZE
        for (station_id, signal), result in zip(ordered, results):
            granted = int(result.RevisedQueueSize)
            self.revised_queue_sizes[
                (station_id, variable_name(signal, self.axis))] = granted
            smallest = min(smallest, granted)

        self.coalescing_protected = smallest > 1
        if not self.coalescing_protected:
            # Loud, because the failure it reintroduces is silent.
            print(f"OPC-UA WARNING: server revised QueueSize to {smallest}. "
                  f"Change notifications will COALESCE, so two transport "
                  f"requests raised close together arrive as one and the "
                  f"second job is never created. This adapter is no better "
                  f"than polling until the server allows queueing.")
        return self.coalescing_protected

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
        from asyncua import ua

        pending, self._acknowledged = self._acknowledged, []
        for call in pending:
            node = await self._node(call.station_id, "AGV_Task_Recive")
            if node is not None:
                await node.write_value(True)

        writes, self._task_processing_writes = self._task_processing_writes, []
        for station_id, code in writes:
            node = await self._node(station_id, "AGV_Task_Processing")
            if node is not None:
                # Int32 explicitly: asyncua will not infer the server's type
                # from a bare Python int and the write fails BadTypeMismatch.
                await node.write_value(ua.Variant(int(code),
                                                  ua.VariantType.Int32))

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

    def task_delete_requested(self, station_id):
        """`MC_Task_Delete`. None until the server has reported it once.

        None is not False here either. Before the first notification we have no
        value, and reading that as "the machine has not deleted the task" would
        make a cancellation look merely unfinished when in truth we are not yet
        listening.
        """
        return self._cache.get(
            station_id, variable_name("MC_Task_Delete", self.axis))

    def write_task_processing(self, station_id, code):
        """Queue `AGV_Task_Processing`. `code` of None writes 0, not nothing.

        Steps 1 and 4 of the cancellation are both this write. Queued rather
        than awaited for the same reason as `acknowledge_call`: the adapter
        interface is synchronous and the client is not.
        """
        if station_id not in self.stations:
            return
        self._task_processing_writes.append((station_id, code or 0))

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
