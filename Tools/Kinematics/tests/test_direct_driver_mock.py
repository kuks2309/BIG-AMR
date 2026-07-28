#!/usr/bin/env python3
"""DirectDriver 무-하드웨어 회귀 (MockTransport) — 안전 게이트 중심.

핵심: **정렬 확정 전 vel≠0 송출 금지** (node4 물리손상 2026-07-27-002 부류 차단) 를 회귀로 고정.
arm 배리어·비무장 구동 거부·enable 프레임·estop 도 검증. stdlib 전용(tegra 실행 가능).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from can_transport import MockTransport, TransportNotArmed  # noqa: E402
from can_protocol import sdo_write  # noqa: E402
from direct_driver import DirectDriver, STEER_NODES  # noqa: E402


def test_arm_barrier_blocks_send():
    t = MockTransport().open()
    try:
        t.send(sdo_write(1, 0x60FF, 0))
        assert False, "비무장 send 가 통과함"
    except TransportNotArmed:
        pass
    t.arm()
    t.send(sdo_write(1, 0x60FF, 0))  # 무장 후 통과
    assert len(t.sent) == 1


def test_run_refuses_unarmed_transport():
    # 비무장 트랜스포트 → run() 즉시 거부, enable/구동 프레임 0
    t = MockTransport().open()  # arm 안 함
    d = DirectDriver(t)
    d.start(); time.sleep(0.2); d.running = False; d.join(timeout=1)
    assert len(t.sent) == 0, f"비무장인데 {len(t.sent)}프레임 송신됨"


def test_no_velocity_before_alignment():
    """★ 안전 게이트: 조향 정렬 확정(0x6064 응답) 없이는 vel≠0 을 절대 송출하지 않는다."""
    t = MockTransport().open(); t.arm()
    d = DirectDriver(t)
    d.start(); time.sleep(0.2)
    d.set_mode("CRAB_L", 800)          # 조향 90° 목표 + pending vel {1:800,2:800}
    time.sleep(1.0)                    # 정렬 응답 미제공 → 절대 정렬 안 됨
    d.shutdown()
    nonzero = [(n, v) for n, v in t.drive_velocity_frames() if v != 0]
    assert not nonzero, f"정렬 전 vel≠0 송출됨(node4 위험): {nonzero[:5]}"


def test_velocity_applied_after_alignment():
    """정렬 응답을 주면 vel 이 인가된다(게이트가 과도차단이 아님을 확인)."""
    t = MockTransport().open(); t.arm()
    d = DirectDriver(t)
    d.start(); time.sleep(0.2)
    d.set_mode("CRAB_L", 800)
    with d._lock:
        target = dict(d._steer)        # 조향 목표(홈+90°)
    # 정렬 폴이 두 조향노드의 0x6064 를 목표값으로 읽도록 충분히 큐잉
    for _ in range(40):
        for n in STEER_NODES:
            t.program_sdo_read(n, 0x6064, target[n])
    time.sleep(1.2)
    d.shutdown()
    nonzero = [(n, v) for n, v in t.drive_velocity_frames() if v != 0]
    assert nonzero, "정렬 응답을 줬는데도 vel 이 인가되지 않음"
    assert all(abs(v) == 800 for _, v in nonzero), nonzero[:5]


def test_enable_frames_and_estop():
    t = MockTransport().open(); t.arm()
    d = DirectDriver(t)
    d.start(); time.sleep(0.2)
    ids = t.sent_ids()
    assert 0x601 in ids and 0x603 in ids, ids   # 구동/조향 enable
    d.set_twist(0.05, 0, 0); time.sleep(0.1)
    d.estop()
    with d._lock:
        assert d._vel == {1: 0, 2: 0} and d.mode == "ESTOP"
    d.shutdown()
    # shutdown 후 트랜스포트 비무장(disarm) 확인
    assert t.is_armed is False


def test_from_channel_mock_arms():
    d = DirectDriver.from_channel("x", backend="mock")
    assert d.transport.is_armed is True
    d.transport.shutdown()


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    ok = 0
    for fn in fns:
        try:
            fn(); print(f"  PASS {fn.__name__}"); ok += 1
        except AssertionError as e:
            print(f"  FAIL {fn.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"direct_driver(mock): {ok}/{len(fns)} PASS")
    return ok == len(fns)


if __name__ == "__main__":
    sys.exit(0 if _run() else 1)
