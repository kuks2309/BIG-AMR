#!/usr/bin/env python3
"""휠 기하 정본 ↔ 오도메트리 수식 회귀.

정본 YAML 의 바퀴 좌표를 그대로 설계행렬에 넣어, 알려진 기동(직진·제자리 스핀·크랩)에서
차체 트위스트가 되돌아오는지 본다. 기하가 바뀌면 여기서 먼저 깨진다.

ROS 없이 돈다(numpy + yaml 만 필요). `python3 test_wheel_geometry.py`.
"""
import math
import os
import sys

import numpy as np
import yaml

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
CANONICAL = os.path.join(
    REPO, 'src', 'Control', 'Motion_Control', '2WS', 'trnav_2ws_core',
    'config', 'robot_geometry_2ws.yaml')

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print(f'[FAIL] {msg}')


def load_geometry(path):
    with open(path) as fh:
        doc = yaml.safe_load(fh)
    p = doc['/**']['ros__parameters']
    return [(p['w1_x'], p['w1_y']), (p['w2_x'], p['w2_y'])], p['wheel_radius']


def design_matrix(wheels):
    rows = []
    for (wx, wy) in wheels:
        rows.append([1.0, 0.0, -wy])
        rows.append([0.0, 1.0, wx])
    return np.array(rows)


def solve(wheels, meas):
    """meas = [(v_i, delta_i)] → (vx, vy, omega) 최소자승해."""
    b = []
    for (v, d) in meas:
        b += [v * math.cos(d), v * math.sin(d)]
    return np.linalg.pinv(design_matrix(wheels)) @ np.array(b)


def main():
    wheels, radius = load_geometry(CANONICAL)
    (x1, y1), (x2, y2) = wheels
    print(f'정본 기하: w1=({x1}, {y1})  w2=({x2}, {y2})  r={radius}')

    # 1) 현재 구조 = inline dual-steer. 두 바퀴가 센터라인 위에 있어야 제자리 스핀이 ±90° 로 성립한다.
    check(y1 == 0.0 and y2 == 0.0, f'inline 구조인데 y 가 0 이 아니다: {y1}, {y2}')
    check(x1 > 0.0 > x2, f'w1 이 앞(+x), w2 가 뒤(−x) 여야 한다: {x1}, {x2}')
    wheelbase = x1 - x2
    check(abs(wheelbase - 1.2) < 1e-9, f'휠베이스가 1.2 m 가 아니다: {wheelbase}')
    check(radius > 0.0, '바퀴 반지름이 양수가 아니다')

    # 2) 관측성 — det(AᵀA) = 2·d² (d = 두 바퀴 간 거리). 겹치면 회전을 분리할 수 없다.
    A = design_matrix(wheels)
    det = np.linalg.det(A.T @ A)
    d = math.hypot(x1 - x2, y1 - y2)
    check(abs(det - 2.0 * d * d) < 1e-9, f'det 이 2·d² 와 다르다: {det} vs {2*d*d}')
    check(det > 1e-6, f'기하가 특이하다(det={det})')

    # 3) 직진 — 양 바퀴 조향 0, 같은 속도.
    vx, vy, wz = solve(wheels, [(0.5, 0.0), (0.5, 0.0)])
    check(abs(vx - 0.5) < 1e-9, f'직진 vx: {vx}')
    check(abs(vy) < 1e-9 and abs(wz) < 1e-9, f'직진인데 vy/ω 가 생겼다: {vy}, {wz}')

    # 4) 제자리 스핀 — 바퀴를 ±90° 로 꺾고 각자 |ω|·거리 만큼 굴린다.
    omega = 1.0
    vx, vy, wz = solve(wheels, [(omega * x1, math.pi / 2), (omega * abs(x2), -math.pi / 2)])
    check(abs(wz - omega) < 1e-9, f'스핀 ω: {wz}')
    check(abs(vx) < 1e-9 and abs(vy) < 1e-9, f'제자리 스핀인데 병진이 생겼다: {vx}, {vy}')

    # 5) 크랩 — 양 바퀴 같은 각으로 꺾고 같은 속도. 회전 없이 비스듬히 간다.
    ang = math.radians(30.0)
    vx, vy, wz = solve(wheels, [(0.4, ang), (0.4, ang)])
    check(abs(vx - 0.4 * math.cos(ang)) < 1e-9, f'크랩 vx: {vx}')
    check(abs(vy - 0.4 * math.sin(ang)) < 1e-9, f'크랩 vy: {vy}')
    check(abs(wz) < 1e-9, f'크랩인데 ω 가 생겼다: {wz}')

    # 6) 요는 조향각의 **차이**로만 생긴다 — 공통 바이어스는 상쇄되고 차이만 적분된다.
    ds, eps = 1.0, math.radians(0.5)
    _, _, w_common = solve(wheels, [(ds, eps), (ds, eps)])
    check(abs(w_common) < 1e-9, f'공통 조향 바이어스가 ω 를 만들었다: {w_common}')
    _, _, w_diff = solve(wheels, [(ds, eps), (ds, -eps)])
    check(abs(w_diff - ds * (2 * eps) / wheelbase) < 1e-6,
          f'차동 조향의 ω 가 Δs·(δ1−δ2)/L 와 다르다: {w_diff}')

    if fails:
        print(f'[FAIL] {len(fails)} 건 실패')
        return 1
    print('[PASS] 휠 기하 정본 ↔ 오도메트리 수식 정합 확인')
    return 0


if __name__ == '__main__':
    sys.exit(main())
