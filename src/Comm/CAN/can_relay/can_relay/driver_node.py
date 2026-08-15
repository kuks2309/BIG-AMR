#!/usr/bin/env python3
"""can_relay 드라이버 노드 — 판다 릴레이 경유 모터 구동 ROS2 진입점.

## 이 노드가 하지 않는 것 (의도적)

- **기동만으로 제어권을 잡지 않는다.** `~/engage` 서비스를 명시 호출해야 Seer 에게서
  버스를 가져온다. launch 만으로 로봇이 움직일 수 있는 상태를 만들지 않는다.
- **역기구학도 단위환산도 하지 않는다.** 이 노드는 모터 계층이다 — 기구학은 액션 서버가,
  SI→raw 환산은 상류 translator 가 소유한다.
- **메시지를 자체 정의하지 않는다.** `trnav_msgs` 를 빌리며, 없으면 조용히 대체하지 않고
  저수준 경로를 **열지 않는다**.
- **자동으로 호밍하지 않는다.** 물리 스윙 100°+ 이므로 `~/home` 명시 호출 전용이고,
  진행 중 취소는 `~/home_cancel` 로 한다.

## 인터페이스

| 방향 | 이름 | 타입 | 비고 |
|---|---|---|---|
| 구독 | `/motor/low_cmd` | `trnav_msgs/MotorCmdArray` | **raw** 지령. 환산·기구학 없음 |
| 발행 | `/motor/low_state` | `trnav_msgs/MotorStateArray` | raw 피드백 → 상류 translator |
| 구독 | `estop` | `std_msgs/Bool` | 소프트 래치. 하드웨어 E-STOP 을 대체하지 않는다 |
| 구독 | `~/steer_deg` · `~/steer_axis_deg` | `Float64` · `Float64MultiArray` | 벤치 직접 조향 |
| 구독 | `~/drive_mmps` | `std_msgs/Float64` | 벤치 직접 구동속도 |
| 발행 | `joint_states` | `sensor_msgs/JointState` | 조향 실측각(믿을 수 있는 축만) |
| 발행 | `diagnostics` | `diagnostic_msgs/DiagnosticArray` | 제어권·심박·워치독·abort |
| 서비스 | `~/engage` | `std_srvs/SetBool` | 제어권 획득/반환 |
| 서비스 | `~/stop` | `std_srvs/Trigger` | 즉시 정지 |
| 서비스 | `~/home` · `~/home_cancel` | `std_srvs/Trigger` | 조향 호밍(⚠ 물리 스윙) · 취소 |
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
from .link import MOTOR_BUS, MockLink, PandaLink, panda_library_error

# E-stop 은 래치 상태다 — 늦게 붙은 구독자도 현재 값을 받아야 한다.
LATCHED_QOS = QoSProfile(depth=1,
                         history=HistoryPolicy.KEEP_LAST,
                         reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)


class CanRelayNode(Node):
    """파라미터를 읽어 백엔드를 세우고 ROS 인터페이스를 여는 드라이버 노드."""

    def __init__(self):
        """파라미터 검증 → 링크·백엔드 생성 → 토픽·서비스·타이머 생성 순으로 기동한다.

        캘리브레이션(조향 홈·길이·호밍 방식·탐색 범위)이 어긋나면 여기서 `ValueError` 로
        멈춘다 — 잘못된 원점으로 움직이면 물리 손상으로 이어지기 때문이다.
        """
        super().__init__("can_relay_node")

        p = self.declare_parameters("", [
            ("link", "panda"),                  # panda | mock
            ("panda_serial", ""),
            ("bus", MOTOR_BUS),
            ("drive_nodes", [1, 2]),
            ("steer_nodes", [3, 4]),
            ("steer_limit_deg", S.STEER_LIMIT_DEG),
            # 벤치 직접 지령(`~/steer_deg`·`~/steer_axis_deg`) 전용 상한. 체인 상한과
            # 분리한다 — 사람이 손으로 넣는 경로는 넓히지 않는다.
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
            # ROS 계층 생존 표시가 이보다 낡으면 백엔드가 심박을 끊는다(0=판정 안 함).
            # 표시를 찍는 것이 아래 진단 타이머이므로 `diag_hz` 와 결합한다.
            ("ros_alive_timeout_s", 2.0),

            # ── 장비별 캘리브레이션 (config/machine/<기체>.yaml) ──────────
            # 여기 기본값은 **안전한 쪽**이다: 호밍 비활성 + 홈 미설정 + 호밍 전 조향 차단.
            # 캘리브레이션 파일을 안 넣으면 아무것도 움직이지 않는다.
            ("machine_name", "(미지정)"),
            ("steer_counts_per_deg", S.COUNTS_PER_DEG),
            ("drive_units_per_mmps", S.VEL_PER_MMPS),
            ("drive_max_units", S.VEL_MAX_UNITS),
            ("homing_method", "firmware"),      # "firmware" | "35"
            ("homing_enabled", False),
            ("steer_home_offset", [], ParameterDescriptor(dynamic_typing=True)),
            # 홈은 코드 기본값을 두지 않는다 — 빈 배열이 곧 "미설정"이고 기동이 거부된다.
            # ⚠ `dynamic_typing` 이 필요하다 — 빈 기본값을 rclpy 가 BYTE_ARRAY 로 추론해
            #   YAML 의 정수 배열 로드를 거부한다. descriptor.type 지정만으로는 부족하다.
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

        # ROS 생존 표시는 진단 타이머가 찍는다 — 임계가 그 주기보다 짧으면 정상 동작 중에도
        # 심박이 끊긴다. 두 파라미터가 결합해 있으므로 기동 시점에 막는다.
        alive_ttl = float(g["ros_alive_timeout_s"])
        diag_hz = float(g["diag_hz"])
        if alive_ttl > 0.0:
            if diag_hz <= 0.0:
                raise ValueError(
                    "ros_alive_timeout_s 를 쓰려면 diag_hz 가 0보다 커야 한다 — "
                    "생존 표시를 찍는 것이 진단 타이머다")
            if alive_ttl < 2.0 / diag_hz:
                raise ValueError(
                    f"ros_alive_timeout_s({alive_ttl}) 가 진단 주기의 2배"
                    f"({2.0 / diag_hz:.2f}s) 보다 짧다 — 정상 동작 중에도 심박이 끊긴다. "
                    f"임계를 늘리거나 diag_hz({diag_hz})를 올릴 것")

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
            ros_alive_timeout_s=alive_ttl,
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
            lib_err = panda_library_error()
            if lib_err is not None:
                # 기동은 막지 않는다(진단·대기 상태는 유효하고, 크래시는 systemd 재기동
                # 루프가 된다). 다만 첫 `~/engage` 에서야 알게 되는 것을 막기 위해
                # 기동 시점에 크게 남긴다.
                self.get_logger().error(
                    f"판다 라이브러리 없음 — `~/engage` 가 거부될 것이다: {lib_err}")
        self.backend = RelayBackend(self.link, cfg, log=logger)

        # 모터 계층 메시지. 없으면 저수준 경로를 열지 않는다(조용히 대체하지 않는다).
        self._MotorCmdArray, self._MotorStateArray, self._MotorState = self._load_msgs()

        # 모터 계층 계약 — QoS 는 체인 전 구간이 RELIABLE + KeepLast(10) + VOLATILE 다.
        self.sub_low_cmd = self.pub_low_state = None
        if self._MotorCmdArray is not None:
            self.sub_low_cmd = self.create_subscription(
                self._MotorCmdArray, "/motor/low_cmd", self._on_low_cmd, 10)
            self.pub_low_state = self.create_publisher(
                self._MotorStateArray, "/motor/low_state", 10)
            self.create_timer(1.0 / float(g["low_state_hz"]), self._on_low_state_timer)

        # ── 콜백 그룹 분리 (정지 계열이 호밍에 묶이지 않게) ──────────────────
        # `~/home` 콜백은 terminal 이나 timeout 까지 반환하지 않는다. 기본 그룹은 상호배타라
        # 같은 그룹에 있으면 그동안 `~/home_cancel`·`~/stop`·`estop` 이 하나도 소비되지
        # 않는다 — 유일한 취소 수단이 정작 호밍 중에만 죽는다.
        # ⚠ 그룹만 나눠서는 부족하다 — 단일 스레드 실행기에서는 여전히 순차 처리다.
        #   `main()` 의 MultiThreadedExecutor 와 **둘이 한 쌍**이다.
        self._cbg_home = MutuallyExclusiveCallbackGroup()      # 오래 잡는 쪽
        self._cbg_safety = MutuallyExclusiveCallbackGroup()    # 취소·정지·estop
        self._cbg_engage = MutuallyExclusiveCallbackGroup()    # 제어권(스레드 join 대기)

        self.sub_estop = self.create_subscription(
            Bool, "estop", self._on_estop, LATCHED_QOS,
            callback_group=self._cbg_safety)
        self.sub_steer = self.create_subscription(
            Float64, "~/steer_deg", self._on_steer_deg, 10)
        # 축별 조향 — 전축 동일각(`~/steer_deg`)만으로는 앞뒤를 따로 세울 수 없다.
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
        """`trnav_msgs` 에서 `(MotorCmdArray, MotorStateArray, MotorState)` 를 빌린다.

        이 패키지는 메시지를 자체 정의하지 않는다 — 상류와 같은 타입을 써야 체인이 이어진다.
        import 에 실패하면 세 값 모두 `None` 이고 저수준 경로를 열지 않는다.
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
        """`/motor/low_cmd` — 상류 translator 가 낸 **raw** 지령을 백엔드에 넘긴다.

        환산도 기구학도 하지 않는다. 안전 클램프만 raw 단위로 걸고 CAN 으로 내보낸다.

        **조향 원점은 이 계층이 소유한다** — `target_pos` 는 홈(직진 0°) 기준 상대 counts 이고
        백엔드가 기체 캘리브레이션을 더해 절대 counts 로 만든다. 피드백도 같은 좌표계로
        되돌리므로 홈 counts 를 상류에 복제하지 않는다.

        축별 조향각이 갈리는 지령(선회)은 정상이다 — bicycle 모델은 전·후 각이 달라야
        회전이 되므로 여기서 편차로 거부하지 않는다.
        필드 접근 실패와 백엔드가 돌려준 거부 사유는 모두 `_reject` 로 센다.
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
        """백엔드의 노드별 raw 피드백을 `MotorStateArray` 로 발행한다."""
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
        """`~/steer_deg` — 전 조향축을 같은 각으로 세운다. 거부되면 사유를 센다."""
        try:
            self.backend.set_steer_deg(float(msg.data))
        except S.UnsafeCommand as exc:
            self._reject(str(exc))

    def _on_steer_axis_deg(self, msg: Float64MultiArray):
        """`~/steer_axis_deg` — `[node, deg]` 로 축 하나만 세운다.

        길이가 2 가 아니거나 node 가 정수가 아니면 거부 사유를 남긴다.
        """
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
        """`~/drive_mmps` — 구동 속도를 세운다. 거부되면 사유를 센다."""
        try:
            self.backend.set_drive_mmps(float(msg.data))
        except S.UnsafeCommand as exc:
            self._reject(str(exc))

    def _on_estop(self, msg: Bool):
        """`estop` 래치를 백엔드에 그대로 전달한다."""
        self.backend.estop(bool(msg.data))

    def _reject(self, why: str):
        """거부 1건을 세고 사유를 경고로 남긴다(초당 1회로 조인다)."""
        self._rejected += 1
        self.get_logger().warn(f"지령 거부 — {why}", throttle_duration_sec=1.0)

    # ── 서비스 ────────────────────────────────────────────────────────
    def _srv_engage(self, req: SetBool.Request, res: SetBool.Response):
        """`~/engage` — 참이면 열기·획득·백엔드 기동, 거짓이면 정지·반환·닫기.

        예외는 종류를 가리지 않고 잡아 응답에 싣는다 — 제어권 조작은 어떤 실패도
        호출자에게 돌려줘야 하기 때문이다.
        """
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
            res.success = False
            res.message = f"{type(exc).__name__}: {exc}"
            self.get_logger().error(res.message)
        self.get_logger().info(res.message)
        return res

    def _srv_stop(self, _req, res: Trigger.Response):
        """`~/stop` — 구동 0 + 조향 현 위치 유지. 유지 실패 사유는 메시지에 싣는다.

        「실측 미확보」와 「이동 중 보류」는 대처가 다르므로 사유를 그대로 전달한다.
        """
        ok = self.backend.stop_all("서비스 요청")
        res.success = True
        res.message = ("구동 0 송신 · 조향 목표 재송신 중단(축은 직전 목표까지 회전할 수 있음)" if ok else
                       f"구동 0 송신 · ⚠ 조향 미유지 — {self.backend.halt_note()}")
        return res

    def _srv_home(self, _req, res: Trigger.Response):
        """`~/home` — 조향 호밍(⚠ 물리 스윙 100°+)을 수행하고 결과를 반환한다.

        결과는 응답뿐 아니라 **로그에도 남긴다** — 0° 복귀가 게이트에 거부돼도 노드 로그로
        사유를 추적할 수 있어야 한다.
        """
        self.get_logger().warn(
            "호밍 요청 — 조향이 100° 이상 스윙합니다. 진행 중 중단은 "
            "`~/home_cancel` 로 가능합니다(펌웨어 시퀀서가 취소 프레임을 냅니다). "
            "그래도 이동구역이 비어 있는지 먼저 확인하세요.")
        ok, why = self.backend.home(speed=int(self._g["homing_speed"]))
        # rclpy 는 로그 컨텍스트를 호출 지점(파일·함수·줄)으로 캐시하고 severity 변경을
        # 거부한다 — 한 줄에서 info/error 를 번갈아 부르면 두 번째가 ValueError 다.
        msg = f"호밍 결과 — {'성공' if ok else '실패'}: {why}"
        if ok:
            self.get_logger().info(msg)
        else:
            self.get_logger().error(msg)
        res.success = ok
        res.message = why
        return res

    def _srv_home_cancel(self, _req, res: Trigger.Response):
        """`~/home_cancel` — 진행 중 호밍을 취소하고 결과를 경고로 남긴다."""
        ok, why = self.backend.cancel_home()
        res.success = ok
        res.message = why
        self.get_logger().warn(f"호밍 취소 — {why}")
        return res

    # ── 타이머 ────────────────────────────────────────────────────────
    def _on_state_timer(self):
        """조향 실측각을 `joint_states`(rad)로 발행한다.

        믿을 수 없는 축은 **발행하지 않는다** — 0 으로 채우면 상위가 그것을 실측으로 읽는다.
        """
        angles = self.backend.steer_angles_deg()
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        for n, deg in sorted(angles.items()):
            if deg is None:
                continue
            js.name.append(f"steer_{n}")
            js.position.append(math.radians(deg))
        if js.name:
            self.pub_joints.publish(js)

    def _on_diag_timer(self):
        """백엔드 스냅샷을 진단 1건으로 요약해 발행한다.

        level 은 심각한 것부터 고른다: 심박 중단 → 루프 오류 → CAN 버스 이상 → E-stop →
        제어권 미획득 → 호밍 중 → 피드백 끊김 → SDO 거부 → 정상. key/value 에는 제어권·
        지령·워치독·노드별 상태와 버스 에러 카운터(REC/TEC 는 uint8 이라 255 에서 포화)를 싣는다.

        **이 타이머가 백엔드에 ROS 생존을 찍는 지점이다.** 실행기가 정체하면 여기가
        멈추고, 백엔드가 그것을 보고 심박을 끊어 펌웨어에 정지를 넘긴다. 찍기를
        발행보다 **먼저** 한다 — 발행이 실패해도 실행기 자체는 돌고 있었기 때문이다.
        """
        self.backend.mark_ros_alive()
        snap = self.backend.snapshot()
        st = DiagnosticStatus()
        st.name = "can_relay: 릴레이 구동"
        st.hardware_id = str(self._g["panda_serial"] or "auto")

        bus_fault = self.backend.bus_fault()
        if snap["hb_suppressed"]:
            # 심박 중단은 「곧 펌웨어가 세운다」는 뜻이라 어떤 사유보다 위다.
            st.level = DiagnosticStatus.ERROR
            st.message = f"심박 중단 — {snap.get('hb_block_note') or '사유 미상'}"
        elif snap["fault"]:
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
        elif snap["home_failed"]:
            # 조향이 잠긴 상태를 「정상」으로 적으면, 지령을 걸어 거부당하기 전까지
            # 운용자가 알 길이 없다. 다음에 할 일까지 문장에 싣는다.
            st.level, st.message = (DiagnosticStatus.WARN,
                                    "조향 잠금 — 직전 호밍 미완료. `~/home` 재수행 필요")
        elif any(not v["fresh"] for v in snap["nodes"].values()):
            stale = sorted(n for n, v in snap["nodes"].items() if not v["fresh"])
            st.level, st.message = DiagnosticStatus.ERROR, f"피드백 끊긴 노드 {stale}"
        elif any(v["aborts"] for v in snap["nodes"].values()):
            st.level, st.message = DiagnosticStatus.WARN, "SDO 거부 발생 — 로그 확인"
        else:
            st.level, st.message = DiagnosticStatus.OK, "정상"

        # 감시 노드(`supervisor.py`)가 **이 목록만 보고** 상태를 기록·복귀한다.
        # 그래서 estop·home_failed·homed_effective·hb_suppressed 는 message 문자열이
        # 아니라
        # key/value 로 낸다 — 문장 파싱에 기대면 문구를 고치는 순간 감시가 깨진다.
        st.values = [
            KeyValue(key="engaged", value=str(snap["engaged"])),
            KeyValue(key="estop", value=str(snap["estop"])),
            KeyValue(key="home_failed", value=str(snap["home_failed"])),
            KeyValue(key="drive_units", value=str(snap["drive_units"])),
            KeyValue(key="steer_target_deg", value=str(snap["steer_target_deg"])),
            KeyValue(key="homed_effective", value=str(snap["homed_effective"])),
            KeyValue(key="hb_suppressed", value=str(snap["hb_suppressed"])),
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
        """종료 시 반드시 정지 → 제어권 반환 → 닫기 순서로 내려간다."""
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

    단일 스레드에서는 `~/home` 콜백이 도는 동안 다른 콜백이 하나도 처리되지 않는다.
    콜백 그룹 분리와 **한 쌍**으로만 성립하며, 둘 중 하나만 있으면 취소·정지는 여전히 막힌다.
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
