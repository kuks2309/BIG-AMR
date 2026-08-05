#!/usr/bin/env python3
"""can_relay 드라이버 노드 — 판다 릴레이 경유 모터 구동 ROS2 진입점.

## 이 노드가 하지 않는 것 (의도적)

- **기동만으로 제어권을 잡지 않는다.** `~/engage` 서비스를 명시 호출해야 Seer 에게서
  버스를 가져온다. launch 만으로 로봇이 움직일 수 있는 상태를 만들지 않는다.
- **역기구학도 단위환산도 하지 않는다.** 이 노드는 모터 계층이다 — 기구학은 액션 서버가,
  SI→raw 환산은 `amr_motor_cmd_translator` 가 소유한다(`MotorCmd.msg`: "Units are raw
  device units — NOT SI"). 계층을 지키면 중복 역기구학 문제 자체가 생기지 않는다.
- **메시지를 자체 정의하지 않는다.** `trnav_msgs` 를 빌리며, 없으면 조용히 대체하지 않고
  저수준 경로를 **열지 않는다**.
- **자동으로 호밍하지 않는다.** 물리 스윙 100°+ 이므로 `~/home` 명시 호출 전용이다.
  진행 중 취소는 `~/home_cancel` 로 한다 — 펌웨어 시퀀서가 취소 프레임을 낸다
  (`safety_seer_gate.h:312-316`).

## 인터페이스

| 방향 | 이름 | 타입 | 비고 |
|---|---|---|---|
| 구독 | `/motor/low_cmd` | `trnav_msgs/MotorCmdArray` | **raw** 지령. 환산·기구학 없음 |
| 발행 | `/motor/low_state` | `trnav_msgs/MotorStateArray` | raw 피드백 → 상류 translator |
| 구독 | `estop` | `std_msgs/Bool` | 소프트 래치. 하드웨어 E-STOP 을 대체하지 않는다 |
| 구독 | `~/steer_deg` | `std_msgs/Float64` | 잭업 시험용 직접 조향각 |
| 구독 | `~/drive_mmps` | `std_msgs/Float64` | 잭업 시험용 직접 구동속도 |
| 발행 | `joint_states` | `sensor_msgs/JointState` | 조향 실측각(믿을 수 있는 축만) |
| 발행 | `diagnostics` | `diagnostic_msgs/DiagnosticArray` | 제어권·심박·워치독·abort |
| 서비스 | `~/engage` | `std_srvs/SetBool` | 제어권 획득/반환 |
| 서비스 | `~/stop` | `std_srvs/Trigger` | 즉시 정지 |
| 서비스 | `~/home` | `std_srvs/Trigger` | 조향 호밍(⚠ 물리 스윙) |
"""
from __future__ import annotations

import math

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, HistoryPolicy, QoSProfile,
                       ReliabilityPolicy)
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, Float64, Float64MultiArray
from std_srvs.srv import SetBool, Trigger

from . import safety as S
from .backend import RelayBackend, RelayConfig
from .link import MOTOR_BUS, MockLink, PandaLink

# E-stop 은 래치 상태다 — 늦게 붙은 구독자도 현재 값을 받아야 한다.
LATCHED_QOS = QoSProfile(depth=1,
                         history=HistoryPolicy.KEEP_LAST,
                         reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)


class CanRelayNode(Node):

    def __init__(self):
        super().__init__("can_relay_node")

        p = self.declare_parameters("", [
            ("link", "panda"),                  # panda | mock
            ("panda_serial", ""),
            ("bus", MOTOR_BUS),
            ("drive_nodes", [1, 2]),
            ("steer_nodes", [3, 4]),
            ("steer_limit_deg", S.STEER_LIMIT_DEG),
            # 벤치 직접 지령(`~/steer_deg`·`~/steer_axis_deg`) 전용 상한. 체인 상한과
            # 분리한다 — 사람이 손으로 넣는 경로는 넓히지 않는다(2026-08-05).
            ("steer_limit_bench_deg", S.STEER_LIMIT_DEG),
            ("vel_max_units", S.VEL_MAX_UNITS),
            ("cmd_timeout_s", 0.3),
            ("cmd_hz", 20.0),
            ("poll_hz", 5.0),
            ("settle_tol_deg", 3.0),
            ("allow_bringup", False),
            ("diag_hz", 1.0),
            ("state_hz", 10.0),
            ("low_state_hz", 50.0),  # /motor/low_state 발행 주기
            ("health_hz", 1.0),     # per-bus CAN 에러 상태(0xc3) 폴링
            ("homing_speed", 0),    # firmware 경로 전용. 0=펌웨어 기본(2500)

            # ── 장비별 캘리브레이션 (config/machine/<기체>.yaml) ──────────
            # 여기 기본값은 **안전한 쪽**이다: 호밍 비활성 + 홈 0 + 호밍 전 조향 차단.
            # 캘리브레이션 파일을 안 넣으면 아무것도 움직이지 않는다.
            ("machine_name", "(미지정)"),
            ("steer_counts_per_deg", S.COUNTS_PER_DEG),
            ("drive_units_per_mmps", S.VEL_PER_MMPS),
            ("drive_max_units", S.VEL_MAX_UNITS),
            ("homing_method", "firmware"),      # "firmware" | "35"(2026-08-01 기각)
            ("homing_enabled", False),
            ("steer_home_offset", [], ParameterDescriptor(dynamic_typing=True)),
            # 홈은 코드 기본값을 두지 않는다 — 빈 배열이 곧 "미설정"이고 기동이 거부된다.
            # 정본은 config/machine/<기체>.yaml (2026-08-02 사용자 지시).
            # ⚠ `dynamic_typing` 이 필요하다 — 빈 기본값을 rclpy 가 BYTE_ARRAY 로 추론해
            #   YAML 의 정수 배열 로드를 거부한다(실기 기동 실패로 확인, 2026-08-02).
            #   descriptor.type 지정만으로는 안 된다(Humble 이 기본값 타입으로 덮어씀).
            ("steer_home_counts", [], ParameterDescriptor(dynamic_typing=True)),
            ("home_reach_tol_counts", 50),
            ("home_profile_vel", 2500),
            ("home_search_range", [-10_000_000, 10_000_000]),
            ("require_homed_for_steer", True),
        ])
        g = {d.name: d.value for d in p}
        self._g = g

        steer_nodes = [int(n) for n in g["steer_nodes"]]
        homes = [int(c) for c in g["steer_home_counts"]]
        if not homes:
            raise ValueError(
                "steer_home_counts 가 설정되지 않았다 — 조향 홈은 기체마다 다르고 "
                "잘못되면 전체 코드가 오판한다. 코드에 기본값을 두지 않으므로 "
                "캘리브레이션 YAML(config/machine/<기체>.yaml)을 반드시 실어야 한다. "
                "launch 인자 machine_file 을 확인할 것")
        offsets = [int(c) for c in g["steer_home_offset"]] or homes
        for name, arr in (("steer_home_counts", homes), ("steer_home_offset", offsets)):
            if len(arr) != len(steer_nodes):
                raise ValueError(
                    f"{name}({len(arr)}) 와 steer_nodes({len(steer_nodes)}) 길이가 다르다 "
                    f"— 조향 원점을 잘못 배정하면 물리 손상으로 이어진다")
        method = str(g["homing_method"])
        if method not in ("35", "firmware"):
            raise ValueError(f"homing_method 는 '35' 또는 'firmware' 여야 한다 (받은 값: {method})")
        rng = [int(v) for v in g["home_search_range"]]
        if len(rng) != 2 or rng[0] >= rng[1]:
            raise ValueError(f"home_search_range 는 [최소, 최대] 여야 한다 (받은 값: {rng})")

        cfg = RelayConfig(
            drive_nodes=tuple(int(n) for n in g["drive_nodes"]),
            steer_nodes=tuple(steer_nodes),
            bus=int(g["bus"]),
            cmd_hz=float(g["cmd_hz"]),
            poll_hz=float(g["poll_hz"]),
            cmd_timeout_s=float(g["cmd_timeout_s"]),
            steer_limit_deg=float(g["steer_limit_deg"]),
            steer_limit_bench_deg=float(g["steer_limit_bench_deg"]),
            # 캘리브레이션의 drive_max_units 가 있으면 그것이 이긴다(기체 고유값이므로).
            vel_max_units=int(g["drive_max_units"] or g["vel_max_units"]),
            steer_counts_per_deg=float(g["steer_counts_per_deg"]),
            drive_units_per_mmps=float(g["drive_units_per_mmps"]),
            steer_home=dict(zip(steer_nodes, homes)),
            settle_tol_deg=float(g["settle_tol_deg"]),
            allow_bringup=bool(g["allow_bringup"]),
            health_hz=float(g["health_hz"]),
            homing_method=method,
            homing_enabled=bool(g["homing_enabled"]),
            steer_home_offset=dict(zip(steer_nodes, offsets)),
            home_reach_tol_counts=int(g["home_reach_tol_counts"]),
            home_profile_vel=int(g["home_profile_vel"]),
            home_search_range=(rng[0], rng[1]),
            require_homed_for_steer=bool(g["require_homed_for_steer"]),
        )
        self._cfg = cfg
        self.get_logger().info(
            f"기체 '{g['machine_name']}' · 호밍 {method} "
            f"(활성={g['homing_enabled']}) · 조향 한계 체인 ±{g['steer_limit_deg']}° "
            f"/ 벤치 ±{g['steer_limit_bench_deg']}°")
        if not g["homing_enabled"]:
            self.get_logger().warn(
                "호밍 비활성 — steer_home_offset 이 실측 확정되지 않았습니다. "
                "캘리브레이션 YAML 을 확인하세요(config/machine/<기체>.yaml)")

        logger = self.get_logger().info
        if g["link"] == "mock":
            self.link = MockLink()
            logger("링크 = mock (하드웨어 무접속)")
        else:
            serial = g["panda_serial"] or None
            self.link = PandaLink(serial=serial, log=logger)
        self.backend = RelayBackend(self.link, cfg, log=logger)

        # 모터 계층 메시지. 없으면 저수준 경로를 열지 않는다(조용히 대체하지 않는다).
        self._MotorCmdArray, self._MotorStateArray, self._MotorState = self._load_msgs()

        # ── 모터 계층 계약 (상류 TR_Nav 와 동일) ──────────────────────────
        # QoS 는 체인 전 구간이 RELIABLE + KeepLast(10) + VOLATILE 다.
        self.sub_low_cmd = self.pub_low_state = None
        if self._MotorCmdArray is not None:
            self.sub_low_cmd = self.create_subscription(
                self._MotorCmdArray, "/motor/low_cmd", self._on_low_cmd, 10)
            self.pub_low_state = self.create_publisher(
                self._MotorStateArray, "/motor/low_state", 10)
            self.create_timer(1.0 / float(g["low_state_hz"]), self._on_low_state_timer)

        # ── 콜백 그룹 분리 (정지 계열이 호밍에 묶이지 않게) ──────────────────
        # `~/home` 콜백은 terminal 이나 timeout(기본 180 s)까지 반환하지 않는다.
        # 기본 그룹은 상호배타라, 같은 그룹에 있으면 그동안 `~/home_cancel`·`~/stop`·
        # `estop` 이 **하나도 소비되지 않는다** — 문서화된 유일한 취소 수단이 정작
        # 호밍 중에만 죽는다(2026-08-03 리뷰 H1). 회귀: `test/test_node_concurrency.py`.
        #
        # ⚠ 그룹만 나눠서는 부족하다 — 단일 스레드 실행기에서는 여전히 순차 처리다.
        #   `main()` 이 MultiThreadedExecutor 를 쓰는 것과 **둘이 한 쌍**이다.
        self._cbg_home = MutuallyExclusiveCallbackGroup()      # 오래 잡는 쪽
        self._cbg_safety = MutuallyExclusiveCallbackGroup()    # 취소·정지·estop
        self._cbg_engage = MutuallyExclusiveCallbackGroup()    # 제어권(스레드 join 대기)

        self.sub_estop = self.create_subscription(
            Bool, "estop", self._on_estop, LATCHED_QOS,
            callback_group=self._cbg_safety)
        self.sub_steer = self.create_subscription(
            Float64, "~/steer_deg", self._on_steer_deg, 10)
        # 축별 조향 — 시험 GUI 의 앞/뒤 슬라이더용. `[node, deg]` 2원소.
        # 전축 동일각(`~/steer_deg`)만으로는 앞뒤를 따로 세울 수 없다
        # (ADR 2026-08-03-amr-test-gui-ros2-port §Decision ⓑ).
        self.sub_steer_axis = self.create_subscription(
            Float64MultiArray, "~/steer_axis_deg", self._on_steer_axis_deg, 10)
        self.sub_drive = self.create_subscription(
            Float64, "~/drive_mmps", self._on_drive_mmps, 10)

        self.pub_joints = self.create_publisher(JointState, "joint_states", 10)
        self.pub_diag = self.create_publisher(DiagnosticArray, "diagnostics", 10)

        self.srv_engage = self.create_service(
            SetBool, "~/engage", self._srv_engage, callback_group=self._cbg_engage)
        self.srv_stop = self.create_service(
            Trigger, "~/stop", self._srv_stop, callback_group=self._cbg_safety)
        self.srv_home = self.create_service(
            Trigger, "~/home", self._srv_home, callback_group=self._cbg_home)
        self.srv_home_cancel = self.create_service(
            Trigger, "~/home_cancel", self._srv_home_cancel,
            callback_group=self._cbg_safety)

        self.create_timer(1.0 / float(g["state_hz"]), self._on_state_timer)
        self.create_timer(1.0 / float(g["diag_hz"]), self._on_diag_timer)

        self._rejected = 0
        self.get_logger().info(
            "can_relay 대기 — 제어권 미획득. `~/engage true` 로 획득하세요")

    # ── 모터 계층 메시지 대여 ─────────────────────────────────────────
    def _load_msgs(self):
        """`trnav_msgs` 를 빌린다. 없으면 저수준 경로를 열지 않는다.

        이 패키지는 메시지를 자체 정의하지 않는다 — 상류(`TR_Nav_ros2_ws`)와 같은 타입을
        써야 체인이 이어지고, 중복 정의는 `trnav_2ws_msgs` 폐기 때 이미 한 번 겪은 문제다.
        """
        try:
            from trnav_msgs.msg import MotorCmdArray, MotorState, MotorStateArray
            return MotorCmdArray, MotorStateArray, MotorState
        except ImportError as exc:
            self.get_logger().error(
                f"trnav_msgs 를 import 하지 못했다 ({exc}) — `/motor/low_cmd` 구독과 "
                f"`/motor/low_state` 발행을 만들지 않는다. 메시지를 이 패키지에 다시 "
                f"정의하지 않는 것이 의도된 설계다. 벤치 지령(~/steer_deg, ~/drive_mmps)은 "
                f"그대로 쓸 수 있다.")
            return None, None, None

    # ── 구독 콜백 ─────────────────────────────────────────────────────
    def _on_low_cmd(self, msg):
        """`/motor/low_cmd`(MotorCmdArray) — 상류 translator 가 낸 **raw** 지령.

        환산도 기구학도 하지 않는다. 그 둘은 상류(액션 서버 IK · translator SI→raw)가
        소유한다. 여기서는 안전 클램프만 raw 단위로 걸고 CAN 으로 내보낸다.

        ⚠ 단 **조향 원점은 여기가 소유한다** — `target_pos` 는 홈(직진 0°) 기준 상대
        counts 이고, `set_motor_cmds` 가 기체 캘리브레이션(`steer_home_counts`)을 더해
        절대 counts 로 만든다. 피드백(`/motor/low_state`)도 같은 좌표계로 되돌린다.
        홈 counts 의 정본은 `config/machine/<기체>.yaml` 하나이므로 상류에 복제하지 않는다.

        ⚠ 축별 조향각이 갈리는 지령(선회)은 **정상**이다 — bicycle 모델의 정의가
        `omega = vx(tan δf − tan δr)/L` 이라 전·후 각이 달라야 회전이 된다.
        구 `cmd_vel` 경로에 있던 1.0° 편차 거부 게이트는 그래서 제거했다.
        """
        try:
            cmds = [(m.motor_id, m.mode, m.target_vel, m.target_pos, m.profile_vel)
                    for m in msg.motors]
        except AttributeError as exc:
            self._reject(f"MotorCmd 필드 접근 실패: {exc}")
            return
        for note in self.backend.set_motor_cmds(cmds):
            self._reject(note)

    def _on_low_state_timer(self):
        if self.pub_low_state is None:
            return
        arr = self._MotorStateArray()
        arr.header.stamp = self.get_clock().now().to_msg()
        for d in self.backend.motor_states():
            st = self._MotorState()
            for k, v in d.items():
                setattr(st, k, v)
            arr.motors.append(st)
        self.pub_low_state.publish(arr)

    def _on_steer_deg(self, msg: Float64):
        try:
            self.backend.set_steer_deg(float(msg.data))
        except S.UnsafeCommand as exc:
            self._reject(str(exc))

    def _on_steer_axis_deg(self, msg: Float64MultiArray):
        """`[node, deg]` — 축 하나만 세운다. 형식이 어긋나면 거부 사유를 남긴다."""
        if len(msg.data) != 2:
            self._reject(f"~/steer_axis_deg 는 [node, deg] 2원소여야 한다 "
                         f"(받은 길이 {len(msg.data)})")
            return
        node, deg = msg.data
        if not float(node).is_integer():
            self._reject(f"~/steer_axis_deg 의 node 는 정수여야 한다 (받은 값 {node})")
            return
        try:
            self.backend.set_steer_axis_deg(int(node), float(deg))
        except S.UnsafeCommand as exc:
            self._reject(str(exc))

    def _on_drive_mmps(self, msg: Float64):
        try:
            self.backend.set_drive_mmps(float(msg.data))
        except S.UnsafeCommand as exc:
            self._reject(str(exc))

    def _on_estop(self, msg: Bool):
        self.backend.estop(bool(msg.data))

    def _reject(self, why: str):
        self._rejected += 1
        self.get_logger().warn(f"지령 거부 — {why}", throttle_duration_sec=1.0)

    # ── 서비스 ────────────────────────────────────────────────────────
    def _srv_engage(self, req: SetBool.Request, res: SetBool.Response):
        try:
            if req.data:
                self.link.open()
                self.link.acquire()
                self.backend.start()
                res.message = "제어권 획득 — 판다 intercept, fail-safe 무장"
            else:
                self.backend.shutdown()
                self.link.release()
                self.link.close()
                res.message = "제어권 반환 — passthrough"
            res.success = True
        except Exception as exc:
            # LinkError·RuntimeError 모두 Exception 하위다 — 나열하면 "구분해서 다룬다"는
            # 인상만 주고 동작은 같다. 제어권 조작은 어떤 실패도 응답으로 돌려줘야 하므로
            # 광범위 포획인 것을 그대로 적는다(2026-08-03 리뷰 L3).
            res.success = False
            res.message = f"{type(exc).__name__}: {exc}"
            self.get_logger().error(res.message)
        self.get_logger().info(res.message)
        return res

    def _srv_stop(self, _req, res: Trigger.Response):
        ok = self.backend.stop_all("서비스 요청")
        res.success = True
        # 사유를 그대로 전달한다 — 「실측 미확보」와 「이동 중 보류」는 대처가 다르다.
        res.message = ("구동 0 + 조향을 현재 위치에 유지" if ok else
                       f"구동 0 송신 · ⚠ 조향 미유지 — {self.backend.halt_note()}")
        return res

    def _srv_home(self, _req, res: Trigger.Response):
        self.get_logger().warn(
            "호밍 요청 — 조향이 100° 이상 스윙합니다. 진행 중 중단은 "
            "`~/home_cancel` 로 가능합니다(펌웨어 시퀀서가 취소 프레임을 냅니다). "
            "그래도 이동구역이 비어 있는지 먼저 확인하세요.")
        ok, why = self.backend.home(speed=int(self._g["homing_speed"]))
        res.success = ok
        res.message = why
        return res

    def _srv_home_cancel(self, _req, res: Trigger.Response):
        ok, why = self.backend.cancel_home()
        res.success = ok
        res.message = why
        self.get_logger().warn(f"호밍 취소 — {why}")
        return res

    # ── 타이머 ────────────────────────────────────────────────────────
    def _on_state_timer(self):
        angles = self.backend.steer_angles_deg()
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        for n, deg in sorted(angles.items()):
            if deg is None:
                continue        # 믿을 수 없는 축은 발행하지 않는다(0 으로 채우지 않는다)
            js.name.append(f"steer_{n}")
            js.position.append(math.radians(deg))
        if js.name:
            self.pub_joints.publish(js)

    def _on_diag_timer(self):
        snap = self.backend.snapshot()
        st = DiagnosticStatus()
        st.name = "can_relay: 릴레이 구동"
        st.hardware_id = str(self._g["panda_serial"] or "auto")

        bus_fault = self.backend.bus_fault()
        if snap["fault"]:
            st.level, st.message = DiagnosticStatus.ERROR, f"루프 오류: {snap['fault']}"
        elif bus_fault:
            # 버스 이상은 지령이 나가도 도달하지 않는다는 뜻이라 상위로 올린다.
            st.level, st.message = DiagnosticStatus.ERROR, f"CAN 버스 이상: {bus_fault}"
        elif snap["estop"]:
            st.level, st.message = DiagnosticStatus.ERROR, "E-stop 인가"
        elif not snap["engaged"]:
            st.level, st.message = DiagnosticStatus.WARN, "제어권 미획득 (대기)"
        elif snap["homing"]:
            st.level, st.message = DiagnosticStatus.WARN, "호밍 진행 중 — 위치 무효"
        elif any(not v["fresh"] for v in snap["nodes"].values()):
            stale = sorted(n for n, v in snap["nodes"].items() if not v["fresh"])
            st.level, st.message = DiagnosticStatus.ERROR, f"피드백 끊긴 노드 {stale}"
        elif any(v["aborts"] for v in snap["nodes"].values()):
            st.level, st.message = DiagnosticStatus.WARN, "SDO 거부 발생 — 로그 확인"
        else:
            st.level, st.message = DiagnosticStatus.OK, "정상"

        st.values = [
            KeyValue(key="engaged", value=str(snap["engaged"])),
            KeyValue(key="drive_units", value=str(snap["drive_units"])),
            KeyValue(key="steer_target_deg", value=str(snap["steer_target_deg"])),
            KeyValue(key="watchdog_trips", value=str(snap["watchdog_trips"])),
            KeyValue(key="rejected_commands", value=str(self._rejected)),
            KeyValue(key="tx", value=str(snap["tx"])),
            KeyValue(key="rx", value=str(snap["rx"])),
        ]
        for n, v in sorted(snap["nodes"].items()):
            st.values.append(KeyValue(
                key=f"node{n}",
                value=(f"pos={v['position']} sw={v['statusword']} "
                       f"homed={v['homed']} fresh={v['fresh']} "
                       f"di={v['digital_input']} aborts={v['aborts']}")))

        # per-bus CAN 에러 상태 — REC/TEC 는 uint8 이라 255 에서 포화한다.
        if snap.get("health_supported") is False:
            st.values.append(KeyValue(key="bus_health",
                                      value=f"미지원 ({snap.get('health_error')})"))
        for bus, h in sorted(snap.get("bus_health", {}).items()):
            st.values.append(KeyValue(
                key=f"bus{bus}",
                value=(f"off={h['bus_off']} passive={h['error_passive']} "
                       f"warn={h['error_warning']} REC={h['rec']} TEC={h['tec']} "
                       f"lec={h['last_error_code']} esr=0x{h['esr_reg']:08X}")))

        hs = snap.get("homing_status") or {}
        if hs:
            st.values.append(KeyValue(
                key="homing",
                value=(f"{hs.get('state_name')} elapsed={hs.get('elapsed_s')}s "
                       f"done=0x{hs.get('done_mask', 0):02X} "
                       f"reached=0x{hs.get('reached_mask', 0):02X}")))

        arr = DiagnosticArray()
        arr.header.stamp = self.get_clock().now().to_msg()
        arr.status = [st]
        self.pub_diag.publish(arr)

    def destroy_node(self):
        """종료 시 반드시 정지 → 제어권 반환 순서로 내려간다."""
        try:
            self.backend.shutdown()
            self.link.release()
            self.link.close()
        except Exception as exc:
            self.get_logger().error(f"종료 처리 실패: {type(exc).__name__}: {exc}")
        finally:
            super().destroy_node()


def main(args=None):
    """진입점. **다중 스레드 실행기**를 쓴다 — 단일 스레드면 취소가 도달하지 못한다.

    `rclpy.spin()`(단일 스레드)에서는 `~/home` 콜백이 도는 동안 다른 콜백이 하나도
    처리되지 않는다. 콜백 그룹 분리(`__init__`)와 **한 쌍**으로만 성립한다 —
    둘 중 하나만 있으면 취소·정지는 여전히 막힌다(2026-08-03 리뷰 H1).
    """
    rclpy.init(args=args)
    node = None
    executor = MultiThreadedExecutor()
    try:
        node = CanRelayNode()
        executor.add_node(node)
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
