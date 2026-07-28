"""링버퍼 검증 — 상한 강제와 "쓰기 실패를 삼키지 않는다"가 핵심이다.

시각은 전부 주입한다(`clock`). 실제 시계에 의존하면 자정 근처에서만 깨지는 테스트가 된다.
"""
import json

import pytest

from system_health.ringlog import RingLog, RingLogWriteError

# 2026-07-28 00:00:00 UTC 근방의 고정 epoch. 정확한 로컬 일자는 테스트가 직접 계산한다.
_T0 = 1785196800.0
_DAY_S = 86400.0


def _make(tmp_path, clock, **kwargs):
    return RingLog(tmp_path, clock=clock, **kwargs)


def test_write_creates_dated_file_and_appends(tmp_path):
    log = _make(tmp_path, lambda: _T0)
    path = log.write({"a": 1})
    log.write({"a": 2})
    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert [json.loads(line)["a"] for line in lines] == [1, 2]


def test_creates_missing_directory(tmp_path):
    target = tmp_path / "deep" / "nested"
    log = RingLog(target, clock=lambda: _T0)
    log.write({"a": 1})
    assert target.is_dir()


def test_korean_text_is_not_escaped(tmp_path):
    log = _make(tmp_path, lambda: _T0)
    path = log.write({"message": "온도 높음"})
    assert "온도 높음" in path.read_text(encoding="utf-8")


def test_non_serializable_value_falls_back_to_str(tmp_path):
    log = _make(tmp_path, lambda: _T0)
    path = log.write({"obj": object()})
    assert "object object at" in path.read_text(encoding="utf-8")


def test_day_change_rotates_to_new_file(tmp_path):
    now = [_T0]
    log = _make(tmp_path, lambda: now[0])
    first = log.write({"a": 1})
    now[0] = _T0 + _DAY_S
    second = log.write({"a": 2})
    assert first != second
    assert len(log.existing_files()) == 2


def test_write_failure_raises_instead_of_silently_passing(tmp_path):
    # 디렉토리 자리에 파일이 있으면 mkdir 이 실패한다. 감시기가 살아 있는 것처럼 보이면서
    # 기록이 0인 상태가 최악이므로 예외로 올라와야 한다.
    blocker = tmp_path / "blocked"
    blocker.write_text("i am a file")
    log = RingLog(blocker / "logs", clock=lambda: _T0)
    with pytest.raises(RingLogWriteError):
        log.write({"a": 1})


def test_enforce_deletes_files_older_than_max_age(tmp_path):
    now = [_T0]
    log = _make(tmp_path, lambda: now[0], max_age_days=2.0, enforce_every=1)
    log.write({"day": 0})
    now[0] = _T0 + 5 * _DAY_S
    log.write({"day": 5})
    remaining = [p.name for p in log.existing_files()]
    assert len(remaining) == 1, remaining


def test_enforce_keeps_newest_file_even_when_over_cap(tmp_path):
    now = [_T0]
    # 상한을 0 으로 두면 모든 파일이 초과다. 그래도 쓰는 중인 파일은 남아야 한다.
    log = _make(tmp_path, lambda: now[0], max_total_mb=0.0, enforce_every=1)
    log.write({"day": 0})
    now[0] = _T0 + _DAY_S
    log.write({"day": 1})
    now[0] = _T0 + 2 * _DAY_S
    log.write({"day": 2})
    remaining = log.existing_files()
    assert len(remaining) == 1
    assert json.loads(remaining[0].read_text())["day"] == 2


def test_enforce_is_noop_with_single_file(tmp_path):
    log = _make(tmp_path, lambda: _T0, max_total_mb=0.0, enforce_every=1)
    log.write({"a": 1})
    assert log.enforce_limits() == []
    assert len(log.existing_files()) == 1


def test_other_prefixes_are_untouched(tmp_path):
    stranger = tmp_path / "other-2026-07-01.jsonl"
    stranger.write_text("x\n")
    now = [_T0]
    log = _make(tmp_path, lambda: now[0], max_total_mb=0.0, max_age_days=0.0, enforce_every=1)
    log.write({"a": 1})
    now[0] = _T0 + _DAY_S
    log.write({"a": 2})
    assert stranger.exists()


def test_existing_files_is_empty_when_directory_absent(tmp_path):
    log = RingLog(tmp_path / "not-created-yet", clock=lambda: _T0)
    assert log.existing_files() == []
