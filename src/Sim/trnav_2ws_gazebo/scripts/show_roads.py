#!/usr/bin/env python3
"""show_roads.py — paint the lane network onto the Gazebo floor.

    ros2 run trnav_2ws_gazebo show_roads.py          # draw
    ros2 run trnav_2ws_gazebo show_roads.py --clear  # remove

The road network lives in csm/adapters/roads.py as numbers. Numbers are not
reviewable: you cannot tell by reading coordinates whether a robot is following
the road or wandering. This spawns the same network into the running world as
flat coloured strips, so the lanes are visible under the robots and the question
"is it on the road?" can be answered by looking.

The strips are VISUAL ONLY — no <collision> element — so painting the roads
cannot change how anything drives. A road that pushed the robots around would
make the picture a lie.
"""

import argparse
import math
import sys

import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import DeleteEntity, SpawnEntity

from csm import plant
from csm.adapters import roads

#: Painted too, because "why is that robot sitting there?" is answered instantly
#: if the parking bay is visible.
PARKING = list(plant.PARKING.values())
EXIT_POSES = plant.JOINS

LANE_W = 0.25          # painted width, metres
LANE_Z = 0.01          # just above the floor, so it never z-fights
DOT_R = 0.30           # waypoint marker radius


def strip_sdf(name, x, y, yaw, length, rgba):
    r, g, b, a = rgba
    return f"""<?xml version="1.0"?>
<sdf version="1.6">
  <model name="{name}">
    <static>true</static>
    <pose>{x} {y} {LANE_Z} 0 0 {yaw}</pose>
    <link name="link">
      <visual name="v">
        <geometry><box><size>{length} {LANE_W} 0.002</size></box></geometry>
        <material>
          <ambient>{r} {g} {b} {a}</ambient>
          <diffuse>{r} {g} {b} {a}</diffuse>
        </material>
      </visual>
    </link>
  </model>
</sdf>"""


def dot_sdf(name, x, y, rgba, radius=DOT_R):
    r, g, b, a = rgba
    return f"""<?xml version="1.0"?>
<sdf version="1.6">
  <model name="{name}">
    <static>true</static>
    <pose>{x} {y} {LANE_Z} 0 0 0</pose>
    <link name="link">
      <visual name="v">
        <geometry><cylinder><radius>{radius}</radius><length>0.004</length></cylinder></geometry>
        <material>
          <ambient>{r} {g} {b} {a}</ambient>
          <diffuse>{r} {g} {b} {a}</diffuse>
        </material>
      </visual>
    </link>
  </model>
</sdf>"""


def _call(node, cli, req):
    """Blocking service call that actually returns.

    rclpy's client.call() waits on a future that only completes while the node
    is being spun, and nothing is spinning it here — so it blocks for ever. Spin
    the future explicitly instead.
    """
    future = cli.call_async(req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)
    return future.result()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clear", action="store_true", help="remove the painted roads")
    args, ros_args = ap.parse_known_args()

    rclpy.init(args=ros_args)
    node = Node("show_roads")
    net = roads.build()

    #: Everything painted, and what each colour means. The legend is the point:
    #: a picture whose colours have to be explained in chat is not a diagnostic.
    dots = []
    for n, (x, y) in net.nodes.items():
        if n.startswith("dock_"):
            dots.append((f"wp_{n}", x, y, (1.0, 0.20, 0.20, 1.0), 0.45))
        elif n.startswith("aisle_"):
            dots.append((f"wp_{n}", x, y, (1.0, 1.0, 1.0, 1.0), DOT_R))
        else:
            dots.append((f"wp_{n}", x, y, (0.55, 0.55, 0.60, 1.0), DOT_R))
    # WHERE A ROBOT WAITS once it has finished inside a station and reversed
    # out. This is the spot the interlock frees on, so if two robots ever meet
    # at a handover, it happens here — which makes it worth seeing.
    for name, (x, y) in EXIT_POSES.items():
        dots.append((f"wait_{name}", x, y, (0.20, 0.95, 0.35, 1.0), 0.50))
    for i, (x, y) in enumerate(PARKING):
        dots.append((f"park_{i}", x, y, (0.75, 0.35, 0.95, 1.0), 0.50))

    names = [f"road_{a}__{b}" for a, b in net.lanes] + [d[0] for d in dots]

    if args.clear:
        cli = node.create_client(DeleteEntity, "/delete_entity")
        cli.wait_for_service(timeout_sec=10.0)
        for n in names:
            _call(node, cli, DeleteEntity.Request(name=n))
        node.get_logger().info(f"removed {len(names)} markers")
        rclpy.shutdown()
        return

    cli = node.create_client(SpawnEntity, "/spawn_entity")
    if not cli.wait_for_service(timeout_sec=15.0):
        node.get_logger().error("/spawn_entity not available — is Gazebo running?")
        rclpy.shutdown()
        sys.exit(1)

    lanes = 0
    for a, b in net.lanes:
        (x1, y1), (x2, y2) = net.nodes[a], net.nodes[b]
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 1e-3:
            continue
        # Spurs are a different colour from the ring: "which part of the network
        # is this?" is the first question when a robot goes wrong.
        spur = a.startswith(("join_", "dock_", "park_")) and \
            b.startswith(("join_", "dock_", "park_"))
        rgba = (0.95, 0.75, 0.10, 1.0) if spur else (0.20, 0.85, 0.95, 1.0)
        sdf = strip_sdf(f"road_{a}__{b}", (x1 + x2) / 2, (y1 + y2) / 2,
                        math.atan2(y2 - y1, x2 - x1), length, rgba)
        res = _call(node, cli, SpawnEntity.Request(name=f"road_{a}__{b}", xml=sdf))
        lanes += 1 if (res and res.success) else 0

    drawn = 0
    for name, x, y, rgba, rad in dots:
        res = _call(node, cli,
                    SpawnEntity.Request(name=name, xml=dot_sdf(name, x, y, rgba, rad)))
        drawn += 1 if (res and res.success) else 0

    node.get_logger().info(
        f"painted {lanes} lanes and {drawn} markers\n"
        f"  CYAN strip   ring road\n"
        f"  YELLOW strip station spur\n"
        f"  WHITE dot    ring waypoint\n"
        f"  GREY dot     spur waypoint\n"
        f"  RED dot      dock — inside the station, where it loads/unloads\n"
        f"  GREEN dot    wait spot — where it pauses after backing out\n"
        f"  PURPLE dot   parking bay")
    rclpy.shutdown()


if __name__ == "__main__":
    main()
