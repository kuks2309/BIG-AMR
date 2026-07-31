"""sim_node - run the Mini MES against the Gazebo simulation.

The full loop, with no hardware and no CATL protocol:

    mock factory finishes a batch
        -> Mini MES creates a job
        -> job FSM: IDLE -> ASSIGNED -> RUNNING
        -> SimAcs drives the simulated robot across the warehouse
        -> arrival -> t3 -> DONE
        -> destination station notified

Start the simulation first, then this node:

    bash src/Sim/trnav_2ws_gazebo/scripts/start_sim.sh
    ros2 run mini_mes sim_node

The Mini MES itself is untouched from the mock demo. Only the class behind
AcsAdapter changed — which is what the adapter layer was built for.
"""

import argparse
import time

import rclpy
from rclpy.node import Node

from .adapters.base import StationStatus
from .adapters.mock import MockEquipment
from .adapters.sim_acs import STATION_POSES, SimAcs
from .main_cycle import MainCycle

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

        self.cycle = MainCycle(
            self.equipment, self.acs,
            clock=time.monotonic,
            logger=lambda m: self.get_logger().info(m),
            job_timeout_s=job_timeout,
        )
        # Follow the process route: a finished batch goes to the next operation.
        self.cycle.on_station_finished = \
            lambda sid: self.cycle.create_job(sid, ROUTE.get(sid, "station_out"))

        self.create_timer(1.0 / MES_RATE_HZ, self.cycle.tick)
        self.create_timer(1.0 / DRIVE_RATE_HZ, self.acs.drive)
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
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.acs._stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
