#!/usr/bin/env python3
"""Seer `.smap` + `/robot_pose` 를 rviz2 로 보여주는 시각화 노드.

`colcon` 불요 — `python3` 로 즉시 실행한다(저장소 규약: 비-ROS2 독립 도구는 `Tools/`).

발행:
  /seer_map/markers   visualization_msgs/MarkerArray  (transient_local — 나중에 뜬 rviz 도 받는다)
      · 장애물 normalPosList        회색 점
      · 반사판 rssiPosList          청록 점
      · 스테이션 advancedPointList  주황 구 + 이름 텍스트
      · 경로 advancedCurveList      노랑 선
  TF map → base_link  (`--no-tf` 로 끌 수 있다)

⚠ TF 를 내는 이유 — rviz2 는 Fixed Frame 이 TF 에 없으면 아무것도 그리지 않는다.
   **실 브링업에서 map→base_link 를 내는 다른 노드가 있으면 반드시 `--no-tf` 로 끌 것.**
   두 발행자가 같은 변환을 내면 TF 가 튄다.

사용:
    python3 Tools/seer_viz/seer_map_viz.py --smap map/260709_test_2026-08-06_79e59a5a.smap
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import rclpy
from geometry_msgs.msg import Point, PoseStamped, TransformStamped
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import ColorRGBA
from tf2_ros import TransformBroadcaster
from visualization_msgs.msg import Marker, MarkerArray


def _color(r: float, g: float, b: float, a: float = 1.0) -> ColorRGBA:
    return ColorRGBA(r=r, g=g, b=b, a=a)


class SeerMapViz(Node):
    def __init__(self, smap_path: Path, frame: str, publish_tf: bool) -> None:
        super().__init__("seer_map_viz")
        self._frame = frame
        self._publish_tf = publish_tf

        latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self._mk_pub = self.create_publisher(MarkerArray, "/seer_map/markers", latched)

        self._tf = TransformBroadcaster(self) if publish_tf else None
        self.create_subscription(PoseStamped, "/robot_pose", self._on_pose, 10)

        doc = json.loads(smap_path.read_text(encoding="utf-8"))
        arr = self._build(doc)
        self._mk_pub.publish(arr)

        h = doc.get("header", {})
        self.get_logger().info(
            f"맵 '{h.get('mapName')}' v{h.get('version')} · 해상도 {h.get('resolution')} m · "
            f"장애물 {len(doc.get('normalPosList', []))}점 · 반사판 {len(doc.get('rssiPosList', []))}점 · "
            f"마커 {len(arr.markers)}개 발행 (frame '{frame}')")
        if publish_tf:
            self.get_logger().warn(
                "TF map→base_link 를 **이 노드가** 낸다. 실 브링업에서 같은 변환을 내는 "
                "노드가 있으면 --no-tf 로 끌 것.")

    # ------------------------------------------------------------- markers

    def _base(self, mid: int, ns: str, mtype: int, scale: float) -> Marker:
        m = Marker()
        m.header.frame_id = self._frame
        m.ns = ns
        m.id = mid
        m.type = mtype
        m.action = Marker.ADD
        m.scale.x = m.scale.y = m.scale.z = scale
        m.pose.orientation.w = 1.0
        return m

    def _points(self, mid: int, ns: str, pts, size: float, col: ColorRGBA) -> Marker:
        m = self._base(mid, ns, Marker.POINTS, size)
        m.color = col
        for p in pts:
            # ⚠ Seer JSON 은 값이 0 인 필드를 **생략**한다 — 반드시 기본값을 준다.
            m.points.append(Point(x=float(p.get("x", 0.0)), y=float(p.get("y", 0.0)), z=0.0))
        return m

    def _build(self, doc: dict) -> MarkerArray:
        arr = MarkerArray()
        mid = 0

        obs = doc.get("normalPosList", [])
        if obs:
            arr.markers.append(self._points(mid, "obstacles", obs, 0.04,
                                            _color(0.55, 0.55, 0.58)))
            mid += 1

        rssi = doc.get("rssiPosList", [])
        if rssi:
            arr.markers.append(self._points(mid, "reflectors", rssi, 0.12,
                                            _color(0.0, 0.85, 0.85)))
            mid += 1

        for st in doc.get("advancedPointList", []):
            pos = st.get("pos", {})
            m = self._base(mid, "stations", Marker.SPHERE, 0.35)
            m.color = _color(1.0, 0.55, 0.0)
            m.pose.position.x = float(pos.get("x", 0.0))
            m.pose.position.y = float(pos.get("y", 0.0))
            arr.markers.append(m)
            mid += 1

            t = self._base(mid, "station_labels", Marker.TEXT_VIEW_FACING, 0.45)
            t.color = _color(1.0, 1.0, 1.0)
            t.pose.position.x = float(pos.get("x", 0.0))
            t.pose.position.y = float(pos.get("y", 0.0)) + 0.5
            t.text = str(st.get("instanceName", ""))
            arr.markers.append(t)
            mid += 1

        for cv in doc.get("advancedCurveList", []):
            m = self._base(mid, "paths", Marker.LINE_STRIP, 0.08)
            m.color = _color(1.0, 0.9, 0.1)
            for key in ("startPos", "endPos"):
                pos = cv.get(key, {}).get("pos", {})
                m.points.append(Point(x=float(pos.get("x", 0.0)),
                                      y=float(pos.get("y", 0.0)), z=0.0))
            if len(m.points) == 2:
                arr.markers.append(m)
                mid += 1

        return arr

    # ---------------------------------------------------------------- pose

    def _on_pose(self, msg: PoseStamped) -> None:
        if self._tf is None:
            return
        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = self._frame
        t.child_frame_id = "base_link"
        t.transform.translation.x = msg.pose.position.x
        t.transform.translation.y = msg.pose.position.y
        t.transform.rotation = msg.pose.orientation
        self._tf.sendTransform(t)


def main() -> int:
    ap = argparse.ArgumentParser(description="Seer smap + /robot_pose 시각화")
    ap.add_argument("--smap", required=True, type=Path)
    ap.add_argument("--frame", default="map")
    ap.add_argument("--no-tf", action="store_true",
                    help="map→base_link TF 를 내지 않는다(다른 발행자가 있을 때)")
    a = ap.parse_args()

    if not a.smap.exists():
        print(f"smap 없음: {a.smap}", file=sys.stderr)
        return 2

    rclpy.init()
    node = SeerMapViz(a.smap, a.frame, not a.no_tf)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
