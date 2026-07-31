"""수집 판단 로직 — ROS 무의존(단위 테스트 가능).

노드는 "언제 저장할지"를 스스로 판단하지 않고 전부 본 모듈에 위임한다. ROS 를 끌어들이지
않으므로 디스크·중복 판정을 실장비 없이 검증할 수 있다.

판정은 두 축이다:
  ① 디스크 여유 — 바닥나면 저장을 멈춘다. 루트 파일시스템이 차면 같은 디스크에 기록 중인
     다른 시험(예: 24 h USB CCTV 내구)까지 같이 죽으므로, 여유 하한은 타협 대상이 아니다.
  ② 프레임 신규성 — 정지 장면을 초당 6장씩 쌓으면 용량만 먹고 학습에는 무용하다.
     직전 **저장** 프레임 대비 평균 절대차로 거른다(직전 수신 프레임이 아니다 — 느린 드리프트가
     누적되어도 결국 임계를 넘도록).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

# 여유 공간 하한 기본값(GB). 루트가 차면 동거 중인 다른 시험이 함께 죽으므로 넉넉히 잡는다.
MIN_FREE_GB_DEFAULT = 5.0
# 평균 절대차 임계 기본값(8비트 grayscale 계조). 조명 잡음(~1계조)보다 크고
# 사람이 화면을 가로지르는 변화(수십 계조)보다 충분히 작다.
MIN_MEAN_ABS_DIFF_DEFAULT = 3.0

_BYTES_PER_GB = 1 << 30


@dataclass(frozen=True)
class SampleVerdict:
    """저장 여부와 그 사유. `reason` 은 로그·통계 집계용 안정 키다."""

    keep: bool
    reason: str


def disk_free_gb(path: str) -> float:
    """`path` 가 속한 파일시스템의 **비특권 사용자** 가용 공간(GB).

    `f_bavail`(예약분 제외)을 쓴다 — `f_bfree` 는 root 예약분을 포함해 실제보다 낙관적이다.

    Args:
        path: 존재하는 파일 또는 디렉토리 경로.
    Returns:
        가용 공간(GB, 1 GB = 2**30 B).
    Raises:
        OSError: 경로가 없거나 stat 실패 시.
    """
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / _BYTES_PER_GB


def mean_abs_diff(prev_gray: np.ndarray | None, cur_gray: np.ndarray) -> float:
    """직전 저장 프레임 대비 평균 절대차(8비트 계조).

    첫 프레임(`prev_gray is None`)이거나 형상이 바뀌면 무한대를 돌려 항상 신규로 판정한다 —
    해상도 변경은 새 장면이지 중복이 아니다.

    Args:
        prev_gray: 직전 저장된 grayscale 프레임. 없으면 None.
        cur_gray: 현재 grayscale 프레임.
    Returns:
        평균 절대차. 비교 불가면 `float("inf")`.
    """
    if prev_gray is None or prev_gray.shape != cur_gray.shape:
        return float("inf")
    # int16 으로 올려 뺀다 — uint8 뺄셈은 음수에서 랩어라운드해 차이를 왜곡한다.
    return float(np.abs(prev_gray.astype(np.int16) - cur_gray.astype(np.int16)).mean())


def judge_frame(
    *,
    free_gb: float,
    min_free_gb: float,
    prev_gray: np.ndarray | None,
    cur_gray: np.ndarray,
    min_mean_abs_diff: float,
) -> SampleVerdict:
    """프레임 저장 여부 판정. 디스크 하한이 신규성보다 **먼저** 걸린다.

    Args:
        free_gb: 저장 대상 파일시스템 가용 공간(GB).
        min_free_gb: 그 하한. 이하이면 무조건 저장하지 않는다.
        prev_gray: 직전 저장 프레임(grayscale) 또는 None.
        cur_gray: 현재 프레임(grayscale).
        min_mean_abs_diff: 신규 판정 임계(평균 절대차).
    Returns:
        `SampleVerdict` — `reason` ∈ {"disk_low", "duplicate", "ok"}.
    """
    if free_gb <= min_free_gb:
        return SampleVerdict(False, "disk_low")
    if mean_abs_diff(prev_gray, cur_gray) < min_mean_abs_diff:
        return SampleVerdict(False, "duplicate")
    return SampleVerdict(True, "ok")


def frame_filename(camera_name: str, index: int, stamp_ns: int) -> str:
    """저장 파일명. 카메라별 폴더 안에서 정렬 가능하고 충돌하지 않도록 index + 타임스탬프.

    Args:
        camera_name: 카메라 식별자(예: "cam0").
        index: 그 카메라의 저장 순번(0부터).
        stamp_ns: 프레임 타임스탬프(나노초).
    Returns:
        `<camera>_<index 6자리>_<stamp_ns>.jpg`
    """
    return f"{camera_name}_{index:06d}_{stamp_ns}.jpg"


def camera_name_from_topic(topic: str) -> str:
    """토픽 이름에서 카메라 식별자를 뽑는다.

    `/cam3/image_raw` → `cam3`. 관례에 맞지 않으면 슬래시를 밑줄로 바꿔 폴더명으로 쓴다
    (빈 이름을 만들지 않는 것이 목적 — 정확한 파싱이 아니다).

    Args:
        topic: ROS 토픽 이름.
    Returns:
        폴더명으로 쓸 수 있는 카메라 식별자.
    """
    parts = [p for p in topic.split("/") if p]
    if len(parts) >= 2:
        return parts[-2]
    return parts[0] if parts else "camera"
