"""라인 중심선 추출 — ROS·ultralytics 무의존 순수 로직(단위 테스트 대상).

알고리즘 출처: `Welding_Robot_Ros2_ws/src/AI/seam_tracking/cpp/src/seam_centerline.cpp`
의 `fit_seam_centerline`. 주방향(bbox 종횡비) 판정 후 스캔라인별 전경 무게중심을 모아
최소자승(`cv2.fitLine`, DIST_L2) 직선 피팅한다. 구현은 per-pixel 루프 대신 numpy 벡터화.

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


def _runs(cols: np.ndarray, gap: int = 2):
    """True 인 열 인덱스 배열을 연속 구간(run)으로 묶는다. `gap` 이하 간격은 이어 붙인다."""
    if cols.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(cols) > gap)
    starts = np.concatenate([[0], breaks + 1])
    ends = np.concatenate([breaks, [cols.size - 1]])
    return [(int(cols[s]), int(cols[e])) for s, e in zip(starts, ends)]


def fit_centerline_roi(mask: np.ndarray, control_row_ratio: float,
                       roi_half_ratio: float = 0.05,
                       window_ratio: float = 0.05,
                       max_run_ratio: float = 0.08,
                       prefer_x: float = None) -> CenterLine:
    """기준행 ROI(Region Of Interest)에서 씨앗을 잡고 위아래로 추적해 중심선을 만든다.

    `fit_centerline` 은 전경 **전체**에 직선 하나를 맞춘다. 바닥에 라인이 여러 개(격자)면
    스캔라인 무게중심이 선들 사이를 평균해 버리고, **기준행에 라인 픽셀이 없어도** 그 직선을
    외삽해 offset 을 낸다 — 실기에서 화면 반대쪽 라인을 잡는 원인이 됐다.

    여기서는 세 가지를 바꾼다.
      1. 기준행 부근 띠에서 **후보 라인(열 방향 연속 구간)** 을 찾는다. 없으면 valid=False —
         외삽하지 않는다.
      2. 후보 중 `prefer_x`(기본: 화면 중앙)에 가장 가까운 것을 고른다.
      3. 씨앗에서 위·아래로 한 줄씩 옮기며 **직전 x 부근 창** 안의 연속 구간만 따라간다.
         가로선이 교차하는 줄은 구간 폭이 급히 넓어지므로 건너뛴다.

    Args:
        mask: uint8 마스크(0/양수).
        control_row_ratio: 기준행 위치(화면 높이 비율).
        roi_half_ratio: 씨앗을 찾을 띠의 반높이(화면 높이 비율).
        window_ratio: 추적 창의 반폭(화면 폭 비율).
        max_run_ratio: 이 폭(화면 폭 비율)을 넘는 구간은 교차로 보고 건너뛴다.
        prefer_x: 후보 선택 기준 x. None 이면 화면 중앙.

    Returns:
        `CenterLine`. 기준행 띠에 전경이 없으면 valid=False.
    """
    out = CenterLine()
    if mask is None or mask.size == 0 or mask.dtype != np.uint8:
        return out
    h, w = mask.shape[:2]
    if h < 2 or w < 2:
        return out

    win = max(2, int(window_ratio * w))
    max_run = max(2, int(max_run_ratio * w))
    if prefer_x is None:
        prefer_x = w / 2.0

    # ── 1) 기준행 띠에서 후보 찾기 ──
    cy = int(round(control_row_ratio * (h - 1)))
    half = max(1, int(roi_half_ratio * h))
    y_lo, y_hi = max(0, cy - half), min(h - 1, cy + half)
    band = mask[y_lo:y_hi + 1, :]
    band_cols = np.flatnonzero(band.any(axis=0))
    cands = _runs(band_cols)
    if not cands:
        return out  # 기준행에 라인이 없다 — 외삽하지 않고 미검출로 낸다

    # ── 2) prefer_x 에 가장 가까운 후보 ──
    seed_lo, seed_hi = min(cands, key=lambda r: abs((r[0] + r[1]) / 2.0 - prefer_x))
    x_pred = (seed_lo + seed_hi) / 2.0

    def walk(rows):
        """rows 순서대로 한 줄씩 추적하며 (x, y) 중심점을 모은다."""
        pts, x_cur, miss = [], x_pred, 0
        for y in rows:
            lo, hi = int(x_cur - win), int(x_cur + win)
            cols = np.flatnonzero(mask[y, max(0, lo):min(w, hi) + 1]) + max(0, lo)
            picked = None
            for r_lo, r_hi in _runs(cols):
                if r_hi - r_lo + 1 > max_run:
                    continue  # 교차선 — 폭이 비정상
                c = (r_lo + r_hi) / 2.0
                if picked is None or abs(c - x_cur) < abs(picked - x_cur):
                    picked = c
            if picked is None:
                miss += 1
                if miss > 20:  # 라인이 끊긴 지점 — 더 따라가지 않는다
                    break
                continue
            miss = 0
            x_cur = picked
            pts.append((picked, float(y)))
        return pts

    pts = walk(range(cy, -1, -1)) + walk(range(cy + 1, h))
    if len(pts) < 2:
        return out

    centers = np.asarray(pts, dtype=np.float32)
    vx, vy, x0, y0 = cv2.fitLine(centers, cv2.DIST_L2, 0, 0.01, 0.01).ravel()
    out.vx, out.vy, out.x0, out.y0 = float(vx), float(vy), float(x0), float(y0)

    y_lo_p, y_hi_p = float(centers[:, 1].min()), float(centers[:, 1].max())
    if abs(out.vy) < _EPS:
        out.p1, out.p2 = (out.x0, y_lo_p), (out.x0, y_hi_p)
    else:
        slope = out.vx / out.vy
        out.p1 = (out.x0 + slope * (y_lo_p - out.y0), y_lo_p)
        out.p2 = (out.x0 + slope * (y_hi_p - out.y0), y_hi_p)
    out.valid = True
    return out


def line_x_at_row(line: CenterLine, y: float):
    """직선이 `y` 행을 지나는 x. 유효하지 않거나 수평에 가까우면 None."""
    if not line.valid or abs(line.vy) < _EPS:
        return None
    return float(line.x0 + (line.vx / line.vy) * (y - line.y0))


def select_line_in_roi(lines, img_w: int, img_h: int, control_row_ratio: float,
                       roi_half_width_ratio: float = 0.6, prefer_x: float = None):
    """후보 직선 중 **기준행 ROI(Region Of Interest)를 지나는** 것을 고른다.

    판정 기준은 마스크 픽셀이 기준행에 있느냐가 아니라 **피팅된 직선이 ROI 를 지나느냐**다.
    바닥 테이프는 이음매·반사로 기준행 부근에서 끊기는 일이 잦은데, 픽셀 유무로 판정하면
    그때마다 미검출이 되어 추종이 끊긴다(2026-08-16 실기에서 확인). 직선으로 판정하면
    끊긴 구간을 직선이 이어 준다.

    동시에 화면 반대편의 다른 라인은 걸러진다 — 그 직선은 기준행에서 ROI 밖을 지난다.

    Args:
        lines: 후보 `CenterLine` 들(인스턴스별 피팅 결과).
        img_w, img_h: 화면 크기(px).
        control_row_ratio: 기준행 위치(화면 높이 비율).
        roi_half_width_ratio: ROI 반폭(화면 반폭 대비 비율). 1.0 이면 화면 전체.
        prefer_x: 같은 조건이면 이 x 에 가까운 것을 고른다. None 이면 화면 중앙.

    Returns:
        고른 `CenterLine`. ROI 를 지나는 후보가 없으면 None.
    """
    cy = control_row_ratio * (img_h - 1)
    half = img_w / 2.0
    lo, hi = half - roi_half_width_ratio * half, half + roi_half_width_ratio * half
    if prefer_x is None:
        prefer_x = half
    best, best_dist = None, None
    for line in lines:
        x = line_x_at_row(line, cy)
        if x is None or not (lo <= x <= hi):
            continue
        dist = abs(x - prefer_x)
        if best_dist is None or dist < best_dist:
            best, best_dist = line, dist
    return best
