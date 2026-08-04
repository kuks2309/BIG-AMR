#!/usr/bin/env python3
"""드라이버 경유 백엔드 — `can_relay_node` 의 토픽·서비스만 쓴다.

설계 근거: `docs/adr/2026-08-04-amr-test-gui-swappable-backend.md`.

**판다를 열지 않는다** — `panda` import 0 · `can_send` 0 · USB 0. 두 프로세스가 각자 USB 를 열면
제어권과 heartbeat 가 겹치기 때문이다. 그래서 `판다 검색`·`USB 연결` capability 를 갖지 않는다
(드라이버가 소유). 그 둘은 CAN 프레임을 만들지 않으므로 실기 바이트 비교에 영향이 없다.

`direct` 백엔드와 달리 이쪽은 드라이버의 보호를 받는다 — 20 Hz 재송신 · `cmd_timeout_s` 워치독 ·
`joint_states` 신선도 게이트 · USB 락 · 정지 시 조향까지 처리(`stop_all`).
"""
from __future__ import annotations

import math
import threading
import time
from typing import Callable, Optional

import rclpy
from diagnostic_msgs.msg import DiagnosticArray
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64, Float64MultiArray
from std_srvs.srv import SetBool, Trigger

from .backend_base import (CAP_DRIVE, CAP_ENGAGE, CAP_HOME, CAP_MOTOR_TABLE,
                           CAP_STEER_ALL, CAP_STEER_AXIS, CAP_STOP, BackendBase)

MEAS_TTL_S = 1.0

# 구동 지령 재발행 주기(Hz). 드라이버의 `cmd_timeout_s`(기본 0.3 s) 안에 갱신이 없으면
# 백엔드가 속도를 0 으로 수렴시킨다 — 그것은 드라이버의 **의도된 안전장치**다
# (`backend.py` 규칙 2: 「지령원이 사라져도 드라이브가 마지막 값을 물고 가지 못하게」).
# 따라서 지령을 유지하려는 쪽이 계속 발행해야 한다. 드라이버 기본 `cmd_hz` 와 같은 20 Hz.
DRIVE_REPUBLISH_HZ = 20.0
# 정지(0) 를 반복 발행하는 시간. 워치독 주기보다 넉넉하면 한 프레임 유실에도 정지가 닿는다.
ZERO_HOLD_S = 0.5



class RelayClient(Node):
    """`can_relay_node` 와 말하는 ROS 노드. **Qt 를 import 하지 않는다.**

    화면 없이 시험할 수 있어야 하므로 UI 와 분리한다(회귀 `test/test_gui_node.py`).
    """

    def __init__(self):
        super().__init__("can_relay_gui")
        p = self.declare_parameters("", [
            ("driver_ns", "/can_relay_node"),
            ("meas_ttl_s", MEAS_TTL_S),
            ("seer_ip", "192.168.44.82"),
            # 원본은 절대경로가 코드에 박혀 있어 다른 PC 에서 Seer 가 통째로 죽었다.
            ("seer_gui_path", "/home/nvidia/T-Robot_seer_gui"),
            ("seer_enabled", True),
        ])
        g = {d.name: d.value for d in p}
        self.cfg = g
        ns = str(g["driver_ns"]).rstrip("/")

        self._lock = threading.Lock()
        self._meas: dict = {}
        self._diag_text = "진단 수신 전"
        self._diag_level = -1
        self._diag_at = 0.0
        self._diag_kv: dict = {}
        self._motor_state: dict = {}
        self._motor_state_at = 0.0

        self.pub_steer = self.create_publisher(Float64, f"{ns}/steer_deg", 10)
        self.pub_steer_axis = self.create_publisher(
            Float64MultiArray, f"{ns}/steer_axis_deg", 10)
        self.pub_drive = self.create_publisher(Float64, f"{ns}/drive_mmps", 10)

        # ⚠ 구동 지령은 **주기 재발행**한다. 단발 발행이면 드라이버 워치독(0.3 s)이 만료시켜
        #   조그가 **스스로 꺼진다** — 원본 `gui.py` 는 폴 루프가 매 주기 재송신하므로 유지되고,
        #   `--backend direct` 도 그렇다. 재발행이 없으면 같은 UI 가 백엔드에 따라 다르게 움직인다.
        #   2026-08-04 실기 실측: 단발 발행 시 실속도가 −1172 까지 올라갔다가 **0.75 초경 0 으로**
        #   떨어졌다(`Log/field_2026-08-04/wd_singleshot.csv`).
        #   ⚠ 다만 **유휴 상태에서까지 0 을 계속 내지는 않는다.** 그러면 이 GUI 가 토픽을
        #     영구 점유해 다른 지령자(`ros2 topic pub`·상위 노드)의 지령을 즉시 덮어쓴다
        #     (2026-08-04 실측: 외부에서 넣은 50 이 우리 0 에 지워져 드라이버에 도달조차 못 했다).
        #     정지 직후 `ZERO_HOLD_S` 동안만 0 을 반복해 **정지가 확실히 닿게** 한 뒤 조용해진다.
        #     조그 중 GUI 가 죽으면 재발행이 끊겨 드라이버 워치독이 0.3 s 안에 0 으로 만든다 —
        #     즉 「지령원이 죽으면 멈춘다」는 보호는 그대로 살아 있다.
        self._drive_mmps = 0.0
        self._zero_until = 0.0
        self.create_timer(1.0 / DRIVE_REPUBLISH_HZ, self._republish_drive)

        self.create_subscription(JointState, "/joint_states", self._on_joints, 10)
        self.create_subscription(DiagnosticArray, "/diagnostics", self._on_diag, 10)

        self.cli_engage = self.create_client(SetBool, f"{ns}/engage")
        self.cli_stop = self.create_client(Trigger, f"{ns}/stop")
        self.cli_home = self.create_client(Trigger, f"{ns}/home")
        # ⚠ `~/home_cancel` 클라이언트는 만들지 않는다 — 취소를 쓰지 않기로 했다
        #   (ADR 2026-08-04 §Decision ②). 드라이버 쪽 서비스와 회귀는 그대로 남아 있다.

        self._MotorStateArray = self._load_msgs()
        if self._MotorStateArray is not None:
            self.create_subscription(self._MotorStateArray, "/motor/low_state",
                                     self._on_low_state, 10)

    def _load_msgs(self):
        try:
            from trnav_msgs.msg import MotorStateArray
            return MotorStateArray
        except ImportError as exc:
            self.get_logger().warn(
                f"trnav_msgs 를 import 하지 못했다 ({exc}) — 모터 표는 각도만 채운다")
            return None

    # ── 수신 ──────────────────────────────────────────────────────────
    def _on_joints(self, msg: JointState):
        now = time.monotonic()
        with self._lock:
            for name, pos in zip(msg.name, msg.position):
                if not name.startswith("steer_"):
                    continue
                try:
                    node = int(name.split("_")[1])
                except (IndexError, ValueError):
                    continue
                self._meas[node] = (math.degrees(pos), now)

    def _on_diag(self, msg: DiagnosticArray):
        for st in msg.status:
            if not st.name.startswith("can_relay"):
                continue
            lvl = int.from_bytes(st.level, "big") if isinstance(st.level, bytes) \
                else int(st.level)
            with self._lock:
                self._diag_level = lvl
                self._diag_text = st.message
                self._diag_at = time.monotonic()
                self._diag_kv = {kv.key: kv.value for kv in st.values}

    def _on_low_state(self, msg):
        with self._lock:
            self._motor_state = {int(m.motor_id): m for m in msg.motors}
            self._motor_state_at = time.monotonic()

    # ── 조회 ──────────────────────────────────────────────────────────
    def meas_angle(self, node: int) -> Optional[float]:
        """**TTL 밖이면 None** — 파라미터를 매번 읽는다(스냅샷을 쓰면 param set 이 무시된다)."""
        ttl = float(self.get_parameter("meas_ttl_s").value)
        with self._lock:
            item = self._meas.get(int(node))
        if item is None:
            return None
        deg, at = item
        return deg if (time.monotonic() - at) <= ttl else None

    def diagnostics(self) -> tuple:
        with self._lock:
            fresh = (time.monotonic() - self._diag_at) <= 3.0 if self._diag_at else False
            return self._diag_level, self._diag_text, fresh, dict(self._diag_kv)

    def motor_states(self) -> dict:
        with self._lock:
            fresh = (time.monotonic() - self._motor_state_at) <= 1.0
            return dict(self._motor_state) if fresh else {}

    def has_low_state(self) -> bool:
        return self._MotorStateArray is not None

    # ── 송신 ──────────────────────────────────────────────────────────
    def send_steer(self, deg: float):
        self.pub_steer.publish(Float64(data=float(deg)))

    def send_steer_axis(self, node: int, deg: float):
        self.pub_steer_axis.publish(Float64MultiArray(data=[float(node), float(deg)]))

    def send_drive(self, mmps: float):
        """구동 지령. 즉시 1회 발행하고 **재발행 타이머가 값을 유지**한다."""
        mmps = float(mmps)
        with self._lock:
            self._drive_mmps = mmps
            if mmps == 0.0:
                self._zero_until = time.monotonic() + ZERO_HOLD_S
        self.pub_drive.publish(Float64(data=mmps))

    def _republish_drive(self):
        """지령을 유지한다. 비영이면 계속, 0 이면 `ZERO_HOLD_S` 동안만, 그 뒤에는 조용히."""
        with self._lock:
            mmps = self._drive_mmps
            if mmps == 0.0 and time.monotonic() >= self._zero_until:
                return
        self.pub_drive.publish(Float64(data=float(mmps)))

    def call(self, client, request, timeout_s: float = 5.0, discovery_s: float = 5.0):
        """서비스 1회 호출. 반환 `(성공, 메시지)`. **블로킹** — 작업 스레드에서 부른다.

        ⚠ `discovery_s` 가 1 초였을 때 드라이버가 떠 있는데도 「서비스 없음」이 났다
        (2026-08-03 실기 dry-run). 첫 호출이 기동 직후에 몰리므로 여유를 둔다.
        """
        if not client.wait_for_service(timeout_sec=discovery_s):
            return False, (f"서비스 없음: {client.srv_name} "
                           f"({discovery_s:.0f}s 대기 — 드라이버가 떠 있습니까?)")
        fut = client.call_async(request)
        t0 = time.monotonic()
        while not fut.done():
            if time.monotonic() - t0 > timeout_s:
                return False, f"응답 없음({timeout_s:.0f}s): {client.srv_name}"
            time.sleep(0.02)
        res = fut.result()
        return bool(getattr(res, "success", False)), str(getattr(res, "message", ""))


class Ros2Backend(BackendBase):
    """`RelayClient` 를 UI 계약에 맞춰 감싼다."""

    name = "ros2"
    capabilities = frozenset({CAP_ENGAGE, CAP_STOP, CAP_HOME, CAP_STEER_AXIS,
                              CAP_STEER_ALL, CAP_DRIVE, CAP_MOTOR_TABLE})

    def __init__(self, log: Optional[Callable[[str], None]] = None, args=None):
        self._log = log or (lambda _m: None)
        if not rclpy.ok():
            rclpy.init(args=args)
        self.node = RelayClient()
        self._exec = MultiThreadedExecutor()
        self._exec.add_node(self.node)
        self._spin = None
        self._released = False

    @property
    def cfg(self) -> dict:
        """Seer 설정 등 UI 가 읽는 파라미터(백엔드 무관 부분)."""
        return self.node.cfg

    def why_not(self, cap: str) -> str:
        return "드라이버(can_relay_node)가 소유합니다 — GUI 는 판다를 열지 않습니다"

    # ── 수명주기 ──────────────────────────────────────────────────────
    def start(self) -> None:
        self._spin = threading.Thread(target=self._exec.spin, daemon=True,
                                      name="ros-spin")
        self._spin.start()

    def shutdown(self, reason: str = "") -> None:
        if self._released:
            return
        self._released = True
        self._log(f"해제 시작 — {reason}")
        try:
            self.node.send_drive(0.0)
            ok, why = self.node.call(self.node.cli_stop, Trigger.Request(), timeout_s=2.0)
            self._log(f"정지 — {why}" if ok else f"정지 실패 — {why}")
            self.node.call(self.node.cli_engage, SetBool.Request(data=False),
                           timeout_s=3.0)
        except Exception as exc:
            self._log(f"⚠ 종료 중 예외: {type(exc).__name__}: {exc}")
        try:
            self._exec.shutdown()
            self.node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass
        self._log("해제 완료 — 정지·제어권 반환 요청")

    # ── 조회 ──────────────────────────────────────────────────────────
    def meas_angle(self, node: int) -> Optional[float]:
        return self.node.meas_angle(node)

    def motor_rows(self) -> dict:
        rows = {}
        states = self.node.motor_states()
        for node, m in states.items():
            rows[node] = (self.node.meas_angle(node), float(m.fb_vel),
                          float(m.amps) / 100.0)
        if not rows:               # low_state 미수신 — 각도만이라도 채운다
            for node in (3, 4):
                rows[node] = (self.node.meas_angle(node), None, None)
        return rows

    def status(self) -> tuple:
        level, message, fresh, kv = self.node.diagnostics()
        if not fresh:
            return ("⚠ 진단 끊김 — 드라이버 응답 없음 (조작 결과를 신뢰하지 마세요)",
                    False, False)
        engaged = str(kv.get("engaged", "")).lower() == "true"
        text = (f"can_relay: {message} · 제어권 {kv.get('engaged', '?')} · "
                f"tx {kv.get('tx', '?')}/rx {kv.get('rx', '?')} · "
                f"거부 {kv.get('rejected_commands', '?')} · "
                f"워치독 {kv.get('watchdog_trips', '?')}")
        return text, level in (0, 1), engaged

    # ── 조작: 블로킹 ──────────────────────────────────────────────────
    def set_engaged(self, on: bool) -> tuple:
        return self.node.call(self.node.cli_engage, SetBool.Request(data=bool(on)))

    def stop(self) -> tuple:
        """정지. **유지값을 먼저 0 으로 내린 뒤** 서비스를 부른다.

        ⚠ 순서가 중요하다. `send_drive(0.0)` 을 먼저 하지 않으면 재발행 타이머가
        정지 직후 마지막 비영 지령을 다시 내보내 **정지를 무효화한다** —
        `test_drive_and_stop_through_ros` 가 이 순서를 고정한다(2026-08-04 실측 회귀).
        """
        self.node.send_drive(0.0)
        return self.node.call(self.node.cli_stop, Trigger.Request())

    def home(self) -> tuple:
        return self.node.call(self.node.cli_home, Trigger.Request(), timeout_s=200.0)

    # ── 조작: 즉시 반환 ───────────────────────────────────────────────
    def steer_axis(self, node: int, deg: float) -> None:
        self.node.send_steer_axis(node, deg)

    def steer_all(self, deg: float) -> None:
        self.node.send_steer(deg)

    def drive(self, mmps: float) -> None:
        self.node.send_drive(mmps)
