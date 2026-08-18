"""가상 라인 센서의 기하 — ROS 무의존 순수 로직(단위 테스트 대상).

맵 좌표계에 놓인 라인과 로봇 자세로부터, 카메라가 볼 오차를 역산한다.

부호 규약은 실제 인식 노드(`line_vision`)와 **반드시 같아야 한다**:
  offset(+) = 라인이 진행방향 기준 오른쪽  ·  angle(+) = 라인 먼 쪽이 오른쪽으로 기움

모사하지 않는 것: 검출 실패·오검출·신뢰도 변동·렌즈 왜곡·원근. 기하만 맞다.
"""

import math
from dataclasses import dataclass


@dataclass
class LineSegment:
    """맵 좌표계의 라인 — (x0,y0) 에서 heading 방향으로 length 만큼.

    `curvature`(1/m)가 0 이면 직선, 아니면 그 곡률의 원호다. 부호는 좌선회가 +
    (진행하며 왼쪽으로 휜다). 반경은 1/|curvature|.
    """

    x0: float = 0.0
    y0: float = 0.0
    heading: float = 0.0
    length: float = 10.0
    curvature: float = 0.0


@dataclass
class Measurement:
    """카메라 규약으로 환산한 관측."""

    detected: bool = False
    offset: float = 0.0
    angle: float = 0.0
    along: float = 0.0  # 라인 시점 기준 진행량 (m) — 구간 이탈 판정 근거


def normalize_angle(rad):
    """각을 ±π 로 접는다."""
    return math.atan2(math.sin(rad), math.cos(rad))


def measure(x, y, yaw, line, lookahead_m, half_width_m, reverse=False):
    """로봇 자세에서 라인 관측을 만든다.

    전방주시점(진행방향으로 `lookahead_m` 앞)이 카메라 기준행에 대응한다고 본다.
    그 점에서 라인까지의 부호 있는 횡거리를 `half_width_m`(기준행에서 화면 반폭이
    덮는 실제 폭)으로 정규화해 offset 을 만든다.

    Args:
        x, y, yaw: 맵 기준 로봇 자세 (m, m, rad).
        line: `LineSegment`.
        lookahead_m: 전방주시 거리 (m, > 0).
        half_width_m: 기준행 화면 반폭이 덮는 실제 폭 (m, > 0).
        reverse: 후진이면 True — 진행방향이 yaw+π 가 된다.

    Returns:
        `Measurement`. 라인이 화각 밖이거나 구간을 벗어나면 `detected=False`.
    """
    if half_width_m <= 0.0:
        return Measurement()

    travel_yaw = normalize_angle(yaw + math.pi) if reverse else normalize_angle(yaw)
    # 전방주시점 — 카메라 기준행이 바라보는 지면 위치
    qx = x + lookahead_m * math.cos(travel_yaw)
    qy = y + lookahead_m * math.sin(travel_yaw)

    if abs(line.curvature) > 1e-9:
        return _measure_arc(qx, qy, travel_yaw, line, half_width_m)

    ux, uy = math.cos(line.heading), math.sin(line.heading)
    wx, wy = qx - line.x0, qy - line.y0

    # 구간 진행량은 `line.heading` 방향으로 잰다. 아래 진행방향 정렬과 독립이며,
    # 구간 경계(0~length)는 라인 정의가 정한다.
    along = wx * ux + wy * uy

    # 라인 방향을 진행방향 쪽으로 정렬한다. 반대로 놓인 라인을 따라갈 때 angle 부호가
    # 뒤집히면 제어가 라인에서 멀어진다.
    head = line.heading
    if ux * math.cos(travel_yaw) + uy * math.sin(travel_yaw) < 0.0:
        ux, uy = -ux, -uy
        head = normalize_angle(head + math.pi)

    # cross > 0 = 주시점이 라인의 왼쪽 = 라인이 주시점의 오른쪽 = offset(+)
    cross = ux * wy - uy * wx
    offset = max(-1.0, min(1.0, cross / half_width_m))

    # angle(+) = 먼 쪽이 오른쪽으로 기움. 진행 heading 이 라인보다 CCW 면(왼쪽을 보면)
    # 라인은 화면에서 오른쪽으로 흘러간다.
    angle = normalize_angle(travel_yaw - head)

    detected = abs(cross) <= half_width_m and 0.0 <= along <= line.length
    return Measurement(detected=detected, offset=offset, angle=angle, along=along)


def _measure_arc(qx, qy, travel_yaw, line, half_width_m):
    """곡률 ≠ 0 인 원호 구간의 관측.

    원호 중심은 시점에서 좌선회(+κ)면 왼쪽, 우선회(−κ)면 오른쪽으로 반경 R 만큼 떨어져 있다.
    주시점의 횡오차는 **중심에서의 거리차**로 얻는다 — 주시점이 중심 쪽으로 치우치면
    좌선회에서는 라인의 왼쪽에 있다는 뜻이다.

    직선판과 같은 규약을 지킨다: offset(+) = 라인이 진행방향 기준 오른쪽,
    angle(+) = 먼 쪽이 오른쪽으로 기움.
    """
    radius = 1.0 / abs(line.curvature)
    turn = 1.0 if line.curvature > 0.0 else -1.0  # +1 좌선회
    # 중심 = 시점에서 좌(우)측 법선 방향으로 R
    nx, ny = -math.sin(line.heading), math.cos(line.heading)
    cx = line.x0 + turn * radius * nx
    cy = line.y0 + turn * radius * ny

    dx, dy = qx - cx, qy - cy
    dist = math.hypot(dx, dy)
    if dist < 1e-9:
        return Measurement()  # 중심 위 — 접선이 정의되지 않는다

    # 주시점이 라인의 왼쪽에 있으면 cross > 0 (직선판과 같은 부호 규약).
    # 좌선회면 중심이 왼쪽이므로 중심에 가까울수록(=dist<R) 왼쪽이다.
    cross = turn * (radius - dist)
    offset = max(-1.0, min(1.0, cross / half_width_m))

    # 주시점의 원주각으로 진행량(호 길이)과 접선 방향을 얻는다.
    #
    # 진행량은 시점에서 **한 바퀴까지** 단조 증가해야 한다. ±π 로 접으면 반 바퀴(π·R)를
    # 지나는 순간 along 이 음수로 뒤집혀, 라인이 아직 남아 있는데 구간 밖으로 판정된다.
    # 그래서 [0, 2π) 로 접는다. 한 바퀴를 넘는 length 는 원주로 잘라 닫힌 고리로 본다.
    theta_q = math.atan2(dy, dx)
    theta_0 = math.atan2(line.y0 - cy, line.x0 - cx)
    swept = (turn * (theta_q - theta_0)) % (2.0 * math.pi)
    along = radius * swept
    max_along = min(line.length, 2.0 * math.pi * radius)
    tangent = normalize_angle(theta_q + turn * math.pi / 2.0)

    # 진행 방향과 반대로 놓인 원호도 같은 규약으로 읽는다(직선판의 정렬과 같은 처리).
    if math.cos(tangent - travel_yaw) < 0.0:
        tangent = normalize_angle(tangent + math.pi)
        cross = -cross
        offset = max(-1.0, min(1.0, cross / half_width_m))

    angle = normalize_angle(travel_yaw - tangent)
    detected = abs(cross) <= half_width_m and 0.0 <= along <= max_along
    return Measurement(detected=detected, offset=offset, angle=angle, along=along)


def anchor_line(start_x, start_y, start_yaw, offset_x, offset_y, heading_deg, length,
                curvature=0.0):
    """로봇 시작 자세를 기준으로 라인을 놓는다.

    맵 원점에 라인을 고정하면 플랜트의 초기 자세(시나리오 웨이포인트)가 원점이 아닐 때
    라인이 화각 밖에 놓여 시나리오가 성립하지 않는다. 시작 자세 기준으로 놓으면
    「출발 지점에서 왼쪽 10 cm 에 나란한 10 m 직선」 같은 서술이 플랜트 설정과 무관하게 성립한다.

    Args:
        start_x, start_y, start_yaw: 로봇 시작 자세 (m, m, rad).
        offset_x: 시작 지점 기준 **전방** 오프셋 (m).
        offset_y: 시작 지점 기준 **좌측** 오프셋 (m, + = 왼쪽).
        heading_deg: 시작 heading 기준 라인 방향 (deg).
        length: 라인 길이 (m).

    Returns:
        맵 좌표계의 `LineSegment`.
    """
    fx, fy = math.cos(start_yaw), math.sin(start_yaw)      # 전방 단위벡터
    lx, ly = -math.sin(start_yaw), math.cos(start_yaw)     # 좌측 단위벡터
    return LineSegment(
        x0=start_x + offset_x * fx + offset_y * lx,
        y0=start_y + offset_x * fy + offset_y * ly,
        heading=normalize_angle(start_yaw + math.radians(heading_deg)),
        length=length,
        curvature=curvature,
    )
