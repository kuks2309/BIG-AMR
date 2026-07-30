#!/usr/bin/env python3
"""can_relay 드라이버 노드 — 판다 릴레이 경유 모터 구동 ROS2 진입점.

## 이 노드가 하지 않는 것 (의도적)

- **기동만으로 제어권을 잡지 않는다.** `~/engage` 서비스를 명시 호출해야 Seer 에게서
  버스를 가져온다. launch 만으로 로봇이 움직일 수 있는 상태를 만들지 않는다.
- **역기구학을 자체 구현하지 않는다.** 이 저장소에는 같은 역기구학이 이미 3벌
  있고 접기 임계가 ±90°/±115°/±140° 로 서로 다르다. 4벌째를 만들면 발산이
  고착된다. `cmd_vel` 경로는 `motor_control.kinematics` 를 **의존**하며,
  그것을 import 하지 못하면 조용히 대체하지 않고 **구독을 만들지 않는다.**
- **자동으로 호밍하지 않는다.** 물리 스윙 100°+ 이고 **본 구현에 취소 경로가 없다**
  (`backend.home()` 은 `0x60FB:04=1` 송신 후 상태워드만 관측). 펌웨어에는 취소 경로가
  있으나 미사용이다 — `safety_seer_gate.h:307-309`. `~/home` 명시 호출 전용이다.

## 인터페이스

| 방향 | 이름 | 타입 | 비고 |
|---|---|---|---|
| 구독 | `cmd_vel` | `geometry_msgs/Twist` | NaN 거부 → 클램프 → IK → 조향/구동 |
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
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, HistoryPolicy, QoSProfile,
                       ReliabilityPolicy)
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, Float64
from std_srvs.srv import SetBool, Trigger

from . import safety as S
from .backend import RelayBackend, RelayConfig
from .link import MOTOR_BUS, LinkError, MockLink, PandaLink

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
            ("steer_home_counts", [S.DEFAULT_STEER_HOME[3],
                                   S.DEFAULT_STEER_HOME[4]]),
            ("steer_limit_deg", S.STEER_LIMIT_DEG),
            ("vel_max_units", S.VEL_MAX_UNITS),
            ("cmd_timeout_s", 0.3),
            ("cmd_hz", 20.0),
            ("poll_hz", 5.0),
            ("settle_tol_deg", 3.0),
            ("allow_bringup", False),
            ("enable_cmd_vel", True),
            ("vmax", 0.2),
            ("wmax", 0.3),
            ("module_x", [0.6039, -0.5961]),
            ("module_y", [-0.0014, -0.0014]),
            ("diag_hz", 1.0),
            ("state_hz", 10.0),
        ])
        g = {d.name: d.value for d in p}
        self._g = g

        steer_nodes = [int(n) for n in g["steer_nodes"]]
        homes = [int(c) for c in g["steer_home_counts"]]
        if len(homes) != len(steer_nodes):
            raise ValueError(
                f"steer_home_counts({len(homes)}) 와 steer_nodes({len(steer_nodes)}) "
                f"길이가 다르다 — 조향 원점을 잘못 배정하면 물리 손상으로 이어진다")

        cfg = RelayConfig(
            drive_nodes=tuple(int(n) for n in g["drive_nodes"]),
            steer_nodes=tuple(steer_nodes),
            bus=int(g["bus"]),
            cmd_hz=float(g["cmd_hz"]),
            poll_hz=float(g["poll_hz"]),
            cmd_timeout_s=float(g["cmd_timeout_s"]),
            steer_limit_deg=float(g["steer_limit_deg"]),
            vel_max_units=int(g["vel_max_units"]),
            steer_home=dict(zip(steer_nodes, homes)),
            settle_tol_deg=float(g["settle_tol_deg"]),
            allow_bringup=bool(g["allow_bringup"]),
        )
        self._cfg = cfg

        logger = self.get_logger().info
        if g["link"] == "mock":
            self.link = MockLink()
            logger("링크 = mock (하드웨어 무접속)")
        else:
            serial = g["panda_serial"] or None
            self.link = PandaLink(serial=serial, log=logger)
        self.backend = RelayBackend(self.link, cfg, log=logger)

        # 역기구학은 빌려 쓴다. 못 빌리면 cmd_vel 을 아예 열지 않는다.
        self._kin = self._load_kinematics() if g["enable_cmd_vel"] else None

        self.sub_estop = self.create_subscription(
            Bool, "estop", self._on_estop, LATCHED_QOS)
        self.sub_steer = self.create_subscription(
            Float64, "~/steer_deg", self._on_steer_deg, 10)
        self.sub_drive = self.create_subscription(
            Float64, "~/drive_mmps", self._on_drive_mmps, 10)
        if self._kin is not None:
            self.sub_cmd = self.create_subscription(
                Twist, "cmd_vel", self._on_cmd_vel, 10)

        self.pub_joints = self.create_publisher(JointState, "joint_states", 10)
        self.pub_diag = self.create_publisher(DiagnosticArray, "diagnostics", 10)

        self.srv_engage = self.create_service(SetBool, "~/engage", self._srv_engage)
        self.srv_stop = self.create_service(Trigger, "~/stop", self._srv_stop)
        self.srv_home = self.create_service(Trigger, "~/home", self._srv_home)

        self.create_timer(1.0 / float(g["state_hz"]), self._on_state_timer)
        self.create_timer(1.0 / float(g["diag_hz"]), self._on_diag_timer)

        self._rejected = 0
        self.get_logger().info(
            "can_relay 대기 — 제어권 미획득. `~/engage true` 로 획득하세요")

    # ── 역기구학 대여 ─────────────────────────────────────────────────
    def _load_kinematics(self):
        try:
            from motor_control.kinematics import DualSteerKinematics
        except ImportError as exc:
            self.get_logger().error(
                f"motor_control.kinematics 를 import 하지 못했다 ({exc}) — "
                f"cmd_vel 구독을 만들지 않는다. 역기구학을 이 패키지에 다시 "
                f"구현하지 않는 것이 의도된 설계다(중복 IK 금지). "
                f"직접 지령(~/steer_deg, ~/drive_mmps)은 그대로 쓸 수 있다.")
            return None
        xs = [float(v) for v in self._g["module_x"]]
        ys = [float(v) for v in self._g["module_y"]]
        drive_nodes = list(self._cfg.drive_nodes)
        if not (len(xs) == len(ys) == len(drive_nodes)):
            self.get_logger().error(
                f"module_x({len(xs)})·module_y({len(ys)})·drive_nodes"
                f"({len(drive_nodes)}) 길이 불일치 — cmd_vel 비활성")
            return None
        node_xy = {n: (x, y) for n, x, y in zip(drive_nodes, xs, ys)}
        return DualSteerKinematics(node_xy, float(self._g["vmax"]))

    # ── 구독 콜백 ─────────────────────────────────────────────────────
    def _on_cmd_vel(self, msg: Twist):
        vx, vy, wz = msg.linear.x, msg.linear.y, msg.angular.z
        if not S.finite(vx, vy, wz):
            self._reject(f"cmd_vel 에 비유한 값 (x={vx} y={vy} wz={wz})")
            return
        vmax, wmax = float(self._g["vmax"]), float(self._g["wmax"])
        vx, vy = S.clamp(vx, vmax), S.clamp(vy, vmax)
        wz = S.clamp(wz, wmax)
        mods = self._kin.twist_to_modules(vx, vy, wz)
        # 이 로봇은 인라인 듀얼스티어라 crab 은 두 축이 같은 각이어야 한다.
        # 축별 각이 갈리는 지령(스핀 등)은 이 골격에서 아직 다루지 않는다.
        angles = [m.steer_rad for m in mods if m.steer_rad is not None]
        if not angles:
            self._reject("cmd_vel → 조향각 없음")
            return
        spread = math.degrees(max(angles) - min(angles))
        if spread > 1.0:
            self._reject(
                f"축별 조향각이 {spread:.1f}° 갈린다 — 이 골격은 동일각(crab/직진)만 "
                f"지원한다. 스핀·선회는 미구현이다")
            return
        deg = math.degrees(angles[0])
        speed = mods[0].velocity_mps
        try:
            self.backend.set_steer_deg(deg)
            self.backend.set_drive_mmps(abs(speed) * 1000.0,
                                        1 if speed >= 0 else -1)
        except S.UnsafeCommand as exc:
            self._reject(str(exc))

    def _on_steer_deg(self, msg: Float64):
        try:
            self.backend.set_steer_deg(float(msg.data))
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
        except (LinkError, RuntimeError, Exception) as exc:
            res.success = False
            res.message = f"{type(exc).__name__}: {exc}"
            self.get_logger().error(res.message)
        self.get_logger().info(res.message)
        return res

    def _srv_stop(self, _req, res: Trigger.Response):
        self.backend.stop("서비스 요청")
        res.success = True
        res.message = "구동 0 송신 (조향은 현 위치 유지)"
        return res

    def _srv_home(self, _req, res: Trigger.Response):
        self.get_logger().warn(
            "호밍 요청 — 조향이 100° 이상 스윙합니다. 시작 뒤에는 소프트웨어가 "
            "멈출 수 없습니다(드라이브 내부 루틴). 중단 수단은 하드웨어 E-STOP 뿐입니다.")
        ok, why = self.backend.home()
        res.success = ok
        res.message = why
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

        if snap["fault"]:
            st.level, st.message = DiagnosticStatus.ERROR, f"루프 오류: {snap['fault']}"
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
    rclpy.init(args=args)
    node = None
    try:
        node = CanRelayNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
