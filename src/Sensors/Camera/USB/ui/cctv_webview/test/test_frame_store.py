# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""FrameStore·HTML 생성 단위 시험 (카메라·ROS 불필요)."""

import pytest

from cctv_webview.frame_store import FrameStore, camera_label, display_name
from cctv_webview.server import build_index_html


@pytest.fixture
def store():
    ticks = iter(range(1000))
    return FrameStore(clock=lambda: float(next(ticks)))


def test_put_and_get(store):
    store.put("cam_f", b"\xff\xd8jpeg")
    data, _stamp, seq = store.get("cam_f")
    assert data == b"\xff\xd8jpeg"
    assert seq == 1


def test_get_missing_camera_is_none(store):
    assert store.get("cam_f") is None


def test_put_overwrites_instead_of_queueing(store):
    """덮어쓰기라야 느린 시청자가 메모리를 무한히 키우지 못한다."""
    for i in range(5):
        store.put("cam_f", bytes([i]))
    data, _stamp, seq = store.get("cam_f")
    assert data == bytes([4])
    assert seq == 5, "seq 는 누적 수신 수를 센다(보관은 1장)"


def test_get_newer_than_blocks_duplicates(store):
    store.put("cam_f", b"a")
    entry = store.get_newer_than("cam_f", 0)
    assert entry is not None
    assert store.get_newer_than("cam_f", entry[2]) is None, "같은 프레임 재전송 금지"
    store.put("cam_f", b"b")
    assert store.get_newer_than("cam_f", entry[2])[0] == b"b"


def test_names_are_sorted(store):
    store.put("cam_r", b"x")
    store.put("cam_f", b"y")
    assert store.names() == ["cam_f", "cam_r"]


def test_stats_reports_age_and_size(store):
    store.put("cam_f", b"1234")          # stamp=0
    stats = store.stats()                # now=1
    assert stats["cam_f"]["bytes"] == 4
    assert stats["cam_f"]["seq"] == 1
    assert stats["cam_f"]["age_s"] == pytest.approx(1.0)


@pytest.mark.parametrize(("topic", "expected"), [
    ("/cam_lf/image_raw/compressed", "cam_lf"),
    ("cam_f/image_raw/compressed", "cam_f"),
    ("/weird", "weird"),
])
def test_camera_label(topic, expected):
    assert camera_label(topic) == expected


def test_display_name_maps_positions():
    assert display_name("cam_lf") == "좌전 LF"
    assert display_name("cam9") == "cam9", "로스터 밖 이름은 그대로 보여준다"


def test_index_html_has_a_stream_per_camera():
    html = build_index_html(["cam_f", "cam_r"], 10.0)
    assert html.count("<img src=") == 2
    assert '/stream/cam_f' in html and '/stream/cam_r' in html
    assert "전면 F" in html and "후면 R" in html


SIX = ["cam_rf", "cam_lf", "cam_rr", "cam_f", "cam_r", "cam_lr"]


def test_six_cameras_use_vehicle_layout():
    """여섯 위치가 다 있으면 차량을 내려다본 배치로 놓는다."""
    html = build_index_html(SIX, 10.0)
    assert 'class="grid vehicle"' in html
    # 좌/우가 화면 좌/우와 일치해야 방향 오독이 없다.
    assert '"lf body rf"' in html and '"lr body rr"' in html
    assert '".  f    ."' in html and '".  r    ."' in html
    for name, area in (("cam_f", "f"), ("cam_lf", "lf"), ("cam_rr", "rr")):
        assert f'style="grid-area:{area}"' in html
        assert f"/stream/{name}" in html


def test_partial_roster_falls_back_to_flow():
    """위치를 모르는 구성이면 배치를 주장하지 않는다(임의 자리 = 방향 오독)."""
    html = build_index_html(["cam_f", "cam_lf"], 10.0)
    assert 'class="grid flow"' in html
    # 타일에 자리를 지정하지 않는다(CSS 규칙 자체는 남아 있어도 무방).
    assert 'style="grid-area:' not in html


def test_unknown_names_fall_back_to_flow():
    html = build_index_html(["cam0", "cam1", "cam2", "cam3", "cam4", "cam5"], 10.0)
    assert 'class="grid flow"' in html


def test_vehicle_layout_keeps_all_six_streams():
    html = build_index_html(SIX, 10.0)
    assert html.count("<img src=") == 6


# ── 검출 저장소 ──────────────────────────────────────────────────────────────

def test_detection_store_snapshot_reports_age():
    from cctv_webview.frame_store import DetectionStore
    ticks = iter([0.0, 0.25])
    store = DetectionStore(clock=lambda: next(ticks))
    store.put("cam_f", [{"x": 1, "y": 2, "w": 3, "h": 4,
                         "label": "person", "conf": 0.9}], 1280, 720)
    snap = store.snapshot()["cam_f"]
    assert snap["width"] == 1280 and snap["height"] == 720
    assert snap["boxes"][0]["label"] == "person"
    assert snap["age_ms"] == pytest.approx(250.0)


def test_detection_store_overwrites_per_camera():
    from cctv_webview.frame_store import DetectionStore
    store = DetectionStore(clock=lambda: 0.0)
    store.put("cam_f", [{"x": 0}], 1280, 720)
    store.put("cam_f", [], 1280, 720)
    assert store.snapshot()["cam_f"]["boxes"] == []


def test_index_html_carries_overlay_targets():
    """타일마다 오버레이 자리와 AI 토글이 있어야 브라우저가 박스를 그린다."""
    html = build_index_html(SIX, 10.0)
    assert html.count('data-ov="') == 6
    assert 'id="ai-toggle"' in html
    assert "/detections" in html
