"""sim_node - run the Mini MES against the Gazebo simulation.

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
    ros2 run mini_mes sim_node

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
from .adapters.sim_acs import STATION_POSES, SimAcs
from .runtime import FsmTask, build_mes

#: Where each station's output goes next. A real line is a process route, not
#: everything piling into one place: a part finishes at one machine and moves to
#: the next operation. This is what makes the robot travel between different
#: pairs of stations rather than shuttling to the same corner every time.
ROUTE = {
    "station_3": "station_5",
    "station_5": "station_9",
    "station_9": "station_out",     # finished goods leave here
}

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

    def __init__(self, batch_seconds, job_timeout):
        super().__init__("mini_mes")

        # Every station the equipment layer knows about, INCLUDING the outbound
        # one — a delivery notification to a station that is not in this list is
        # refused, which is what produced the "did not accept 'delivered'"
        # warnings before.
        all_stations = list(STATION_POSES)
        #: Only these produce work. station_out is a sink; it receives and
        #: never finishes a batch of its own.
        self._producers = [s for s in ROUTE]

        self.equipment = MockEquipment(all_stations, time.monotonic,
                                       process_seconds=batch_seconds)
        self.acs = SimAcs(self)

        self.app = build_mes(
            self.equipment, self.acs,
            route=lambda sid: ROUTE.get(sid, "station_out"),
            clock=time.monotonic,
            logger=lambda m: self.get_logger().info(m),
            job_timeout_s=job_timeout,
            poll_seconds={"job_tracker": 1.0 / MES_RATE_HZ},
        )

        # The fake factory. A ROS timer is fine — RosSpinTask fires it.
        self.create_timer(batch_seconds + 2.0, self._produce_batch)
        self._next_station = 0

        routes = " · ".join(f"{a}→{b}" for a, b in ROUTE.items())
        self.get_logger().info(f"Mini MES up — route: {routes}")
        self.get_logger().info(f"job timeout {job_timeout:.0f}s")
        self.get_logger().info("waiting for /odom from the simulation...")

    def _produce_batch(self):
        """The fake factory finishes a batch, round-robin across stations."""
        station = self._producers[self._next_station % len(self._producers)]
        self._next_station += 1
        self.equipment.force_status(station, StationStatus.FINISHED)
        self.get_logger().info(f"--- {station} finished a batch ---")


async def _run(node):
    """Register the ROS-facing tasks alongside the three MES FSMs, and go."""
    supervisor = node.app.supervisor
    supervisor.register(RosSpinTask(node))
    supervisor.register(DriveTask(node.acs))

    health = await supervisor.run()
    node.get_logger().info(f"final health: {health}")
    node.get_logger().info(f"jobs: {node.app.health()}")


def main():
    parser = argparse.ArgumentParser(description="Mini MES against Gazebo")
    parser.add_argument("--batch-seconds", type=float, default=25.0,
                        help="how often the fake factory finishes a batch")
    parser.add_argument("--job-timeout", type=float, default=120.0,
                        help="seconds a job may spend in one state before t5")
    args, ros_args = parser.parse_known_args()

    rclpy.init(args=ros_args)
    node = MesSimNode(args.batch_seconds, args.job_timeout)
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
