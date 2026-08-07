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
from .adapters.mock import MockEquipment
from . import plant
from .adapters.sim_acs import SimAcs
from .runtime import FsmTask, build_mes

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


class MesSimNode(Node):

    def __init__(self, batch_seconds, job_timeout, process_seconds,
                 robot_names=None):
        super().__init__("csm")

        # Every station the equipment layer knows about, INCLUDING the outbound
        # one — a delivery notification to a station that is not in this list is
        # refused, which is what produced the "did not accept 'delivered'"
        # warnings before.
        all_stations = list(plant.DOCKS)
        #: The machines that can call for material. The store never calls —
        #: it is a warehouse, it only supplies.
        self._callers = list(FEEDS)

        self.equipment = MockEquipment(all_stations, time.monotonic,
                                       process_seconds=process_seconds)
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
        self.acs = SimAcs(self, robot_names=robot_names)

        self.app = build_mes(
            self.equipment, self.acs,
            source_for=lambda sid: FEEDS.get(sid, "ASRS"),
            clock=time.monotonic,
            logger=lambda m: self.get_logger().info(m),
            job_timeout_s=job_timeout,
            poll_seconds={"job_tracker": 1.0 / MES_RATE_HZ},
        )

        # The fake factory. A ROS timer is fine — RosSpinTask fires it.
        self.create_timer(batch_seconds + 2.0, self._produce_batch)
        self._next_station = 0

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
    args, ros_args = parser.parse_known_args()

    rclpy.init(args=ros_args)
    # Fleet names must match the Gazebo model names, which fleet.launch.py
    # sets with -entity. None means the single-robot world.
    names = [f"amr{i + 1}" for i in range(args.robots)] if args.robots else None
    node = MesSimNode(args.batch_seconds, args.job_timeout,
                      args.process_seconds, robot_names=names)
    try:
        asyncio.run(_run(node))
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
