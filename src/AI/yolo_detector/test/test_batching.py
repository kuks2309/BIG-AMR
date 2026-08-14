"""배치 추론 회귀 시험 — ROS 노드를 띄우지 않고 메서드를 직접 호출한다.

`YoloDetectorNode.__init__` 은 YOLO 가중치를 적재하므로 시험에서 인스턴스를 만들지 않는다.
대신 필요한 속성만 가진 대역(stub)에 **언바운드 메서드**를 적용해 로직만 검증한다.

방어 대상은 2026-08-06 에 고친 결함들이다(ADR 2026-08-06 · 인벤토리 §구조 관찰):
  ② 한 틱에 한 대만 처리해 수신 프레임의 약 83%를 버리던 것
  ③ 카메라당 검출률이 `total_hz/N` 나눗셈에 숨어 있던 것
  ④ `_cursor` 와 `_latest.pop` 두 상태가 순서를 정하던 것
"""
import types

import pytest

from yolo_detector.detector_node import (LEGACY_TOTAL_HZ_PARAM, YoloDetectorNode,
                                         camera_name_from_topic)

TOPICS = [f"/cam{i}/image_raw" for i in range(6)]


class _Logger:
    def __init__(self):
        self.warns, self.errors, self.infos = [], [], []

    def warning(self, m):
        self.warns.append(m)

    def error(self, m):
        self.errors.append(m)

    def info(self, m):
        self.infos.append(m)


def _tick_stub(latest):
    """`_on_tick` 이 쓰는 최소 속성만 가진 대역. 배치로 넘어간 목록을 기록한다."""
    stub = types.SimpleNamespace(_topics=list(TOPICS), _latest=dict(latest), batched=None)
    stub._infer_batch_and_publish = lambda pending: setattr(stub, "batched", list(pending))
    return stub


# ── ② 한 틱에 들어온 프레임을 전부 묶는다 ───────────────────────────────────
def test_tick_batches_every_pending_frame():
    """회귀 방어 본체 — 종전에는 한 대만 처리하고 `return` 해 나머지를 버렸다."""
    stub = _tick_stub({t: f"msg{i}" for i, t in enumerate(TOPICS)})
    YoloDetectorNode._on_tick(stub)
    assert len(stub.batched) == 6
    assert [t for t, _ in stub.batched] == TOPICS


def test_tick_drains_latest_so_frames_are_not_reused():
    """소비한 프레임은 사라져야 한다 — 남으면 같은 장을 두 번 추론한다."""
    stub = _tick_stub({t: "msg" for t in TOPICS})
    YoloDetectorNode._on_tick(stub)
    assert stub._latest == {}


def test_tick_with_no_frames_does_not_call_model():
    stub = _tick_stub({})
    YoloDetectorNode._on_tick(stub)
    assert stub.batched is None


# ── ④ 커서 없이도 일부 카메라만 와도 정상 동작 ─────────────────────────────
def test_tick_batches_only_available_cameras():
    """3대만 도착해도 그 3장을 한 배치로 넘긴다(빈 카메라를 기다리지 않는다)."""
    stub = _tick_stub({TOPICS[1]: "a", TOPICS[3]: "b", TOPICS[5]: "c"})
    YoloDetectorNode._on_tick(stub)
    assert [t for t, _ in stub.batched] == [TOPICS[1], TOPICS[3], TOPICS[5]]


def test_tick_never_starves_a_camera_that_keeps_arriving():
    """회귀 방어 — 커서 방식에서는 한 대만 계속 오면 그 대만 처리되고 순서가 헛돌았다.

    배치는 도착한 것을 전부 가져가므로 '차례' 개념 자체가 없다. 두 틱 연속으로
    같은 카메라만 와도 매 틱 처리된다.
    """
    stub = _tick_stub({TOPICS[4]: "only"})
    YoloDetectorNode._on_tick(stub)
    assert [t for t, _ in stub.batched] == [TOPICS[4]]
    stub._latest[TOPICS[4]] = "again"
    stub.batched = None
    YoloDetectorNode._on_tick(stub)
    assert [t for t, _ in stub.batched] == [TOPICS[4]]


# ── 배치 추론: 디코드 실패·개수 불일치 방어 ────────────────────────────────
def _batch_stub(decoded, results, logger=None):
    stub = types.SimpleNamespace(
        _imgsz=640, _conf=0.35, _iou=0.45, _device="cuda",
        _batch_sizes=[], published=[], _logger=logger or _Logger())
    stub.get_logger = lambda: stub._logger
    stub._decode = lambda topic, msg: decoded.get(topic)
    stub._model = types.SimpleNamespace(predict=lambda frames, **kw: list(results))
    stub._publish_one = lambda t, m, f, r, ms: stub.published.append((t, r, ms))
    return stub


def test_undecodable_frame_is_dropped_but_batch_survives():
    """한 장이 깨져도 나머지는 추론한다 — 종전에는 장별 호출이라 자연히 격리됐다."""
    decoded = {TOPICS[0]: "frameA", TOPICS[1]: None, TOPICS[2]: "frameC"}
    stub = _batch_stub(decoded, ["rA", "rC"])
    YoloDetectorNode._infer_batch_and_publish(
        stub, [(t, f"msg{t}") for t in TOPICS[:3]])
    assert [t for t, _, _ in stub.published] == [TOPICS[0], TOPICS[2]]


def test_all_frames_undecodable_publishes_nothing():
    stub = _batch_stub({t: None for t in TOPICS[:3]}, [])
    YoloDetectorNode._infer_batch_and_publish(
        stub, [(t, "msg") for t in TOPICS[:3]])
    assert stub.published == []
    assert stub._batch_sizes == []


def test_result_count_mismatch_publishes_nothing():
    """결과 개수가 어긋나면 어느 결과가 어느 카메라인지 보장할 수 없다.

    `zip` 은 조용히 짧은 쪽에서 끊기므로, 그대로 두면 **다른 카메라의 검출을
    남의 토픽에 발행**하게 된다 — 안전 오인식이라 폐기가 맞다.
    """
    logger = _Logger()
    decoded = {t: f"frame{t}" for t in TOPICS[:3]}
    stub = _batch_stub(decoded, ["r0", "r1"], logger)      # 3장 넣고 2건만 돌아옴
    YoloDetectorNode._infer_batch_and_publish(
        stub, [(t, "msg") for t in TOPICS[:3]])
    assert stub.published == []
    assert any("개수 불일치" in m for m in logger.errors)


def test_per_frame_ms_is_batch_time_divided_by_count():
    """배치 1회 비용을 장수로 나눠 기록해야 배치 1 시절 수치와 비교가 된다."""
    decoded = {t: f"frame{t}" for t in TOPICS[:4]}
    stub = _batch_stub(decoded, ["r0", "r1", "r2", "r3"])
    YoloDetectorNode._infer_batch_and_publish(
        stub, [(t, "msg") for t in TOPICS[:4]])
    per_frame = [ms for _, _, ms in stub.published]
    assert len(set(per_frame)) == 1                # 같은 배치는 같은 값
    assert per_frame[0] >= 0.0
    assert stub._batch_sizes == [4]


def test_inference_exception_publishes_nothing():
    stub = _batch_stub({t: "f" for t in TOPICS[:2]}, [])
    def boom(frames, **kw):
        raise RuntimeError("CUDA out of memory")
    stub._model = types.SimpleNamespace(predict=boom)
    YoloDetectorNode._infer_batch_and_publish(stub, [(t, "msg") for t in TOPICS[:2]])
    assert stub.published == []
    assert any("배치 추론 실패" in m for m in stub._logger.errors)


# ── ③ 구 파라미터가 조용히 의미를 바꾸지 않는다 ─────────────────────────────
def _hz_stub(detect_hz, legacy, ncam=6):
    values = {"detect_hz": detect_hz, LEGACY_TOTAL_HZ_PARAM: legacy}
    stub = types.SimpleNamespace(_topics=TOPICS[:ncam], _logger=_Logger())
    stub.get_parameter = lambda n: types.SimpleNamespace(value=values[n])
    stub.get_logger = lambda: stub._logger
    return stub


def test_detect_hz_used_directly_when_no_legacy_param():
    stub = _hz_stub(10.0, -1.0)
    assert YoloDetectorNode._resolve_detect_hz(stub) == pytest.approx(10.0)
    assert stub._logger.warns == []


def test_legacy_total_hz_is_converted_and_warned():
    """회귀 방어 본체 — 환산 없이 받으면 카메라당 검출률이 조용히 6배가 된다."""
    stub = _hz_stub(10.0, 30.0)
    assert YoloDetectorNode._resolve_detect_hz(stub) == pytest.approx(5.0)
    assert any(LEGACY_TOTAL_HZ_PARAM in m for m in stub._logger.warns)


def test_legacy_conversion_scales_with_camera_count():
    """카메라 수가 다르면 환산값도 달라야 한다 — 상수로 굳히면 안 된다."""
    assert YoloDetectorNode._resolve_detect_hz(_hz_stub(10.0, 30.0, ncam=3)) \
        == pytest.approx(10.0)


# ── 보조 ────────────────────────────────────────────────────────────────────
def test_camera_name_extraction_unchanged():
    assert camera_name_from_topic("/cam_rf/image_raw") == "cam_rf"
