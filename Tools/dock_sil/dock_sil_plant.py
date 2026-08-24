#!/usr/bin/env python3
"""도킹 폐루프 SIL 플랜트 — 지령 소비 → 가상 로봇 적분 → 벽 스캔 재생성.

전 체인: 본 플랜트(/dock_sil/scan) → wall_localizer(/dock_sil/wall_pose)
       → dock_approach_action_server(/dock_sil/wheel_cmd) → 본 플랜트.
전 토픽·서비스가 /dock_sil/* — 실기 체인과 격리(리맵은 run_dock_sil.sh 소관).

플랜트 모형 (스테이션 프레임, 인라인 듀얼스티어 y=0):
  바퀴 i 속도벡터 (v_i cos a_i, v_i sin a_i), 위치 (±arm, 0)
  순기구학: vx = (vf·cos af + vr·cos ar)/2
            vy = (vf·sin af + vr·sin ar)/2
            ω  = (vf·sin af − vr·sin ar)/(2·arm)
  조향은 슬루 제한 1차 동특성(57.1 °/s — 2WS SIL 플랜트 실측치), 속도는 즉응.
  잡음: 거리 방향 가우시안 σ=2 mm (실기 SICK 적합 잔차 실측).
"""
import argparse
import json
import math
import random

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from trnav_msgs.msg import WheelSetArray
from trnav_msgs.srv import SelectMotionSource

WALLS = [((2.0, -1.5), (2.0, 1.5)),   # front
         ((0.0, 1.5), (2.0, 1.5)),    # left
         ((0.0, -1.5), (2.0, -1.5))]  # right
N_BEAMS = 1441
ANGLE_MIN = -math.pi
ANGLE_INC = 2.0 * math.pi / N_BEAMS
RANGE_MAX = 10.0
SCAN_HZ = 30.0
SUBSTEPS = 4                 # 적분 부스텝 (dt = 1/30/4)
STEER_SLEW_DPS = 57.1        # 조향 슬루 (deg/s)


def raycast(ox, oy, dx, dy):
    best = float("inf")
    for (p1, p2) in WALLS:
        vx, vy = p2[0] - p1[0], p2[1] - p1[1]
        det = vx * dy - vy * dx
        if abs(det) < 1e-12:
            continue
        qx, qy = p1[0] - ox, p1[1] - oy
        r = (vx * qy - vy * qx) / det
        t = (dx * qy - dy * qx) / det
        if r > 1e-6 and 0.0 <= t <= 1.0 and r < best:
            best = r
    return best


class DockSilPlant(Node):
    def __init__(self, args):
        super().__init__("dock_sil_plant")
        self.x, self.y, self.yaw = args.x0, args.y0, math.radians(args.yaw0_deg)
        self.arm = args.arm_m
        self.sigma = args.sigma_m
        self.rng = random.Random(args.seed)
        self.log = open(args.truth_log, "w") if args.truth_log else None

        # 지령 상태 (수신값) 와 실효 조향 (슬루 적용)
        self.cmd = (0.0, 0.0, 0.0, 0.0)  # vf, af, vr, ar
        self.af_act = 0.0
        self.ar_act = 0.0

        self.create_subscription(WheelSetArray, "/dock_sil/wheel_cmd", self.on_cmd, 10)
        self.scan_pub = self.create_publisher(LaserScan, "/dock_sil/scan", 10)
        self.create_service(SelectMotionSource, "/dock_sil/select_motion_source", self.on_select)
        self.create_timer(1.0 / SCAN_HZ, self.tick)
        self.get_logger().info(
            f"plant 시작 — 초기 ({self.x:.3f}, {self.y:.3f}, {math.degrees(self.yaw):.1f}°)")

    def on_select(self, req, res):
        res.success = True
        res.message = f"sil: source {req.source_id}"
        return res

    def on_cmd(self, m):
        if len(m.wheels) >= 2:
            self.cmd = (m.wheels[0].velocity, m.wheels[0].steering,
                        m.wheels[1].velocity, m.wheels[1].steering)

    def tick(self):
        dt = 1.0 / SCAN_HZ / SUBSTEPS
        vf, af_t, vr, ar_t = self.cmd
        slew = math.radians(STEER_SLEW_DPS) * dt
        for _ in range(SUBSTEPS):
            self.af_act += max(-slew, min(slew, af_t - self.af_act))
            self.ar_act += max(-slew, min(slew, ar_t - self.ar_act))
            vx = 0.5 * (vf * math.cos(self.af_act) + vr * math.cos(self.ar_act))
            vy = 0.5 * (vf * math.sin(self.af_act) + vr * math.sin(self.ar_act))
            w = (vf * math.sin(self.af_act) - vr * math.sin(self.ar_act)) / (2.0 * self.arm)
            c, s = math.cos(self.yaw), math.sin(self.yaw)
            self.x += (c * vx - s * vy) * dt
            self.y += (s * vx + c * vy) * dt
            self.yaw += w * dt

        # 라이다 스캔 재생성 (base_link = 라이다 프레임 — /scan_merged 항등 TF 와 동일 규약)
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "dock_sil_scan"
        msg.angle_min = ANGLE_MIN
        msg.angle_max = ANGLE_MIN + (N_BEAMS - 1) * ANGLE_INC
        msg.angle_increment = ANGLE_INC
        msg.range_min = 0.05
        msg.range_max = RANGE_MAX
        ranges = []
        for i in range(N_BEAMS):
            a = ANGLE_MIN + i * ANGLE_INC
            dx = math.cos(self.yaw + a)
            dy = math.sin(self.yaw + a)
            r = raycast(self.x, self.y, dx, dy)
            if r <= RANGE_MAX:
                ranges.append(r + (self.rng.gauss(0.0, self.sigma) if self.sigma > 0 else 0.0))
            else:
                ranges.append(float("inf"))
        msg.ranges = ranges
        self.scan_pub.publish(msg)

        if self.log:
            self.log.write(json.dumps({
                "t": msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
                "x": self.x, "y": self.y, "yaw_deg": math.degrees(self.yaw),
                "vf": vf, "af_deg": math.degrees(self.af_act),
                "vr": vr, "ar_deg": math.degrees(self.ar_act)}) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--x0", type=float, default=0.4)
    ap.add_argument("--y0", type=float, default=0.1)
    ap.add_argument("--yaw0-deg", type=float, default=2.0)
    ap.add_argument("--arm-m", type=float, default=0.6039)
    ap.add_argument("--sigma-m", type=float, default=0.002)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--truth-log", default="")
    args = ap.parse_args()
    rclpy.init()
    n = DockSilPlant(args)
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    if n.log:
        n.log.flush()
        n.log.close()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
