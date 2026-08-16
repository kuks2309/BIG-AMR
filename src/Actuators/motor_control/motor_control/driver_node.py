"""motor_control_node — Tongyi AMR CAN 구동 ROS2 노드.

토픽: cmd_vel(Twist)·estop(Bool) 구독 · odom(Odometry)+TF · joint_states · diagnostics 발행.
콜백은 목표 저장만 하고 즉시 반환한다 — CAN 타이밍은 backend 스레드가 소유한다.

여기서 발행하는 odom 은 **휠 오도메트리**다: 구동륜 속도와 조향각을 기구학으로 합쳐 적분한다.
레이저 정합 오도(icp_odometry)와는 별개 소스이며, 둘 중 무엇을 /odom 으로 쓸지는 런치가 정한다.

⚠ 부호·매핑 3건이 미판정이다(값 변경 금지). 확정 전까지 crab·스핀 twist 와 **odom yaw 를 신뢰하지 말 것**:
  kin_steer_sign(debt-004) · steer_home_counts 기준(debt-007) · module_x 의 전·후 배정.
"""
from __future__ import annotations

import math

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool
from tf2_ros import TransformBroadcaster

from .backend import ModuleConfig, TongyiSdoBackend
from .kinematics import DiffDriveKinematics, DualSteerKinematics

# ── 스케일 상수 ──────────────────────────────────────────────────────────────
# ⚠ 네 값 모두 드라이브 설정에서 오는 것이라 기체·펌웨어가 바뀌면 달라진다. 코드에 박힌 값은
#   이 기체 기준이며 독립 실측으로 재확인된 적이 없다 — 특히 조향 counts/° 는 같은 상수로
#   지령하고 되읽는 순환 측정이라 그 방식으로는 검증되지 않는다.
M_S_PER_UNIT = 4.0906e-5                       # 드라이브 1 unit(0.1 rpm) → m/s
COUNTS_PER_RAD = 57344.0 * 180.0 / math.pi     # 조향 엔코더 counts per rad (설정값 57,344 counts/deg 환산)
COUNTS_PER_M = 2670177.0                       # 구동 엔코더 counts per m
WHEEL_RADIUS = 0.125                           # m


class MotorControlNode(Node):
    def __init__(self):
        super().__init__("motor_control_node")
        p = self.declare_parameters("", [
            ("can_channel", "can1"),
            ("kinematics", "dual_steer"),          # dual_steer | diff_drive
            ("vmax", 0.2), ("wmax", 0.3),
            ("cmd_timeout", 0.2),
            ("allow_homing_motion", False),
            ("steer_settle_tol_deg", 3.0),
            ("homing_tol_deg", 5.0),
            # ⚠ 라벨이 서로 어긋나 부호가 미판정이다. 값을 바꾸지 말 것.
            ("drive_sign", -1),
            # ⚠ 미검증 — 실측은 -1 을 시사한다(debt-004). 확정 전에는 crab·스핀 twist 를 쓰지 말 것.
            ("kin_steer_sign", 1),
            ("module_drive_nodes", [1, 2]),
            ("module_steer_nodes", [3, 4]),            # diff_drive 는 무시
            # ⚠ node1 이 전륜인지 후륜인지가 미판정이며 반대 근거가 유력하다.
            #   이 배정이 뒤집히면 spin·crab 의 회전 방향과 odom yaw 부호가 함께 뒤집힌다.
            ("module_x", [-0.5961, 0.6039]),
            ("module_y", [-0.0014, -0.0014]),
            # ⚠ 조향 원점 기준이 미판정이다(debt-007) — 호밍 후 정착 목표와 달라 조향각에 상시
            #   바이어스가 남고, 그 바이어스는 odom yaw 로 그대로 흘러간다.
            #   YAML 을 로드하지 않으면 이 기본값이 그대로 0x607A 로 송신된다.
            ("steer_home_counts", [7871815, 7840086]),
            ("track_width", 1.2),                      # diff_drive 용
            ("odom_frame", "odom"), ("base_frame", "base_link"),
            ("publish_tf", True),
            ("odom_rate", 25.0), ("diag_rate", 1.0),
        ])
        g = {q.name: q.value for q in p}
        self._g = g

        drive_nodes = list(g["module_drive_nodes"])
        steer_nodes = list(g["module_steer_nodes"])
        self.node_xy = {n: (g["module_x"][i], g["module_y"][i]) for i, n in enumerate(drive_nodes)}
        if g["kinematics"] == "diff_drive":
            self.kin = DiffDriveKinematics(drive_nodes[0], drive_nodes[1], g["track_width"], g["vmax"])
            modules = [ModuleConfig(n, None, 0) for n in drive_nodes]
        else:
            self.kin = DualSteerKinematics(self.node_xy, g["vmax"])
            modules = [ModuleConfig(n, steer_nodes[i], int(g["steer_home_counts"][i]))
                       for i, n in enumerate(drive_nodes)]
        self.modules = modules
        self.steer_of = {m.drive_node: m.steer_node for m in modules}
        self.steer_home = {m.steer_node: m.steer_home for m in modules if m.steer_node is not None}

        import can
        bus = can.Bus(channel=g["can_channel"], interface="socketcan", receive_own_messages=False)
        self.backend = TongyiSdoBackend(
            bus, modules,
            m_s_per_unit=M_S_PER_UNIT, drive_sign=int(g["drive_sign"]),
            counts_per_rad=COUNTS_PER_RAD, steer_sign=int(g["kin_steer_sign"]),
            vel_limit_units=int(round(g["vmax"] / M_S_PER_UNIT)),
            cmd_timeout=float(g["cmd_timeout"]),
            steer_settle_tol_counts=int(g["steer_settle_tol_deg"] * 57344),
            allow_homing_motion=bool(g["allow_homing_motion"]),
            homing_tol_counts=int(g["homing_tol_deg"] * 57344),
            logger=lambda m: self.get_logger().info(m))
        try:
            self.backend.start()
        except Exception:
            self.backend.shutdown()  # 브링업 실패 시 CAN 버스 정리(소켓 누수 방지)
            raise

        self.create_subscription(Twist, "cmd_vel", self._on_cmd_vel, 10)
        self.create_subscription(Bool, "estop", self._on_estop, 10)
        self.create_subscription(Bool, "freewheel", self._on_freewheel, 10)
        self.pub_odom = self.create_publisher(Odometry, "odom", 10)
        self.pub_js = self.create_publisher(JointState, "joint_states", 10)
        self.pub_diag = self.create_publisher(DiagnosticArray, "diagnostics", 10)
        self.tf_bc = TransformBroadcaster(self) if g["publish_tf"] else None

        self._pose = [0.0, 0.0, 0.0]           # x, y, yaw (odom 적분)
        self._prev_pos: dict[int, int] | None = None  # 노드별 이전 0x6064
        self.create_timer(1.0 / float(g["odom_rate"]), self._on_odom_timer)
        self.create_timer(1.0 / float(g["diag_rate"]), self._on_diag_timer)
        self.get_logger().info(f"motor_control_node up — kinematics={g['kinematics']}, "
                               f"channel={g['can_channel']}, vmax={g['vmax']} m/s")

    # ── 콜백 (비블로킹: 목표 저장만) ─────────────────────────────────────────
    def _on_cmd_vel(self, msg: Twist):
        g = self._g
        vx = max(-g["vmax"], min(g["vmax"], msg.linear.x))
        vy = max(-g["vmax"], min(g["vmax"], msg.linear.y))
        wz = max(-g["wmax"], min(g["wmax"], msg.angular.z))
        self.backend.set_command(self.kin.twist_to_modules(vx, vy, wz))

    def _on_estop(self, msg: Bool):
        self.backend.estop(msg.data)

    def _on_freewheel(self, msg: Bool):
        # ⚠ True 는 구동축 servo-off 라 **홀딩토크가 사라진다** — 경사에서는 차가 굴러간다.
        #   견인·정비 전용이며 주행 중에 부르는 경로가 있어서는 안 된다.
        self.backend.freewheel(msg.data)

    # ── 휠 오도메트리 ─────────────────────────────────────────────────────
    # 구동축 위치(0x6064) 변위와 조향각을 정기구학 최소자승으로 합쳐 (dx, dy, dyaw) 를 얻고,
    #   그것을 현재 yaw 로 회전시켜 자세에 누적한다. 속도를 시간 적분하는 것이 아니라
    #   **변위를 누적**하므로 주기 지터가 자세에 섞이지 않는다.
    # 절대 기준이 없어 오차는 계속 쌓인다 — 소비자(측위)는 절대값이 아니라 증분만 써야 한다.
    def _on_odom_timer(self):
        snap = self.backend.snapshot()
        nodes = snap["nodes"]
        cur = {n: nodes[n].pos for n in [m.drive_node for m in self.modules]}
        if any(v is None for v in cur.values()):
            return
        steer_rad = {}
        for m in self.modules:
            if m.steer_node is not None and nodes[m.steer_node].pos is not None:
                # ⚠ 호밍 중에는 0x6064 가 0 으로 오는데 이 식은 그것을 유효한 판독으로 받아
                #   큰 음의 조향각을 odom·joint_states 로 그대로 발행한다.
                #   상태워드 유효성(bit15) 게이트가 아직 없다(debt-007).
                steer_rad[m.drive_node] = (self._g["kin_steer_sign"]
                                           * (nodes[m.steer_node].pos - m.steer_home) / COUNTS_PER_RAD)
            else:
                steer_rad[m.drive_node] = 0.0
        if self._prev_pos is not None:
            meas = {}
            for n, pos in cur.items():
                ds = self._g["drive_sign"] * (pos - self._prev_pos[n]) / COUNTS_PER_M
                meas[n] = (ds, steer_rad[n])
            dx, dy, dyaw = self.kin.modules_to_twist(meas)
            x, y, yaw = self._pose
            c, s = math.cos(yaw), math.sin(yaw)
            self._pose = [x + c * dx - s * dy, y + s * dx + c * dy, yaw + dyaw]
        self._prev_pos = cur
        self._publish_odom(steer_rad, cur)

    def _publish_odom(self, steer_rad: dict, drive_pos: dict):
        now = self.get_clock().now().to_msg()
        x, y, yaw = self._pose
        od = Odometry()
        od.header.stamp = now
        od.header.frame_id = self._g["odom_frame"]
        od.child_frame_id = self._g["base_frame"]
        od.pose.pose.position.x = x
        od.pose.pose.position.y = y
        od.pose.pose.orientation.z = math.sin(yaw / 2.0)
        od.pose.pose.orientation.w = math.cos(yaw / 2.0)
        self.pub_odom.publish(od)
        if self.tf_bc is not None:
            tf = TransformStamped()
            tf.header.stamp = now
            tf.header.frame_id = self._g["odom_frame"]
            tf.child_frame_id = self._g["base_frame"]
            tf.transform.translation.x = x
            tf.transform.translation.y = y
            tf.transform.rotation.z = od.pose.pose.orientation.z
            tf.transform.rotation.w = od.pose.pose.orientation.w
            self.tf_bc.sendTransform(tf)
        js = JointState()
        js.header.stamp = now
        for m in self.modules:
            js.name.append(f"drive_{m.drive_node}_wheel")
            js.position.append(self._g["drive_sign"] * drive_pos[m.drive_node]
                               / COUNTS_PER_M / WHEEL_RADIUS)
            if m.steer_node is not None:
                js.name.append(f"steer_{m.steer_node}")
                js.position.append(steer_rad[m.drive_node])
        self.pub_js.publish(js)

    def _on_diag_timer(self):
        snap = self.backend.snapshot()
        da = DiagnosticArray()
        da.header.stamp = self.get_clock().now().to_msg()
        st = DiagnosticStatus(name="motor_control/bus", hardware_id=self._g["can_channel"])
        stale = [n for n, s in snap["nodes"].items() if s.last_seen == 0.0]
        errors = {n: s.error for n, s in snap["nodes"].items() if s.error}
        if snap["estop"]:
            st.level, st.message = DiagnosticStatus.ERROR, "E-STOP engaged"
        elif errors:
            st.level, st.message = DiagnosticStatus.ERROR, f"drive error codes: {errors}"
        elif snap.get("freewheel"):
            st.level, st.message = DiagnosticStatus.WARN, "freewheel engaged (drive servo-off, no holding torque)"
        elif stale:
            st.level, st.message = DiagnosticStatus.WARN, f"silent nodes: {stale}"
        elif snap["settling"]:
            st.level, st.message = DiagnosticStatus.WARN, "steering settling (drive held)"
        else:
            st.level, st.message = DiagnosticStatus.OK, "ok"
        st.values = [KeyValue(key="tx", value=str(snap["tx"])),
                     KeyValue(key="rx", value=str(snap["rx"]))]
        if snap.get("freewheel"):
            # 최상위 level(estop/error)에 가려지지 않도록 독립 신호로 항상 노출(안전 가시성)
            st.values.append(KeyValue(key="freewheel", value="ENGAGED - no holding torque"))
        for n, s in sorted(snap["nodes"].items()):
            status_txt = f"{s.status:#06x}" if s.status is not None else "?"
            st.values.append(KeyValue(
                key=f"node{n}",
                value=f"pos={s.pos} status={status_txt} err={s.error} "
                      f"cur={s.current} aborts={s.aborts}"))
        da.status.append(st)
        self.pub_diag.publish(da)

    def destroy_node(self):
        try:
            self.backend.shutdown()
        finally:
            super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    try:
        node = MotorControlNode()
    except Exception:
        rclpy.shutdown()  # 노드 생성(브링업 포함) 실패 시 rclpy 컨텍스트 정리
        raise
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():  # SIGTERM 등으로 이미 종료된 컨텍스트 이중 shutdown 방지
            rclpy.shutdown()


if __name__ == "__main__":
    main()
