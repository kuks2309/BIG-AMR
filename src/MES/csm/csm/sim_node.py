"""sim_node - run the CSM against the Gazebo simulation.

The full loop, with no hardware and no CATL protocol:

    mock factory finishes a batch
        -> EquipmentMonitorTask notices and creates a job
        -> DispatcherTask decides whose turn it is
        -> JobTrackerTask advances the job FSM: IDLE -> ASSIGNED -> RUNNING
        -> SimAcs drives the simulated robot across the warehouse
        -> arrival -> t3 -> DONE
        -> both stations notified

Start the simulation first, then this node:

    bash src/Sim/trnav_2ws_gazebo/scripts/start_sim.sh
    ros2 run csm sim_node

**Two loops, one thread.** The Supervisor runs on asyncio and rclpy has a loop
of its own, and running both means either two threads sharing the job store — a
real race, since SimAcs mutates robot state while the FSMs read it — or one loop
pumping the other. This node takes the second: asyncio is primary, and a
`RosSpinTask` calls `rclpy.spin_once(timeout_sec=0)` at 100 Hz. ROS callbacks
and subscriptions all still fire; they simply fire from inside an asyncio task.
Everything stays on one thread, which is what makes the whole system reason-able
without a single lock.

The velocity controller becomes a supervised FSM too (`DriveTask`), rather than
a ROS timer. It is a periodic activity with a rate of its own, which is exactly
what an FsmTask is, and it means one shutdown path instead of two.
"""

import argparse
import asyncio
import time

import rclpy
from rclpy.node import Node

from .adapters.base import StationStatus
from .adapters.mock import OpcUaEquipment
from . import plant, records, records_sqlite
from .material_profile import simulator_profile
from .ui.server import UiServer
from .adapters.sim_acs import SimAcs
from .pda import Pda
from .runtime import FsmTask, build_mes
from .runtime.capacity import LineCapacity

#: Who feeds whom, built from the documented Big AGV material flow — see
#: plant.SEGMENTS and the source list at the top of plant.py.
#:
#: The previous table was invented and wrong in a way that changed which jobs
#: exist at all: it fed the cold press directly from the coater, a link the real
#: line does not have (Slitting and Calendering sit between them), and it gave
#: every machine a single port instead of separate LD and ULD.
#:
#: Each LD port is fed from the ULD ports of the previous stage. A machine calls
#: for material at its LD; the CSM answers by naming a source, exactly as before.
FEEDS = dict(plant.FEEDS)

STATIONS = list(plant.DOCKS)

#: The job FSM thinks in jobs, which last minutes — a few hertz is ample.
MES_RATE_HZ = 4.0
#: The velocity controller wants a steadier rate to keep motion smooth.
DRIVE_RATE_HZ = 20.0
#: How often rclpy is pumped. Well above every other rate here, so a ROS
#: callback is never what anything is waiting on.
SPIN_RATE_HZ = 100.0


class RosSpinTask(FsmTask):
    """Pumps rclpy from inside the asyncio loop.

    Non-blocking (`timeout_sec=0.0`), so it services whatever is ready and
    returns. Subscriptions, timers and services all still work — they are simply
    driven from here instead of from `rclpy.spin`.
    """

    name = "ros_spin"
    period = 1.0 / SPIN_RATE_HZ

    def __init__(self, node):
        super().__init__()
        self.node = node

    async def step(self):
        if rclpy.ok():
            rclpy.spin_once(self.node, timeout_sec=0.0)


class DriveTask(FsmTask):
    """The velocity controller — SimAcs's per-cycle drive step.

    A ROS timer before. It is a periodic activity with its own rate, which is
    what an FsmTask is, and as a supervised task it gets the same shutdown path
    as everything else instead of a separate one.
    """

    name = "drive"
    period = 1.0 / DRIVE_RATE_HZ

    def __init__(self, acs):
        super().__init__()
        self.acs = acs

    async def step(self):
        self.acs.drive()

    async def on_stop(self):
        """Stop the wheels however the run ended — clean exit, Ctrl-C, or a
        crash somewhere else. This is the reason release belongs in on_stop."""
        self.acs._stop()


#: How many batches after a station is fed before we ask for its empty
#: core back. Stands for "the machine has finished with the roll"; two
#: batches comfortably exceeds the default 12 s processing time.
BOBBIN_DELAY_BATCHES = 2


def _machine_number_for(station):
    """Our station name -> the customer's `MC_Num`, e.g. `2A01`.

    Cathode (2) throughout, because that is the line the simulator models.
    Returns None for ports the scheme does not cover — the ASRS and the WIP
    racks are not machines and have no machine number, and inventing one for
    them would put a fiction into the station_map record.
    """
    family = station.split("_")[0]
    letter = None
    if family.startswith("GRV"):
        letter = "A"                    # gravure
    elif family.startswith("CTR"):
        letter = "T"                    # coating
    elif family.startswith("SLT") or station.startswith("SLT"):
        # ⚠ OURS, NOT THEIRS. The documented letters are A, T and L (cold
        # press); the slitter is not among them. L is borrowed so the record
        # has something consistent, and it is wrong the moment the customer
        # tells us their real letter.
        letter = "L"
    if letter is None:
        return None
    instance = records.instance_of(station)
    return f"2{letter}{instance or 1:02d}"


#: WIP RACK CAPACITY, from the specification's naming table:
#: WIPGP 2, WIPCTR 13, WIPSLT 30 (and WIPCAL 28 on the anode side, which the
#: simulator does not model). These are the customer's numbers, not ours.
RACK_CAPACITY = {"WIP_GRV": 2, "WIP_CTR": 13, "WIP_SLT": 30}


def _redundancy(text):
    """Parse `--line-redundancy=`, tolerating the empty value launch produces.

    The launch file joins flag and value (`--line-redundancy=`) so an empty
    LaunchConfiguration cannot eat the next token. That means argparse can be
    handed a bare empty string, which `type=int` rejects with a hard exit — the
    same trap the charging thresholds document above.
    """
    text = (text or "").strip()
    return int(text) if text else 0


def _rack_sizes():
    """Slots per rack PORT, split from the documented family capacity.

    ⚠ THE SPLIT IS OURS. The specification gives a capacity per rack family —
    "WIPCTR (coater, 13)" — while the plant model has two access ports per
    family. Nothing tells us how the slots are divided between them, so they
    are split as evenly as possible and the odd one goes to the first port.

    The TOTAL is the customer's number, which is what "the destination is full"
    depends on; only the division between ports is assumed.
    """
    sizes = {}
    for family, total in RACK_CAPACITY.items():
        ports = sorted(p for p in plant.DOCKS if p.startswith(family))
        if not ports:
            continue
        base, extra = divmod(total, len(ports))
        for i, port in enumerate(ports):
            sizes[port] = base + (1 if i < extra else 0)
    return sizes


def _leg_of(station_id):
    """The leg NAME a station belongs to, or None.

    `plant.segment_of_station` returns the segment DICT. The capacity layer
    keys its counts by leg, and a dict is unhashable — so unwrapping happens
    here, once, rather than being assumed at every call site.

    Getting this wrong on 2026-08-20 threw `TypeError: unhashable type: 'dict'`
    out of every EquipmentMonitorTask step. Nothing crashed and nothing moved:
    the Supervisor caught the exception, logged it, and kept the other five
    FSMs running, so the fleet sat idle looking like a navigation problem. That
    is the supervisor behaving exactly as designed, and it is also why a silent
    per-step failure needs to be loud somewhere else.
    """
    segment = plant.segment_of_station(station_id)
    return segment["name"] if segment else None


class MesSimNode(Node):

    def __init__(self, batch_seconds, job_timeout, process_seconds,
                 robot_names=None, battery_scale=1.0,
                 charging_thresholds=None, start_battery=None,
                 db_path=None, line_redundancy=0, acs_loopback=False,
                 acs_endpoint=None):
        super().__init__("csm")

        # Every station the equipment layer knows about, INCLUDING the outbound
        # one — a delivery notification to a station that is not in this list is
        # refused, which is what produced the "did not accept 'delivered'"
        # warnings before.
        all_stations = list(plant.DOCKS)
        #: The machines that can call for material. The store never calls —
        #: it is a warehouse, it only supplies.
        self._callers = list(FEEDS)

        # THE PROTOCOL-FAITHFUL STAND-IN, not the plain mock.
        #
        # OpcUaEquipment is MockEquipment plus the things the real machines
        # actually have: an MC_Num identity, the three presence booleans, the
        # nine task-processing codes, a heartbeat, and — the reason for the
        # switch — MC_Enter_Permitted, which is what the docking watchdog
        # reads. A mock without those cannot exercise them, so they stayed
        # proven in unit tests and unproven in the running system.
        self.equipment = OpcUaEquipment(all_stations, time.monotonic,
                                        process_seconds=process_seconds)

        # MC_Num, so the station_map record fills in from the machines rather
        # than being configured. Polarity 2 = cathode; the simulator models the
        # cathode line. Type letters are the customer's: A gravure, T coating,
        # L cold press. The slitter has no letter of its own in the documented
        # set, so it takes L — flagged rather than invented silently, and it is
        # question Q14-adjacent whenever the customer confirms their scheme.
        for station in all_stations:
            mc = _machine_number_for(station)
            if mc is not None:
                self.equipment.set_machine_number(station, mc)

        # Entry is PERMITTED by default, and held. The watchdog needs the
        # signal present continuously to allow a dock at all, so withholding it
        # here would stop the line rather than test anything. A test that wants
        # to prove the watchdog withdraws it deliberately.
        for station in all_stations:
            self.equipment.set_enter_permitted(station, True)
        # The store is a warehouse: always supplied, never processing. It is
        # the only thing that starts with something to give.
        self.equipment.mark_store("ASRS")
        # A machine's output appears at its UNLOAD port, not where the material
        # went in. Without this the line cannot fill past gravure: a coater job
        # asks GRV_i_ULD for material and nothing ever puts any there, so the
        # job is never created and amr2 and amr3 never move. Observed exactly
        # that — 16 coater and slitter calls raised, zero jobs created.
        for _load, _unload in plant.PORT_LINKS:
            self.equipment.link_ports(_load, _unload)
        # The equipment goes to the ACS as well, so a robot can ask a
        # machine whether it may enter — MC_Enter_Permitted, condition 7.
        self.acs = SimAcs(self, robot_names=robot_names,
                          equipment=self.equipment)
        for robot in self.acs.robots:
            robot.battery_scale = battery_scale
            # NOT a model of anything — robots really do start a shift
            # charged. This exists so a charge cycle can be watched in a
            # minute instead of the hour the drain rate implies, which is
            # the only honest way to check the charging path works.
            level = (start_battery.get(robot.name)
                     if isinstance(start_battery, dict) else start_battery)
            if level is not None:
                robot.battery = float(level)

        # The racks, at the customer's documented capacities. Without these
        # the rack records exist and hold nothing, so "the destination is
        # full" could never become true and the diversion jobs could never
        # fire — which is exactly what the live view showed.
        # WHERE SECTION 7's RECORDS LIVE.
        #
        # In memory unless a path is given, which keeps a throwaway run
        # throwaway. Persistence is opt-in rather than default because a
        # simulator that silently reloads yesterday's rack contents is
        # confusing in a way a real plant is not — there, yesterday's pallets
        # really are still on the racks.
        if db_path:
            self._records = records_sqlite.SqliteRecords(
                db_path, rack_sizes=_rack_sizes())
            self.get_logger().info(f"records: SQLite at {db_path}")
        else:
            self._records = records.InMemoryRecords(_rack_sizes())
            self.get_logger().info("records: in memory — lost on exit "
                                   "(pass --db to keep them)")

        # THE ACS THE CSM ACTUALLY TALKS TO.
        #
        # Normally `self.acs` itself — a direct Python call. With
        # --acs-loopback the real GraphQL client goes in the middle:
        #
        #     CSM --(GraphQL over a socket)--> LoopbackAcsServer --> SimAcs
        #
        # Same fleet, same Gazebo, but every order and every outcome crosses a
        # real socket through the client that will one day talk to the
        # customer's ACS. It is the only way to exercise that client under real
        # timers before we can reach their network — see acs_server.py.
        #
        # `self.acs` stays SimAcs regardless, because the drive loop below
        # steps it directly and that is not an ACS operation.
        self._acs_server = self._acs_client = None
        mes_acs = self.acs
        if acs_endpoint:
            # A REAL FLEET CONTROLLER. The client is the same one the loopback
            # exercises; only the address differs.
            #
            # ⚠ NO RESULT VOCABULARY IS PASSED. Against their server we do not
            # know the words an order's `result` can contain — customer
            # question A6 — so every outcome reads UNKNOWN and jobs run to
            # their timeout rather than completing. That is the honest
            # behaviour and it is why the log line below says so out loud: a
            # fleet that appears to work while every job times out is the
            # worst way to discover a missing table.
            from .adapters.acs_client import AcsGraphQLClient
            self._acs_client = AcsGraphQLClient(acs_endpoint)
            self._acs_client.start()
            mes_acs = self._acs_client
            self.get_logger().info(f"ACS: real endpoint {acs_endpoint}")
            self.get_logger().warning(
                "no result vocabulary for this ACS (customer question A6) — "
                "orders will be sent and their outcomes will read UNKNOWN")
        elif acs_loopback:
            from .adapters.acs_client import AcsGraphQLClient
            from .adapters.acs_server import (LOOPBACK_RESULT_STATES,
                                              LoopbackAcsServer)
            self._acs_server = LoopbackAcsServer(self.acs).start()
            self._acs_client = AcsGraphQLClient(
                self._acs_server.endpoint,
                result_states=LOOPBACK_RESULT_STATES)
            self._acs_client.start()
            mes_acs = self._acs_client
            self.get_logger().info(
                f"ACS loopback: CSM -> {self._acs_server.endpoint} -> SimAcs")

        # EVERY PLACE MATERIAL CAN BE, declared into the records store so a
        # location reference resolves. The plant is the source of truth; this
        # copies its index in, the same way rack sizes are passed in above.
        plant.declare_locations(self._records)

        self.app = build_mes(
            self.equipment, mes_acs,
            source_for=lambda sid: FEEDS.get(sid, "ASRS"),
            clock=time.monotonic,
            logger=lambda m: self.get_logger().info(m),
            job_timeout_s=job_timeout,
            poll_seconds={"job_tracker": 1.0 / MES_RATE_HZ},
            # Turns on the specification's bobbin returns (jobs 3, 7, 11).
            # Every hop in this plant is an exchange, so without this the line
            # moves rolls forward and never sends an empty core back.
            return_for=plant.bobbin_return_for,
            records=self._records,
            charging_thresholds=charging_thresholds,
            # The CCS manual §2.15 ceiling. Without it a machine that keeps
            # calling produces an unbounded queue: a six-minute run on
            # 2026-08-20 created 14 jobs, finished 5, and grew its open-call
            # list for the whole run with nothing anywhere saying so.
            capacity=LineCapacity(plant.SEGMENTS, _rack_sizes().get,
                                  redundancy=line_redundancy),
            leg_of=_leg_of,
            # The one job type CSM originates itself: a source holding finished
            # material with every destination occupied, parked on the WIP rack
            # so the upstream machine does not block.
            #
            # Shipped opt-in and never opted into here, so it fired only in
            # tests. Measured 2026-08-20 across four runs: diverted_to_rack 0,
            # all 45 rack slots empty, every time. It also kept the §2.15
            # ceiling loose, because material on a leg's racks is one of the
            # four terms that ceiling counts and ours was always zero.
            divert_for=plant.SEGMENTS,

            # ⚠ INVENTED, and marked as such where it is built. Nobody has
            # told us which machine requires which attribute, and without SOME
            # description every roll in the plant is a thing nobody can name:
            # §1.3 then refuses to feed every machine, the rotation rules have
            # nothing to match on, and the map draws every payload the same
            # grey. Replace wholesale when the real machine configuration
            # arrives — nothing else changes.
            profile=simulator_profile(plant.STATIONS),
        )

        # THE HANDHELD, so its state is visible rather than only testable.
        #
        # `Pda` is CSM's fourth responsibility and it had no instance in the
        # running system at all — the logic was proven by tests and then
        # nothing held it, so an abnormal report had nowhere to live and the
        # live view had nothing to show. One here gives the UI something real
        # to read, and gives a person somewhere to file a report.
        #
        # POSITION CODES STAY EMPTY. The 001-100 / 101-199 / 200-299 / 300-399
        # ranges have never been mapped to our station names (customer question
        # Q18), and `resolve_position` refuses what it cannot resolve rather
        # than inventing a destination for a worker's button press.
        self.pda = Pda(self.app.store)

        # The fake factory. A ROS timer is fine — RosSpinTask fires it.
        self.create_timer(batch_seconds + 2.0, self._produce_batch)
        self._next_station = 0
        #: Stations fed a roll and not yet asked for their empty core back.
        self._fed = []

        if start_battery is not None:
            # Said out loud because a mistyped robot name silently leaves that
            # robot full, which reads as the charging rule failing to fire.
            levels = ", ".join(f"{r.name} {r.battery:.0f}%"
                               for r in self.acs.robots)
            self.get_logger().info(f"starting battery — {levels}")

        chain = " -> ".join(s["name"] + ": " + s["from"][0] + " -> "
                             + s["to"][0].split("_")[0] + "_LD"
                             for s in plant.SEGMENTS)
        self.get_logger().info(f"CSM up — process route: {chain}")
        self.get_logger().info(f"job timeout {job_timeout:.0f}s")
        self.get_logger().info("waiting for /odom from the simulation...")

    def _produce_batch(self):
        """A machine calls for material — the way work actually starts.

        Round-robin across the machines. The supply chain is kept stocked so
        the calls can be served; the Gazebo world has one robot, so what this
        node is for is watching a job go end to end, not watching a line fill.
        """
        from .adapters.base import TaskType

        station = self._callers[self._next_station % len(self._callers)]
        self._next_station += 1
        self.equipment.raise_call(station, TaskType.LOAD, source="PDA")

        # AND THE OTHER HALF OF THE EXCHANGE.
        #
        # A machine that has been fed a roll is holding the empty core once it
        # has consumed it, and the specification has three jobs for getting
        # that core back (3, 7 and 11). Nothing in this factory used to ask for
        # them, so the forward half of every hop was exercised and the return
        # half never was.
        #
        # Delayed rather than raised immediately: the machine cannot hand back
        # a core it has not finished with, and asking instantly would test a
        # state the real line never reaches.
        #
        # The delay is counted in BATCHES, not in a rotation of the caller
        # list. Keying it to the rotation made the first bobbin appear after
        # twelve batches — about five and a half minutes — which is long enough
        # that a person watching concludes the feature does not work. What the
        # delay actually stands for is "the machine has finished with the
        # roll", and two batches already exceeds the processing time.
        self._fed.append(station)
        if len(self._fed) > BOBBIN_DELAY_BATCHES:
            spent = self._fed.pop(0)
            if plant.bobbin_return_for(spent):
                self.equipment.raise_call(spent, TaskType.UNLOAD,
                                          source="machine")
                self.get_logger().info(
                    f"--- {spent} has an empty bobbin to return ---")

        # No force-stocking. Only the store is permanently supplied; every
        # machine has to be FED, then PROCESS, before anything downstream can
        # collect from it. So the line fills:
        #
        #     ASRS -> 1A01,  1A01 processes,  then 1T01 can be fed, ...
        #
        # A call that cannot be served yet stays outstanding rather than being
        # dropped, which is exactly the behaviour worth watching — the machine
        # keeps asking and is served the moment its supplier has output.
        self.get_logger().info(f"--- {station} called for material (PDA) ---")


async def _run(node):
    """Register the ROS-facing tasks alongside the three MES FSMs, and go."""
    supervisor = node.app.supervisor
    supervisor.register(RosSpinTask(node))
    supervisor.register(DriveTask(node.acs))

    health = await supervisor.run()
    node.get_logger().info(f"final health: {health}")
    node.get_logger().info(f"jobs: {node.app.health()}")


def _truthy(value):
    """A launch-supplied flag. Empty means off, which is what an omitted
    launch argument arrives as."""
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _start_levels(text):
    """Starting battery: one number for the whole fleet, or one per robot.

        20                     every robot starts at 20%
        amr1=35,amr2=36        amr1 and amr2 named, the rest start full

    Per robot because a fleet that all starts at the same level all crosses the
    low mark at the same moment, and three robots queueing for chargers at once
    is not the case worth watching — they should reach it one at a time.

    Returns a float, a {name: float} dict, or None for "leave them full".
    """
    text = (text or "").strip()
    if not text:
        return None
    if "=" not in text:
        return float(text)
    levels = {}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        name, _, value = part.partition("=")
        # Named robots only. A typo here would otherwise start a robot full
        # and look like the charging rule failing to fire.
        levels[name.strip()] = float(value)
    return levels


def _percent(text):
    """A battery threshold, or None for "leave the CSM's default alone".

    Empty means unset because a launch file cannot omit an argument
    conditionally — the value is not known while the launch description is
    being built — so an unset threshold arrives as an empty string rather than
    not arriving.
    """
    text = (text or "").strip()
    return float(text) if text else None


def main():
    parser = argparse.ArgumentParser(description="CSM against Gazebo")
    parser.add_argument("--batch-seconds", type=float, default=25.0,
                        help="how often the fake factory finishes a batch")
    parser.add_argument("--robots", type=int, default=0,
                        help="fleet size; 0 uses the single-robot world")
    parser.add_argument("--process-seconds", type=float, default=12.0,
                        help="how long a machine works before it has output")
    # 600 s, matching job.py and mes_app.py. The old 120 s appears in no
    # customer document and contradicted the CSM's own default; the meeting
    # files give PROCESS times (30 s gluing, 65/130/260 s stations) and no
    # transport timeout at all. It was too short to cover a job's two docks
    # plus travel, so every delivery was guillotined mid-dock: 3 collections
    # and zero deliveries, which starved amr2 and amr3 of work entirely.
    # See docs/adr/2026-08-07-job-timeout-and-idle-parking.md
    parser.add_argument("--job-timeout", type=float, default=600.0,
                        help="seconds a job may spend in one state before t5")
    parser.add_argument("--ui-port", type=int, default=8080,
                        help="live view in a browser; 0 turns it off")
    parser.add_argument("--battery-scale", type=float, default=1.0,
                        help="speed up battery drain and charge, for watching "
                             "a charge cycle without waiting an hour")
    # The three charging thresholds. None of them is a measured number — see
    # runtime/tasks/charging.py — so they are arguments rather than constants,
    # and a run that wants to WATCH charging rather than avoid it turns them
    # up and down from here.
    parser.add_argument("--low-battery", type=_percent, default=None,
                        help="percent below which an idle robot is sent to "
                             "charge (default 30)")
    parser.add_argument("--charge-to", type=_percent, default=None,
                        help="percent to charge to before returning to work. "
                             "Lower finishes sooner (default 90)")
    parser.add_argument("--critical-battery", type=_percent, default=None,
                        help="percent below which a robot goes even while "
                             "holding a job (default 12)")
    # CCS manual §2.15's tuning knob, and a number nobody has given us — see
    # debt-118. 0 means the ceiling is exactly ports + rack slots. NEGATIVE is
    # legitimate and the manual says so: it keeps a line deliberately short,
    # which is how a three-robot cell can exercise the ceiling at all.
    parser.add_argument("--line-redundancy", type=_redundancy, default=0,
                        help="shift every leg's task ceiling (CCS §2.15); "
                             "may be negative to make the ceiling bind sooner")
    parser.add_argument("--db", default="",
                        help="keep the records in this SQLite file so they "
                             "survive a restart; empty means in memory")
    parser.add_argument("--start-battery", type=_start_levels, default=None,
                        help="start robots below full, so a charge cycle "
                             "happens without waiting: one number for the "
                             "whole fleet (20), or per robot "
                             "(amr1=35,amr2=36,amr3=40)")
    # A VALUE, not store_true. The launch file can only pass a flag in the
    # joined `--flag=value` form — it drops an empty argument, and a bare
    # `--acs-loopback` would swallow the next token — so the flag has to be
    # able to arrive as `--acs-loopback=` and mean off. See the note beside
    # `--low-battery` in fleet.launch.py.
    parser.add_argument("--acs-endpoint", default="",
                        help="GraphQL endpoint of a REAL ACS, e.g. "
                             "http://10.0.0.5:8080/graphql. Empty means drive "
                             "the simulated fleet instead. Overrides "
                             "--acs-loopback.")
    parser.add_argument("--acs-loopback", type=_truthy, default=False,
                        help="put the real GraphQL client between the CSM and "
                             "SimAcs, so the ACS link is exercised over a real "
                             "socket instead of a direct call")
    args, ros_args = parser.parse_known_args()

    rclpy.init(args=ros_args)
    # Fleet names must match the Gazebo model names, which fleet.launch.py
    # sets with -entity. None means the single-robot world.
    names = [f"amr{i + 1}" for i in range(args.robots)] if args.robots else None
    thresholds = {k: v for k, v in (
        ("low_battery", args.low_battery),
        ("charge_to", args.charge_to),
        ("critical_battery", args.critical_battery),
    ) if v is not None}
    node = MesSimNode(args.batch_seconds, args.job_timeout,
                      args.process_seconds, robot_names=names,
                      battery_scale=args.battery_scale,
                      charging_thresholds=thresholds,
                      start_battery=args.start_battery,
                      db_path=args.db.strip() or None,
                      line_redundancy=args.line_redundancy,
                      acs_loopback=args.acs_loopback,
                      acs_endpoint=args.acs_endpoint.strip() or None)

    # The live view. Started AFTER the node, so it always has something to
    # show, and never allowed to stop the simulation: a port already in use is
    # an inconvenience, not a reason not to run a factory.
    ui = None
    if args.ui_port:
        ui = UiServer(node, port=args.ui_port,
                      logger=lambda m: node.get_logger().info(m))
        ui.start()

    try:
        asyncio.run(_run(node))
    except KeyboardInterrupt:
        pass
    finally:
        if ui is not None:
            ui.stop()
        # Before destroy_node: the client's subscription thread reads the node's
        # ACS, and a socket left open outlives the process it belongs to.
        if getattr(node, "_acs_client", None) is not None:
            node._acs_client.stop()
        if getattr(node, "_acs_server", None) is not None:
            node._acs_server.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
