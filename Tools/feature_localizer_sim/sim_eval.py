#!/usr/bin/env python3
"""feature_localizer 시나리오 시뮬레이션 평가.

U자 스테이션(전방 x=2, 좌·우 y=±1.5, 구간 x∈[0,2])의 합성 LaserScan 을 발행하고,
feature_localizer_node 의 /feature_pose·진단을 스캔 스탬프로 페어링해 오차 통계를 낸다.
참값 궤적은 해석식이라 시뮬레이터 내부에서 정확히 안다 — 별도 truth 토픽 불요.

단위: m·rad 내부 단일 (출력 요약의 yaw 는 deg).
실행: python3 sim_eval.py --scenario S3 --trajectory approach --sigma 0.01 ...
"""
import argparse
import json
import math
import os
import random

import rclpy
from geometry_msgs.msg import PoseStamped
from diagnostic_msgs.msg import DiagnosticArray
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

# 기준 특징면 (config/feature_localizer.yaml 의 예시 스테이션과 동일해야 한다)
REF_WALLS = [((2.0, -1.5), (2.0, 1.5)),   # front
             ((0.0, 1.5), (2.0, 1.5)),    # left
             ((0.0, -1.5), (2.0, -1.5))]  # right
LASER_IN_BASE = (0.3, 0.0, 0.0)
N_BEAMS = 720
ANGLE_MIN = -math.pi
ANGLE_INC = 2.0 * math.pi / N_BEAMS
RANGE_MAX = 10.0

# 클러터(비기준 물체): 좌측 벽 앞 0.3 m 의 평행 판재 + 전방 시야 안의 작은 상자 모서리.
# 좌측 판재는 대응 게이트(거리 0.3 m) 경계에 걸리는 적대 사례다.
CLUTTER_WALLS = [((1.0, 1.2), (1.4, 1.2)),
                 ((1.3, -0.6), (1.3, -0.3))]


def truth_at(t, trajectory):
    """시각 t[s]의 참값 base_link 자세 (스테이션 프레임, m·rad)."""
    if trajectory == "static":
        return (0.5, 0.1, math.radians(2.0))
    if trajectory == "offset":  # 초기 추정(0.4,0,0°)에서 일부러 벗어난 정지 자세
        return (0.55, -0.12, math.radians(-4.0))
    # approach: 도킹 접근 — x 전진 + 횡오차/헤딩 지수 수렴
    x = 0.4 + 0.05 * t
    y = 0.12 * math.exp(-t / 5.0)
    yaw = math.radians(3.0) * math.exp(-t / 5.0)
    return (x, y, yaw)


def raycast(features, ox, oy, dx, dy):
    """원점(ox,oy)·방향(dx,dy) 빔의 최근접 교차 (거리, 벽 인덱스). 미충돌 = (inf, -1)."""
    best, hit = float("inf"), -1
    for i, (p1, p2) in enumerate(features):
        vx, vy = p2[0] - p1[0], p2[1] - p1[1]
        det = vx * dy - vy * dx
        if abs(det) < 1e-12:
            continue
        qx, qy = p1[0] - ox, p1[1] - oy
        r = (vx * qy - vy * qx) / det
        s = (dx * qy - dy * qx) / det
        if r > 1e-6 and 0.0 <= s <= 1.0 and r < best:
            best, hit = r, i
    return best, hit


class SimEval(Node):
    def __init__(self, args):
        super().__init__("wl_sim_eval")
        self.args = args
        self.rng = random.Random(args.seed)
        self.features = list(REF_WALLS) + (CLUTTER_WALLS if args.clutter else [])
        self.scan_pub = self.create_publisher(LaserScan, "/wl_sim_scan", 10)
        self.pose_sub = self.create_subscription(PoseStamped, "/feature_pose", self.on_pose, 10)
        self.diag_sub = self.create_subscription(DiagnosticArray, "/feature_localizer/diagnostics",
                                                 self.on_diag, 10)
        self.truth_by_stamp = {}
        self.records = []
        self.diag_records = []
        self.diag_counts = {"OK": 0, "DEGRADED": 0, "LOST": 0}
        self.first_fix_scan = None
        self.n_scans = 0
        self.t = 0.0
        self.dt = 1.0 / args.rate
        self.warmup_deadline = self.get_clock().now().nanoseconds / 1e9 + 10.0
        self.timer = self.create_timer(self.dt, self.tick)
        self.done = False

    # 구독자(측위 노드)가 붙기 전에는 시뮬레이션 시간을 진행하지 않는다.
    def tick(self):
        if self.scan_pub.get_subscription_count() < 1:
            if self.get_clock().now().nanoseconds / 1e9 > self.warmup_deadline:
                self.get_logger().error("측위 노드가 /wl_sim_scan 을 구독하지 않음 — 중단")
                self.done = True
            return
        if self.t > self.args.duration:
            self.done = True
            return
        x, y, yaw = truth_at(self.t, self.args.trajectory)
        c, s = math.cos(yaw), math.sin(yaw)
        lx, ly, lyaw = LASER_IN_BASE
        ox, oy, oyaw = x + c * lx - s * ly, y + s * lx + c * ly, yaw + lyaw

        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "laser_sim"
        msg.angle_min = ANGLE_MIN
        msg.angle_max = ANGLE_MIN + (N_BEAMS - 1) * ANGLE_INC
        msg.angle_increment = ANGLE_INC
        msg.range_min = 0.05
        msg.range_max = RANGE_MAX
        ranges = []
        for i in range(N_BEAMS):
            a = ANGLE_MIN + i * ANGLE_INC
            dx, dy = math.cos(oyaw + a), math.sin(oyaw + a)
            r, hit = raycast(self.features, ox, oy, dx, dy)
            if self.args.occlude_wall >= 0 and hit == self.args.occlude_wall:
                r = float("inf")
            if r <= RANGE_MAX:
                if self.args.sigma > 0.0:
                    r += self.rng.gauss(0.0, self.args.sigma)
                ranges.append(r)
            else:
                ranges.append(float("inf"))
        msg.ranges = ranges

        stamp_ns = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
        self.truth_by_stamp[stamp_ns] = (x, y, yaw)
        self.n_scans += 1
        self.scan_pub.publish(msg)
        self.t += self.dt

    def on_pose(self, msg):
        stamp_ns = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
        truth = self.truth_by_stamp.get(stamp_ns)
        if truth is None:
            return
        yaw = 2.0 * math.atan2(msg.pose.orientation.z, msg.pose.orientation.w)
        ex = msg.pose.position.x - truth[0]
        ey = msg.pose.position.y - truth[1]
        eyaw = math.atan2(math.sin(yaw - truth[2]), math.cos(yaw - truth[2]))
        if self.first_fix_scan is None:
            self.first_fix_scan = self.n_scans
        self.records.append({"stamp_ns": stamp_ns, "ex_m": ex, "ey_m": ey,
                             "eyaw_deg": math.degrees(eyaw)})

    def on_diag(self, msg):
        stamp_ns = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
        for st in msg.status:
            if st.name == "feature_localizer":
                parts = st.message.split(":", 1)
                key = parts[0].strip()
                if key in self.diag_counts:
                    self.diag_counts[key] += 1
                rec = {"stamp_ns": stamp_ns, "status": key,
                       "reason": parts[1].strip() if len(parts) > 1 else ""}
                truth = self.truth_by_stamp.get(stamp_ns)
                if truth is not None:
                    rec["truth"] = [truth[0], truth[1], math.degrees(truth[2])]
                rec.update({kv.key: kv.value for kv in st.values})
                self.diag_records.append(rec)

    def summary(self):
        n = len(self.records)
        if n == 0:
            return {"scenario": self.args.scenario, "n_scans": self.n_scans, "n_fix": 0,
                    "fix_rate": 0.0, "diag": self.diag_counts, "note": "no fixes"}
        exy = [math.hypot(r["ex_m"], r["ey_m"]) for r in self.records]
        eyaw = [abs(r["eyaw_deg"]) for r in self.records]
        exy_s = sorted(exy)
        eyaw_s = sorted(eyaw)
        return {
            "scenario": self.args.scenario,
            "trajectory": self.args.trajectory,
            "sigma_m": self.args.sigma,
            "occlude_wall": self.args.occlude_wall,
            "clutter": self.args.clutter,
            "n_scans": self.n_scans,
            "n_fix": n,
            "fix_rate": n / max(1, self.n_scans),
            "first_fix_scan": self.first_fix_scan,
            "xy_rmse_m": math.sqrt(sum(e * e for e in exy) / n),
            "xy_p95_m": exy_s[int(0.95 * (n - 1))],
            "xy_max_m": exy_s[-1],
            "yaw_rmse_deg": math.sqrt(sum(e * e for e in eyaw) / n),
            "yaw_max_deg": eyaw_s[-1],
            "diag": self.diag_counts,
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--trajectory", default="static", choices=["static", "approach", "offset"])
    ap.add_argument("--sigma", type=float, default=0.0)
    ap.add_argument("--duration", type=float, default=15.0)
    ap.add_argument("--rate", type=float, default=20.0)
    ap.add_argument("--occlude-wall", type=int, default=-1,
                    help="가릴 기준 특징면 인덱스 (0=front,1=left,2=right, -1=없음)")
    ap.add_argument("--clutter", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", default="Log/feature_localizer_sim")
    args = ap.parse_args()

    rclpy.init()
    node = SimEval(args)
    while rclpy.ok() and not node.done:
        rclpy.spin_once(node, timeout_sec=0.1)
    # 마지막 스캔의 응답이 도착할 시간을 준다
    end = node.get_clock().now().nanoseconds / 1e9 + 0.5
    while node.get_clock().now().nanoseconds / 1e9 < end:
        rclpy.spin_once(node, timeout_sec=0.05)

    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, f"{args.scenario}.jsonl"), "w") as f:
        for r in node.records:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(args.out_dir, f"{args.scenario}_diag.jsonl"), "w") as f:
        for r in node.diag_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summ = node.summary()
    with open(os.path.join(args.out_dir, f"{args.scenario}_summary.json"), "w") as f:
        json.dump(summ, f, indent=2, ensure_ascii=False)
    print(json.dumps(summ, ensure_ascii=False))
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
