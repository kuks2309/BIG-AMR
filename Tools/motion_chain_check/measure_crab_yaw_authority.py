#!/usr/bin/env python3
"""크랩의 yaw 보정 권한을 측정한다 — 조향 차동이 실제로 얼마의 회전을 만드는가.

크랩은 omega 가 아니라 **전/후 조향 차동**(delta_heading)으로 yaw 를 보정한다
(crab_linear_action_server.cpp:624-628). 그 차동이 만드는 회전은 inline 2WS 정기구학상

    omega = v(sin θ_f - sin θ_r) / (x_f - x_r)

이고, sin 은 90도 근처에서 평평하다 — 즉 **측면 크랩(θ≈90도)일수록 같은 차동이 만드는
회전이 작아진다.** 그것이 실제로 얼마인지 지령·자세를 동시에 받아 잰다.
"""
import math
import re
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
from trnav_msgs.msg import WheelSetArray

WB = 0.6039 - (-0.5961)   # 휠베이스 1.200 m (정본)


class M(Node):
    def __init__(self):
        super().__init__("crab_yaw_meas")
        self.cmd = []
        self.yaw = []
        self.create_subscription(WheelSetArray, "/motion/wheel_cmd/crab_linear", self._c, 10)
        # /imu/data 는 SensorDataQoS(BEST_EFFORT) — 기본 RELIABLE 로 구독하면
        # RxO 불일치로 **한 건도 못 받는다**(실측: 자세 표본 0).
        self.create_subscription(Imu, "/imu/data", self._i, qos_profile_sensor_data)

    def _c(self, m):
        t = self.get_clock().now().nanoseconds * 1e-9
        if len(m.wheels) >= 2:
            self.cmd.append((t, m.wheels[0].steering, m.wheels[1].steering,
                             m.wheels[0].velocity))

    def _i(self, m):
        t = self.get_clock().now().nanoseconds * 1e-9
        self.yaw.append((t, 2.0 * math.atan2(m.orientation.z, m.orientation.w)))


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0
    rclpy.init()
    n = M()
    t0 = n.get_clock().now().nanoseconds * 1e-9
    while rclpy.ok() and (n.get_clock().now().nanoseconds * 1e-9 - t0) < secs:
        rclpy.spin_once(n, timeout_sec=0.1)
    cmd, yaw = n.cmd, n.yaw
    n.destroy_node()
    rclpy.shutdown()

    if not cmd:
        print("지령 표본 0 — 액션이 실행되지 않았다")
        return 1
    print(f"지령 표본 {len(cmd):,} · 자세 표본 {len(yaw):,} · 구간 {cmd[-1][0]-cmd[0][0]:.1f} s")
    print()
    d = [math.degrees(a - b) for _t, a, b, _v in cmd]
    f = [math.degrees(a) for _t, a, _b, _v in cmd]
    print(f"  전륜 조향   {min(f):+7.2f}° ~ {max(f):+7.2f}°")
    print(f"  전/후 차동  {min(d):+7.3f}° ~ {max(d):+7.3f}°  (평균 {sum(d)/len(d):+.3f}°)")
    print()
    # 차동이 만드는 이론 회전
    om = [v * (math.sin(a) - math.sin(b)) / WB for _t, a, b, v in cmd]
    om_d = [math.degrees(o) for o in om]
    print(f"  이론 ω = v(sinθf − sinθr)/L  →  {min(om_d):+.4f} ~ {max(om_d):+.4f} °/s "
          f"(평균 {sum(om_d)/len(om_d):+.4f})")
    if len(yaw) > 2:
        dt = yaw[-1][0] - yaw[0][0]
        dy = math.degrees(yaw[-1][1] - yaw[0][1])
        print(f"  실측 yaw   {math.degrees(yaw[0][1]):+.3f}° → {math.degrees(yaw[-1][1]):+.3f}° "
              f"({dy:+.3f}° / {dt:.1f} s = {dy/max(dt,1e-9):+.4f} °/s)")
    print()
    # 같은 차동이 직진 자세(θ≈0)였다면
    avg_d = sum(d) / len(d)
    avg_v = sum(abs(v) for _t, _a, _b, v in cmd) / len(cmd)
    om_straight = math.degrees(avg_v * math.sin(math.radians(avg_d)) / WB)
    print(f"  같은 차동({avg_d:+.3f}°)이 **직진 자세**였다면 ω ≈ {om_straight:+.4f} °/s")
    cur = sum(om_d) / len(om_d)
    if abs(cur) > 1e-9:
        print(f"  → 측면 크랩의 yaw 권한은 직진 대비 약 {abs(om_straight/cur):.0f}배 작다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
