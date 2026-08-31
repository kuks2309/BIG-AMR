"""카메라 내부 파라미터(intrinsic) 캘리브레이션 기본 기능 — 체커보드 기반.

기본 기능만 담는다: 체커보드 코너 검출 + cv2.calibrateCamera 로 intrinsics 해.
저장소·UI·다중카메라·factory 대조·판정(SPC)은 이 파일에 없다(차후 단계).
"""
from __future__ import annotations

import cv2
import numpy as np

# 서브픽셀 코너 정밀화 종료조건 (30회 반복 또는 정확도 0.001 도달).
_CORNER_REFINE_CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# 지원 왜곡 모델 → cv2.calibrateCamera flags (fisheye 는 별도 경로).
_STANDARD_MODEL_FLAGS = {
    "plumb_bob": 0,                              # 5계수 (k1 k2 p1 p2 k3)
    "rational_polynomial": cv2.CALIB_RATIONAL_MODEL,  # 8계수 (+k4 k5 k6)
}
SUPPORTED_MODELS = tuple(_STANDARD_MODEL_FLAGS) + ("fisheye",)

# fisheye(Kannala-Brandt) 반복 종료조건.
_FISHEYE_CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-6)
_FISHEYE_NUM_COEFFS = 4  # Kannala-Brandt 왜곡 계수 개수 (k1 k2 k3 k4)


def build_object_points(pattern_size, square_size):
    """체커보드 한 뷰의 내부 코너 3D 좌표(Z=0 평면)를 만든다.

    pattern_size: (cols, rows) 내부 코너 개수.
    square_size: 사각형 한 변의 실제 길이(일관 단위, 예: mm).
    반환: (cols*rows, 3) float32.
    """
    cols, rows = pattern_size
    objp = np.zeros((cols * rows, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)
    objp *= float(square_size)
    return objp


def build_object_points_acircles(pattern_size, spacing):
    """비대칭 원형 그리드 한 뷰의 3D 좌표(Z=0). OpenCV 비대칭 배열 규약.

    pattern_size: (cols, rows) — findCirclesGrid ASYMMETRIC 규약의 (열, 행).
    spacing: 인접 원 중심 간 최소 거리(대각 기준 mm).
    """
    cols, rows = pattern_size
    objp = []
    for r in range(rows):
        for c in range(cols):
            objp.append([(2 * c + r % 2) * spacing, r * spacing, 0.0])
    return np.array(objp, np.float32)


def find_circles(gray, pattern_size, asymmetric=False):
    """원형 그리드 중심을 검출한다. 반환: (found, centers|None)."""
    flag = (
        cv2.CALIB_CB_ASYMMETRIC_GRID if asymmetric else cv2.CALIB_CB_SYMMETRIC_GRID
    )
    found, centers = cv2.findCirclesGrid(gray, pattern_size, flags=flag)
    return found, (centers if found else None)


def find_corners(gray, pattern_size, refine=True):
    """그레이스케일 이미지에서 체커보드 내부 코너를 검출한다.

    반환: (found, corners) — corners 는 (N,1,2) float32 또는 None.
    """
    found, corners = cv2.findChessboardCorners(
        gray,
        pattern_size,
        flags=cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE,
    )
    if found and refine:
        corners = cv2.cornerSubPix(
            gray, corners, (11, 11), (-1, -1), _CORNER_REFINE_CRITERIA
        )
    return found, (corners if found else None)


def calibrate_intrinsics(
    image_points, pattern_size, square_size, image_size, model="plumb_bob",
    asymmetric_circles=False,
):
    """체커보드/원형 그리드 코너 집합으로 카메라 intrinsics 를 해.

    image_points: 뷰별 (N,1,2) float32 코너 배열 리스트.
    image_size: (width, height) 픽셀.
    model: 왜곡 모델 — "plumb_bob"(5계수)·"rational_polynomial"(8계수)·"fisheye"(4계수).
    asymmetric_circles: 비대칭 원형 그리드면 True (객체점 배열이 다름).
    반환 dict: rms, K(3x3), D, per_view_errors, image_size, model.
    """
    if len(image_points) < 3:
        raise ValueError(
            "intrinsic 캘리브레이션엔 뷰 3장 이상 필요, 입력=%d" % len(image_points)
        )
    object_points = checkerboard_object_points(
        image_points, pattern_size, square_size, asymmetric_circles
    )
    return _calibrate_dispatch(object_points, image_points, image_size, model)


def checkerboard_object_points(image_points, pattern_size, square_size,
                               asymmetric_circles=False):
    """뷰 수만큼 동일한 3D 객체점 배열을 복제해 리스트로 만든다(체커/원형 그리드)."""
    if asymmetric_circles:
        objp = build_object_points_acircles(pattern_size, square_size)
    else:
        objp = build_object_points(pattern_size, square_size)
    return [objp for _ in image_points]


def _calibrate_dispatch(object_points, image_points, image_size, model):
    """model 문자열에 따라 표준(calibrateCamera)/fisheye 경로로 분기한다."""
    if model == "fisheye":
        return _calibrate_and_prune(
            object_points, image_points, image_size, model,
            _fisheye_calibrate, _fisheye_per_view_errors,
        )
    if model not in _STANDARD_MODEL_FLAGS:
        raise ValueError(
            "지원하지 않는 모델: %r (지원: %s)" % (model, ", ".join(SUPPORTED_MODELS))
        )
    return _calibrate_and_prune(
        object_points, image_points, image_size, model,
        _standard_calibrate(_STANDARD_MODEL_FLAGS[model]), _per_view_errors,
    )


def _standard_calibrate(flags):
    """주어진 flags 로 cv2.calibrateCamera 를 호출하는 calibrate_fn 을 만든다."""
    def _fn(object_points, image_points, image_size):
        return cv2.calibrateCamera(
            object_points, image_points, image_size, None, None, flags=flags
        )
    return _fn


def _calibrate_and_prune(object_points, image_points, image_size, model,
                         calibrate_fn, per_view_fn, drop_outliers=True):
    """calibrate + 아웃라이어 뷰 제거 후 재계산 (표준·fisheye 공용 골격).

    calibrate_fn(obj, img, size) -> (rms, K, D, rvecs, tvecs).
    per_view_fn(obj, img, rvecs, tvecs, K, D) -> 뷰별 오차 리스트.
    1차 계산 → 뷰별 재투영 오차 → 오차가 max(1.0px, 2×중앙값) 초과 뷰 제거 →
    남은 뷰로 재계산. 흔들림·오검출 뷰가 rms·intrinsics 를 오염시키는 것을 막는다.
    반환 dict 에 used_views, dropped, rms_before 포함.
    """
    rms, camera_matrix, dist, rvecs, tvecs = calibrate_fn(
        object_points, image_points, image_size
    )
    per_view = per_view_fn(object_points, image_points, rvecs, tvecs, camera_matrix, dist)
    rms_before = float(rms)
    dropped = 0
    if drop_outliers and len(object_points) >= 6:
        median = float(np.median(per_view))
        threshold = max(1.0, 2.0 * median)
        keep = [i for i, err in enumerate(per_view) if err <= threshold]
        # TODO(debt-002): len(keep)<4 로 스킵되면 오염 결과를 dropped=0 으로 오도 보고.
        if 4 <= len(keep) < len(object_points):
            obj_keep = [object_points[i] for i in keep]
            img_keep = [image_points[i] for i in keep]
            rms, camera_matrix, dist, rvecs, tvecs = calibrate_fn(
                obj_keep, img_keep, image_size
            )
            per_view = per_view_fn(
                obj_keep, img_keep, rvecs, tvecs, camera_matrix, dist
            )
            dropped = len(object_points) - len(keep)
    return {
        "rms": float(rms),
        "K": camera_matrix,
        "D": dist.ravel(),
        "per_view_errors": per_view,
        "image_size": tuple(image_size),
        "model": model,
        "used_views": len(per_view),
        "dropped": dropped,
        "rms_before": rms_before,
    }


def _per_view_errors(object_points, image_points, rvecs, tvecs, camera_matrix, dist):
    """뷰별 평균 재투영 오차(픽셀)를 계산한다 (표준 plumb_bob/rational)."""
    errors = []
    for objp, imgp, rvec, tvec in zip(object_points, image_points, rvecs, tvecs):
        projected, _ = cv2.projectPoints(objp, rvec, tvec, camera_matrix, dist)
        err = cv2.norm(imgp, projected, cv2.NORM_L2) / len(projected)
        errors.append(float(err))
    return errors


def _fisheye_calibrate(object_points, image_points, image_size):
    """cv2.fisheye.calibrate 로 어안(Kannala-Brandt) intrinsics 를 해.

    fisheye API 는 객체점 (N,1,3)·이미지점 (N,1,2) float64 를 요구한다.
    fisheye 내부 InitExtrinsics 는 노이즈 없는 평면 타깃에서 degenerate(`norm_u1>0`
    assertion)하므로, 먼저 표준 pinhole 캘리로 K 를 부트스트랩해 초기 추정값으로 준다
    (CALIB_USE_INTRINSIC_GUESS). CHECK_COND 는 ill-conditioned 예외를 유발하므로 배제
    (아웃라이어 뷰는 상위 pruning 이 담당).
    반환: (rms, K(3x3), D(4,), rvecs, tvecs) — 표준 경로와 시그니처 호환.
    """
    obj = [np.asarray(p, np.float64).reshape(-1, 1, 3) for p in object_points]
    img = [np.asarray(p, np.float64).reshape(-1, 1, 2) for p in image_points]
    # pinhole 부트스트랩: calibrateCamera 는 Point3f(float32) 를 요구.
    # TODO(debt-003): pruning 재계산 시 이 부트스트랩이 이중 수행됨(K 재사용 최적화 여지).
    obj32 = [p.astype(np.float32) for p in obj]
    img32 = [p.astype(np.float32) for p in img]
    _, k_init, _, _, _ = cv2.calibrateCamera(
        obj32, img32, image_size, None, None, flags=0
    )
    camera_matrix = k_init.copy()
    dist = np.zeros((_FISHEYE_NUM_COEFFS, 1))
    n = len(obj)
    rvecs = [np.zeros((1, 1, 3)) for _ in range(n)]
    tvecs = [np.zeros((1, 1, 3)) for _ in range(n)]
    flags = (
        cv2.fisheye.CALIB_USE_INTRINSIC_GUESS
        | cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC
        | cv2.fisheye.CALIB_FIX_SKEW
    )
    rms, camera_matrix, dist, rvecs, tvecs = cv2.fisheye.calibrate(
        obj, img, image_size, camera_matrix, dist, rvecs, tvecs, flags,
        _FISHEYE_CRITERIA,
    )
    return rms, camera_matrix, dist.ravel(), rvecs, tvecs


def _fisheye_per_view_errors(object_points, image_points, rvecs, tvecs,
                             camera_matrix, dist):
    """뷰별 평균 재투영 오차(픽셀)를 계산한다 (fisheye 투영 사용)."""
    errors = []
    for objp, imgp, rvec, tvec in zip(object_points, image_points, rvecs, tvecs):
        op = np.asarray(objp, np.float64).reshape(-1, 1, 3)
        ip = np.asarray(imgp, np.float64).reshape(-1, 1, 2)
        projected, _ = cv2.fisheye.projectPoints(op, rvec, tvec, camera_matrix, dist)
        projected = projected.reshape(-1, 1, 2)
        err = cv2.norm(ip, projected, cv2.NORM_L2) / len(projected)
        errors.append(float(err))
    return errors


# ---------------------------------------------------------------------------
# ChArUco 경로 (마커 내장 체커보드) — cv2.aruco 신규 API (OpenCV 4.7+)
# ---------------------------------------------------------------------------


def make_charuco_board(squares_x, squares_y, square_mm, marker_mm, dict_name):
    """ChArUco 보드와 검출기를 만든다.

    squares_x/y: 사각형 개수(내부 코너 아님). square_mm/marker_mm: 실측 길이.
    반환: (board, detector).
    """
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dict_name))
    board = cv2.aruco.CharucoBoard(
        (squares_x, squares_y), float(square_mm), float(marker_mm), dictionary
    )
    detector = cv2.aruco.CharucoDetector(board)
    return board, detector


def find_charuco(gray, detector):
    """그레이스케일에서 ChArUco 코너·마커를 검출한다.

    반환: dict(charuco_corners, charuco_ids, marker_corners, marker_ids).
    검출 실패 항목은 None.
    """
    charuco_corners, charuco_ids, marker_corners, marker_ids = detector.detectBoard(gray)
    return {
        "charuco_corners": charuco_corners,
        "charuco_ids": charuco_ids,
        "marker_corners": marker_corners,
        "marker_ids": marker_ids,
    }


def calibrate_intrinsics_charuco(views, board, image_size, model="plumb_bob"):
    """ChArUco 뷰들로 intrinsics 를 해.

    views: [(charuco_corners, charuco_ids)] 리스트(뷰별 검출 결과).
    board.matchImagePoints 로 3D-2D 대응을 만든 뒤 model 경로로 캘리.
    model: "plumb_bob"·"rational_polynomial"·"fisheye".
    반환 dict: calibrate_intrinsics 와 동일 구조 + used_views.
    """
    object_points, image_points = charuco_points(views, board)
    if len(object_points) < 3:
        raise ValueError(
            "유효 뷰 3장 이상 필요(코너≥4/뷰), 현재=%d" % len(object_points)
        )
    return _calibrate_dispatch(object_points, image_points, image_size, model)


def charuco_points(views, board):
    """ChArUco 뷰들을 board.matchImagePoints 로 (3D 객체점, 2D 이미지점) 리스트로 변환.

    뷰당 코너 6개 미만(calibrateCamera DLT pose 최소 요건)은 제외. 뷰마다 코너 수
    상이(가변 길이). 반환: (object_points, image_points).
    """
    object_points, image_points = [], []
    for charuco_corners, charuco_ids in views:
        if charuco_ids is None or len(charuco_ids) < 6:
            continue
        obj_pts, img_pts = board.matchImagePoints(charuco_corners, charuco_ids)
        if obj_pts is None or len(obj_pts) < 6:
            continue
        object_points.append(obj_pts)
        image_points.append(img_pts)
    return object_points, image_points


# ---------------------------------------------------------------------------
# 자동 모델 선택 — 교차검증(held-out 재투영오차) 기준 (ADR-0003)
# ---------------------------------------------------------------------------

_CV_MIN_VIEWS = 4          # 교차검증에 필요한 최소 뷰 수
_CV_MIN_TRAIN_VIEWS = 3    # 폴드 학습셋 최소 뷰(calibrate 요건)
_DEFAULT_K_FOLDS = 5


def _reprojection_rms_on_views(object_points, image_points, camera_matrix, dist,
                               model):
    """주어진 K,D 로 각 뷰의 자세를 solvePnP 추정 후 재투영한 RMS 오차(px) 반환.

    intrinsic(K,D)은 공유하되 extrinsic(자세)은 뷰별이므로, held-out 뷰 평가 시
    자세를 추정해야 재투영이 가능하다. fisheye 는 undistortPoints→solvePnP(K=I)→
    fisheye.projectPoints 경로. RMS = sqrt(Σ(dx²+dy²)/총점수) — cv2.calibrateCamera
    의 rms 와 동일 관례라 full_rms 와 직접 비교 가능. 추정 실패 뷰는 제외.
    """
    camera_matrix = np.asarray(camera_matrix, np.float64)
    sq_sum = 0.0
    n_points = 0
    for objp, imgp in zip(object_points, image_points):
        op = np.asarray(objp, np.float64).reshape(-1, 1, 3)
        ip = np.asarray(imgp, np.float64).reshape(-1, 1, 2)
        if model == "fisheye":
            dvec = np.asarray(dist, np.float64).reshape(_FISHEYE_NUM_COEFFS, 1)
            undist = cv2.fisheye.undistortPoints(ip, camera_matrix, dvec)
            ok, rvec, tvec = cv2.solvePnP(op, undist, np.eye(3), None)
            if not ok:
                continue
            projected, _ = cv2.fisheye.projectPoints(op, rvec, tvec, camera_matrix, dvec)
        else:
            dvec = np.asarray(dist, np.float64).reshape(-1, 1)
            ok, rvec, tvec = cv2.solvePnP(op, ip, camera_matrix, dvec)
            if not ok:
                continue
            projected, _ = cv2.projectPoints(op, rvec, tvec, camera_matrix, dvec)
        diff = ip.reshape(-1, 2) - projected.reshape(-1, 2)
        sq_sum += float(np.sum(diff ** 2))
        n_points += len(diff)
    return float(np.sqrt(sq_sum / n_points)) if n_points else float("inf")


def _cv_error_for_model(object_points, image_points, image_size, model, folds):
    """model 의 k-fold 교차검증 held-out 재투영오차 평균을 계산한다."""
    n = len(object_points)
    fold_errors = []
    for test_idx in folds:
        test_set = set(test_idx)
        train_o = [object_points[i] for i in range(n) if i not in test_set]
        train_i = [image_points[i] for i in range(n) if i not in test_set]
        test_o = [object_points[i] for i in test_idx]
        test_i = [image_points[i] for i in test_idx]
        if len(train_o) < _CV_MIN_TRAIN_VIEWS or not test_o:
            continue
        # 학습 캘리와 held-out 재투영(solvePnP/undistort)을 함께 감싸, 한 폴드의
        # cv2.error(예: ill-conditioned 학습 K → test solvePnP 발산)가 전체 모델
        # 탐색을 중단시키지 않고 해당 폴드만 건너뛰도록 한다.
        try:
            trained = _calibrate_dispatch(train_o, train_i, image_size, model)
            err = _reprojection_rms_on_views(
                test_o, test_i, trained["K"], trained["D"], model
            )
        except cv2.error:
            continue
        if np.isfinite(err):
            fold_errors.append(err)
    return float(np.mean(fold_errors)) if fold_errors else float("inf")


def select_best_model(object_points, image_points, image_size, models=None,
                      k_folds=_DEFAULT_K_FOLDS, seed=0):
    """여러 왜곡 모델을 교차검증으로 비교해 held-out 재투영오차 최저 모델을 고른다.

    object_points/image_points: materialize 된 뷰별 3D/2D 대응 리스트.
    models: 후보 모델 리스트(기본 SUPPORTED_MODELS 전체).
    반환 dict: best_model, best(전체 뷰로 캘리한 결과 dict), report(모델별
    {model, full_rms, cv_error, result|error}).
    단순 전체 RMS 는 계수 많은 모델로 편향되므로, 선택은 cv_error 로만 한다(full_rms 는 참고).
    """
    if models is None:
        models = list(SUPPORTED_MODELS)
    n = len(object_points)
    if n < _CV_MIN_VIEWS:
        raise ValueError(
            "교차검증엔 뷰 %d장 이상 필요, 현재=%d" % (_CV_MIN_VIEWS, n)
        )
    k = max(2, min(k_folds, n))
    order = np.random.default_rng(seed).permutation(n)
    folds = [list(part) for part in np.array_split(order, k)]

    report = []
    for model in models:
        try:
            full = _calibrate_dispatch(object_points, image_points, image_size, model)
        except cv2.error as exc:
            report.append({"model": model, "error": str(exc).splitlines()[-1]})
            continue
        cv_error = _cv_error_for_model(
            object_points, image_points, image_size, model, folds
        )
        report.append({
            "model": model,
            "full_rms": full["rms"],
            "cv_error": cv_error,
            "result": full,
        })

    ranked = [r for r in report if np.isfinite(r.get("cv_error", float("inf")))]
    if not ranked:
        raise ValueError("모든 후보 모델의 교차검증에 실패했습니다")
    best = min(ranked, key=lambda r: r["cv_error"])
    return {"best_model": best["model"], "best": best["result"], "report": report}
