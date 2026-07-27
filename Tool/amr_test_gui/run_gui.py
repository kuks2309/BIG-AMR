#!/usr/bin/env python3
"""Tongyi 4축 AMR 구동 테스트 GUI 진입점.

  python3 run_gui.py --dry-run          # 하드웨어 무접촉 시뮬레이터 (검증계단 ①)
  python3 run_gui.py                    # 실기 판다 relay (⚠ 실로봇 구동)

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
    ap.add_argument("--dry-run", action="store_true",
                    help="시뮬레이터 버스 사용 (판다·모터 무접촉). UI·램프·FAULT 경로 검증용")
    ap.add_argument("--seer-ip", default=DEFAULT_IP,
                    help=f"Seer 알람 폴링 대상 IP (기본 {DEFAULT_IP}, 무선망)")
    args = ap.parse_args()
    if not args.dry_run:
        print("⚠ 실기 모드 — 실로봇이 움직입니다. E-stop 상비, 이동구역 확보, 저속부터.", flush=True)
    return run(dry_run=args.dry_run, seer_ip=args.seer_ip)


if __name__ == "__main__":
    sys.exit(main())
