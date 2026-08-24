#!/usr/bin/env python3
"""노드(경유점) 간 주행 실행기 — FAT 시나리오 1 의 조립 계층.

검증된 액션의 orchestration 만 한다(신규 제어 수식 0):
  레그마다  spin(진행 헤딩 정렬, heading=keep 이면 생략)
          → crab_linear(map 프레임 현재→노드 직선, target_yaw 유지, 레그별 속도)
  경로 끝  dock 스펙이 있으면 AMRMotionDockApproach 로 정밀 도킹 전환
          (⚠ dock.target 은 스테이션 프레임 — 노드의 map 프레임과 다르다.
           전환 성립 조건: 마지막 노드가 wall_localizer 초기 게이트 ±0.3 m/±10° 안)

노드 소스: Seer smap advancedPointList(LocationMark) 기본, route yaml 의 nodes 로 오버라이드.
자세 소스: /robot_pose (실기: mcl2d → sil_pose_adapter 리맵 브리지 / SIL: 공유 플랜트).
사용: run_route.py --route route.yaml [--smap map/xxx.smap] [--dry-run] [--skip-dock]
"""
import argparse
import json
import math
import sys
import time

import rclpy
import yaml
from rclpy.action import ActionClient
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped

from trnav_2ws_interfaces.action import (AMRMotionCrabLinear, AMRMotionDockApproach,
                                         AMRMotionSpin)


def wrap_deg(a):
    return (a + 180.0) % 360.0 - 180.0


def load_nodes_smap(path):
    d = json.load(open(path))
    out = {}
    for p in d.get('advancedPointList', []):
        if p.get('className') != 'LocationMark':
            continue
        pos = p.get('pos', {})
        out[p.get('instanceName', '?')] = (pos.get('x', 0.0), pos.get('y', 0.0),
                                           p.get('dir', 0.0))
    return out


def load_route(path):
    d = yaml.safe_load(open(path))
    nodes = {k: (v['x'], v['y'], math.radians(v.get('yaw_deg', 0.0)))
             for k, v in (d.get('nodes') or {}).items()}
    legs = d.get('route') or []
    dock = d.get('dock')
    return nodes, legs, dock


class RouteRunner(Node):
    def __init__(self):
        super().__init__('waypoint_route_runner')
        self.pose = None
        self.create_subscription(PoseStamped, '/robot_pose', self._on_pose, 10)
        self.spin_cli = ActionClient(self, AMRMotionSpin, 'amr_motion_spin_abstract')
        self.crab_cli = ActionClient(self, AMRMotionCrabLinear, 'amr_motion_crab_linear_abstract')
        self.dock_cli = ActionClient(self, AMRMotionDockApproach, 'amr_motion_dock_approach')

    def _on_pose(self, m):
        yaw = 2.0 * math.atan2(m.pose.orientation.z, m.pose.orientation.w)
        self.pose = (m.pose.position.x, m.pose.position.y, yaw)

    def wait_pose(self, timeout_s=10.0):
        t0 = time.time()
        while self.pose is None and time.time() - t0 < timeout_s:
            rclpy.spin_once(self, timeout_sec=0.2)
        return self.pose is not None

    def _run_action(self, cli, goal, label, timeout_s):
        if not cli.wait_for_server(timeout_sec=5.0):
            self.get_logger().error(f'{label}: 액션 서버 없음')
            return None
        fut = cli.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=10.0)
        gh = fut.result()
        if gh is None or not gh.accepted:
            self.get_logger().error(f'{label}: goal 거부')
            return None
        rfut = gh.get_result_async()
        t0 = time.time()
        while not rfut.done():
            rclpy.spin_once(self, timeout_sec=0.2)
            if time.time() - t0 > timeout_s:
                self.get_logger().error(f'{label}: 결과 대기 시간 초과 — 취소 요청')
                gh.cancel_goal_async()
                return None
        return rfut.result().result

    def spin_to(self, dyaw_deg, spec):
        goal = AMRMotionSpin.Goal()
        goal.target_angle = float(dyaw_deg)
        goal.max_angular_speed = float(spec.get('spin_speed_dps', 10.0))
        goal.angular_acceleration = float(spec.get('spin_accel_dps2', 10.0))
        goal.hold_steer = False
        goal.exit_steer_angle = 0.0
        res = self._run_action(self.spin_cli, goal, f'spin {dyaw_deg:+.1f}°', 120.0)
        return res is not None and res.status == 0

    def crab_to(self, cur, node_xy, heading_deg, spec):
        goal = AMRMotionCrabLinear.Goal()
        goal.start_x, goal.start_y = float(cur[0]), float(cur[1])
        goal.end_x, goal.end_y = float(node_xy[0]), float(node_xy[1])
        goal.target_yaw_deg = float(heading_deg)
        goal.max_linear_speed = float(spec.get('max_speed', 0.3))
        goal.acceleration = float(spec.get('accel', 0.3))
        goal.hold_steer = False
        goal.exit_steer_angle = 0.0
        goal.exit_speed = 0.0
        goal.entry_speed = 0.0
        goal.has_next = False
        goal.enable_localization_watchdog = bool(spec.get('watchdog', True))
        dist = math.hypot(node_xy[0] - cur[0], node_xy[1] - cur[1])
        res = self._run_action(self.crab_cli, goal,
                               f"crab→({node_xy[0]:.2f},{node_xy[1]:.2f}) {dist:.2f}m", 300.0)
        return res is not None and res.status == 0

    def dock(self, spec):
        goal = AMRMotionDockApproach.Goal()
        t = spec['target']
        goal.target_x_m = float(t['x'])
        goal.target_y_m = float(t['y'])
        goal.target_yaw_deg = float(t.get('yaw_deg', 0.0))
        goal.approach_axis_deg = float(spec.get('axis_deg', 0.0))
        goal.max_speed_mps = float(spec.get('max_speed', 0.15))
        tol = spec.get('tol', {})
        goal.tol_d_mm = float(tol.get('d_mm', 3.0))
        goal.tol_lat_mm = float(tol.get('lat_mm', 3.0))
        goal.tol_yaw_deg = float(tol.get('yaw_deg', 0.5))
        goal.timeout_s = float(spec.get('timeout_s', 90.0))
        res = self._run_action(self.dock_cli, goal, '정밀 도킹', goal.timeout_s + 20.0)
        if res is None:
            return False
        self.get_logger().info(
            f'도킹 결과: success={res.success} reason={res.stop_reason} '
            f'd={res.final_e_d_mm:.1f} lat={res.final_e_lat_mm:.1f} mm yaw={res.final_e_yaw_deg:.2f}°')
        return bool(res.success)

    def run(self, nodes, legs, dock_spec, spin_tol_deg, dry):
        if not dry and not self.wait_pose():
            self.get_logger().error('/robot_pose 없음 — 측위 체인부터 확인')
            return False
        for i, leg in enumerate(legs, 1):
            name = leg['to']
            if name not in nodes:
                self.get_logger().error(f'미정의 노드: {name}')
                return False
            nx, ny, ndir = nodes[name]
            cur = self.pose if not dry else (nodes[legs[i - 2]['to']][:2] + (0.0,)
                                             if i > 1 else (0.0, 0.0, 0.0))
            heading = math.degrees(math.atan2(ny - cur[1], nx - cur[0]))
            keep = leg.get('heading') == 'keep'
            hdg_cmd = math.degrees(cur[2]) if keep else heading
            dyaw = wrap_deg(heading - math.degrees(cur[2]))
            plan = (f"[{i}/{len(legs)}] → {name} ({nx:.2f},{ny:.2f}) "
                    f"거리 {math.hypot(nx-cur[0], ny-cur[1]):.2f} m · "
                    f"{'측방(heading 유지)' if keep else f'회전 {dyaw:+.1f}° 후 전진'} · "
                    f"v={leg.get('max_speed', 0.3)} m/s a={leg.get('accel', 0.3)}")
            self.get_logger().info(plan)
            if dry:
                continue
            if not keep and abs(dyaw) > spin_tol_deg:
                if not self.spin_to(dyaw, leg):
                    return False
                rclpy.spin_once(self, timeout_sec=0.5)
                cur = self.pose
            if not self.crab_to(cur, (nx, ny), hdg_cmd, leg):
                return False
            rclpy.spin_once(self, timeout_sec=0.5)
        if dock_spec:
            self.get_logger().info('경로 완료 — 정밀 도킹 전환 (스테이션 프레임)')
            if dry:
                return True
            return self.dock(dock_spec)
        return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--route', required=True)
    ap.add_argument('--smap', default='')
    ap.add_argument('--spin-tol-deg', type=float, default=5.0)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--skip-dock', action='store_true')
    args = ap.parse_args()

    nodes = load_nodes_smap(args.smap) if args.smap else {}
    y_nodes, legs, dock = load_route(args.route)
    nodes.update(y_nodes)
    if not legs:
        print('route 에 레그가 없다', file=sys.stderr)
        return 2
    if args.skip_dock:
        dock = None

    rclpy.init()
    n = RouteRunner()
    ok = n.run(nodes, legs, dock, args.spin_tol_deg, args.dry_run)
    n.get_logger().info(f'경로 {"성공" if ok else "실패"}')
    rclpy.shutdown()
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
