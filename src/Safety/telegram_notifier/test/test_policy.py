"""AlertPolicy 전이 단위시험 — ROS 무의존. 시각은 인자로 주입한다."""
from telegram_notifier.policy import (
    AlertPolicy, LEVEL_ERROR, LEVEL_OK, LEVEL_WARN)

IDLE_WARN = "제어권 미획득 (대기)"


def make(**kw):
    base = dict(notify_warn=False, warn_ignore=(IDLE_WARN,),
                renotify_s=1800.0, stale_after_s=15.0)
    base.update(kw)
    return AlertPolicy(**base)


def test_ok_stream_is_silent():
    p = make()
    assert p.on_status(LEVEL_OK, "정상", "", 0.0) is None
    assert p.on_status(LEVEL_OK, "정상", "", 1.0) is None


def test_error_entry_then_recovery():
    p = make()
    ev = p.on_status(LEVEL_ERROR, "CAN 버스 이상: bus2 bus_off", "bus2: off=1", 0.0)
    assert ev is not None and "🔴 ERROR" in ev.text and "bus2: off=1" in ev.text
    # 같은 ERROR 지속(간격 미달)은 침묵
    assert p.on_status(LEVEL_ERROR, "CAN 버스 이상: bus2 bus_off", "", 10.0) is None
    ev = p.on_status(LEVEL_OK, "정상", "", 20.0)
    assert ev is not None and "🟢 복구" in ev.text


def test_error_persist_renotifies_after_interval():
    p = make(renotify_s=100.0)
    assert p.on_status(LEVEL_ERROR, "피드백 끊긴 노드 [1]", "", 0.0) is not None
    assert p.on_status(LEVEL_ERROR, "피드백 끊긴 노드 [1]", "", 99.0) is None
    ev = p.on_status(LEVEL_ERROR, "피드백 끊긴 노드 [1]", "", 100.0)
    assert ev is not None and "지속" in ev.text


def test_error_message_change_notifies_immediately():
    p = make()
    assert p.on_status(LEVEL_ERROR, "E-stop 인가", "", 0.0) is not None
    ev = p.on_status(LEVEL_ERROR, "피드백 끊긴 노드 [3]", "", 1.0)
    assert ev is not None and "피드백" in ev.text and "지속" not in ev.text


def test_error_to_warn_counts_as_recovery():
    p = make()
    assert p.on_status(LEVEL_ERROR, "E-stop 인가", "", 0.0) is not None
    ev = p.on_status(LEVEL_WARN, IDLE_WARN, "", 1.0)
    assert ev is not None and "🟢 복구" in ev.text


def test_warn_silent_by_default():
    p = make()
    assert p.on_status(LEVEL_WARN, "호밍 진행 중 — 위치 무효", "", 0.0) is None


def test_warn_notify_when_enabled_but_idle_ignored():
    p = make(notify_warn=True)
    assert p.on_status(LEVEL_WARN, IDLE_WARN, "", 0.0) is None
    ev = p.on_status(LEVEL_WARN, "SDO 거부 발생 — 로그 확인", "", 1.0)
    assert ev is not None and "🟡 WARN" in ev.text
    # 같은 WARN 반복은 침묵
    assert p.on_status(LEVEL_WARN, "SDO 거부 발생 — 로그 확인", "", 2.0) is None


def test_stale_then_resume():
    p = make(stale_after_s=15.0)
    p.on_status(LEVEL_OK, "정상", "", 0.0)
    assert p.on_tick(10.0) is None
    ev = p.on_tick(15.0)
    assert ev is not None and "무수신" in ev.text
    # 스테일 통보는 1회뿐
    assert p.on_tick(30.0) is None
    ev = p.on_status(LEVEL_OK, "정상", "", 40.0)
    assert ev is not None and "수신 재개" in ev.text


def test_startup_without_any_rx_goes_stale():
    p = make(stale_after_s=15.0)
    assert p.on_tick(0.0) is None  # 첫 tick 이 기준점
    assert p.on_tick(14.0) is None
    assert p.on_tick(15.0) is not None


def test_stale_resume_combined_with_error_entry():
    p = make(stale_after_s=15.0)
    p.on_status(LEVEL_OK, "정상", "", 0.0)
    assert p.on_tick(20.0) is not None
    ev = p.on_status(LEVEL_ERROR, "E-stop 인가", "", 25.0)
    assert ev is not None
    assert "수신 재개" in ev.text and "🔴 ERROR" in ev.text
