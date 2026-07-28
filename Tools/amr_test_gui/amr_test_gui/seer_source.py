"""Seer 알람 관측 소스 — API 1050(robot_status_alarm) 폴링(읽기 전용).

정본 재사용: `Tools/docking_field_kit/seer_can_monitor.py` 의 알람 분류(`snapshot`·`is_can`)를
그대로 import 한다 — CAN/모터 계열 알람코드 집합을 재작성하지 않는다.

읽기 전용(status 포트 19204)이라 Seer 제어권을 취득하지 않는다. 접속 실패 시 graceful 비활성.
⚠ Seer 는 무선망(192.168.44.x)에만 있다 — 유선 eth0 에 44 대역을 붙이지 말 것(memory: biguamr-seer-network-access).
"""
from __future__ import annotations

import os
import sys
import threading
import time

DEFAULT_IP = "192.168.44.82"
_REPO_KIT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "..", "..", "docking_field_kit"))
_HOME_KIT = os.path.expanduser("~/Project/CAN-Relay/docking_field_kit")


class SeerAlarmSource:
    """1050 을 주기 폴링해 fatals/errors/warnings 와 CAN 계열 여부를 보관한다."""

    def __init__(self, ip: str = DEFAULT_IP, period_s: float = 2.0, logger=print):
        self.ip = ip
        self.period = float(period_s)
        self.log = logger
        self.available = False
        self.reason = "미시작"
        self._lock = threading.Lock()
        self._snap: dict = {}
        self._can_hits: list[str] = []
        self._updated: float | None = None
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="seer-alarm")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def latest(self) -> dict:
        with self._lock:
            return {"alarms": {k: dict(v) for k, v in self._snap.items()},
                    "can_hits": list(self._can_hits),
                    "age_s": round(time.monotonic() - self._updated, 1) if self._updated else None,
                    "available": self.available, "reason": self.reason}

    # ── 내부 ────────────────────────────────────────────────────────────────
    def _import_monitor(self):
        for kit in (_REPO_KIT, _HOME_KIT):
            if os.path.isfile(os.path.join(kit, "seer_can_monitor.py")):
                if kit not in sys.path:
                    sys.path.insert(0, kit)
                import seer_can_monitor
                return seer_can_monitor
        raise ImportError(f"seer_can_monitor.py 를 찾지 못했습니다 (탐색: {_REPO_KIT}, {_HOME_KIT})")

    def _loop(self):
        try:
            mon = self._import_monitor()
            from seer_core.client import RobokitClient
        except Exception as exc:
            self.reason = f"모듈 import 실패: {exc}"
            self.log(f"[seer] 비활성: {self.reason}")
            self._running = False
            return
        client = None
        while self._running:
            try:
                if client is None:
                    client = RobokitClient(self.ip)
                snap = mon.snapshot(client)
                hits = [f"[{lvl}] {code} {desc}"
                        for lvl, items in snap.items()
                        for code, desc in items.items() if mon.is_can(code, desc)]
                with self._lock:
                    self._snap = snap
                    self._can_hits = hits
                    self._updated = time.monotonic()
                if not self.available:
                    self.available = True
                    self.reason = f"1050 폴링 중 ({self.ip})"
                    self.log(f"[seer] {self.reason}")
            except Exception as exc:
                client = None
                if self.available or self.reason == "미시작":
                    self.reason = f"접속 실패 ({self.ip}): {type(exc).__name__}"
                    self.log(f"[seer] {self.reason}")
                self.available = False
            time.sleep(self.period)
