"""바퀴 그림의 좌우 규약 — `+θ` 는 화면 왼쪽인가.

## 왜 필요한가

2026-08-12: 좌전 45° 를 눌렀는데 그림 화살표가 우전을 가리켰다. **값(+45.0)도 모션도 정상**이고
렌더링만 좌우 반전이라, 눈으로는 「지령이 틀렸나 그림이 틀렸나」를 가를 수 없었다. 판정은 Seer
위치(1004) 기록으로 했다 — 차체 기준 이동방향 실측 `POSE_ANCHORS`.

## 무엇을 고정하는가

`_px` 가 기체 `+y`(좌)를 화면 왼쪽에 놓으므로(app.py:105-107), 기체 방향 `(cos θ, sin θ)` 의
화면 표현은 `(−sin θ, −cos θ)` 다. 이 부호가 뒤집히면 그림만 조용히 거울이 된다 —
크랩(±90°)은 바퀴 사각형이 같은 가로선이라 **모호성 때문에 맞아 보이므로**, 45° 로 고정한다.
"""
import math

import pytest

pytest.importorskip("PyQt5", reason="PyQt5 미설치 — GUI 를 로드할 수 없다")

from can_relay.ui.app import wheel_axis                       # noqa: E402


def test_zero_points_forward():
    ax, ay = wheel_axis(0.0)
    assert ax == pytest.approx(0.0, abs=1e-9)
    assert ay == pytest.approx(-1.0), "화면 y 는 아래로 증가 — 전방은 −y"


def test_positive_is_left():
    """이번 결함의 직접 회귀 — `+45°` 는 화면 **왼쪽** 위여야 한다."""
    ax, ay = wheel_axis(45.0)
    assert ax < 0, f"+45° 가 화면 오른쪽을 가리킨다 (ax={ax:+.3f}) — 좌우 반전"
    assert ay < 0, "전방 성분이 없다"


def test_negative_is_right():
    ax, ay = wheel_axis(-45.0)
    assert ax > 0, f"−45° 가 화면 왼쪽을 가리킨다 (ax={ax:+.3f}) — 좌우 반전"
    assert ay < 0


def test_crab_is_sideways():
    """±90° 는 순수 좌/우. 사각형만 보면 둘이 같아 보이므로 축 부호로 고정한다."""
    assert wheel_axis(90.0)[0] == pytest.approx(-1.0)
    assert wheel_axis(-90.0)[0] == pytest.approx(+1.0)
    assert wheel_axis(90.0)[1] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("deg", [-90.0, -45.0, -1.0, 0.0, 1.0, 45.0, 90.0, 123.4])
def test_axis_is_unit_vector(deg):
    assert math.hypot(*wheel_axis(deg)) == pytest.approx(1.0)


@pytest.mark.parametrize("deg", [-90.0, -45.0, 0.0, 30.0, 45.0, 90.0])
def test_matches_px_frame(deg):
    """`_px` 가 정의하는 화면 프레임과 같은 변환인가 — 좌표계와 바퀴 축을 묶어 둔다.

    `_px(x_m, y_m)` = `(c.x − y_m·s, c.y − x_m·s)` 이므로 기체 단위벡터 `(cos θ, sin θ)` 의
    화면 증분은 `(−sin θ·s, −cos θ·s)` 다. 스케일을 빼면 `wheel_axis` 와 같아야 한다.
    """
    th = math.radians(deg)
    px_dx, px_dy = -math.sin(th), -math.cos(th)
    ax, ay = wheel_axis(deg)
    assert (ax, ay) == (pytest.approx(px_dx), pytest.approx(px_dy))


# 기체별 실측 앵커(HIL(Hardware In the Loop) pose 대조)는 기체 트리 소관이다 —
# LGIT 포크의 `test_hil_pose_anchors` 가 그 예. 여기는 화면 규약(순수)만 고정한다.
