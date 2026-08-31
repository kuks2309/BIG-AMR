"""CalibrationSession 단위 검증 — Qt·카메라 없이 합성 프레임만으로.

UI 분리의 증거: 세션 로직이 UI/카메라에 결합되지 않아 여기서 전부 테스트된다.
"""
import cv2
import numpy as np

import make_charuco_pdf as mcp
from calib_session import CalibrationSession


def _checker_gray(cols_sq=10, rows_sq=7, sq=40, margin=40):
    """흰 여백을 둔 체커보드 그레이스케일(검출 안정화)."""
    inner = np.full((rows_sq * sq, cols_sq * sq), 255, np.uint8)
    for r in range(rows_sq):
        for c in range(cols_sq):
            if (r + c) % 2 == 0:
                inner[r * sq:(r + 1) * sq, c * sq:(c + 1) * sq] = 0
    canvas = np.full((rows_sq * sq + 2 * margin, cols_sq * sq + 2 * margin), 255, np.uint8)
    canvas[margin:margin + inner.shape[0], margin:margin + inner.shape[1]] = inner
    return canvas


def _circles_gray(cols=7, rows=6, sp=60, rad=16, mar=60):
    W = mar * 2 + (cols - 1) * sp
    H = mar * 2 + (rows - 1) * sp
    img = np.full((H, W), 255, np.uint8)
    for i in range(rows):
        for j in range(cols):
            cv2.circle(img, (mar + j * sp, mar + i * sp), rad, 0, -1)
    return img


def test_configure_clears_only_on_structural_change():
    s = CalibrationSession()
    s.configure("checkerboard", 9, 6, 25.0, 21.6, "DICT_5X5_1000")
    s.collected.append(np.zeros((54, 1, 2), np.float32))
    s.pose_sigs.append(np.zeros(4, np.float32))
    # 척도만 변경 → 유지
    assert s.configure("checkerboard", 9, 6, 30.0, 21.6, "DICT_5X5_1000") is False
    assert s.count == 1
    # 격자 변경(구조) → 초기화
    assert s.configure("checkerboard", 8, 6, 30.0, 21.6, "DICT_5X5_1000") is True
    assert s.count == 0
    print("OK configure structural-clear")


def test_checkerboard_detect_and_capture():
    s = CalibrationSession()
    s.configure("checkerboard", 9, 6, 25.0, 21.6, "DICT_5X5_1000")
    gray = _checker_gray()
    det = s.detect_preview(gray)
    assert det["found"], "체커보드 프리뷰 검출 실패"
    ok, reason = s.capture(gray, gray.shape[1::-1], 100, auto=False)
    assert ok, reason
    assert s.count == 1
    print("OK checkerboard detect+capture")


def test_charuco_capture():
    s = CalibrationSession()
    s.configure("charuco", 5, 5, 30.0, 21.6, "DICT_5X5_1000")
    gray = mcp.make_board(5, 5, 30.0, "DICT_5X5_1000", 150)[0]
    det = s.detect_preview(gray)
    assert det["found"], "ChArUco 프리뷰 검출 실패"
    ok, reason = s.capture(gray, gray.shape[1::-1], 100, auto=False)
    assert ok, reason
    print("OK charuco capture")


def test_circles_capture():
    s = CalibrationSession()
    s.configure("circles", 7, 6, 30.0, 21.6, "DICT_5X5_1000")
    gray = _circles_gray()
    ok, reason = s.capture(gray, gray.shape[1::-1], 100, auto=False)
    assert ok, reason
    print("OK circles capture")


def test_auto_cooldown_and_novelty():
    s = CalibrationSession()
    s.configure("checkerboard", 9, 6, 25.0, 21.6, "DICT_5X5_1000")
    s.auto_cooldown = 6
    gray = _checker_gray()
    size = gray.shape[1::-1]
    # 실제 UI 흐름: 매 프레임 detect_preview→capture. 정지 게이트가 통과하려면
    # 프리뷰로 '정지' 상태를 확립해야 한다(동일 프레임 2회 → motion≈0).
    s.detect_preview(gray)
    s.detect_preview(gray)
    ok1, r1 = s.capture(gray, size, 100, auto=True)          # 첫 수집
    ok2, r2 = s.capture(gray, size, 103, auto=True)          # 쿨다운 미달
    ok3, r3 = s.capture(gray, size, 110, auto=True)          # 쿨다운 통과·동일자세
    assert ok1 and r1 == "captured"
    assert (not ok2) and r2 == "cooldown", r2
    assert (not ok3) and r3 == "not_novel", r3
    assert s.count == 1
    print("OK auto cooldown+novelty")


def test_pose_signature_enriched_with_tilt():
    """시그니처가 tilt/회전 차원을 포함(6-D) — 조기 포화 완화의 근거."""
    s = CalibrationSession()
    xs, ys = np.meshgrid(np.linspace(200, 400, 9), np.linspace(150, 300, 6))
    frontal = np.stack([xs.ravel(), ys.ravel()], 1).astype(np.float32)
    sig_f = s._pose_signature(frontal, 640, 480)
    assert sig_f.shape[0] == 6, "tilt/회전 차원 누락 — %d-D" % sig_f.shape[0]
    # 중심 회전(30°) → 방위 각도 차원이 novelty 를 벌린다.
    cx, cy = frontal[:, 0].mean(), frontal[:, 1].mean()
    th = np.deg2rad(30.0)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]], np.float32)
    rotated = (frontal - (cx, cy)) @ R.T + (cx, cy)
    sig_r = s._pose_signature(rotated, 640, 480)
    assert np.linalg.norm(sig_f - sig_r) >= s.novelty_thresh, "회전 자세 미구별"
    print("OK pose signature enriched (tilt/rotation)")


def test_novelty_relaxes_near_target():
    """목표 근접 시 문턱 완화 → 포화 동결 방지(C)."""
    s = CalibrationSession()
    s.auto_target = 4
    s.novelty_thresh = 0.12
    base = np.zeros(6, np.float32)
    s.pose_sigs = [base.copy()]
    near = base.copy()
    near[0] = 0.08  # 기존과 0.08 거리
    s.collected = [None]                    # count=1 → 엄격(≈0.099) → 거부
    assert s._is_novel_pose(near) is False, "초기엔 엄격해야"
    s.collected = [None, None, None]        # count=3 → 완화(≈0.057) → 통과
    assert s._is_novel_pose(near) is True, "목표 근접 완화 실패"
    print("OK novelty relaxes near target")


def test_calibrate_requires_views():
    s = CalibrationSession()
    s.configure("checkerboard", 9, 6, 25.0, 21.6, "DICT_5X5_1000")
    try:
        s.calibrate()
    except ValueError:
        print("OK calibrate raises on <3 views")
        return
    raise AssertionError("expected ValueError")


def test_calibrate_best_selects_and_updates_model():
    """calibrate_best 가 후보를 비교해 최적 모델을 고르고 self.model 을 갱신한다."""
    from calib_intrinsics import build_object_points, SUPPORTED_MODELS

    s = CalibrationSession()
    s.configure("checkerboard", 9, 6, 25.0, 21.6, "DICT_5X5_1000")
    s.image_size = (1280, 720)
    k_true = np.array([[900.0, 0.0, 640.0], [0.0, 905.0, 360.0], [0.0, 0.0, 1.0]])
    d_true = np.array([-0.02, 0.001, -0.001, -0.012, -0.03])
    objp = build_object_points((9, 6), 25.0)
    rng = np.random.default_rng(3)
    views = []
    while len(views) < 12:
        rvec = rng.uniform(-0.4, 0.4, 3)
        tvec = np.array([rng.uniform(-120, 120), rng.uniform(-80, 80),
                         rng.uniform(600, 1000)])
        p, _ = cv2.projectPoints(objp, rvec, tvec, k_true, d_true)
        q = p.reshape(-1, 2)
        if (q[:, 0].min() < 0 or q[:, 0].max() >= 1280
                or q[:, 1].min() < 0 or q[:, 1].max() >= 720):
            continue
        views.append((p + rng.normal(0, 0.3, p.shape)).astype(np.float32))
    s.collected = views

    report = s.calibrate_best(models=["plumb_bob", "fisheye"])
    assert report["best_model"] in SUPPORTED_MODELS
    assert s.model == report["best_model"], "self.model 이 최적으로 갱신되지 않음"
    assert report["best_model"] != "fisheye", "원근 데이터에서 fisheye 선택은 오류"
    print("OK calibrate_best: best=%s, session.model 동기화" % report["best_model"])


def test_calibrate_best_requires_min_views():
    s = CalibrationSession()
    s.configure("checkerboard", 9, 6, 25.0, 21.6, "DICT_5X5_1000")
    s.image_size = (1280, 720)
    s.collected = [np.zeros((54, 1, 2), np.float32)] * 3  # <4
    try:
        s.calibrate_best()
    except ValueError:
        print("OK calibrate_best raises on <4 views")
        return
    raise AssertionError("expected ValueError for <4 views")


if __name__ == "__main__":
    test_configure_clears_only_on_structural_change()
    test_checkerboard_detect_and_capture()
    test_charuco_capture()
    test_circles_capture()
    test_auto_cooldown_and_novelty()
    test_pose_signature_enriched_with_tilt()
    test_novelty_relaxes_near_target()
    test_calibrate_requires_views()
    test_calibrate_best_selects_and_updates_model()
    test_calibrate_best_requires_min_views()
    print("ALL SESSION TESTS PASS")
