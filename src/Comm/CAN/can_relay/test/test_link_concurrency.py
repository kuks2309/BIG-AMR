"""링크 계층 동시성 회귀 — 판다 USB 핸들이 두 스레드에서 겹치지 않는지 고정한다.

## 이 파일이 존재하는 이유

`link.py:32-33` 이 스스로 적어 둔 이력이다 — 「heartbeat 를 별도 스레드에서 보내면
폴링과 USB 핸들을 경합해 실패한 이력이 있다. 그래서 송수신과 같은 스레드에서 인터리브한다」.

그 전제는 **모든 USB 접근이 제어 스레드 하나**일 때만 성립했다. 호밍 시퀀서(0xea/0xeb)가
들어오면서 `home()`·`cancel_home()` 이 **서비스 콜백 스레드**에서 `homing_status`·`_homing_cmd`
를 호출하게 됐고(backend.py `home`·`cancel_home`), 그때부터 제어 스레드의 `heartbeat` 와
같은 핸들에서 동시에 전송될 수 있다.

`send`·`recv`·`can_health`·`_homing_cmd`·`homing_status` 는 `self._lock` 안이지만
`heartbeat` 만 밖에 있었다(2026-08-03 코드 리뷰 H2).

심박 실패는 펌웨어 fail-safe(구동 0 + 릴레이 개방) 발동으로 이어진다 — 안전 방향이지만
**주행 중 예고 없는 정지**다. 그래서 "겹치지 않는다"를 회귀로 박는다.
"""
import threading
import time

from can_relay.link import PandaLink


class _CountingHandle:
    """USB 핸들 대역 — 동시에 몇 개의 전송이 진행 중이었는지 센다."""

    def __init__(self, delay: float = 0.004):
        self._lock = threading.Lock()
        self._delay = delay
        self.active = 0
        self.max_active = 0
        self.calls = 0

    def _enter(self):
        with self._lock:
            self.active += 1
            self.calls += 1
            self.max_active = max(self.max_active, self.active)

    def _leave(self):
        with self._lock:
            self.active -= 1

    def controlWrite(self, *_a, **_kw):
        self._enter()
        time.sleep(self._delay)
        self._leave()
        return 0

    def controlRead(self, _req_in, _request, _value, _index, length):
        self._enter()
        time.sleep(self._delay)
        self._leave()
        return bytes(length)


class _FakePandaCls:
    REQUEST_OUT = 0x40
    REQUEST_IN = 0xC0


class _FakePanda:
    def __init__(self, handle):
        self._handle = handle

    def can_send(self, _can_id, _data, _bus):
        """`PandaLink.send` 가 쓰는 경로. 같은 핸들 계수기를 통과시킨다."""
        self._handle._enter()
        time.sleep(self._handle._delay)
        self._handle._leave()


def _link_with(handle) -> PandaLink:
    link = PandaLink()
    link._panda = _FakePanda(handle)
    link._cls = _FakePandaCls
    link._engaged = True
    return link


def _hammer(fns, rounds: int = 40):
    """여러 함수를 각각의 스레드에서 rounds 회씩 호출한다."""
    errors = []

    def run(fn):
        try:
            for _ in range(rounds):
                fn()
        except Exception as exc:                    # pragma: no cover - 진단용
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(f,)) for f in fns]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)
    assert not errors, f"동시 호출 중 예외: {errors}"


def test_heartbeat_does_not_overlap_homing_status():
    """제어 스레드의 심박과 서비스 스레드의 0xeb 조회가 겹치면 안 된다.

    이것이 H2 의 실제 조합이다 — `_loop` 이 `heartbeat`(link.py `heartbeat`)를,
    `home()` 이 `homing_status`(0xeb)를 각각 다른 스레드에서 부른다.
    """
    handle = _CountingHandle()
    link = _link_with(handle)
    _hammer([link.heartbeat, link.homing_status])
    assert handle.max_active == 1, (
        f"USB 핸들에 동시 전송 {handle.max_active} 건이 겹쳤다 — "
        f"heartbeat 가 _lock 밖이면 이 조합이 성립한다")


def test_heartbeat_does_not_overlap_frame_send():
    """심박과 프레임 송신도 겹치면 안 된다(같은 핸들, 다른 스레드)."""
    from can_relay import protocol as P

    handle = _CountingHandle()
    link = _link_with(handle)
    frames = [P.sdo_read(3, 0x6064)]
    _hammer([link.heartbeat, lambda: link.send(frames)])
    assert handle.max_active == 1, (
        f"USB 핸들에 동시 전송 {handle.max_active} 건이 겹쳤다")


def test_heartbeat_does_not_overlap_homing_cmd():
    """심박과 0xea(시작/취소)도 겹치면 안 된다 — 취소는 정지 경로다."""
    handle = _CountingHandle()
    link = _link_with(handle)
    _hammer([link.heartbeat, link.homing_cancel])
    assert handle.max_active == 1, (
        f"USB 핸들에 동시 전송 {handle.max_active} 건이 겹쳤다")


def test_all_usb_entrypoints_are_exercised_by_the_probe():
    """대역이 실제로 호출됐는지 확인한다 — 0 회 호출로 통과하는 위양성 차단."""
    handle = _CountingHandle()
    link = _link_with(handle)
    _hammer([link.heartbeat, link.homing_status], rounds=5)
    assert handle.calls == 10
