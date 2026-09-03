#!/usr/bin/env python3
"""flash_gui 의 로직 계층 (뷰 분리) — 판다 상태 감지 + 플래시/복구 argv 구성. Qt 미의존.

UI 분리 원칙: 위젯은 여기 없다(전부 `flash_gui.py`). 플래시 로직 자체도 여기 없다 —
검증된 스크립트(`flash_new_board.py`·`flash_panda.py`)의 경로와 실행 argv 만 만든다.
경로는 이 파일 위치(`Tools/Can_Relay/ui/`) 기준 절대경로라 **어느 폴더에서 실행해도** 유효하다.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))                  # Tools/Can_Relay/ui
ROOT = os.path.dirname(HERE)                                       # Tools/Can_Relay
FLASH_NEW = os.path.join(ROOT, "flash_new_board.py")               # DFU·앱 겸용(서명검증)
FLASH_PANDA = os.path.normpath(os.path.join(ROOT, "..", "docking_field_kit", "flash_panda.py"))
DEFAULT_FW = os.path.join(ROOT, "panda-firmware", "board", "obj", "panda.bin.signed")
_PF = os.path.join(ROOT, "panda-firmware")                         # Panda/PandaDFU 감지용
if _PF not in sys.path:
    sys.path.insert(0, _PF)

MODE_TEXT = {
    "dfu": ("DFU 모드 (공장/부트스텁)", "#b36b00"),
    "app": ("앱 모드 (정상 부팅 중)", "#1a7f37"),
    "both": ("판다 2대 감지 — 모호", "#c0392b"),
    "multi": ("판다 여러 대 — 모호", "#c0392b"),
    "none": ("판다 없음 (USB·udev 확인)", "#7a7a7a"),
    "error": ("감지 오류", "#c0392b"),
}


def detect():
    """현재 판다 상태를 (mode, detail) 로 돌려준다.

    mode ∈ {'dfu','app','none','both','multi','error'}. 'both'/'multi' 는 대상이
    모호하므로 호출부가 플래시를 막는다(flash_new_board.py 도 2대 이상이면 중단한다).
    """
    try:
        from python import Panda
        from python.dfu import PandaDFU
        apps = list(Panda.list() or [])
        dfus = list(PandaDFU.list() or [])
    except Exception as exc:                                       # pragma: no cover - 실기 전용
        return ("error", f"{type(exc).__name__}: {exc}")
    if dfus and apps:
        return ("both", f"DFU {dfus} + 앱 {apps} — 한 대만 남기세요")
    if len(dfus) > 1:
        return ("multi", f"DFU {len(dfus)}대 {dfus} — 한 대만 남기세요")
    if dfus:
        return ("dfu", dfus[0])
    if len(apps) > 1:
        return ("multi", f"앱 {len(apps)}대 {apps} — 한 대만 남기세요")
    if apps:
        return ("app", apps[0])
    return ("none", "")


def flash_argv(fw):
    """DFU·앱 겸용 플래시 실행 argv (flash_new_board.py 가 모드 자동 처리)."""
    return [sys.executable, FLASH_NEW, "--fw", fw]


def recover_argv():
    """부트스텁 갇힘 → DFU 로 밀어넣는 복구 argv."""
    return [sys.executable, FLASH_PANDA, "--recover"]
