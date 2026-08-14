"""라인 중심선 추출 — ROS·ultralytics 무의존 순수 로직(단위 테스트 대상).

알고리즘 출처는 **타 저장소** `kuks2309/Welding_Robot_Ros2_ws` 의 `fit_seam_centerline` 이다:
`Welding_Robot_Ros2_ws/src/AI/seam_tracking/cpp/src/seam_centerline.cpp:15` (comment-check: ignore — 저장소 밖 경로)
주방향(bbox 종횡비) 판정 후 스캔라인별 전경 무게중심을 모아 최소자승
(`cv2.fitLine`, DIST_L2, 0, 0.01, 0.01) 직선 피팅한다. 구현은 per-pixel 루프 대신 numpy 벡터화.

좌표계: 입력 마스크 픽셀 좌표계 그대로. 프레임 변환 없음.
"""

from dataclasses import dataclass, field
from typing import Tuple

import cv2
import numpy as np

# 0 나눗셈 방어용 (원본 kEps 와 동일 값)
_EPS = 1e-6


@dataclass
class CenterLine:
    """중심선 직선: 통과점 (x0,y0) + 단위 방향 (vx,vy), 표시용 끝점 p1·p2."""

    valid: bool = False
    vx: float = 0.0
    vy: float = 0.0
    x0: float = 0.0
    y0: float = 0.0
    p1: Tuple[float, float] = field(default=(0.0, 0.0))
    p2: Tuple[float, float] = field(default=(0.0, 0.0))


def fit_centerline(mask: np.ndarray) -> CenterLine:
    """uint8 마스크(0/양수)에서 중심선을 피팅한다.

    전경 없음·스캔라인 중심점 2개 미만이면 valid=False.
    """
    out = CenterLine()
    if mask is None or mask.size == 0 or mask.dtype != np.uint8:
        return out

    ys, xs = np.nonzero(mask)
    if xs.size < 2:
        return out
    x_min, x_max = int(xs.min()), int(xs.max())
    y_min, y_max = int(ys.min()), int(ys.max())
    vertical = (y_max - y_min) >= (x_max - x_min)  # 주방향 판정

    # 스캔라인별 전경 무게중심 (numpy: bincount 로 스캔라인 합/개수 집계)
    if vertical:
        counts = np.bincount(ys - y_min)
        sums = np.bincount(ys - y_min, weights=xs.astype(np.float64))
        have = counts > 0
        centers_main = np.flatnonzero(have) + y_min          # y 좌표
        centers_cross = sums[have] / counts[have]            # x 무게중심
        centers = np.column_stack([centers_cross, centers_main])
    else:
        counts = np.bincount(xs - x_min)
        sums = np.bincount(xs - x_min, weights=ys.astype(np.float64))
        have = counts > 0
        centers_main = np.flatnonzero(have) + x_min          # x 좌표
        centers_cross = sums[have] / counts[have]            # y 무게중심
        centers = np.column_stack([centers_main, centers_cross])

    if len(centers) < 2:
        return out

    vx, vy, x0, y0 = cv2.fitLine(
        centers.astype(np.float32), cv2.DIST_L2, 0, 0.01, 0.01).ravel()
    out.vx, out.vy, out.x0, out.y0 = float(vx), float(vy), float(x0), float(y0)

    # 표시용 끝점: 주방향 극단 스캔라인에서의 직선 교차좌표
    if vertical:
        y_lo, y_hi = float(y_min), float(y_max)
        if abs(out.vy) < _EPS:  # 완전 수평 방향 → 수직선 폴백
            out.p1, out.p2 = (out.x0, y_lo), (out.x0, y_hi)
        else:
            slope = out.vx / out.vy  # dx/dy
            out.p1 = (out.x0 + slope * (y_lo - out.y0), y_lo)
            out.p2 = (out.x0 + slope * (y_hi - out.y0), y_hi)
    else:
        x_lo, x_hi = float(x_min), float(x_max)
        if abs(out.vx) < _EPS:
            out.p1, out.p2 = (x_lo, out.y0), (x_hi, out.y0)
        else:
            slope = out.vy / out.vx  # dy/dx
            out.p1 = (x_lo, out.y0 + slope * (x_lo - out.x0))
            out.p2 = (x_hi, out.y0 + slope * (x_hi - out.x0))
    out.valid = True
    return out


def line_error(line: CenterLine, img_w: int, img_h: int,
               control_row_ratio: float) -> Tuple[float, float]:
    """중심선에서 제어 오차 (offset, angle) 를 계산한다.

    offset: control_row(=img_h*ratio 행)에서 직선의 x 위치와 화면 중앙의 차이를
            반폭으로 정규화 [-1,1] (클리핑). +면 라인이 화면 오른쪽.
    angle:  수직 기준 기울기 [rad]. +면 라인 위쪽이 오른쪽으로 기움.
    """
    control_y = img_h * control_row_ratio
    if abs(line.vy) < _EPS:  # 수평선 — 기준행 교차 불능 → 통과점 x 사용
        line_x = line.x0
    else:
        line_x = line.x0 + (line.vx / line.vy) * (control_y - line.y0)
    offset = (line_x - img_w / 2.0) / (img_w / 2.0)
    offset = float(np.clip(offset, -1.0, 1.0))

    # 방향벡터를 '아래(+y)→위(-y)' 로 정렬한 뒤 수직 기준 각도
    vx, vy = (line.vx, line.vy) if line.vy < 0 else (-line.vx, -line.vy)
    angle = float(np.arctan2(vx, -vy))  # 수직(위쪽) 기준, +x 기움이 +
    return offset, angle
