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
    """맵 좌표계의 직선 구간 — (x0,y0) 에서 heading 방향으로 length 만큼."""

    x0: float = 0.0
    y0: float = 0.0
    heading: float = 0.0
    length: float = 10.0


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


def anchor_line(start_x, start_y, start_yaw, offset_x, offset_y, heading_deg, length):
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
    )
