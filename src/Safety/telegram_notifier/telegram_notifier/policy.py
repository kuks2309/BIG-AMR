"""경보 전이 판정 — 순수 로직, rclpy 무의존. 시각은 인자로 받는다(테스트가 통제).

전이 기반이라 같은 상태의 반복 수신은 통보를 만들지 않는다. ERROR 지속만
``renotify_s`` 간격으로 재통보한다(사람이 잊지 않도록).
"""
from __future__ import annotations

import dataclasses

# diagnostic_msgs/DiagnosticStatus.level 과 같은 값. 메시지 클래스를 import 하지
# 않기 위한 정수 상수다(이 모듈은 ROS 무의존).
LEVEL_OK = 0
LEVEL_WARN = 1
LEVEL_ERROR = 2


@dataclasses.dataclass(frozen=True)
class Event:
    """통보 1건. text 가 그대로 텔레그램 본문이 된다."""

    text: str


class AlertPolicy:
    """전이 상태기. ``on_status``(진단 수신)·``on_tick``(주기 점검)이 Event 를 낸다.

    상태는 인스턴스 안에만 있다(가변 전역 0). 스레드 안전하지 않다 —
    rclpy 기본 실행기의 콜백 한 스레드에서만 부른다.
    """

    def __init__(self, notify_warn: bool, warn_ignore: tuple[str, ...],
                 renotify_s: float, stale_after_s: float) -> None:
        self._notify_warn = notify_warn
        self._warn_ignore = warn_ignore
        self._renotify_s = renotify_s
        self._stale_after_s = stale_after_s
        self._last_level: int | None = None  # None = 첫 수신 전
        self._last_message = ""
        self._error_sent_at = 0.0
        self._last_rx_at: float | None = None  # None = 첫 수신 전(기동 직후)
        self._stale_reported = False

    def on_status(self, level: int, message: str, detail: str,
                  now: float) -> Event | None:
        """진단 1건을 반영하고, 통보할 것이 있으면 Event 를 돌려준다.

        level 은 LEVEL_* 정수, detail 은 ERROR 통보에만 덧붙는 부가 줄(버스
        카운터 등, 빈 문자열 허용).
        """
        self._last_rx_at = now
        lines = []
        if self._stale_reported:
            self._stale_reported = False
            lines.append("🟢 진단 수신 재개")
        prev = self._last_level
        if level >= LEVEL_ERROR:
            entered = prev is None or prev < LEVEL_ERROR
            changed = (not entered) and message != self._last_message
            due = now - self._error_sent_at >= self._renotify_s
            if entered or changed or due:
                tag = "🔴 ERROR 지속" if not (entered or changed) else "🔴 ERROR"
                lines.append(f"{tag}: {message}")
                if detail:
                    lines.append(detail)
                self._error_sent_at = now
        elif prev is not None and prev >= LEVEL_ERROR:
            lines.append(f"🟢 복구: {message}")
        elif (level == LEVEL_WARN and self._notify_warn
              and message not in self._warn_ignore
              and (prev != LEVEL_WARN or message != self._last_message)):
            lines.append(f"🟡 WARN: {message}")
        self._last_level = level
        self._last_message = message
        return Event("\n".join(lines)) if lines else None

    def on_tick(self, now: float) -> Event | None:
        """주기 점검 — ``stale_after_s`` 동안 수신이 없으면 스테일 통보 1회."""
        if self._last_rx_at is None:
            # 기동 후 무수신도 스테일로 잡아야 한다(도메인 오설정·릴레이 미가동).
            # 첫 tick 시각을 기준점으로 삼는다.
            self._last_rx_at = now
            return None
        if self._stale_reported:
            return None
        if now - self._last_rx_at >= self._stale_after_s:
            self._stale_reported = True
            return Event(
                f"⚠ can_relay 진단 무수신 {now - self._last_rx_at:.0f} s — "
                "릴레이 노드 중단 또는 도메인 설정 확인")
        return None
