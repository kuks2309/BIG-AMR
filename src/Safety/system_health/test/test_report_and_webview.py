"""보고서 집계와 웹 대시보드 검증 — 실제 HTTP 요청까지 포함(포트 0 사용).

핵심은 **읽기 전용 불변식**이다: 대시보드는 로그를 읽기만 하고 어떤 것도 제어하지 않으므로
POST 를 받지 않아야 한다. 그리고 표본이 없거나 값이 빠진 상태에서도 죽지 않아야 한다 —
감시 화면이 500 을 내면 사람이 상태를 못 본다.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

from system_health import report, webview

_T0 = 1785200000.0


def _rec(i, *, level="OK", cpu=10.0, tj=50.0, avail=8000.0, swap=0.0, free=36.0, findings=()):
    return {
        "iso_time": f"2026-07-28T12:{i // 60:02d}:{i % 60:02d}",
        "epoch_s": _T0 + i * 5,
        "level": level,
        "cpu_total_pct": cpu,
        "temperatures_c": {"cpu-thermal": tj - 1, "tj-thermal": tj},
        "memory": {"available_mb": avail, "swap_used_mb": swap},
        "disks": [{"path": "/", "free_gb": free}],
        "fan": {"pwm": 1, "rpm": None},
        "findings": list(findings),
    }


def _write(tmp_path, recs, name="health-2026-07-28.jsonl"):
    d = tmp_path / "log"
    d.mkdir(exist_ok=True)
    (d / name).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n", encoding="utf-8")
    return d


# ── report 집계 ──────────────────────────────────────────────────────────────


def test_load_records_is_time_sorted(tmp_path):
    d = _write(tmp_path, [_rec(2), _rec(0), _rec(1)])
    got = report.load_records(d)
    assert [r["epoch_s"] for r in got] == sorted(r["epoch_s"] for r in got)


def test_broken_line_is_skipped_not_fatal(tmp_path):
    # 프로세스가 쓰는 중 끊기면 마지막 줄이 부분 기록될 수 있다.
    d = _write(tmp_path, [_rec(0), _rec(1)])
    with (d / "health-2026-07-28.jsonl").open("a", encoding="utf-8") as h:
        h.write('{"iso_time": "부분기록')
    assert len(report.load_records(d)) == 2


def test_missing_dir_is_empty_not_error(tmp_path):
    assert report.load_records(tmp_path / "없음") == []
    assert report.load_files(tmp_path / "없음") == []


def test_gap_stats_counts_missing_samples(tmp_path):
    # 0,5,10 … 인데 하나를 빼면 10초 간격이 생긴다 → 표본 1개 누락으로 세야 한다.
    recs = [_rec(0), _rec(1), _rec(3), _rec(4)]
    g = report.gap_stats(report.sample_gaps(recs), 5.0)
    assert len(g["gaps_over"]) == 1
    assert g["missing_estimate"] == 1


def test_gap_stats_clean_run_has_no_gaps():
    recs = [_rec(i) for i in range(10)]
    g = report.gap_stats(report.sample_gaps(recs), 5.0)
    assert g["gaps_over"] == []
    assert g["missing_estimate"] == 0
    assert g["mean"] == pytest.approx(5.0)


def test_gap_stats_empty_is_safe():
    assert report.gap_stats([], 5.0)["count"] == 0


def test_level_and_finding_counts():
    recs = [
        _rec(0),
        _rec(1, level="WARN", findings=[{"key": "cpu", "level": "WARN"}]),
        _rec(2, level="ERROR", findings=[{"key": "cpu", "level": "ERROR"},
                                         {"key": "swap_used", "level": "WARN"}]),
    ]
    assert report.level_counts(recs) == {"OK": 1, "WARN": 1, "ERROR": 1}
    fc = report.finding_counts(recs)
    assert fc["cpu"] == {"WARN": 1, "ERROR": 1}
    assert fc["swap_used"] == {"WARN": 1}


def test_resource_ranges_tracks_min_max_last():
    recs = [_rec(0, tj=50.0), _rec(1, tj=70.0), _rec(2, tj=60.0)]
    r = report.resource_ranges(recs)["최고온도(°C)"]
    assert (r["min"], r["max"], r["last"]) == (50.0, 70.0, 60.0)


def test_report_flags_single_file_rotation_gap(tmp_path):
    d = _write(tmp_path, [_rec(i) for i in range(5)])
    text = report.format_report(d, 5.0)
    assert "자정 회전 경로가 아직 실시간 검증되지 않았다" in text


def test_report_does_not_flag_when_rotated(tmp_path):
    d = _write(tmp_path, [_rec(i) for i in range(3)])
    (d / "health-2026-07-29.jsonl").write_text(
        json.dumps(_rec(5), ensure_ascii=False) + "\n", encoding="utf-8")
    assert "실시간 검증되지 않았다" not in report.format_report(d, 5.0)


def test_report_on_empty_dir_says_so(tmp_path):
    assert "표본 없음" in report.format_report(tmp_path / "없음", 5.0)


# ── webview 페이로드 ─────────────────────────────────────────────────────────


def test_latest_payload_marks_empty():
    assert webview.latest_payload([])["empty"] is True


def test_latest_payload_uses_span_for_whole_log_info():
    """`records` 는 꼬리만 받는다 — 기록 전체 정보는 `span` 이 담당한다."""
    p = webview.latest_payload([_rec(9)], {"first_time": "2026-07-28T00:00:00",
                                           "files": 2, "bytes": 1234})
    assert p["iso_time"] == _rec(9)["iso_time"]
    assert p["_first_time"] == "2026-07-28T00:00:00"
    assert p["_files"] == 2 and p["_bytes"] == 1234


def test_history_keeps_none_instead_of_zero():
    """없는 값을 0 으로 채우면 '한가함'으로 오독된다 — None 을 그대로 보내야 한다."""
    r = _rec(0)
    del r["cpu_total_pct"]          # 첫 표본에는 CPU% 가 없다
    h = webview.history_payload([r], 10)
    assert h["cpu"] == [None]
    assert h["temp"] == [50.0]


def test_history_respects_limit():
    h = webview.history_payload([_rec(i) for i in range(50)], 5)
    assert len(h["t"]) == 5 and len(h["cpu"]) == 5


def test_history_caps_absurd_request():
    h = webview.history_payload([_rec(i) for i in range(3)], 10**9)
    assert len(h["t"]) == 3


# ── 실제 HTTP ────────────────────────────────────────────────────────────────


@pytest.fixture
def server(tmp_path):
    d = _write(tmp_path, [_rec(i, level="WARN" if i == 2 else "OK",
                               findings=[{"key": "cpu", "level": "WARN", "value": 90.0,
                                          "message": "테스트 경보"}] if i == 2 else [])
                          for i in range(5)])
    srv = webview.make_server(d, bind="127.0.0.1", port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    host, port = srv.server_address[:2]
    yield f"http://{host}:{port}"
    srv.shutdown()
    srv.server_close()


def _get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.status, r.read().decode("utf-8")


def test_root_serves_html(server):
    code, body = _get(server + "/")
    assert code == 200
    assert "AMR PC 자원 감시" in body
    assert "읽기 전용" in body


def test_api_latest_returns_last_sample(server):
    _, body = _get(server + "/api/latest")
    data = json.loads(body)
    assert data["iso_time"] == _rec(4)["iso_time"]   # 마지막 표본이 나와야 한다
    assert data["_first_time"] == _rec(0)["iso_time"]
    assert data["_files"] == 1


def test_api_history_returns_series(server):
    _, body = _get(server + "/api/history?n=3")
    data = json.loads(body)
    assert len(data["t"]) == 3
    assert set(data) == {"t", "temp", "cpu", "gpu", "mem", "swaprate", "curr"}


def test_api_report_is_text(server):
    _, body = _get(server + "/api/report")
    assert "운영 결과" in body and "주기 지터" in body


def test_unknown_path_is_404(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(server + "/nope")
    assert e.value.code == 404


def test_post_is_rejected(server):
    """읽기 전용 불변식 — 쓰기 메서드를 받아들이면 안 된다."""
    req = urllib.request.Request(server + "/", data=b"x", method="POST")
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req, timeout=10)
    assert e.value.code in (400, 405, 501)


def test_bad_history_param_does_not_crash_server(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(server + "/api/history?n=abc")
    assert e.value.code == 500
    # 서버가 살아 있어야 한다 — 한 요청 실패가 감시 화면 전체를 죽이면 안 된다.
    assert _get(server + "/api/latest")[0] == 200


def test_empty_log_dir_serves_without_error(tmp_path):
    srv = webview.make_server(tmp_path / "빈폴더", bind="127.0.0.1", port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        host, port = srv.server_address[:2]
        base = f"http://{host}:{port}"
        assert _get(base + "/")[0] == 200
        assert json.loads(_get(base + "/api/latest")[1])["empty"] is True
    finally:
        srv.shutdown()
        srv.server_close()


def test_history_reports_gpu_and_swap_rate():
    """GPU 는 Jetson 필수 항목이고, 스왑은 **활동량**을 그린다(사용량 아님)."""
    r = _rec(0)
    r["gpu"] = {"load_pct": 42.5, "freq_hz": 918000000, "max_freq_hz": 918000000}
    r["swap_rate_pages_s"] = {"in": 3.0, "out": 7.0}
    h = webview.history_payload([r], 10)
    assert h["gpu"] == [42.5]
    assert h["swaprate"] == [10.0]          # in + out 합산


def test_history_gpu_none_when_node_absent():
    h = webview.history_payload([_rec(0)], 10)   # gpu 키 없음
    assert h["gpu"] == [None] and h["swaprate"] == [None]


def test_filter_since_scopes_the_window():
    recs = [_rec(i) for i in range(6)]
    kept = report.filter_since(recs, recs[3]["iso_time"])
    assert len(kept) == 3 and kept[0]["iso_time"] == recs[3]["iso_time"]


def test_filter_since_none_keeps_all():
    recs = [_rec(i) for i in range(4)]
    assert len(report.filter_since(recs, None)) == 4


def test_report_since_excludes_earlier_run_gap(tmp_path):
    """별개 실행 사이의 공백이 결손으로 집계되지 않아야 한다.

    2026-07-28 시험 운전 평가에서 실제로 이 오해가 났다 — 수집률 23.7 % 로 보였으나
    앞서 돌린 짧은 시험들과의 공백(8094s)이 원인이었다.
    """
    old = [_rec(i) for i in range(3)]
    new = [_rec(i) for i in range(700, 704)]      # 큰 시간 공백 뒤 재시작
    d = _write(tmp_path, old + new)
    full = report.format_report(d, 5.0)
    scoped = report.format_report(d, 5.0, since=new[0]["iso_time"])
    assert "결손 의심(7.5s 초과 간격): 1건" in full
    assert "결손 의심(7.5s 초과 간격): 0건" in scoped


# ── 꼬리 읽기 (화면 갱신 경로의 비용) ────────────────────────────────────────


def test_tail_records_returns_only_last_n(tmp_path):
    d = _write(tmp_path, [_rec(i) for i in range(200)])
    got = report.tail_records(d, 5)
    assert len(got) == 5
    assert got[-1]["iso_time"] == _rec(199)["iso_time"]
    assert got[0]["iso_time"] == _rec(195)["iso_time"]


def test_tail_records_spans_multiple_files(tmp_path):
    d = _write(tmp_path, [_rec(i) for i in range(3)], name="health-2026-07-28.jsonl")
    (d / "health-2026-07-29.jsonl").write_text(
        "\n".join(json.dumps(_rec(i)) for i in range(100, 102)) + "\n", encoding="utf-8")
    got = report.tail_records(d, 4)
    assert len(got) == 4      # 신 파일 2개 + 구 파일 2개


def test_tail_records_handles_file_shorter_than_block(tmp_path):
    d = _write(tmp_path, [_rec(0)])
    assert len(report.tail_records(d, 10)) == 1


def test_tail_records_does_not_lose_first_line_of_small_file(tmp_path):
    # 블록 경계 처리에서 파일 선두까지 읽었으면 첫 줄을 버리면 안 된다.
    d = _write(tmp_path, [_rec(0), _rec(1)])
    got = report.tail_records(d, 5)
    assert [r["iso_time"] for r in got] == [_rec(0)["iso_time"], _rec(1)["iso_time"]]


def test_tail_records_empty_dir(tmp_path):
    assert report.tail_records(tmp_path / "없음", 5) == []


def test_list_log_paths_does_not_read_contents(tmp_path):
    d = _write(tmp_path, [_rec(i) for i in range(3)])
    paths = report.list_log_paths(d)
    assert len(paths) == 1 and paths[0].name == "health-2026-07-28.jsonl"


def test_log_span_reads_only_first_line(tmp_path):
    d = _write(tmp_path, [_rec(i) for i in range(50)])
    span = report.log_span(d)
    assert span["files"] == 1
    assert span["first_time"] == _rec(0)["iso_time"]
    assert span["bytes"] > 0


def test_log_span_on_empty_dir(tmp_path):
    span = report.log_span(tmp_path / "없음")
    assert span == {"files": 0, "bytes": 0, "first_time": None}


def test_history_includes_current_rail():
    r = _rec(0)
    r["power"] = {"VDD_IN": {"mv": 11600, "ma": 1580, "mw": 18328.0}}
    h = webview.history_payload([r], 10)
    assert h["curr"] == [1580]


def test_history_current_none_without_sensor():
    assert webview.history_payload([_rec(0)], 10)["curr"] == [None]


# ── 목표 주기 0·음수 방어 ────────────────────────────────────────────────────


def test_gap_stats_survives_zero_interval():
    """0 을 나눗셈에 그대로 쓰면 보고서 생성이 통째로 중단된다."""
    stats = report.gap_stats([5.0, 5.0], 0.0)
    assert stats["missing_estimate"] == 0
    assert stats["gaps_over"] == []


def test_format_report_survives_zero_interval(tmp_path):
    d = _write(tmp_path, [_rec(i) for i in range(5)])
    text = report.format_report(d, 0.0)
    assert "운영 결과" in text
    assert "하루 추정" not in text   # 목표 주기가 없으면 추정도 내지 않는다


# ── --since 와 로그 성장률의 구간 일치 ───────────────────────────────────────


def test_growth_rate_is_not_inflated_by_since(tmp_path):
    """분자는 파일 전체 바이트인데 분모만 잘리면 표본당 바이트가 부풀려진다."""
    recs = [_rec(i) for i in range(10)]
    d = _write(tmp_path, recs)
    full = report.format_report(d, 5.0)
    scoped = report.format_report(d, 5.0, since=recs[7]["iso_time"])

    def per_sample(text):
        line = [l for l in text.splitlines() if "표본당" in l][0]
        return line.split("표본당")[1].split("B")[0].strip()

    assert per_sample(full) == per_sample(scoped)
    assert "전 구간 기준" in scoped


# ── 표본 상한 (반복 호출 경로 보호) ──────────────────────────────────────────


def test_max_samples_caps_read_and_says_so(tmp_path):
    d = _write(tmp_path, [_rec(i) for i in range(50)])
    text = report.format_report(d, 5.0, max_samples=10)
    assert "최근 10개 표본만 읽었다" in text
    assert "표본   : 10개" in text


def test_report_api_uses_the_cap(tmp_path):
    d = _write(tmp_path, [_rec(i) for i in range(webview.REPORT_MAX_SAMPLES + 5)])
    srv = webview.make_server(d, bind="127.0.0.1", port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        body = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/report").read().decode()
    finally:
        srv.shutdown()
        srv.server_close()
    assert f"최근 {webview.REPORT_MAX_SAMPLES}개 표본만 읽었다" in body


# ── 로그 완독 횟수 ───────────────────────────────────────────────────────────


def test_cli_reads_the_log_only_once(tmp_path, monkeypatch, capsys):
    """보고문과 종료 코드를 위해 같은 디렉토리를 두 번 파싱하지 않는다."""
    d = _write(tmp_path, [_rec(i) for i in range(5)])
    calls = []
    original = report.load_records
    monkeypatch.setattr(report, "load_records",
                        lambda *a, **k: (calls.append(1), original(*a, **k))[1])
    assert report.main([str(d), "--interval", "5"]) == 0
    capsys.readouterr()
    assert len(calls) == 1, f"로그를 {len(calls)}회 완독했다"


def test_cli_rejects_zero_interval(tmp_path):
    d = _write(tmp_path, [_rec(0)])
    with pytest.raises(SystemExit) as exc:
        report.main([str(d), "--interval", "0"])
    assert exc.value.code == 2


# ── 대시보드 문자열 처리 ─────────────────────────────────────────────────────


def test_page_injects_level_view_and_escapes(tmp_path):
    """등급 표는 서버가 단일 근원으로 내려주고, 로그 문자열은 이스케이프해서 넣는다."""
    d = _write(tmp_path, [_rec(0)])
    srv = webview.make_server(d, bind="127.0.0.1", port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        page = urllib.request.urlopen(f"http://127.0.0.1:{port}/").read().decode()
    finally:
        srv.shutdown()
        srv.server_close()
    assert "__LEVEL_VIEW__" not in page, "자리표시자가 치환되지 않았다"
    assert '"OK"' in page and "정상" in page
    assert "esc(f.message)" in page and "esc(f.key)" in page
