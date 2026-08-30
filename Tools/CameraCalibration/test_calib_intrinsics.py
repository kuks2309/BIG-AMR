"""calib_intrinsics 기본 기능 검증 — 합성 정답 데이터.

알려진 K(정답)로 체커보드를 여러 자세에서 투영해 코너를 만들고,
그 코너로 캘리브레이션한 결과가 정답 K 를 복원하는지 확인한다(하드웨어 불필요).
"""
import cv2
import numpy as np

from calib_intrinsics import (
    SUPPORTED_MODELS,
    _calibrate_dispatch,
    build_object_points,
    calibrate_intrinsics,
    checkerboard_object_points,
    find_corners,
    select_best_model,
)


def _synth_views(pattern_size, square_size, image_size, k_true, n_views=15, seed=42):
    """정답 K 로 체커보드를 여러 자세에서 투영해 코너 뷰들을 생성."""
    rng = np.random.default_rng(seed)
    objp = build_object_points(pattern_size, square_size)
    dist_zero = np.zeros(5)
    width, height = image_size
    views = []
    while len(views) < n_views:
        rvec = rng.uniform(-0.4, 0.4, 3)
        tvec = np.array(
            [rng.uniform(-120, 120), rng.uniform(-80, 80), rng.uniform(600, 1000)]
        )
        projected, _ = cv2.projectPoints(objp, rvec, tvec, k_true, dist_zero)
        pts = projected.reshape(-1, 2)
        # 전 코너가 이미지 프레임 안에 들어오는 뷰만 채택.
        if (pts[:, 0].min() < 0 or pts[:, 0].max() >= width
                or pts[:, 1].min() < 0 or pts[:, 1].max() >= height):
            continue
        views.append(projected.astype(np.float32))
    return views


def test_recovers_known_intrinsics():
    pattern_size = (9, 6)
    square_size = 25.0
    image_size = (1280, 720)
    k_true = np.array(
        [[900.0, 0.0, 640.0], [0.0, 905.0, 360.0], [0.0, 0.0, 1.0]]
    )

    views = _synth_views(pattern_size, square_size, image_size, k_true)
    result = calibrate_intrinsics(views, pattern_size, square_size, image_size)

    k_est = result["K"]
    # 노이즈 없는 투영이므로 재투영 오차는 극히 작아야 한다.
    assert result["rms"] < 0.5, "rms too high: %f" % result["rms"]
    # fx, fy 를 0.5% 이내, cx, cy 를 2px 이내로 복원해야 한다.
    assert abs(k_est[0, 0] - k_true[0, 0]) / k_true[0, 0] < 0.005
    assert abs(k_est[1, 1] - k_true[1, 1]) / k_true[1, 1] < 0.005
    assert abs(k_est[0, 2] - k_true[0, 2]) < 2.0
    assert abs(k_est[1, 2] - k_true[1, 2]) < 2.0
    print(
        "OK recover: fx=%.2f fy=%.2f cx=%.2f cy=%.2f rms=%.4g"
        % (k_est[0, 0], k_est[1, 1], k_est[0, 2], k_est[1, 2], result["rms"])
    )


def test_too_few_views_raises():
    try:
        calibrate_intrinsics([np.zeros((54, 1, 2), np.float32)], (9, 6), 25.0, (1280, 720))
    except ValueError:
        print("OK too-few-views raises")
        return
    raise AssertionError("expected ValueError for <3 views")


def _synth_fisheye_views(pattern_size, square_size, image_size, k_true, d_true,
                         n_views=18, seed=7):
    """정답 K·D(fisheye 4계수)로 보드를 여러 자세에서 어안 투영해 코너 뷰 생성."""
    objp = build_object_points(pattern_size, square_size).astype(np.float64)
    objp = objp.reshape(-1, 1, 3)
    width, height = image_size
    rng = np.random.default_rng(seed)
    views = []
    while len(views) < n_views:
        rvec = rng.uniform(-0.35, 0.35, 3).reshape(3, 1)
        tvec = np.array([
            rng.uniform(-160, 160), rng.uniform(-110, 110), rng.uniform(600, 1100)
        ]).reshape(3, 1)
        projected, _ = cv2.fisheye.projectPoints(objp, rvec, tvec, k_true, d_true)
        pts = projected.reshape(-1, 2)
        if (pts[:, 0].min() < 0 or pts[:, 0].max() >= width
                or pts[:, 1].min() < 0 or pts[:, 1].max() >= height):
            continue
        views.append(projected.reshape(-1, 1, 2).astype(np.float32))
    return views


def test_fisheye_recovers_known_intrinsics():
    pattern_size = (9, 6)
    square_size = 25.0
    image_size = (1280, 720)
    k_true = np.array([[300.0, 0.0, 640.0], [0.0, 302.0, 360.0], [0.0, 0.0, 1.0]])
    d_true = np.array([[0.04], [-0.01], [0.004], [-0.001]])  # fisheye 4계수

    views = _synth_fisheye_views(pattern_size, square_size, image_size, k_true, d_true)
    result = calibrate_intrinsics(
        views, pattern_size, square_size, image_size, model="fisheye"
    )

    k_est = result["K"]
    assert result["model"] == "fisheye"
    assert len(result["D"]) == 4, "fisheye D 는 4계수여야 함: %d" % len(result["D"])
    assert result["rms"] < 0.5, "rms too high: %f" % result["rms"]
    assert abs(k_est[0, 0] - k_true[0, 0]) / k_true[0, 0] < 0.01
    assert abs(k_est[1, 1] - k_true[1, 1]) / k_true[1, 1] < 0.01
    assert abs(k_est[0, 2] - k_true[0, 2]) < 3.0
    assert abs(k_est[1, 2] - k_true[1, 2]) < 3.0
    print(
        "OK fisheye recover: fx=%.2f fy=%.2f cx=%.2f cy=%.2f rms=%.4g"
        % (k_est[0, 0], k_est[1, 1], k_est[0, 2], k_est[1, 2], result["rms"])
    )


def test_model_selection_coeff_counts():
    """모델별 D 계수 개수: plumb_bob=5, fisheye=4. (rational 은 버전별 상이하므로 >5만 확인.)"""
    pattern_size = (9, 6)
    square_size = 25.0
    image_size = (1280, 720)
    k_true = np.array([[900.0, 0.0, 640.0], [0.0, 905.0, 360.0], [0.0, 0.0, 1.0]])
    views = _synth_views(pattern_size, square_size, image_size, k_true)

    r_plumb = calibrate_intrinsics(views, pattern_size, square_size, image_size,
                                   model="plumb_bob")
    r_rational = calibrate_intrinsics(views, pattern_size, square_size, image_size,
                                      model="rational_polynomial")
    assert r_plumb["model"] == "plumb_bob"
    assert len(r_plumb["D"]) == 5
    assert r_rational["model"] == "rational_polynomial"
    assert len(r_rational["D"]) > 5, "rational 은 plumb_bob 보다 계수 많아야 함"
    assert "fisheye" in SUPPORTED_MODELS
    print(
        "OK model coeffs: plumb_bob=%d rational=%d"
        % (len(r_plumb["D"]), len(r_rational["D"]))
    )


def test_invalid_model_raises():
    try:
        calibrate_intrinsics(
            [np.zeros((54, 1, 2), np.float32)] * 3, (9, 6), 25.0, (1280, 720),
            model="bogus",
        )
    except ValueError:
        print("OK invalid-model raises")
        return
    raise AssertionError("expected ValueError for unknown model")


def _fisheye_project(objp_view, image_size, k_true, d_true, rng):
    """objp_view(N,3)를 이미지 프레임 안에 들도록 임의 자세에서 어안 투영.

    반환: (N,1,2) float32 이미지점 또는 None(프레임 벗어남).
    """
    width, height = image_size
    rvec = rng.uniform(-0.35, 0.35, 3).reshape(3, 1)
    tvec = np.array([
        rng.uniform(-160, 160), rng.uniform(-110, 110), rng.uniform(600, 1100)
    ]).reshape(3, 1)
    op = objp_view.astype(np.float64).reshape(-1, 1, 3)
    projected, _ = cv2.fisheye.projectPoints(op, rvec, tvec, k_true, d_true)
    pts = projected.reshape(-1, 2)
    if (pts[:, 0].min() < 0 or pts[:, 0].max() >= width
            or pts[:, 1].min() < 0 or pts[:, 1].max() >= height):
        return None
    return projected.reshape(-1, 1, 2).astype(np.float32)


def test_fisheye_variable_corner_counts():
    """ChArUco 처럼 뷰마다 코너 수가 다른 fisheye 입력에서도 K 를 복원한다.

    각 뷰가 전체 그리드의 임의 부분집합만 담아(matchImagePoints 출력 모사),
    _calibrate_dispatch 의 fisheye 경로가 variable-length 뷰를 처리하는지 검증.
    """
    pattern_size = (9, 6)
    square_size = 25.0
    image_size = (1280, 720)
    k_true = np.array([[300.0, 0.0, 640.0], [0.0, 302.0, 360.0], [0.0, 0.0, 1.0]])
    d_true = np.array([[0.04], [-0.01], [0.004], [-0.001]])
    full = build_object_points(pattern_size, square_size)  # (54,3)
    rng = np.random.default_rng(11)

    obj_views, img_views = [], []
    while len(obj_views) < 16:
        n_keep = rng.integers(20, 54)  # 뷰마다 다른 코너 수
        idx = np.sort(rng.choice(54, size=int(n_keep), replace=False))
        objp_view = full[idx]
        img = _fisheye_project(objp_view, image_size, k_true, d_true, rng)
        if img is None:
            continue
        obj_views.append(objp_view.reshape(-1, 1, 3).astype(np.float32))
        img_views.append(img)

    counts = {len(o) for o in obj_views}
    assert len(counts) > 1, "코너 수가 실제로 다양해야 함: %s" % counts
    result = _calibrate_dispatch(obj_views, img_views, image_size, "fisheye")
    k_est = result["K"]
    assert result["model"] == "fisheye"
    assert len(result["D"]) == 4
    assert result["rms"] < 1.0, "rms too high: %f" % result["rms"]
    assert abs(k_est[0, 0] - k_true[0, 0]) / k_true[0, 0] < 0.02
    assert abs(k_est[1, 1] - k_true[1, 1]) / k_true[1, 1] < 0.02
    print(
        "OK fisheye variable-corners(%s): fx=%.2f fy=%.2f rms=%.4g"
        % (sorted(counts), k_est[0, 0], k_est[1, 1], result["rms"])
    )


def test_fisheye_prunes_outlier_view():
    """fisheye 경로에서 오염된 뷰가 아웃라이어로 제거되고 rms 가 개선된다."""
    pattern_size = (9, 6)
    square_size = 25.0
    image_size = (1280, 720)
    k_true = np.array([[300.0, 0.0, 640.0], [0.0, 302.0, 360.0], [0.0, 0.0, 1.0]])
    d_true = np.array([[0.04], [-0.01], [0.004], [-0.001]])
    full = build_object_points(pattern_size, square_size)
    rng = np.random.default_rng(23)

    obj_views, img_views = [], []
    while len(obj_views) < 12:
        img = _fisheye_project(full, image_size, k_true, d_true, rng)
        if img is None:
            continue
        obj_views.append(full.reshape(-1, 1, 3).astype(np.float32))
        img_views.append(img)
    # 마지막 2뷰를 뷰별 랜덤 노이즈로 오염(아웃라이어). 균일 오프셋은 자세로
    # 흡수되므로, 자세로 설명 불가능한 큰 가우시안 노이즈(σ≈20px)를 준다.
    for i in (-1, -2):
        noise = rng.normal(0.0, 20.0, img_views[i].shape).astype(np.float32)
        img_views[i] = (img_views[i] + noise).astype(np.float32)

    result = _calibrate_dispatch(obj_views, img_views, image_size, "fisheye")
    assert result["dropped"] >= 1, "오염 뷰가 제거되지 않음(dropped=%d)" % result["dropped"]
    assert result["rms"] <= result["rms_before"], "pruning 후 rms 가 악화됨"
    assert result["rms"] < 1.0, "정제 후 rms 가 여전히 높음: %f" % result["rms"]
    print(
        "OK fisheye pruning: dropped=%d rms %.3f→%.3f"
        % (result["dropped"], result["rms_before"], result["rms"])
    )


def _synth_noisy_perspective_views(pattern_size, square_size, image_size, k_true,
                                   d_true, n_views=30, noise=0.3, seed=1):
    """정답 K·plumb_bob D 로 원근 투영 + 가우시안 노이즈를 준 코너 뷰 생성."""
    objp = build_object_points(pattern_size, square_size)
    width, height = image_size
    rng = np.random.default_rng(seed)
    views = []
    while len(views) < n_views:
        rvec = rng.uniform(-0.4, 0.4, 3)
        tvec = np.array([
            rng.uniform(-120, 120), rng.uniform(-80, 80), rng.uniform(600, 1000)
        ])
        projected, _ = cv2.projectPoints(objp, rvec, tvec, k_true, d_true)
        pts = projected.reshape(-1, 2)
        if (pts[:, 0].min() < 0 or pts[:, 0].max() >= width
                or pts[:, 1].min() < 0 or pts[:, 1].max() >= height):
            continue
        noisy = projected + rng.normal(0.0, noise, projected.shape)
        views.append(noisy.astype(np.float32))
    return views


def test_select_best_model_rejects_fisheye_on_perspective():
    """원근(비어안) 렌즈 데이터에서 자동 탐색이 fisheye 를 고르지 않는다.

    교차검증 held-out RMS 기준이라 과적합 모델이 벌점을 받아, 참 모델 계열
    (plumb_bob/rational)이 fisheye 보다 낮은 cv_error 를 갖는지 확인.
    """
    pattern_size = (9, 6)
    square_size = 25.0
    image_size = (1280, 720)
    k_true = np.array([[900.0, 0.0, 640.0], [0.0, 905.0, 360.0], [0.0, 0.0, 1.0]])
    d_true = np.array([-0.02, 0.001, -0.001, -0.012, -0.03])  # plumb_bob 5계수
    views = _synth_noisy_perspective_views(
        pattern_size, square_size, image_size, k_true, d_true, n_views=18
    )
    obj = checkerboard_object_points(views, pattern_size, square_size)

    report = select_best_model(obj, views, image_size, k_folds=3, seed=0)

    by_model = {r["model"]: r for r in report["report"]}
    # 세 모델 모두 유한한 cv_error 를 산출했는가.
    for m in SUPPORTED_MODELS:
        assert m in by_model, "리포트에 %s 누락" % m
        assert np.isfinite(by_model[m]["cv_error"]), "%s cv_error 비유한" % m
    # TODO(debt-004): nested 케이스(rational vs 참 plumb_bob) 과적합 벌점은 미입증 —
    # 여기선 모델 family 불일치(fisheye) 탈락만 검증한다.
    # 원근 데이터이므로 fisheye 는 선택되면 안 된다.
    assert report["best_model"] != "fisheye"
    assert report["best_model"] in ("plumb_bob", "rational_polynomial")
    # fisheye 의 held-out 오차가 표준 모델 이상이어야(과적합/모델 불일치 벌점).
    assert by_model["fisheye"]["cv_error"] >= by_model["plumb_bob"]["cv_error"]
    # cv_rms 는 full_rms 와 같은 스케일(held-out 이라 약간 큼) — 정규화 정합 확인.
    assert by_model["plumb_bob"]["cv_error"] >= by_model["plumb_bob"]["full_rms"] * 0.5
    print(
        "OK select_best: best=%s (plumb cv=%.4f, fisheye cv=%.4f)"
        % (report["best_model"], by_model["plumb_bob"]["cv_error"],
           by_model["fisheye"]["cv_error"])
    )


def test_select_best_model_too_few_views_raises():
    obj = [np.zeros((54, 1, 3), np.float32)] * 3
    img = [np.zeros((54, 1, 2), np.float32)] * 3
    try:
        select_best_model(obj, img, (1280, 720))
    except ValueError:
        print("OK select_best too-few-views raises")
        return
    raise AssertionError("expected ValueError for <4 views")


def test_find_corners_on_synthetic_board():
    # 흰 바탕에 9x6 내부코너(=10x7 사각형) 체커보드를 그려 코너 검출을 확인.
    square_px = 40
    cols_sq, rows_sq = 10, 7
    img = np.full((rows_sq * square_px, cols_sq * square_px), 255, np.uint8)
    for r in range(rows_sq):
        for c in range(cols_sq):
            if (r + c) % 2 == 0:
                y, x = r * square_px, c * square_px
                img[y:y + square_px, x:x + square_px] = 0
    found, corners = find_corners(img, (9, 6))
    assert found, "체커보드 코너 검출 실패"
    assert corners.shape[0] == 54
    print("OK find_corners: %d corners" % corners.shape[0])


if __name__ == "__main__":
    test_recovers_known_intrinsics()
    test_too_few_views_raises()
    test_fisheye_recovers_known_intrinsics()
    test_model_selection_coeff_counts()
    test_invalid_model_raises()
    test_fisheye_variable_corner_counts()
    test_fisheye_prunes_outlier_view()
    test_select_best_model_rejects_fisheye_on_perspective()
    test_select_best_model_too_few_views_raises()
    test_find_corners_on_synthetic_board()
    print("ALL PASS")
