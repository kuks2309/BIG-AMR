# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""검출 박스 오버레이의 순수 로직 — Qt·ROS 무의존이라 화면 없이 단위 테스트할 수 있다.

담당은 둘뿐이다:
  ① **좌표 변환** — 검출은 원본 해상도 픽셀로 오고, 화면은 `KeepAspectRatio` 로 축소·중앙배치된다.
  ② **나이 판정** — 검출은 카메라당 약 5 Hz 인데 영상은 약 21 fps 다. 같은 박스가 여러 프레임에
     재사용되므로, 얼마나 낡았는지를 화면이 드러내야 한다.

②가 왜 필수인가: 사람이 1.4 m/s 로 걸으면 박스 나이 Δt 동안 어긋남은 `1.4·Δt / 어깨폭(0.5 m)`
배다 — 이 비율은 거리·화각·해상도와 무관하다(둘 다 1/거리로 스케일). 실측 기준 최악 약 266 ms
이면 **몸통 폭의 0.74배**가 밀린다. 낡은 박스를 신선한 것처럼 그리면 "박스 밖 = 안전" 으로
오독된다(2026-07-28 적대적 설계 검토 F2, docs/adr/2026-07-28-cctv-ai-overlay-toggle.md).
"""
from __future__ import annotations

from dataclasses import dataclass

# 나이 임계(ms). 산출 = **검출 1라운드 간격 + 취득→발행 지연**.
#   기본 10 Hz 설정: 카메라당 4.9 Hz → 204 ms + 약 60 ms = 최악 **약 264 ms**(몸통 폭 0.74배)
#   render_hz:=30   : 카메라당 4.2 Hz → 238 ms + 약 60 ms = 최악 **약 298 ms**(0.83배)
# STALE 상한 400 은 그 최악값에 여유를 더한 값이다.
#
# ⚠ FRESH 150 은 **근거 없는 임의 마진**이다 — 지연 단독(55~67 ms)도, 지연+반주기(약 160 ms)도
#   아니다. 게다가 평균 나이(약 162~179 ms)가 이 값을 넘어 **정상 상태의 박스 대부분이 STALE
#   (황색 점선)로 보인다.** 재측정 전까지 근거 미확립.
# ⚠ 지연 55~67 ms 는 뷰어 30 Hz 조건 측정값이며 10 Hz 조건에서 재측정된 바 없다.
FRESH_MS = 150.0
STALE_MS = 400.0

FRESH = "fresh"      # 실선으로 그린다
STALE = "stale"      # 점선·저채도로 그려 "낡았다"를 드러낸다
EXPIRED = "expired"  # 그리지 않는다 — 없는 정보를 있는 것처럼 두지 않는다


@dataclass(frozen=True)
class ViewBox:
    """위젯 좌표로 변환된, 그릴 준비가 된 박스."""

    x: int
    y: int
    width: int
    height: int
    label: str
    freshness: str


def classify_age(age_ms: float) -> str:
    """박스 나이 → 표시 등급.

    :param age_ms: 표시 시각 − 검출 프레임 취득 시각(ms). 음수면 시계 역전이므로 신선 취급.
    :returns: `FRESH` / `STALE` / `EXPIRED`
    """
    if age_ms < FRESH_MS:
        return FRESH
    if age_ms < STALE_MS:
        return STALE
    return EXPIRED


def map_box(box, source_size, pixmap_size, label_size):
    """원본 픽셀 박스 → 위젯 좌표 박스.

    레터박스 보정은 호출자가 `pixmap_size != label_size` 를 넘길 때만 적용된다.
    **현재 유일한 프로덕션 호출부**(`main_window._paint_boxes`)는 축소된 픽스맵 **위에** 직접
    그리므로 원점이 픽스맵 좌상단이고, 두 값을 같게 넘겨 오프셋이 항상 0 이다. 박스를 `QLabel`
    좌표로 그리는 호출자가 생기면(그 경우 `AlignCenter` 로 여백이 생긴다) 이 보정이 살아난다.

    ⚠ 배율은 **실제 pixmap 크기로 나눠서** 구한다. `scaled()` 는 내림 처리를 하므로
    `min(W_label/W_src, H_label/H_src)` 로 계산한 값과 어긋날 수 있다(적대적 검토 지적).

    :param box: `(x, y, w, h)` 원본 이미지 픽셀.
    :param source_size: `(width, height)` 검출이 수행된 원본 해상도.
    :param pixmap_size: `(width, height)` 화면에 실제로 그려진 픽스맵 크기.
    :param label_size: `(width, height)` 픽스맵을 담은 위젯 크기.
    :returns: `(x, y, w, h)` 위젯 좌표. 원본 크기가 0이면 None.
    """
    src_w, src_h = source_size
    pix_w, pix_h = pixmap_size
    lab_w, lab_h = label_size
    if src_w <= 0 or src_h <= 0 or pix_w <= 0 or pix_h <= 0:
        return None

    scale_x = pix_w / src_w
    scale_y = pix_h / src_h
    off_x = (lab_w - pix_w) / 2.0
    off_y = (lab_h - pix_h) / 2.0

    x, y, w, h = box
    return (int(round(off_x + x * scale_x)),
            int(round(off_y + y * scale_y)),
            int(round(w * scale_x)),
            int(round(h * scale_y)))


def build_view_boxes(detections, source_size, pixmap_size, label_size, age_ms):
    """검출 목록을 그릴 수 있는 `ViewBox` 목록으로 바꾼다. 만료면 빈 목록.

    :param detections: `ai_msgs/Detection` 유사 객체들(`class_name`·`confidence`·`x`·`y`·`width`·`height`).
    :param source_size: 검출 기준 원본 해상도 `(w, h)`.
    :param pixmap_size: 실제 표시 픽스맵 `(w, h)`.
    :param label_size: 위젯 `(w, h)`.
    :param age_ms: 박스 나이(ms).
    :returns: `ViewBox` 목록.
    """
    freshness = classify_age(age_ms)
    if freshness == EXPIRED:
        return []
    out = []
    for det in detections:
        mapped = map_box((det.x, det.y, det.width, det.height),
                         source_size, pixmap_size, label_size)
        if mapped is None:
            continue
        x, y, w, h = mapped
        if w <= 0 or h <= 0:
            continue
        out.append(ViewBox(x=x, y=y, width=w, height=h,
                           label=f"{det.class_name} {det.confidence:.2f}",
                           freshness=freshness))
    return out


def detector_status(publisher_count: int, seconds_since_message: float | None,
                    expected_period_s: float) -> tuple[str, bool]:
    """탐지기 상태 문구와 '정상 여부'.

    박스가 0개인 상황은 세 가지가 전부 같은 화면으로 보인다 — 사람이 없다 / 탐지기가 죽었다 /
    아직 첫 결과가 안 왔다. 운용자가 이를 구별할 수 없으면 "사람 없음" 으로 오독한다
    (적대적 검토 F6·F11).

    :param publisher_count: 검출 토픽의 발행자 수.
    :param seconds_since_message: 마지막 검출 수신 후 경과(초). 한 번도 못 받았으면 None.
    :param expected_period_s: 정상 갱신 주기(초).
    :returns: `(문구, 정상여부)`
    """
    if publisher_count == 0:
        return "AI: 탐지기 없음", False
    if seconds_since_message is None:
        return "AI: 대기 중", False
    if seconds_since_message == float("inf"):
        # 감시 대상 중 한 번도 결과를 못 받은 카메라가 있다 — 부분 고장이다.
        return "AI: 일부 카메라 무응답", False
    if seconds_since_message > 2.0 * expected_period_s:
        return f"AI: 응답 없음 ({seconds_since_message:.0f}s)", False
    return "AI: 감시 중", True
