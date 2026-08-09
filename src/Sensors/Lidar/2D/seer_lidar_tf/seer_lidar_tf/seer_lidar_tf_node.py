#!/usr/bin/env python3
"""seer_lidar_tf_node.

SEER SRC 컨트롤러의 Robokit TCP API(Robot Status API, port 19204, API 1009 =
robot_status_laser_req)로 각 2D LiDAR 의 장착 pose(install_info: x/y/yaw)를 읽어
`parent_frame -> <lidar>_frame` 정적 TF 로 발행한다.

install_info 는 2D(x/y/yaw)만 제공하므로 z/roll/pitch = 0 (z 는 파라미터로 override 가능).
장착 캘리브는 거의 불변이므로 기본은 1회 읽어 latch(StaticTransformBroadcaster).
poll_period > 0 이면 주기적으로 재조회하여 갱신한다.

프로토콜 구현은 여기 있지 않다 — `src/Comm/TCP_IP/seer_api` 가 저장소에서 Seer 와 TCP 로
말하는 유일한 지점이다(ADR docs/adr/2026-08-07-seer-api-tcp-hal.md).
출처/프로토콜: References/Seer-Driver/robokit_tcp_api_laser.md
"""
import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros import StaticTransformBroadcaster

from seer_api import SeerApi
from seer_api.api import API_LASER


def _yaw_to_quat(yaw_rad):
    """roll=pitch=0 인 yaw-only 쿼터니언 (x, y, z, w)."""
    return (0.0, 0.0, math.sin(yaw_rad * 0.5), math.cos(yaw_rad * 0.5))


class SeerLidarTf(Node):
    def __init__(self):
        super().__init__("seer_lidar_tf")

        self.seer_ip = self.declare_parameter("seer_ip", "192.168.44.82").value
        self.seer_port = int(self.declare_parameter("seer_port", 19204).value)
        self.parent_frame = self.declare_parameter("parent_frame", "base_footprint").value
        self.front_frame = self.declare_parameter("front_frame", "scan_front").value
        self.rear_frame = self.declare_parameter("rear_frame", "scan_rear").value
        # install_info 미제공 축 override (실측 장착 높이 등)
        self.z_front = float(self.declare_parameter("z_front", 0.0).value)
        self.z_rear = float(self.declare_parameter("z_rear", 0.0).value)
        self.connect_timeout = float(self.declare_parameter("connect_timeout", 3.0).value)
        self.retry_period = float(self.declare_parameter("retry_period", 5.0).value)
        # 0.0 = 1회만 읽고 latch. >0 = 주기 재조회(초).
        self.poll_period = float(self.declare_parameter("poll_period", 0.0).value)
        # one-shot 모드: 값이 있으면 Seer 조회 → merger calibration_result.yaml 로 써넣고 종료
        # (TF 라이브 발행 안 함 = merger 가 런타임 TF 소유, 부모 충돌 없음). "가지고와서 복사".
        self.calibration_out = str(self.declare_parameter("calibration_out", "").value)

        self.done = False  # main() 에서 one-shot 종료 판정

        # 조회 전용(19204). 지령 포트를 쓸 일이 없으므로 allow_guarded 기본값(False) 유지 —
        # seer_port 에 지령 포트를 넣으면 seer_api 게이트가 막는다(의도된 동작).
        self._client = SeerApi(self.seer_ip, timeout=self.connect_timeout)

        if self.calibration_out:
            self.get_logger().info(
                f"[write 모드] {self.seer_ip}:{self.seer_port} 조회 → {self.calibration_out} 기록 후 종료"
            )
            self._write_once()
            return

        # ---- 라이브 TF 발행 모드 (merger 미사용 시) ----
        self._broadcaster = StaticTransformBroadcaster(self)
        self._published = False
        period = self.poll_period if self.poll_period > 0.0 else self.retry_period
        self._timer = self.create_timer(period, self._tick)
        self.get_logger().info(
            f"[publish 모드] {self.seer_ip}:{self.seer_port} API {API_LASER} "
            f"-> {self.parent_frame}->({self.front_frame},{self.rear_frame}), "
            f"{'1회 latch' if self.poll_period <= 0 else f'{self.poll_period}s 폴링'}"
        )
        self._tick()  # 시작 즉시 1회 시도

    def _write_once(self):
        """Seer 조회 → merger calibration YAML 기록 → done 플래그 (one-shot)."""
        try:
            lasers = self._query_lasers()
        except Exception as exc:
            self.get_logger().error(f"Seer 조회 실패({exc}) — 기록 안 함")
            self.done = True
            return
        poses = {}
        for laser in lasers:
            dev = laser.get("device_info", {}).get("device_name")
            ii = laser.get("install_info")
            child, _ = self._frame_for(dev)
            if child and ii:
                poses[child] = (float(ii["x"]), float(ii["y"]), float(ii["yaw"]))
                self.get_logger().info(
                    f"  {dev}: x={ii['x']:.4f} y={ii['y']:.4f} yaw={float(ii['yaw']):.3f}deg -> {child}"
                )
        if self.front_frame not in poses or self.rear_frame not in poses:
            self.get_logger().error(f"front/rear pose 부족 {list(poses)} — 기록 안 함")
            self.done = True
            return
        self._write_calibration_yaml(poses)
        self.done = True

    def _write_calibration_yaml(self, poses):
        fx, fy, fyaw = poses[self.front_frame]
        rx, ry, ryaw = poses[self.rear_frame]
        fyaw_r, ryaw_r = math.radians(fyaw), math.radians(ryaw)
        text = (
            "# SEER install_info -> merger calibration (seer_lidar_tf write 모드 생성)\n"
            f"# 출처: SEER {self.seer_ip}:{self.seer_port} API {API_LASER}. "
            "install_info 는 2D(x/y/yaw)만 제공 -> z/roll=0, icp=0.\n"
            "calibration:\n"
            "  reference_frame: merged_lidar\n"
            f"  reference_sensor: /{self.front_frame}\n"
            f"  calibrated_sensor: /{self.rear_frame}\n"
            "  icp_correction: {dx: 0.0, dy: 0.0, dyaw_rad: 0.0, dyaw_deg: 0.0}\n"
            "  merged_lidar_to_scan_front:\n"
            f"    tx: {fx}\n    ty: {fy}\n    yaw_rad: {fyaw_r}\n    yaw_deg: {fyaw}\n    flipped: true\n"
            "  merged_lidar_to_scan_rear_original:\n"
            f"    tx: {rx}\n    ty: {ry}\n    yaw_rad: {ryaw_r}\n    yaw_deg: {ryaw}\n    flipped: true\n"
            "  merged_lidar_to_scan_rear_corrected:\n"
            f"    tx: {rx}\n    ty: {ry}\n    yaw_rad: {ryaw_r}\n    yaw_deg: {ryaw}\n    flipped: true\n"
        )
        with open(self.calibration_out, "w", encoding="utf-8") as f:
            f.write(text)
        self.get_logger().info(f"calibration 기록 완료: {self.calibration_out}")

    def _tick(self):
        try:
            lasers = self._query_lasers()
        except Exception as exc:  # 연결/파싱 실패 → 재시도
            self.get_logger().warning(f"Seer 조회 실패({exc}) — {self.retry_period}s 후 재시도")
            return

        transforms = self._build_transforms(lasers)
        if not transforms:
            self.get_logger().warning("install_info 를 가진 laser 가 없음 — 재시도")
            return

        self._broadcaster.sendTransform(transforms)
        self._published = True
        names = ", ".join(t.child_frame_id for t in transforms)
        self.get_logger().info(f"TF 발행 완료: {self.parent_frame} -> [{names}]")

        if self.poll_period <= 0.0:
            self._timer.cancel()  # latch 후 종료(static 은 계속 유지됨)

    def _query_lasers(self):
        """레이저 목록 조회. 응답 편호·seq 대조와 부분 수신 처리는 seer_api 가 한다."""
        return self._client.call(self.seer_port, API_LASER).get("lasers", [])

    def _frame_for(self, device_name):
        name = (device_name or "").lower()
        if "front" in name:
            return self.front_frame, self.z_front
        if "rear" in name:
            return self.rear_frame, self.z_rear
        return None, None

    def _build_transforms(self, lasers):
        now = self.get_clock().now().to_msg()
        out = []
        for laser in lasers:
            dev = laser.get("device_info", {}).get("device_name")
            ii = laser.get("install_info")
            if not ii:
                continue
            child, z = self._frame_for(dev)
            if child is None:
                self.get_logger().warning(f"매핑 없는 device '{dev}' — 건너뜀")
                continue
            qx, qy, qz, qw = _yaw_to_quat(math.radians(float(ii["yaw"])))
            t = TransformStamped()
            t.header.stamp = now
            t.header.frame_id = self.parent_frame
            t.child_frame_id = child
            t.transform.translation.x = float(ii["x"])
            t.transform.translation.y = float(ii["y"])
            t.transform.translation.z = float(z)
            t.transform.rotation.x = qx
            t.transform.rotation.y = qy
            t.transform.rotation.z = qz
            t.transform.rotation.w = qw
            out.append(t)
            self.get_logger().info(
                f"  {dev}: x={ii['x']:.4f} y={ii['y']:.4f} yaw={float(ii['yaw']):.3f}deg -> {child}"
            )
        return out


def main(args=None):
    rclpy.init(args=args)
    node = SeerLidarTf()
    try:
        if node.done:
            pass  # write 모드: 이미 완료 → spin 없이 종료
        else:
            rclpy.spin(node)  # publish 모드: latch TF 유지
    except KeyboardInterrupt:
        pass
    finally:
        node._client.close()  # 소켓을 남기지 않는다 (19204 는 동시연결 10 — 누수는 한도를 먹는다)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
