"""UI-무관 캘리브레이션 세션 로직.

UI 분리 원칙(USB_CCTV ADR 0001 '분리형 파이프라인': 캡처/처리 ↔ 뷰어 분리,
뷰어는 렌더·입력만) 에 따라 프레임 검출·수집·자세다양성·자동캡처 정책·캘리브레이션
을 UI(Qt/web) 밖에 둔다. UI 는 카메라·표시·입력만 담당하고 이 세션을 호출한다.

의존: numpy / OpenCV 만. Qt·rclpy 무의존 → PyQt5 UI 와 web 백엔드가 동일 세션 재사용.
"""
from __future__ import annotations

import cv2
import numpy as np

from calib_intrinsics import (
    calibrate_intrinsics,
    calibrate_intrinsics_charuco,
    charuco_points,
    checkerboard_object_points,
    find_charuco,
    find_circles,
    find_corners,
    make_charuco_board,
    select_best_model,
)

PATTERN_KINDS = ("checkerboard", "charuco", "circles", "acircles")
_PREVIEW_DETECT_WIDTH = 640  # 체커보드 프리뷰 검출용 축소 폭(무보드 프레임 부하 완화)


class CalibrationSession:
    """카메라·UI 와 무관한 캘리브레이션 수집/판정 상태기계.

    프레임(BGR/그레이 numpy)만 입력받는다. 카메라 핸들을 소유하지 않으므로
    합성 프레임으로 완전 단위테스트 가능하며 web UI 도 동일하게 호출한다.
    """

    def __init__(self):
        self.kind = "checkerboard"
        self.cols = 9
        self.rows = 6
        self.square_mm = 25.0
        self.marker_mm = 21.6
        self.model = "plumb_bob"  # 왜곡 모델(plumb_bob/rational_polynomial/fisheye)
        self.dict_name = "DICT_5X5_1000"

        self.collected = []  # 뷰별 페이로드(체커/원=corners, charuco=(corners,ids))
        self.pose_sigs = []  # collected 병렬 — 자세 다양성 판정 시그니처
        self.image_size = None  # (w, h)

        self.auto_target = 50
        self.auto_cooldown = 6  # 성공 캡처 간 최소 프레임 간격
        self.novelty_thresh = 0.12  # 자세 시그니처 최소 거리
        self.min_sharpness = 100.0  # 보드 ROI 라플라시안 분산 하한(모션블러 거부; 0=off, 튜너블)
        # 정지 게이트: 프리뷰 프레임 간 위치·크기 변화가 이 값 초과면 '움직임'으로
        # 보고 자동 캡처를 막는다(롤링셔터 전단 뷰 배제; 0=off, 튜너블).
        self.max_capture_motion = 0.008
        self._prev_preview_sig = None
        self._preview_motion = 1.0
        self._auto_last = -999

        self._charuco_sig = None
        self._board = None
        self._detector = None

    # ---- 설정 ----
    def configure(self, kind, cols, rows, square_mm, marker_mm, dict_name):
        """패턴/규격 설정. 구조 변경(패턴·격자·dict) 시에만 수집 초기화하고 True 반환.

        square/marker(척도)만 바뀌면 기수집 픽셀 코너는 유효하므로 초기화하지 않는다.
        """
        structural = (kind, cols, rows, dict_name)
        changed = structural != (self.kind, self.cols, self.rows, self.dict_name)
        self.kind, self.cols, self.rows, self.dict_name = kind, cols, rows, dict_name
        self.square_mm, self.marker_mm = square_mm, marker_mm
        if changed:
            self.clear()
        return changed

    def pattern_size(self):
        return (self.cols, self.rows)

    def _charuco(self):
        sig = (self.cols, self.rows, self.square_mm, self.marker_mm, self.dict_name)
        if sig != self._charuco_sig:
            self._board, self._detector = make_charuco_board(*sig)
            self._charuco_sig = sig
        return self._board, self._detector

    # ---- 검출 ----
    def detect_preview(self, gray):
        """프리뷰용 경량 검출. 반환 dict(kind, found, geometry, status).

        overlay 렌더는 UI 몫 — 여기서는 기하(코너/마커 좌표)와 상태문만 돌려준다.
        """
        k = self.kind
        if k == "charuco":
            _, detector = self._charuco()
            r = find_charuco(gray, detector)
            n_c = 0 if r["charuco_ids"] is None else len(r["charuco_ids"])
            n_m = 0 if r["marker_ids"] is None else len(r["marker_ids"])
            res = {"kind": k, "found": n_c > 0, "charuco": r,
                   "status": "마커 %d / 코너 %d" % (n_m, n_c)}
            pts = r["charuco_corners"] if n_c > 0 else None
        elif k in ("circles", "acircles"):
            found, centers = find_circles(gray, self.pattern_size(), k == "acircles")
            res = {"kind": k, "found": found, "points": centers,
                   "status": "원 발견" if found else "없음"}
            pts = centers if found else None
        else:
            # 체커보드: 축소 + FAST_CHECK 로 빠르게(무보드 프레임 GUI 정지 방지).
            h, w = gray.shape[:2]
            scale = _PREVIEW_DETECT_WIDTH / float(w)
            small = cv2.resize(gray, None, fx=scale, fy=scale)
            found, corners = cv2.findChessboardCorners(
                small, self.pattern_size(),
                flags=cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK,
            )
            pts = (corners / scale).astype(np.float32) if found else None
            res = {"kind": k, "found": found, "points": pts,
                   "status": "코너 발견" if found else "없음"}
        self._track_motion(pts, gray.shape[:2])
        res["motion"] = self._preview_motion
        return res

    @staticmethod
    def _motion_signature(points, w, h):
        """위치·크기만의 4차원 시그니처(정지 게이트용 — tilt 노이즈 배제)."""
        p = np.asarray(points, np.float32).reshape(-1, 2)
        cx, cy = p[:, 0].mean(), p[:, 1].mean()
        bw = p[:, 0].max() - p[:, 0].min()
        bh = p[:, 1].max() - p[:, 1].min()
        return np.array([cx / w, cy / h, bw / w, bh / h], np.float32)

    def _track_motion(self, points, gray_shape):
        """프리뷰 프레임 간 자세 변화량(정지 게이트용)을 갱신한다."""
        if points is None or len(points) < 1:
            self._prev_preview_sig = None
            self._preview_motion = 1.0
            return
        h, w = gray_shape
        sig = self._motion_signature(points, w, h)
        if self._prev_preview_sig is not None:
            self._preview_motion = float(np.linalg.norm(sig - self._prev_preview_sig))
        else:
            self._preview_motion = 1.0
        self._prev_preview_sig = sig

    def _detect_full(self, gray):
        """캡처용 정밀 검출. 반환 (points, payload) 또는 (None, None)."""
        k = self.kind
        if k == "charuco":
            _, detector = self._charuco()
            r = find_charuco(gray, detector)
            # calibrateCamera 의 뷰별 pose 추정(DLT)은 뷰당 코너 >= 6 이 필요하다.
            # 4~5개 부분검출 뷰를 수집하면 calibrate 단계에서 크래시난다.
            if r["charuco_ids"] is None or len(r["charuco_ids"]) < 6:
                return None, None
            return r["charuco_corners"], (r["charuco_corners"], r["charuco_ids"])
        if k in ("circles", "acircles"):
            found, centers = find_circles(gray, self.pattern_size(), k == "acircles")
            return (centers, centers) if found else (None, None)
        found, corners = find_corners(gray, self.pattern_size(), refine=True)
        return (corners, corners) if found else (None, None)

    # ---- 수집 ----
    def capture(self, gray, image_size, frame_index, auto):
        """정밀 검출 후 수집한다. auto 면 쿨다운·자세 다양성 통과 시에만.

        반환 (ok, reason). reason ∈ {captured, no_detect, cooldown, not_novel}.
        """
        points, payload = self._detect_full(gray)
        if points is None:
            return False, "no_detect"
        w, h = image_size
        sig = self._pose_signature(points, w, h)
        if auto:
            if frame_index - self._auto_last < self.auto_cooldown:
                return False, "cooldown"
            # 정지 게이트: 보드가 움직이는 중이면(롤링셔터 전단) 캡처 보류.
            if self.max_capture_motion > 0 and self._preview_motion > self.max_capture_motion:
                return False, "moving"
            if not self._is_novel_pose(sig):
                return False, "not_novel"
            if self.min_sharpness > 0 and self._roi_sharpness(gray, points) < self.min_sharpness:
                return False, "blurry"
        self.pose_sigs.append(sig)
        self.collected.append(payload)
        self.image_size = image_size
        self._auto_last = frame_index
        return True, "captured"

    def clear(self):
        self.collected = []
        self.pose_sigs = []
        self._auto_last = -999
        self._prev_preview_sig = None
        self._preview_motion = 1.0

    @property
    def count(self):
        return len(self.collected)

    @property
    def reached_target(self):
        return len(self.collected) >= self.auto_target

    # ---- 캘리브레이션 ----
    def calibrate(self):
        """수집분으로 intrinsics 를 해. 반환 결과 dict(rms,K,D,...)."""
        if self.image_size is None or len(self.collected) < 3:
            raise ValueError("뷰 3장 이상 필요, 현재=%d" % len(self.collected))
        if self.kind == "charuco":
            board, _ = self._charuco()
            return calibrate_intrinsics_charuco(
                self.collected, board, self.image_size, model=self.model
            )
        return calibrate_intrinsics(
            self.collected, self.pattern_size(), self.square_mm, self.image_size,
            model=self.model, asymmetric_circles=(self.kind == "acircles"),
        )

    def calibrate_best(self, models=None, k_folds=5):
        """후보 모델을 교차검증으로 비교해 최적 모델을 자동 선택한다(ADR-0003).

        성공 시 self.model 을 최적 모델로 갱신하고 select_best_model 리포트를 반환.
        교차검증엔 뷰 4장 이상 필요. k_folds: 교차검증 폴드 수.
        """
        if self.image_size is None or len(self.collected) < 4:
            raise ValueError(
                "교차검증엔 뷰 4장 이상 필요, 현재=%d" % len(self.collected)
            )
        if self.kind == "charuco":
            board, _ = self._charuco()
            object_points, image_points = charuco_points(self.collected, board)
        else:
            image_points = self.collected
            object_points = checkerboard_object_points(
                image_points, self.pattern_size(), self.square_mm,
                asymmetric_circles=(self.kind == "acircles"),
            )
        report = select_best_model(
            object_points, image_points, self.image_size,
            models=models, k_folds=k_folds,
        )
        self.model = report["best_model"]  # 세션 모델을 최적으로 갱신
        return report

    # ---- 자세 다양성 ----
    @staticmethod
    def _pose_signature(points, w, h):
        """자세 시그니처: 평행이동·크기 + 기울기(tilt)·회전.

        기존 [중심, 바운딩박스] 4차원만으로는 '위치·거리는 같고 기울기만 다른'
        자세를 구별하지 못해 novelty 가 조기 포화(수집 동결)했다. 점군 공분산의
        축비(원근 단축 → tilt)와 주축 방위(회전)를 더해 tilt 다양성을 인정한다.
        """
        p = np.asarray(points, np.float32).reshape(-1, 2)
        cx, cy = p[:, 0].mean(), p[:, 1].mean()
        bw = p[:, 0].max() - p[:, 0].min()
        bh = p[:, 1].max() - p[:, 1].min()
        # 중심화 공분산 → tilt(축비)·rotation(방위) 프록시
        d = p - (cx, cy)
        cxx = float((d[:, 0] * d[:, 0]).mean())
        cyy = float((d[:, 1] * d[:, 1]).mean())
        cxy = float((d[:, 0] * d[:, 1]).mean())
        tr = cxx + cyy
        det = cxx * cyy - cxy * cxy
        disc = max(0.0, tr * tr / 4.0 - det) ** 0.5
        lmax = tr / 2.0 + disc
        lmin = tr / 2.0 - disc
        axis_ratio = (lmin / lmax) ** 0.5 if lmax > 1e-9 else 1.0  # 0=강한 tilt, 1=정면
        angle = 0.5 * float(np.arctan2(2.0 * cxy, cxx - cyy)) / np.pi  # 회전 방위 −0.5..0.5
        return np.array([cx / w, cy / h, bw / w, bh / h, axis_ratio, angle], np.float32)

    def _is_novel_pose(self, sig):
        # 목표에 근접할수록 다양성 문턱을 낮춰 포화로 인한 수집 동결을 방지(최저 30%).
        frac = len(self.collected) / max(1, self.auto_target)
        thresh = self.novelty_thresh * max(0.3, 1.0 - 0.7 * frac)
        for s in self.pose_sigs:
            if np.linalg.norm(sig - s) < thresh:
                return False
        return True

    @staticmethod
    def _roi_sharpness(gray, points):
        """검출 보드 ROI 의 라플라시안 분산(초점/모션블러 지표). 높을수록 선명."""
        p = np.asarray(points, np.float32).reshape(-1, 2)
        h, w = gray.shape[:2]
        x0 = max(0, int(p[:, 0].min()))
        y0 = max(0, int(p[:, 1].min()))
        x1 = min(w, int(p[:, 0].max()) + 1)
        y1 = min(h, int(p[:, 1].max()) + 1)
        roi = gray[y0:y1, x0:x1]
        if roi.size == 0:
            return 0.0
        return float(cv2.Laplacian(roi, cv2.CV_64F).var())
