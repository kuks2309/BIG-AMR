"""JSONL 링버퍼 — 감시기 자신의 로그가 디스크를 채우지 못하게 스스로 상한을 강제한다.

**왜 상한이 필수인가** (ADR 2026-07-28 §Decision 6):
감시기를 넣는 목적은 "사고 순간의 증거를 남기는 것"이다. 그런데 무한히 커지는 로그는 디스크를
채워서 **정확히 그 순간에 아무것도 못 남기게** 만든다. 게다가 쓰기 실패를 예외로 삼키면
감시기가 살아 있는 것처럼 보이면서 실제로는 기록이 0인 최악의 상태가 된다. 그래서
`write()` 는 실패를 `RingLogWriteError` 로 **올린다** — 호출자가 이를 상태로 승격해야 한다.

파일은 일자별(`health-YYYY-MM-DD.jsonl`)로 나뉘고, 총량·보존기간을 넘기면 **가장 오래된
파일부터** 지운다. 쓰는 중인 최신 파일은 절대 지우지 않는다.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Mapping

_BYTES_PER_MB = 1 << 20
_SECONDS_PER_DAY = 86400.0


class RingLogWriteError(RuntimeError):
    """로그 기록 실패. 호출자는 이를 삼키지 말고 최고 심각도 상태로 승격해야 한다."""


class RingLog:
    """일자 회전 + 총량/보존기간 상한을 갖는 JSONL 기록기.

    Attributes 는 생성 후 바뀌지 않는다. 인스턴스는 단일 스레드에서만 쓴다(감시기 메인 루프).
    """

    def __init__(
        self,
        out_dir: str | Path,
        *,
        prefix: str = "health",
        max_total_mb: float = 512.0,
        max_age_days: float = 14.0,
        enforce_every: int = 100,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """
        Args:
            out_dir: 로그 디렉토리. 없으면 만든다.
            prefix: 파일명 접두. `<prefix>-YYYY-MM-DD.jsonl`.
            max_total_mb: 이 디렉토리에서 본 접두가 차지할 총량 상한(MB).
            max_age_days: 이보다 오래된 파일은 삭제.
            enforce_every: 몇 번 쓸 때마다 상한을 강제할지. 매 쓰기마다 디렉토리를 훑으면
                낭비라 주기적으로만 한다(날짜가 바뀌면 즉시 강제).
            clock: 현재 시각(epoch 초)을 주는 함수. 테스트에서 주입한다.
        """
        self._dir = Path(out_dir)
        self._prefix = prefix
        self._max_total_bytes = max_total_mb * _BYTES_PER_MB
        self._max_age_s = max_age_days * _SECONDS_PER_DAY
        self._enforce_every = max(1, enforce_every)
        self._clock = clock
        self._writes_since_enforce = 0
        self._current_day: str | None = None

    @property
    def directory(self) -> Path:
        """로그 디렉토리."""
        return self._dir

    def _day_string(self) -> str:
        """현재 로컬 일자(`YYYY-MM-DD`)."""
        return time.strftime("%Y-%m-%d", time.localtime(self._clock()))

    def path_for_day(self, day: str) -> Path:
        """해당 일자의 로그 파일 경로."""
        return self._dir / f"{self._prefix}-{day}.jsonl"

    def existing_files(self) -> list[Path]:
        """본 접두를 가진 로그 파일들, 이름 오름차순(= 날짜 오름차순)."""
        if not self._dir.is_dir():
            return []
        return sorted(self._dir.glob(f"{self._prefix}-*.jsonl"))

    def write(self, record: Mapping[str, Any]) -> Path:
        """record 를 JSON 한 줄로 덧붙인다.

        Args:
            record: 직렬화 가능한 매핑.
        Returns:
            기록된 파일 경로.
        Raises:
            RingLogWriteError: 디렉토리 생성·직렬화·쓰기 중 어느 하나라도 실패하면.
        """
        day = self._day_string()
        day_changed = day != self._current_day
        path = self.path_for_day(day)
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            line = json.dumps(record, ensure_ascii=False, default=str)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except (OSError, TypeError, ValueError) as exc:
            raise RingLogWriteError(f"로그 기록 실패 ({path}): {exc}") from exc

        self._current_day = day
        self._writes_since_enforce += 1
        if day_changed or self._writes_since_enforce >= self._enforce_every:
            self._writes_since_enforce = 0
            self.enforce_limits()
        return path

    def enforce_limits(self) -> list[Path]:
        """보존기간·총량 상한을 적용해 오래된 파일을 지운다.

        최신 파일(쓰는 중인 파일)은 어떤 경우에도 남긴다 — 상한을 지키려다 방금 기록한
        증거를 지우면 본말전도다. 최신 파일 하나가 상한을 넘으면 상한을 못 지킨 채로 둔다.

        Returns:
            삭제한 파일 목록(없으면 빈 리스트).
        """
        files = self.existing_files()
        if len(files) <= 1:
            return []

        deleted: list[Path] = []
        now = self._clock()
        # 최신 파일은 후보에서 제외한다.
        candidates = files[:-1]

        for path in list(candidates):
            try:
                age_s = now - path.stat().st_mtime
            except OSError:
                continue
            if age_s > self._max_age_s and self._unlink(path):
                deleted.append(path)
                candidates.remove(path)

        while candidates and self._total_size() > self._max_total_bytes:
            oldest = candidates.pop(0)
            if self._unlink(oldest):
                deleted.append(oldest)

        return deleted

    def _total_size(self) -> float:
        """본 접두 파일들의 총 바이트."""
        total = 0.0
        for path in self.existing_files():
            try:
                total += path.stat().st_size
            except OSError:
                continue
        return total

    @staticmethod
    def _unlink(path: Path) -> bool:
        """파일을 지운다. 실패는 무시하고 False — 회수 실패로 감시를 멈추지 않는다."""
        try:
            path.unlink()
            return True
        except OSError:
            return False
