#!/usr/bin/env python3
"""호밍과 조향 0° 복귀를 순서대로 수행하는 운용 클라이언트.

`~/home`(`std_srvs/Trigger`) 을 호출하고, **성공한 응답을 받은 경우에만** `~/steer_deg`
(`std_msgs/Float64`) 에 0.0 을 발행한 뒤 `joint_states` 로 두 조향축이 `tol_deg` 안에
들어오는지 확인한다. 호밍이 실패하면 0° 를 발행하지 않고 끝낸다.

0° 지령이 따로 필요한 이유: 호밍 완료는 **원점(리밋) 검출**을 뜻할 뿐 그 위치가 조향 0° 는
아니다. 0° 는 기체 캘리브레이션(`steer_home_counts`)이 정의하는 자리다.

사용:
    ros2 run can_relay home_and_zero --ros-args -p confirm:=true
    ros2 run can_relay home_and_zero --ros-args -p confirm:=true -p tol_deg:=0.1 -p timeout_s:=10.0

`confirm:=true` 없이는 아무 것도 요청하지 않는다 — 호밍은 조향을 100° 이상
스윙시키므로 이동구역 확인을 절차에 강제한다.

종료코드: 0 성공 · 2 호밍 실패(0° 미발행) · 3 0° 미도달 · 4 서비스 없음 ·
5 지령 미수용(드라이버가 0° 목표를 받지 않음) · 6 파라미터 무효 · 7 미확인(confirm 없음)
"""
from __future__ import annotations

STEER_NODES = (3, 4)
#   기본값일 뿐이다 — 실행 시 `steer_nodes` 파라미터가 이긴다(기체 YAML 과 맞출 것).
EXIT_OK, EXIT_HOME_FAILED, EXIT_ZERO_UNREACHED, EXIT_NO_SERVICE = 0, 2, 3, 4
EXIT_CMD_NOT_ACCEPTED, EXIT_BAD_PARAM, EXIT_NOT_CONFIRMED = 5, 6, 7
RESEND_PERIOD_S = 1.0
#   0° 지령 재발행 주기. 지령은 절대각이라 재발행이 멱등이다 — 1회 발행이 volatile 로
#   유실되거나 게이트에 버려진 경우를 대기 중에 스스로 복구한다.
TOL_MAX_DEG = 5.0
TIMEOUT_MAX_S = 300.0
FEEDBACK_TTL_S = 1.0
#   실측을 인정하는 최대 나이(초). ⚠ 선택값이며 실측 근거가 없다.


def validate_params(tol_deg, timeout_s) -> "str | None":
    """파라미터가 판정을 무의미하게 만들면 사유를 돌려준다. 유효하면 `None`.

    `tol_deg` 가 크면(예 180) 어떤 자세든 「복귀 완료」가 되고, 0·음수면 영구
    미도달이다. 검증은 호밍 요청 **전**에 한다 — 무효 파라미터로 축을 움직이지 않는다.
    """
    try:
        tol = float(tol_deg)
        to = float(timeout_s)
    except (TypeError, ValueError):
        return f"숫자가 아니다: tol_deg={tol_deg!r} timeout_s={timeout_s!r}"
    if not (0.0 < tol <= TOL_MAX_DEG):
        return f"tol_deg={tol} — (0, {TOL_MAX_DEG}] 범위여야 판정이 의미를 가진다"
    if not (0.0 < to <= TIMEOUT_MAX_S):
        return f"timeout_s={to} — (0, {TIMEOUT_MAX_S:.0f}] 범위여야 한다"
    return None


def steer_angles_from_joint_states(names, positions, steer_nodes) -> dict:
    """`joint_states` 한 장에서 축별 각도(도). **실리지 않은 축은 `None`** 이다.

    발행자가 믿을 수 없는 축을 빼고 보내는 경우, 그 축을 직전 값으로 채우면 그 보호가
    사라진다. 그래서 매 장마다 새로 구성한다 — 누적하지 않는다.
    이름 규약은 `steer_<node>` 이고 각도 단위는 라디안이다.
    """
    import math

    out = {int(n): None for n in steer_nodes}
    for name, pos in zip(names, positions):
        if not str(name).startswith("steer_"):
            continue
        try:
            n = int(str(name).split("_", 1)[1])
        except ValueError:
            continue
        if n in out:
            out[n] = math.degrees(float(pos))
    return out


def fresh_or_none(angles: dict, age_s, ttl_s: float) -> dict:
    """`age_s`(마지막 수신 이후 초)가 `ttl_s` 를 넘으면 전 축을 `None` 으로 만든다.

    `age_s` 가 `None` 이면 수신 이력이 없다는 뜻이라 역시 전 축 `None` 이다.
    낡은 값을 도달 판정에 쓰면 통신이 끊긴 뒤에도 「도달」이 성립한다.
    """
    if age_s is None or float(age_s) > float(ttl_s):
        return {n: None for n in angles}
    return dict(angles)


class ZeroReturnGuard:
    """호밍 → 0° 복귀 절차의 판정 로직. ROS 를 import 하지 않는다.

    입출력은 `client` 에 위임한다. `client` 가 갖춰야 할 것:

      · `service_available() -> bool`       — 호밍을 요청할 상대가 있는가
      · `call_home() -> (bool, str)`        — 호밍 수행 결과와 사유
      · `send_steer_zero() -> None`         — 조향 0° 지령 1회 발행
      · `steer_angles_deg() -> dict`        — {node: 각도(도) 또는 None}. None 은 실측 없음
      · `sleep(seconds) -> None`
      · `elapsed() -> float`                — 0° 지령 이후 경과(초, monotonic)
      · `steer_target_confirmed() -> bool|None` — 드라이버가 0° 목표를 물었는가
                                                  (`None` = 진단 미수신·판단 불가)
      · `log(msg) -> None`

    `tol_deg`(도)·`timeout_s`(초) 기본값은 **선택값이며 실측 근거가 없다.**
    """

    def __init__(self, client, tol_deg: float = 0.1, timeout_s: float = 10.0,
                 nodes=STEER_NODES):
        self.c = client
        self.tol = float(tol_deg)
        self.timeout = float(timeout_s)
        self.nodes = tuple(nodes)

    def run(self) -> int:
        """호밍 → 0° 지령 → 도달 확인. 반환은 모듈 상단의 종료코드.

        호밍이 실패하면 0° 를 발행하지 않는다 — 실패한 호밍 뒤의 축 위치는 알 수 없고,
        `~/steer_deg` 는 **절대각** 지령이라 현재 위치를 모른 채 보내면 이동량도 모른다.
        """
        if not self.c.service_available():
            self.c.log("호밍 서비스를 찾지 못했습니다 — can_relay_node 가 떠 있는지 확인하세요")
            return EXIT_NO_SERVICE
        ok, why = self.c.call_home()
        if not ok:
            self.c.log(f"호밍 실패 — 조향 0° 지령을 보내지 않습니다: {why}")
            return EXIT_HOME_FAILED
        self.c.log(f"호밍 성공 — {why}. 조향 0° 복귀 지령을 보냅니다")
        self.c.send_steer_zero()
        return self._await_zero()

    def _classify_timeout(self, missing, angles) -> int:
        """시한 초과의 사유를 가른다 — 미수용과 미도달은 다음 행동이 다르다.

        드라이버 진단의 `steer_target_deg` 가 0 이 아니면(또는 목표 자체가 없으면)
        지령이 게이트(E-stop·호밍 잠금 등)에 버려진 것이다 — 각도를 기다려 봐야
        소용없고, 드라이버 쪽 거부 사유를 봐야 한다.
        """
        accepted = self.c.steer_target_confirmed()
        if accepted is False:
            self.c.log("0° 지령이 드라이버에 수용되지 않았습니다 — 드라이버 진단의 "
                       "거부 사유(E-stop·호밍 잠금)를 확인하세요")
            return EXIT_CMD_NOT_ACCEPTED
        detail = (f"실측 없음 N{missing}" if missing else
                  ", ".join(f"N{n} {angles[n]:+.3f}°" for n in self.nodes))
        self.c.log(f"조향 0° 복귀 미확인 — {self.timeout:.0f}초 안에 "
                   f"±{self.tol:.3f}° 안에 들어오지 않았습니다 ({detail}). "
                   f"0° 지령은 반복 발행했습니다")
        return EXIT_ZERO_UNREACHED

    def _await_zero(self) -> int:
        """두 조향축이 0° ±`tol_deg` 안에 들어올 때까지 기다린다.

        도달로 인정하는 조건은 **모든 조향축의 실측이 있고 전부 허용치 안**이다.
        실측이 없는 축(`None`)은 도달로 치지 않는다.
        """
        last_send = self.c.elapsed()
        while True:
            angles = self.c.steer_angles_deg()
            missing = [n for n in self.nodes if angles.get(n) is None]
            if not missing and all(abs(angles[n]) <= self.tol for n in self.nodes):
                self.c.log("조향 0° 복귀 완료 — "
                           + ", ".join(f"N{n} {angles[n]:+.3f}°" for n in self.nodes))
                return EXIT_OK
            now = self.c.elapsed()
            if now > self.timeout:
                return self._classify_timeout(missing, angles)
            if now - last_send >= RESEND_PERIOD_S:
                # 절대각 0° 재발행은 멱등이다 — 유실·게이트 거부를 대기 중에 복구한다.
                self.c.send_steer_zero()
                last_send = now
            self.c.sleep(0.05)


class _RosClient:
    """`ZeroReturnGuard` 가 요구하는 것을 ROS 로 채운다."""

    def __init__(self, node, steer_nodes=STEER_NODES, target_node="can_relay_node",
                 diag_name_prefix="can_relay"):
        from diagnostic_msgs.msg import DiagnosticArray
        from sensor_msgs.msg import JointState
        from std_msgs.msg import Float64
        from std_srvs.srv import Trigger

        self.node = node
        self.steer_nodes = tuple(steer_nodes)
        self._diag_prefix = str(diag_name_prefix)
        self._angles: dict = {n: None for n in self.steer_nodes}
        self._angles_t = None      # 마지막 joint_states 수신 시각(monotonic)
        self._t0 = None            # 0° 대기 시계 기점(monotonic)
        self._diag_target = None   # 진단이 보고한 조향 목표(도). 미수신이면 None
        self._diag_seen = False
        self.cli_home = node.create_client(Trigger, f"{target_node}/home")
        self.pub_steer = node.create_publisher(Float64, f"{target_node}/steer_deg", 10)
        node.create_subscription(JointState, "joint_states", self._on_joint_states, 10)
        node.create_subscription(DiagnosticArray, "/diagnostics", self._on_diag, 10)

    def _on_joint_states(self, msg):
        """받은 한 장으로 축별 각도를 **통째로 교체**하고 수신 시각을 남긴다."""
        import time

        self._angles = steer_angles_from_joint_states(
            msg.name, msg.position, self.steer_nodes)
        self._angles_t = time.monotonic()

    def _on_diag(self, msg):
        """드라이버 진단에서 조향 목표(`steer_target_deg`)만 뽑는다."""
        for st in msg.status:
            if not str(st.name).startswith(self._diag_prefix):
                continue
            kv = {v.key: v.value for v in st.values}
            if "steer_target_deg" in kv:
                self._diag_seen = True
                try:
                    self._diag_target = float(kv["steer_target_deg"])
                except (TypeError, ValueError):
                    self._diag_target = None
            return

    def steer_target_confirmed(self):
        """드라이버가 0° 목표를 물고 있는가. 진단 미수신이면 `None`(모름)."""
        if not self._diag_seen:
            return None
        return self._diag_target is not None and abs(self._diag_target) < 1e-6

    def start_clock(self):
        import time
        self._t0 = time.monotonic()

    def elapsed(self) -> float:
        """0° 대기 경과(초). 신선도와 같은 `monotonic` 축을 쓴다.

        ROS 시계를 쓰면 `use_sim_time` 에서 `/clock` 이 없을 때 0 에 머물러
        `_await_zero` 의 유일한 탈출구(시한)가 사라진다.
        """
        import time
        if self._t0 is None:
            return 0.0
        return time.monotonic() - self._t0

    def service_available(self) -> bool:
        return self.cli_home.wait_for_service(timeout_sec=5.0)

    def call_home(self):
        from std_srvs.srv import Trigger
        fut = self.cli_home.call_async(Trigger.Request())
        import rclpy
        rclpy.spin_until_future_complete(self.node, fut, timeout_sec=300.0)
        if not fut.done() or fut.result() is None:
            return False, "`~/home` 응답이 오지 않았습니다"
        # 0° 대기 시계는 **호밍이 끝난 시점**부터 센다.
        self.start_clock()
        return bool(fut.result().success), str(fut.result().message)

    def send_steer_zero(self):
        from std_msgs.msg import Float64
        self.pub_steer.publish(Float64(data=0.0))

    def steer_angles_deg(self) -> dict:
        import time

        import rclpy
        rclpy.spin_once(self.node, timeout_sec=0.0)
        age = None if self._angles_t is None else time.monotonic() - self._angles_t
        return fresh_or_none(self._angles, age, FEEDBACK_TTL_S)

    def sleep(self, seconds: float):
        import rclpy
        rclpy.spin_once(self.node, timeout_sec=seconds)

    def log(self, msg: str):
        self.node.get_logger().info(msg)


def main(argv=None) -> int:
    import rclpy
    from rclpy.node import Node

    rclpy.init(args=argv)
    node = Node("home_and_zero")
    node.declare_parameter("tol_deg", 0.1)
    node.declare_parameter("timeout_s", 10.0)
    node.declare_parameter("confirm", False)
    node.declare_parameter("target_node", "can_relay_node")
    node.declare_parameter("steer_nodes", list(STEER_NODES))
    try:
        tol = node.get_parameter("tol_deg").value
        timeout = node.get_parameter("timeout_s").value
        why = validate_params(tol, timeout)
        if why is not None:
            node.get_logger().error(f"파라미터 무효 — 아무 것도 요청하지 않습니다: {why}")
            return EXIT_BAD_PARAM
        if not bool(node.get_parameter("confirm").value):
            node.get_logger().error(
                "확인 없음 — 호밍은 조향을 100° 이상 스윙시킵니다. 이동구역이 비어 "
                "있는지 확인한 뒤 `-p confirm:=true` 로 다시 실행하세요. "
                "아무 것도 요청하지 않았습니다")
            return EXIT_NOT_CONFIRMED
        steer_nodes = [int(n) for n in node.get_parameter("steer_nodes").value]
        if not steer_nodes:
            node.get_logger().error("steer_nodes 가 비었습니다 — 아무 것도 요청하지 않습니다")
            return EXIT_BAD_PARAM
        target = str(node.get_parameter("target_node").value)
        client = _RosClient(node, steer_nodes=steer_nodes, target_node=target)
        guard = ZeroReturnGuard(client, tol_deg=float(tol),
                                timeout_s=float(timeout), nodes=steer_nodes)
        node.get_logger().warn(
            f"호밍을 요청합니다({target}, 조향축 {steer_nodes}) — 조향이 100° 이상 "
            f"스윙합니다. 호밍이 성공한 경우에만 조향 0° 지령이 이어집니다")
        return guard.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
