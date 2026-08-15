#!/usr/bin/env python3
"""호밍 → 조향 0° 복귀를 순서대로 수행하는 운용 스크립트.

드라이버는 두 기능을 **따로** 노출한다 — `~/home`(호밍)과 `~/steer_deg`(조향 절대각).
호밍만으로는 축이 0° 에 서지 않는다: 펌웨어 시퀀서의 `GOZERO` 목표
(`safety_seer_gate.h` `SEER_HOME_ZERO_N3/N4` = 7882020 / 7859062)는 **호밍 후 정착값**이고
실측 0°(`steer_home_counts` = [7871815, 7840086])에서 **+0.178° / +0.331°** 떨어져 있다.
펌웨어 도달 허용오차가 1.0° 라 펌웨어는 그 편차를 검출하지 못한다.

그래서 둘을 이어서 쓴다. **이 스크립트가 존재하는 이유는 순서가 아니라 가드다.**

⚠ 드라이버는 호밍 실패를 조향 게이트로 막지 않는다.
  `RelayBackend.homed_effective()` 는 드라이브가 보고한 `0x6041` bit15 만으로도 True 를
  돌려준다. 따라서 호밍이 실패해도(`ERR_GOZERO` 등) `~/steer_deg` 는 **수리된다** —
  호밍이 `ERR_GOZERO` 로 끝나도 두 조향축 statusword 는 `0x9450`(bit15=1) 이고,
  복귀하지 못한 축은 `0x6064` 가 0 을 읽어 각도를 알 수 없다. 그 상태에서 절대위치
  지령이 나가면 축이 어디로 갈지 아무도 모른다.
  ⇒ **`~/home` 응답 success 가 False 면 0° 를 보내지 않는다.** 그것이 이 파일의 요지다.

사용:
    ros2 run can_relay home_and_zero
    ros2 run can_relay home_and_zero --ros-args -p tol_deg:=0.1 -p timeout_s:=10.0

종료코드: 0 성공 · 2 호밍 실패(0° 미발행) · 3 0° 미도달 · 4 서비스 없음
"""
from __future__ import annotations

STEER_NODES = (3, 4)
EXIT_OK, EXIT_HOME_FAILED, EXIT_ZERO_UNREACHED, EXIT_NO_SERVICE = 0, 2, 3, 4


class ZeroReturnGuard:
    """호밍 → 0° 복귀 절차의 판정 로직. **ROS 에 의존하지 않는다.**

    전송은 `client` 에 위임한다 — 그래야 「호밍 실패 시 0° 를 보내지 않는다」를
    하드웨어·ROS 없이 회귀로 고정할 수 있다. `client` 가 갖춰야 할 것:

      · `call_home() -> (bool, str)`        — `~/home` 호출 결과
      · `send_steer_zero() -> None`         — `~/steer_deg` 에 0.0 발행
      · `steer_angles_deg() -> dict`        — {node: deg 또는 None}, joint_states 유래
      · `sleep(seconds) -> None`
      · `elapsed() -> float`                — 절차 시작 이후 경과 초
      · `log(msg) -> None`
    """

    def __init__(self, client, tol_deg: float = 0.1, timeout_s: float = 10.0,
                 nodes=STEER_NODES):
        self.c = client
        self.tol = float(tol_deg)
        self.timeout = float(timeout_s)
        self.nodes = tuple(nodes)

    def run(self) -> int:
        """절차 전체. 반환은 종료코드."""
        ok, why = self.c.call_home()
        if not ok:
            # ⚠ 여기서 멈추는 것이 이 스크립트의 전부다. 드라이버는 막아주지 않는다.
            self.c.log(f"호밍 실패 — 조향 0° 지령을 보내지 않습니다: {why}")
            return EXIT_HOME_FAILED
        self.c.log(f"호밍 성공 — {why}. 조향 0° 복귀 지령을 보냅니다")
        self.c.send_steer_zero()
        return self._await_zero()

    def _await_zero(self) -> int:
        """두 조향축이 `tol_deg` 안에 들어올 때까지 기다린다.

        **실측이 없는 축은 도달로 치지 않는다** — 모르는 것을 도달로 적으면
        그 다음 구동이 열린다.
        """
        while True:
            angles = self.c.steer_angles_deg()
            missing = [n for n in self.nodes if angles.get(n) is None]
            if not missing and all(abs(angles[n]) <= self.tol for n in self.nodes):
                self.c.log("조향 0° 복귀 완료 — "
                           + ", ".join(f"N{n} {angles[n]:+.3f}°" for n in self.nodes))
                return EXIT_OK
            if self.c.elapsed() > self.timeout:
                detail = (f"실측 없음 N{missing}" if missing else
                          ", ".join(f"N{n} {angles[n]:+.3f}°" for n in self.nodes))
                self.c.log(f"조향 0° 복귀 미확인 — {self.timeout:.0f}초 안에 "
                           f"±{self.tol:.3f}° 안에 들어오지 않았습니다 ({detail}). "
                           f"목표는 걸려 있으므로 축이 계속 움직이는 중일 수 있습니다")
                return EXIT_ZERO_UNREACHED
            self.c.sleep(0.05)


class _RosClient:
    """`ZeroReturnGuard` 가 요구하는 것을 ROS 로 채운다."""

    def __init__(self, node, steer_nodes=STEER_NODES):
        import math

        from sensor_msgs.msg import JointState
        from std_msgs.msg import Float64
        from std_srvs.srv import Trigger

        self._math = math
        self.node = node
        self.steer_nodes = tuple(steer_nodes)
        self._angles: dict = {n: None for n in self.steer_nodes}
        self._t0 = None
        self.cli_home = node.create_client(Trigger, "can_relay_node/home")
        self.pub_steer = node.create_publisher(Float64, "can_relay_node/steer_deg", 10)
        node.create_subscription(JointState, "joint_states", self._on_joint_states, 10)

    def _on_joint_states(self, msg):
        """`steer_<node>` 이름으로 실린 축만 읽는다(라디안 → 도)."""
        for name, pos in zip(msg.name, msg.position):
            if not name.startswith("steer_"):
                continue
            try:
                n = int(name.split("_", 1)[1])
            except ValueError:
                continue
            if n in self._angles:
                self._angles[n] = self._math.degrees(pos)

    def start_clock(self):
        self._t0 = self.node.get_clock().now()

    def elapsed(self) -> float:
        if self._t0 is None:
            return 0.0
        return (self.node.get_clock().now() - self._t0).nanoseconds / 1e9

    def call_home(self):
        from std_srvs.srv import Trigger
        if not self.cli_home.wait_for_service(timeout_sec=5.0):
            return False, "`~/home` 서비스가 없습니다 — can_relay_node 가 떠 있는지 확인하세요"
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
        import rclpy
        rclpy.spin_once(self.node, timeout_sec=0.0)
        return dict(self._angles)

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
    try:
        client = _RosClient(node)
        guard = ZeroReturnGuard(
            client,
            tol_deg=float(node.get_parameter("tol_deg").value),
            timeout_s=float(node.get_parameter("timeout_s").value))
        node.get_logger().warn(
            "호밍을 요청합니다 — 조향이 100° 이상 스윙합니다. 이동구역이 비어 있는지 "
            "먼저 확인하세요. 호밍이 성공한 경우에만 조향 0° 지령이 이어집니다")
        return guard.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
