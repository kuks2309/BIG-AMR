# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""카메라 관리자 상주 노드 — 카메라별 프레임 생존 감시 + 자동 복구.

카메라별 `<cam>/image_raw/compressed` 도착 시각만 기록한다(페이로드 미사용 —
MJPEG 패스스루 원칙대로 어디서도 디코드하지 않는다). 1Hz 판정 틱이
`CameraMonitor` 상태기계를 돌리고, 재시작 지시는 큐를 통해 전용 스레드가
실행한다 — systemctl subprocess 를 ROS 콜백 안에서 부르지 않기 위해서다
(ros2-coding.md §2 콜백 내 blocking 금지).

상태는 `/diagnostics` (diagnostic_msgs/DiagnosticArray) 로 1Hz 발행한다.
자동 재시작은 `~/set_auto` (std_srvs/SetBool) 로 켜고 끈다(camctl auto).
"""
from __future__ import annotations

import os
import queue
import threading
import time

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from rclpy.node import Node
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
    qos_profile_sensor_data,
)
from sensor_msgs.msg import CompressedImage
from std_srvs.srv import SetBool

from camera_manager.monitor import (
    STATE_NO_DEVICE,
    STATE_OK,
    STATE_RESTARTING,
    STATE_STALL,
    STATE_STOPPED,
    STATE_SUPPRESSED,
    CameraInputs,
    CameraMonitor,
    MonitorConfig,
)
from camera_manager.roster import find_shared_config, load_roster
from camera_manager.systemd_ctl import SystemdControl

# 상태 → diagnostics 레벨. 억제(suppressed)는 의도된 상태라 OK 로 둔다.
_LEVEL_BY_STATE = {
    STATE_OK: DiagnosticStatus.OK,
    STATE_SUPPRESSED: DiagnosticStatus.OK,
    STATE_RESTARTING: DiagnosticStatus.WARN,
    STATE_STOPPED: DiagnosticStatus.WARN,
    STATE_STALL: DiagnosticStatus.ERROR,
    STATE_NO_DEVICE: DiagnosticStatus.ERROR,
}


class CameraManagerNode(Node):
    """로스터의 전 카메라를 감시하는 단일 노드."""

    def __init__(self):
        super().__init__("camera_manager")
        config_file = self.declare_parameter("config_file", "").value
        stall_sec = self.declare_parameter("stall_sec", 10.0).value
        cooldown = self.declare_parameter("restart_cooldown_sec", 30.0).value
        grace = self.declare_parameter("startup_grace_sec", 20.0).value
        self._auto_enabled = bool(self.declare_parameter("auto_restart", True).value)
        tick_sec = self.declare_parameter("tick_sec", 1.0).value
        self._unit_poll_sec = self.declare_parameter("unit_poll_sec", 2.0).value

        path = config_file or find_shared_config()
        if not path:
            raise RuntimeError(
                "공용 카메라 설정을 찾지 못했다 — config_file 파라미터 또는 "
                "CAMERA_CONFIG 환경변수로 config/camera/camera_common.yaml 을 지정")
        self._cameras = load_roster(path)
        self.get_logger().info(
            f"로스터 {len(self._cameras)}대: {', '.join(c.name for c in self._cameras)}"
            f" (config: {path})")

        monitor_config = MonitorConfig(
            stall_sec=stall_sec, restart_cooldown_sec=cooldown, startup_grace_sec=grace)
        now = time.monotonic()
        self._monitors = {
            cam.name: CameraMonitor(cam.name, monitor_config, now)
            for cam in self._cameras
        }
        self._last_rx: dict[str, float] = {}
        self._unit_states: dict[str, bool | None] = {}
        self._systemd = SystemdControl()
        self._restart_queue: "queue.Queue[str]" = queue.Queue()
        self._stop_event = threading.Event()

        # 프레임 구독 — 도착 시각만 기록. 센서 스트림 관례(best-effort) 그대로.
        self._subs = [
            self.create_subscription(
                CompressedImage, f"{cam.name}/image_raw/compressed",
                self._make_frame_callback(cam.name), qos_profile_sensor_data)
            for cam in self._cameras
        ]
        # /diagnostics 는 이벤트성 상태 보고 — reliable·keep-last 10 을 명시.
        self._diag_pub = self.create_publisher(
            DiagnosticArray, "/diagnostics",
            QoSProfile(
                history=QoSHistoryPolicy.KEEP_LAST, depth=10,
                reliability=QoSReliabilityPolicy.RELIABLE,
                durability=QoSDurabilityPolicy.VOLATILE))
        self._auto_srv = self.create_service(SetBool, "~/set_auto", self._on_set_auto)
        self._tick_timer = self.create_timer(tick_sec, self._on_tick)
        self._worker = threading.Thread(
            target=self._systemd_worker, name="systemd_worker", daemon=True)
        self._worker.start()

    def _make_frame_callback(self, cam_name: str):
        """구독 콜백 생성 — 루프 변수 캡처 함정을 피하기 위한 팩토리."""

        def _on_frame(_msg) -> None:
            self._last_rx[cam_name] = time.monotonic()

        return _on_frame

    def _on_tick(self) -> None:
        """1틱: 입력 조립 → 판정 → 재시작 위임 → diagnostics 발행.

        blocking 호출 없음 — 유닛 상태는 워커의 캐시를 읽고, 재시작은 큐로
        넘긴다. 장치 실재는 stat 1회(by-id 심링크)로 충분히 짧다.
        """
        now = time.monotonic()
        decisions: dict[str, tuple] = {}
        for cam in self._cameras:
            last = self._last_rx.get(cam.name)
            age = None if last is None else now - last
            inputs = CameraInputs(
                frame_age=age,
                unit_active=self._unit_states.get(cam.name),
                device_present=os.path.exists(cam.device),
                depth_active=self.count_publishers(f"{cam.name}/depth/image_raw") > 0,
            )
            decision = self._monitors[cam.name].evaluate(inputs, now, self._auto_enabled)
            if decision.restart:
                self.get_logger().warn(f"[{cam.name}] {decision.reason}")
                self._restart_queue.put(cam.name)
            decisions[cam.name] = (decision, age)
        self._publish_diagnostics(decisions)

    def _on_set_auto(self, request, response):
        """`camctl auto on|off` — 자동 재시작 토글."""
        self._auto_enabled = bool(request.data)
        response.success = True
        response.message = f"자동 재시작 {'켜짐' if self._auto_enabled else '꺼짐'}"
        self.get_logger().info(response.message)
        return response

    def _systemd_worker(self) -> None:
        """전용 스레드 — subprocess(systemctl) 는 전부 여기서만 실행된다.

        재시작 큐를 소진하고, 유닛 활성 상태 캐시를 주기 갱신한다. 큐 get 의
        타임아웃이 폴링 주기의 하한을 겸한다.
        """
        next_poll = 0.0
        while not self._stop_event.is_set():
            now = time.monotonic()
            if now >= next_poll:
                for cam in self._cameras:
                    self._unit_states[cam.name] = self._systemd.is_active(cam.name)
                next_poll = now + self._unit_poll_sec
            try:
                cam_name = self._restart_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            ok, message = self._systemd.control("restart", cam_name)
            if ok:
                self.get_logger().info(f"[{cam_name}] {message}")
            else:
                self.get_logger().error(f"[{cam_name}] {message}")

    def _publish_diagnostics(self, decisions: dict[str, tuple]) -> None:
        """카메라별 Decision → DiagnosticArray 1건."""
        array = DiagnosticArray()
        array.header.stamp = self.get_clock().now().to_msg()
        for name, (decision, age) in decisions.items():
            status = DiagnosticStatus()
            status.level = _LEVEL_BY_STATE.get(decision.state, DiagnosticStatus.WARN)
            status.name = f"camera_manager: {name}"
            status.hardware_id = name
            status.message = decision.state + (f" — {decision.reason}" if decision.reason else "")
            status.values = [
                KeyValue(key="frame_age_sec", value="-" if age is None else f"{age:.1f}"),
                KeyValue(key="restarts", value=str(self._monitors[name].consecutive_restarts)),
                KeyValue(key="auto", value=str(self._auto_enabled)),
            ]
            array.status.append(status)
        self._diag_pub.publish(array)

    def shutdown(self) -> None:
        """워커 스레드 정리 — main 의 finally 에서 호출."""
        self._stop_event.set()
        if self._worker.is_alive():
            self._worker.join(timeout=2.0)


def main(argv=None):
    rclpy.init(args=argv)
    node = CameraManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
