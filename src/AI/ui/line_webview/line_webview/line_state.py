"""라인 오차 상태 보관 — ROS 무의존 순수 로직(단위 테스트 대상).

브라우저가 그릴 수 있는 형태(정규화 0~1 좌표)까지 여기서 만든다. 서버는 픽셀을 만지지
않으므로 오버레이 좌표는 화면 비율로만 표현한다.
"""

import math
import time

# 수신율 추정 표본 수. 너무 짧으면 값이 튀고, 너무 길면 인식이 끊긴 것을 늦게 안다.
HZ_WINDOW = 20


class LineState:
    """최신 `/line/error` 표본과 수신율."""

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._latest = None
        self._stamp = None
        self._recent = []

    def put(self, detected, offset, angle, confidence, camera):
        """표본 하나를 받는다. 미검출도 받는다 — 소실을 화면에서 봐야 하기 때문이다."""
        now = self._clock()
        self._latest = {
            "detected": bool(detected),
            "offset": float(offset),
            "angle": float(angle),
            "confidence": float(confidence),
            "camera": str(camera),
        }
        self._stamp = now
        self._recent.append(now)
        if len(self._recent) > HZ_WINDOW:
            self._recent = self._recent[-HZ_WINDOW:]

    def snapshot(self):
        """JSON 으로 바로 나갈 dict. 표본이 없으면 `received=False` 만 담는다."""
        if self._latest is None:
            return {"received": False}
        age_ms = (self._clock() - self._stamp) * 1000.0
        out = dict(self._latest)
        out["received"] = True
        out["age_ms"] = round(age_ms, 1)
        out["hz"] = round(self._hz(), 1)
        return out

    def _hz(self):
        """표본 간격의 역수. 표본 2개 미만이면 0."""
        if len(self._recent) < 2:
            return 0.0
        span = self._recent[-1] - self._recent[0]
        return (len(self._recent) - 1) / span if span > 0 else 0.0


def centerline_points(offset, angle, control_row_ratio, aspect=16.0 / 9.0):
    """중심선을 **정규화 화면 좌표**(x,y ∈ 0~1)의 두 끝점과 제어점으로 만든다.

    좌표계는 영상과 같다 — 원점 좌상단, y 는 아래로 증가.
    offset 은 기준행에서의 횡오차(반폭 정규화)이고, angle 은 수직 기준 기울기[rad]로
    +면 위쪽이 오른쪽으로 기운다.

    **종횡비 보정이 필수다.** `angle` 은 픽셀 좌표계에서 잰 값이라 픽셀 기울기가
    `dx/dy = tan(angle)` 이다. x 를 폭 W, y 를 높이 H 로 각각 정규화하면 같은 방향의
    기울기가 `tan(angle)·H/W = tan(angle)/aspect` 로 바뀐다. 이 보정을 빼면 16:9 화면에서
    선이 **1.78배 가파르게** 그려져 제어점에서만 맞고 위로 갈수록 라인에서 벌어진다
    (2026-08-14 실카메라 캡처로 확인).

    Args:
        aspect: 영상 가로/세로 비 (예: 1280/720 = 1.778).

    Returns:
        {"x1","y1","x2","y2","cx","cy"} — 선분 끝점과 제어점.
    """
    cy = min(1.0, max(0.0, float(control_row_ratio)))
    cx = 0.5 + float(offset) * 0.5
    ratio = float(aspect) if float(aspect) > 1e-6 else 1.0
    slope = math.tan(float(angle)) / ratio  # 정규화 좌표에서 위로 갈 때의 x 증가량
    top_y, bot_y = 0.0, 1.0
    x_top = cx + slope * (cy - top_y)   # 위쪽(작은 y)로 갈수록 +x
    x_bot = cx - slope * (bot_y - cy)
    return {
        "x1": round(x_top, 4), "y1": top_y,
        "x2": round(x_bot, 4), "y2": bot_y,
        "cx": round(cx, 4), "cy": round(cy, 4),
    }
