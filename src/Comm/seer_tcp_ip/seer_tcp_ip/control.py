"""제어권 세션과 dead-man jog — 편호 래퍼가 아니라 **동작**이라 별 모듈에 둔다.

Seer 는 지령 계열 API 를 받기 전에 제어권(4005)을 요구하고, 없으면 `ret_code 40020` 으로 거부한다.
제어권은 뺏고 뺏기는 자원이라 획득과 반납이 반드시 짝이어야 한다 — 반납하지 않고 죽으면 다음
클라이언트가 40020 으로 막히고, 그 원인이 로봇 쪽에 남지 않는다.

이 모듈은 스레드를 만들지 않는다. 호출자의 타이머·루프가 `tick()` 을 부른다 — 단일 스레드
executor 에 그대로 얹히고, 시험에서 시계를 주입할 수 있다.
"""
import time

from . import ports
from .api import SeerApi


class SeerControlError(RuntimeError):
    """제어권 상태가 요구와 맞지 않아 진행할 수 없다."""


class SeerControlSession:
    """제어권을 잡고 쓰고 반납하는 컨텍스트 매니저.

    진입 시 이전 소유자를 조회해 `previous_owner` 에 남기고 4005 로 획득한다.
    이탈 시 **정지(2000) 를 먼저 보낸 뒤** 4006 으로 반납한다 — 예외로 빠져나가도 마찬가지다.
    정지가 실패해도 반납은 시도한다(제어권을 쥔 채 죽는 것이 더 나쁘다).

    지령 포트를 쓰므로 `SeerApi(..., allow_guarded=True)` 로 만든 클라이언트가 필요하다.

        with SeerControlSession(api, "big-amr-jog") as sess:
            api.open_loop_move(0.1, 0.0, 0.0, duration_ms=600)
    """

    def __init__(self, api: SeerApi, nick_name: str, stop_on_exit: bool = True):
        """:param nick_name: 로봇이 소유자로 표시할 이름. 어느 프로세스가 잡았는지 알아볼 수 있게 짓는다.
        :param stop_on_exit: 반납 전 정지(2000) 를 보낼지. 끄면 관성으로 계속 갈 수 있다.
        """
        if not str(nick_name).strip():
            raise ValueError("nick_name 은 비어 있을 수 없다 — 로봇 화면에서 소유자를 식별해야 한다")
        self.api = api
        self.nick_name = str(nick_name)
        self.stop_on_exit = bool(stop_on_exit)
        self.previous_owner = None
        self.held = False

    def acquire(self) -> dict:
        """이전 소유자를 기록하고 제어권을 획득한다.

        :returns: 이전 소유자 응답(1060). 조회가 실패하면 빈 dict — 획득은 그대로 시도한다.
        :raises SeerControlError: 이미 이 세션이 쥐고 있을 때(이중 획득).
        """
        if self.held:
            raise SeerControlError("이미 제어권을 쥐고 있다 — 이중 획득은 반납 짝을 깨뜨린다")
        try:
            self.previous_owner = self.api.get_control_owner()
        except Exception:
            self.previous_owner = {}
        self.api.seize_control(self.nick_name)
        self.held = True
        return self.previous_owner

    def release(self) -> None:
        """정지 후 제어권을 반납한다. 쥐고 있지 않으면 아무것도 하지 않는다."""
        if not self.held:
            return
        try:
            if self.stop_on_exit:
                self.api.stop()
        finally:
            self.held = False
            self.api.release_control()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()
        return False


class JogKeepalive:
    """dead-man 이 걸린 개루프 주행 — `duration` 보다 짧은 주기로 2010 을 재송신한다.

    `duration_ms` 안에 새 지령이 없으면 로봇이 스스로 선다. 그래서 재송신 주기가 `duration` 보다
    짧아야 연속 주행이 되고, 보내는 쪽이 죽으면 `duration` 안에 로봇이 멈춘다. 그 성질이 이
    클래스의 존재 이유다 — 주기가 `duration` 이상이면 매 주기 섰다 갔다 하므로 생성 시 거부한다.

    스레드를 만들지 않는다. 호출자가 `tick()` 을 자주 부르면 되고, 보낼 시점이 아니면 아무 일도
    하지 않는다(과송신은 로봇이 연결을 정리하는 사유가 된다).

        jog = JogKeepalive(api, vx=0.1, duration_ms=600, interval_s=0.2)
        jog.tick()          # 타이머 콜백에서 반복 호출
        jog.stop()          # 끝낼 때
    """

    def __init__(self, api: SeerApi, vx: float = 0.0, vy: float = 0.0, w: float = 0.0,
                 duration_ms: int = 600, interval_s: float = 0.2, clock=time.monotonic):
        """:param duration_ms: dead-man 시간. 보내는 쪽이 죽으면 이 시간 안에 로봇이 선다.
        :param interval_s: 재송신 주기. `duration_ms` 보다 작아야 한다.
        :param clock: 단조 시계. 시험 주입점.
        """
        if duration_ms <= 0:
            raise ValueError("duration_ms 는 양수여야 한다 — 0 은 무한이라 dead-man 이 없어진다")
        if interval_s <= 0:
            raise ValueError("interval_s 는 양수여야 한다")
        if interval_s * 1000.0 >= duration_ms:
            raise ValueError(
                f"interval_s({interval_s}s) 가 duration_ms({duration_ms}ms) 이상이다 — "
                f"이러면 매 주기 dead-man 이 먼저 만료돼 로봇이 섰다 갔다 한다"
            )
        self.api = api
        self.vx, self.vy, self.w = float(vx), float(vy), float(w)
        self.duration_ms = int(duration_ms)
        self.interval_s = float(interval_s)
        self._clock = clock
        self._last_sent_at = None
        self.sent_count = 0

    def set_velocity(self, vx: float = 0.0, vy: float = 0.0, w: float = 0.0) -> None:
        """다음 tick 부터 실을 속도를 바꾼다. 즉시 보내지는 않는다."""
        self.vx, self.vy, self.w = float(vx), float(vy), float(w)

    def due(self) -> bool:
        """지금 재송신할 시점인가. 첫 호출은 항상 True."""
        if self._last_sent_at is None:
            return True
        return (self._clock() - self._last_sent_at) >= self.interval_s

    def tick(self) -> bool:
        """시점이면 2010 을 한 번 보낸다.

        :returns: 실제로 보냈으면 True, 아직 시점이 아니면 False.
        """
        if not self.due():
            return False
        self.api.open_loop_move(self.vx, self.vy, self.w, duration_ms=self.duration_ms)
        self._last_sent_at = self._clock()
        self.sent_count += 1
        return True

    def stop(self) -> dict:
        """즉시 정지(2000) 를 보내고 재송신 상태를 지운다."""
        self._last_sent_at = None
        self.vx = self.vy = self.w = 0.0
        return self.api.stop()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop()
        return False


def preempted_by_control(exc: Exception) -> bool:
    """예외가 「제어권이 없어서 거부됨」인가 — 4005 를 먼저 잡으라는 신호.

    호출자가 `ret_code` 문자열을 직접 뒤지지 않게 한다.
    """
    from .api import CONTROL_PREEMPTED_RET_CODE

    return f"ret_code={CONTROL_PREEMPTED_RET_CODE}" in str(exc)


#: 조회 포트로만 나가는 진단 — 제어권을 잡지 않고 지금 누가 쥐고 있는지 본다.
def describe_owner(api: SeerApi) -> str:
    """1060 응답을 한 줄로 요약한다. 로그·진단용."""
    owner = api.get_control_owner()
    if not owner.get("locked"):
        return "제어권 비어 있음"
    return (f"제어권 보유: nick_name={owner.get('nick_name')!r} ip={owner.get('ip')} "
            f"(port {ports.API_PORT_CONFIG} 로 4005 를 걸면 뺏는다)")
