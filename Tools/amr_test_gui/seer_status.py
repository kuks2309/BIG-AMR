#!/usr/bin/env python3
"""Seer 상태 폴링 — 1040(모터 값)·1050(알람) 읽기 + 4300(Fatal 리셋).

**Qt 를 알지 못한다.** 결과는 생성자가 받은 콜백으로만 나간다. 네트워크 읽기 전용이라
제어권과 무관하며, 판다·CAN 을 만지지 않는다(4300 만 예외적으로 쓰기 명령이다).

`RobokitClient` 는 사용자 저장소(`SEER_GUI`)의 것을 그대로 쓴다 — 이식하지 않는다.
"""
from __future__ import annotations

import sys
import threading
import time

from callbacks import emit

SEER_IP = "192.168.44.82"
SEER_GUI = "/home/nvidia/T-Robot_seer_gui"

POLL_S = 0.5          # 1040 폴링 주기
ALARM_EVERY = 4       # 1050 은 4 주기(≈2 s)에 한 번


def _client(ip: str):
    """Seer TCP/IP API 클라이언트 (사용자 저장소 동봉본)."""
    if SEER_GUI not in sys.path:
        sys.path.insert(0, SEER_GUI)
    from seer_core.client import RobokitClient
    return RobokitClient(ip)


class SeerStatus:
    """Seer 폴링 스레드.

    콜백은 **폴링 스레드에서** 불린다. 호출부가 스레드 경계를 책임진다(GUI 라면 Qt
    시그널 emit 을 넘긴다).

    창이 먼저 파괴되면 emit 이 `RuntimeError` 를 던진다 — 그때는 역추적만 남으므로
    **조용히 루프를 끝낸다**. 그 판정은 `callbacks.emit` 이 한 곳에서 내리므로, 어느
    콜백에서 창이 사라지든 같은 방식으로 끝난다(False 를 보면 그 자리에서 return).
    """

    def __init__(self, ip: str = SEER_IP, on_motors=None, on_status=None,
                 on_log=None, on_alarm_counts=None):
        self.ip = ip
        self.running = True
        self._alarm_tick = 0
        self._alarm_seen = set()
        self._motors_cb = on_motors
        self._status_cb = on_status
        self._log_cb = on_log
        self._counts_cb = on_alarm_counts

    def start(self) -> None:
        threading.Thread(target=self._loop, daemon=True, name="seer").start()

    def stop(self) -> None:
        self.running = False

    @staticmethod
    def fmt_alarm(item) -> str:
        """1050 항목을 한 줄로. 구조가 확정되지 않아 방어적으로 처리한다."""
        if isinstance(item, dict):
            code = item.get("code", item.get("id", ""))
            desc = (item.get("desc") or item.get("description")
                    or item.get("msg") or item.get("message") or "")
            return f"{code} {desc}".strip() or str(item)
        return str(item)

    def _loop(self):
        """Seer 1040(모터)·1050(알람) 폴링 — 네트워크 읽기 전용. 제어권과 무관하다."""
        try:
            cli = _client(self.ip)
        except Exception as exc:
            emit(self._log_cb, f"Seer 연결 불가: {type(exc).__name__}: {exc}")
            emit(self._status_cb,
                 f"Seer {self.ip} · 연결 불가 ({type(exc).__name__})", False)
            return
        while self.running:
            try:
                d = cli.call("status", 1040)
                ms = d.get("motor_info") or d.get("motors") or []
                if not self.running:    # 대기 중 종료됐으면 위젯을 건드리지 않는다
                    return
                if not emit(self._motors_cb,
                            {int(m["can_id"]): m for m in ms if m.get("can_id")}):
                    return
                if not emit(self._status_cb,
                            f"Seer {self.ip} · 연결됨 · 모터 {len(ms)}축 · "
                            f"갱신 {time.strftime('%H:%M:%S')}", True):
                    return
            except Exception as exc:    # 일시 실패는 상태 바에만 (제어 경로 아님)
                if not self.running:
                    return
                if not emit(self._status_cb,
                            f"Seer {self.ip} · 폴링 실패 ({type(exc).__name__})",
                            False):
                    return

            # 알람(1050)은 4 주기(=약 2 s)에 한 번. **신규만** 로그에 남긴다 —
            # Seer 는 해제되지 않은 오래된 항목도 계속 목록에 들고 있어서
            # 전량을 매번 찍으면 방금 난 것처럼 보인다(2026-07-27 오해 사례).
            self._alarm_tick += 1
            if self._alarm_tick % ALARM_EVERY == 0:
                try:
                    a = cli.call("status", 1050)
                    if not emit(self._counts_cb, len(a.get("fatals") or []),
                                len(a.get("errors") or [])):
                        return
                    for lvl in ("fatals", "errors", "warnings", "notices"):
                        for item in (a.get(lvl) or []):
                            line = self.fmt_alarm(item)
                            key = f"{lvl}|{line}"
                            if key not in self._alarm_seen:
                                self._alarm_seen.add(key)
                                if not emit(self._log_cb, f"[{lvl}] {line}"):
                                    return
                except Exception:
                    pass
            time.sleep(POLL_S)

    def clear_fatal(self, done=None) -> None:
        """Seer Fatal 오류코드 클리어 — config API 4300. 별도 스레드로 나간다.

        근거: References/Seer-Driver/github_sdk/robotkit-netprotocol-l-1.2.1.txt §5.2.5
              요청 4300 (0x10CC) robot_config_clearfatal_req / 응답 14300, JSON 데이터 없음.
        ⚠ 이름 그대로 **Fatal 만** 지운다. errors·warnings 는 대상이 아니다(표시는 계속 유지).
        ⚠ 지금까지의 Seer 기능과 달리 이건 **로봇 상태를 바꾸는 쓰기 명령**이다.
        """
        def work():
            try:
                res = _client(self.ip).call("config", 4300)
                rc = res.get("ret_code") if isinstance(res, dict) else res
                emit(self._log_cb, f"Fatal 리셋 요청(4300) → ret_code={rc}")
                self._alarm_seen.clear()          # 재표시되게 중복필터 초기화
            except Exception as exc:
                emit(self._log_cb, f"Fatal 리셋 실패: {type(exc).__name__}: {exc}")
            finally:
                emit(done)

        threading.Thread(target=work, daemon=True, name="clearfatal").start()
