"""검출 결과 변환·스케줄 로직 — ROS·ultralytics 무의존(단위 테스트 가능).

노드는 모델 호출과 발행만 하고, "어느 카메라 차례인가"·"이 박스를 내보낼 것인가"·"좌표를 어떻게
정리할 것인가" 는 전부 본 모듈이 정한다. GPU 도 카메라도 없이 검증할 수 있어야 하기 때문이다.

핵심 제약(실측 2026-07-28, Jetson Orin NX):
  CUDA 18.8 ms/frame (53.2 FPS) · CPU 509 ms/frame (2.0 FPS) — 27배 차이.
  GPU 는 **한 번에 한 프레임**만 처리하므로 6대를 동시에 돌릴 수 없다. 라운드로빈으로
  한 틱에 한 대씩 처리해 전체 예산을 나눠 쓴다.
"""
from __future__ import annotations

from dataclasses import dataclass

# 추론 총 갱신률 **상한**(Hz). 이 값은 목표치일 뿐 달성치가 아니다 —
# 6대 실서비스 추론은 22.1~24.2 ms 이고 실측 총 처리량은 25.4~29.3 Hz 에 머문다.
# 즉 30 은 "여유" 가 아니라 사실상 포화 설정이다. 다른 노드(주행·센서)에 GPU 를
# 양보하려면 이 값을 낮춰야 한다 — 그냥 두면 탐지기가 계속 물고 있다.
DEFAULT_TOTAL_HZ = 30.0
# 박스 최소 변 길이(픽셀). 주 목적은 `clamp_box()` 가 화면 밖 박스를 접어 만든
# 0~수 px 퇴화 박스 제거다. 4 는 근거 측정이 없는 잠정값 — "원거리 사람" 을 버릴
# 위험이 있으므로 안전 용도로 올리기 전 반드시 실측할 것.
MIN_BOX_SIDE_PX = 4


@dataclass(frozen=True)
class Box:
    """발행 직전 형태의 검출 1건. 좌표는 원본 이미지 픽셀(좌상단 원점)."""

    class_id: int
    class_name: str
    confidence: float
    x: int
    y: int
    width: int
    height: int


def next_camera_index(cursor: int, count: int) -> int:
    """라운드로빈 다음 인덱스.

    Args:
        cursor: 현재 인덱스.
        count: 카메라 수.
    Returns:
        다음 인덱스. `count` 가 0 이하이면 0.
    """
    if count <= 0:
        return 0
    return (cursor + 1) % count


def per_camera_hz(total_hz: float, camera_count: int) -> float:
    """카메라 한 대에 배분되는 **이론** 갱신률(Hz) — 실측치가 아니다.

    라운드로빈이므로 전체 예산을 대수로 나눈 산술값이다. 실측은 이보다 낮다:
    30 Hz 설정·6대 기준 이론 5.0 Hz 인데 실측은 4.77~4.87 Hz(뷰어 없음),
    뷰어 동반 시 4.2 Hz(뷰어 30 Hz)~4.9 Hz(뷰어 10 Hz).

    ⚠ **안전 판단에 이 반환값을 쓰지 말 것.** 실측 Hz 는 `verify_live` 로 잰다.
    """
    if camera_count <= 0:
        return 0.0
    return total_hz / camera_count


def keep_class(class_id: int, class_filter: tuple[int, ...] | list[int]) -> bool:
    """클래스 필터 통과 여부. 필터가 비어 있으면 전부 통과."""
    if not class_filter:
        return True
    return class_id in class_filter


def clamp_box(x1: float, y1: float, x2: float, y2: float,
              img_width: int, img_height: int) -> tuple[int, int, int, int]:
    """박스를 이미지 경계 안으로 자르고 정수 픽셀로 만든다.

    모델은 이미지 밖으로 삐져나온 좌표를 낼 수 있다. 그대로 발행하면 소비자가
    음수 인덱스로 잘라내다 터진다.

    Returns:
        `(x, y, width, height)` — width/height 는 0 이상.
    """
    left = max(0, min(int(round(x1)), img_width))
    top = max(0, min(int(round(y1)), img_height))
    right = max(0, min(int(round(x2)), img_width))
    bottom = max(0, min(int(round(y2)), img_height))
    if right < left:
        left, right = right, left
    if bottom < top:
        top, bottom = bottom, top
    return left, top, right - left, bottom - top


def build_boxes(rows, names: dict[int, str], class_filter, img_width: int,
                img_height: int, min_side_px: int = MIN_BOX_SIDE_PX) -> list[Box]:
    """모델 출력 행들을 발행용 `Box` 목록으로 변환한다.

    Args:
        rows: `(class_id, confidence, x1, y1, x2, y2)` 반복자. 좌표는 원본 이미지 기준.
        names: 클래스 인덱스 → 이름.
        class_filter: 통과시킬 클래스 인덱스들(비면 전부).
        img_width: 원본 폭.
        img_height: 원본 높이.
        min_side_px: 이보다 작은 변을 가진 박스는 버린다.
    Returns:
        신뢰도 내림차순 `Box` 목록.
    """
    boxes = []
    for class_id, confidence, x1, y1, x2, y2 in rows:
        class_id = int(class_id)
        if not keep_class(class_id, class_filter):
            continue
        x, y, width, height = clamp_box(x1, y1, x2, y2, img_width, img_height)
        if width < min_side_px or height < min_side_px:
            continue
        boxes.append(Box(class_id=class_id,
                         class_name=names.get(class_id, str(class_id)),
                         confidence=float(confidence),
                         x=x, y=y, width=width, height=height))
    boxes.sort(key=lambda b: b.confidence, reverse=True)
    return boxes


def resolve_class_filter(names: dict[int, str], wanted: list[str]) -> tuple[int, ...]:
    """클래스 **이름** 목록을 모델 인덱스로 바꾼다.

    이름으로 설정하는 이유: 사전학습 COCO 모델의 person 은 0 이지만, 자체 학습 모델에서는
    다른 번호가 된다. 인덱스를 파라미터로 굳히면 모델 교체 때 조용히 엉뚱한 클래스를 본다.

    Args:
        names: 모델의 인덱스 → 이름 매핑.
        wanted: 원하는 클래스 이름들. 비어 있으면 전체 허용(빈 튜플).
    Returns:
        인덱스 튜플. 이름이 모델에 없으면 그 이름은 제외된다.
    """
    if not wanted:
        return ()
    lookup = {name: index for index, name in names.items()}
    return tuple(lookup[n] for n in wanted if n in lookup)


def missing_class_names(names: dict[int, str], wanted: list[str]) -> list[str]:
    """`wanted` 중 모델에 없는 이름들 — 기동 시 경고용.

    조용히 무시하면 "탐지가 안 된다"는 증상만 남고 원인을 찾기 어렵다.
    """
    available = set(names.values())
    return [n for n in wanted if n not in available]
