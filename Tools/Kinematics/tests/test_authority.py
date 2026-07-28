#!/usr/bin/env python3
"""KernelCangwAuthority 회귀 — High(주도권 영구상실)·Medium(gate_off 은폐)·L2(stop 순서) 봉인.

코드리뷰 M1(2026-07-28): run_cangw(subprocess)·can.Bus 를 mock 하여 부분실패 롤백·멱등 release·
gate_off rc 처리를 결정론 검증. stdlib 전용(tegra 실행 가능 — python-can 불요, fake can 주입).
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import authority  # noqa: E402


class _CangwStub:
    """run_cangw 대체 — action 별 (rc,out) 프로그래밍 + 호출 순서 기록."""
    def __init__(self):
        self.calls = []
        self.responses = {}       # action -> (rc, out)

    def __call__(self, action, timeout=30):
        self.calls.append(action)
        return self.responses.get(action, (0, "ok"))


class _FakeBus:
    def __init__(self, **kw):
        self.sent = []

    def send(self, m):
        self.sent.append(m)

    def recv(self, timeout=0.5):
        return None

    def shutdown(self):
        pass


def _install_fake_can(bus_fail=False):
    """sys.modules['can'] 에 최소 fake 주입 (Message/Bus/CanError). bus_fail 이면 Bus() 예외."""
    m = types.ModuleType("can")

    class CanError(Exception):
        pass

    class Message:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    def Bus(**kw):
        if bus_fail:
            raise RuntimeError("bus open 실패(주입)")
        return _FakeBus(**kw)

    m.CanError = CanError
    m.Message = Message
    m.Bus = Bus
    sys.modules["can"] = m
    return m


def _patch(stub):
    authority.run_cangw = stub  # 모듈 전역 교체 (acquire/release 가 참조)


def test_partial_failure_rolls_back_gate():
    """★ High: gate_on 성공 후 can.Bus 예외 → acquire 예외 전파 전에 gate_off 롤백(주도권 복원)."""
    _install_fake_can(bus_fail=True)
    stub = _CangwStub(); _patch(stub)
    a = authority.KernelCangwAuthority("can0", "can1")
    raised = False
    try:
        a.acquire()
    except Exception:
        raised = True
    assert raised, "부분실패인데 예외 미전파"
    assert "gate_on" in stub.calls and "gate_off" in stub.calls, stub.calls
    # gate_off 가 gate_on 뒤에 호출됐는가(롤백 순서)
    assert stub.calls.index("gate_off") > stub.calls.index("gate_on")


def test_no_gate_off_when_gate_on_fails():
    """gate_on 자체 실패 시 gate_off 불필요 호출 없음(_gated False)."""
    _install_fake_can()
    stub = _CangwStub(); stub.responses["gate_on"] = (1, "gate_on 실패")
    _patch(stub)
    a = authority.KernelCangwAuthority("can0", "can1")
    try:
        a.acquire()
    except Exception:
        pass
    assert "gate_off" not in stub.calls, stub.calls


def test_release_idempotent():
    """★ 멱등: acquire 성공 후 release 2회 → gate_off 정확히 1회."""
    _install_fake_can()
    stub = _CangwStub(); _patch(stub)
    a = authority.KernelCangwAuthority("can0", "can1")
    a.acquire()
    a.release()
    a.release()
    assert stub.calls.count("gate_off") == 1, stub.calls


def test_gate_off_failure_still_stops_kernel():
    """★ L2: gate_off 실패해도 커널 릴레이 stop 은 시도된다(early-return 회귀 방지)."""
    _install_fake_can()
    stub = _CangwStub(); stub.responses["gate_off"] = (1, "gate_off 실패")
    _patch(stub)
    a = authority.KernelCangwAuthority("can0", "can1", kernel_relay=True)
    a.acquire()   # start, gate_on
    a.release()   # gate_off 실패 → 그래도 stop 시도
    assert "stop" in stub.calls, f"gate_off 실패 시 stop 건너뜀: {stub.calls}"
    assert stub.calls.count("gate_off") == 1


def test_context_manager_acquires_and_releases():
    _install_fake_can()
    stub = _CangwStub(); _patch(stub)
    with authority.KernelCangwAuthority("can0", "can1"):
        pass
    assert "gate_on" in stub.calls and "gate_off" in stub.calls


def test_no_authority_noop():
    a = authority.NoAuthority()
    a.acquire(); a.release()  # 예외 없이 통과


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
    print(f"authority: {ok}/{len(fns)} PASS")
    return ok == len(fns)


if __name__ == "__main__":
    sys.exit(0 if _run() else 1)
