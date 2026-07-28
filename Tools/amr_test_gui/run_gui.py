#!/usr/bin/env python3
"""Tongyi 4축 AMR 구동 테스트 GUI 진입점 — 실기 전용.

  python3 run_gui.py        # ⚠ 실로봇이 움직인다

판다는 USB 장치 하나이므로 검출 여부로 확인된다. 시뮬레이션 모드는 두지 않는다.

ADR: docs/adr/2026-07-27-amr-test-gui.md  ·  안전 절차는 README.md 참조.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from amr_test_gui.seer_source import DEFAULT_IP   # noqa: E402
from amr_test_gui.ui_main import run              # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Tongyi 4축 AMR 구동 테스트 GUI")
    ap.add_argument("--seer-ip", default=DEFAULT_IP,
                    help=f"Seer 알람 폴링 대상 IP (기본 {DEFAULT_IP}, 무선망)")
    args = ap.parse_args()
    print("⚠ 실로봇이 움직입니다. 이동구역 확보, 저속부터.", flush=True)
    return run(seer_ip=args.seer_ip)


if __name__ == "__main__":
    sys.exit(main())
