"""검출 결과 변환 로직 — ROS·ultralytics 무의존(단위 테스트 가능).

노드는 모델 호출과 발행만 하고, "이 박스를 내보낼 것인가"·"좌표를 어떻게 정리할 것인가" 는
전부 본 모듈이 정한다. GPU 도 카메라도 없이 검증할 수 있어야 하기 때문이다.

핵심 제약(실측 2026-08-06, Jetson Orin NX 16GB · yolov8n · imgsz=640 · cuda):
  프레임당 CPU 는 **한 번에 몇 장을 넘기느냐**로 결정된다 — 배치 1 은 18.83 ms,
  배치 6 은 5.68 ms(3.3배). 원인은 계산이 아니라 **호출당 고정비**다:
  `predict` 19.10 ms 중 libtorch 커널 런치가 14.16 ms(74%)이고, 동기화를 제외해도
  같은 14.16 ms 다(= CPU 는 GPU 를 기다리는 게 아니라 커널을 쏘고 있다).
  런치는 호출당 발생하므로 6장을 한 호출에 묶으면 프레임당 6분의 1이 된다.

  ⚠ 종전 이 자리에 있던 "GPU 는 한 번에 한 프레임만 처리하므로 6대를 동시에 돌릴 수 없다"
     는 **검증 없이 적힌 추정이었고 위 실측으로 반증됐다**(ADR 2026-08-06). 그 문장 위에
     라운드로빈이 세워져 수신 프레임의 약 83%를 버리고 있었다.
  ⚠ 효과 없음이 확인된 것(재시도 금지): FP16(`half=True`)·입력 해상도 축소(640→416)는
     차이 1% 이내. 반면 CPU 로 떨어지면 509 ms/frame(2.0 FPS)로 27배 느려진다.
"""
from __future__ import annotations

from dataclasses import dataclass

# 카메라 **한 대당** 검출률(Hz). 배치 추론은 한 틱에 전 카메라를 처리하므로
# 타이머 주기가 곧 카메라당 검출률이다 — 대수로 나누지 않는다.
# 10 의 근거: 실측 여력이 배치6 = 90.03 fps ÷ 6대 = 카메라당 15 fps 이고,
# 종전 실효치(6대 30 Hz 합산 → 카메라당 약 4.8 Hz)의 2배다.
# 올리기 전 `verify_live` 로 실측할 것 — 이 값은 목표치이지 달성치가 아니다.
DEFAULT_DETECT_HZ = 10.0
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


def per_camera_hz(total_hz: float, camera_count: int) -> float:
    """**구 파라미터 `total_hz` 환산 전용** — 신규 코드는 `detect_hz` 를 그대로 쓴다.

    라운드로빈 시절 `total_hz` 는 전 카메라 **합산** 추론률이었고, 카메라당 값은 대수로
    나눈 이 산술값이었다. 배치 추론에서는 한 틱이 전 카메라를 처리하므로 나눌 필요가 없어
    파라미터가 `detect_hz`(카메라당)로 바뀌었다(ADR 2026-08-06).

    구 설정 파일을 그대로 띄우면 의미가 조용히 6배로 바뀌므로, 노드가 `total_hz` 를 받으면
    이 함수로 환산하고 경고한다. 그 하위호환 경로 하나만을 위해 남긴다.

    Returns:
        `total_hz / camera_count`. `camera_count` 가 0 이하이면 0.0.
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
