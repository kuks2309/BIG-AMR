#!/usr/bin/env python3
"""`verify_doc_claims.py` 가 **실제로 오류를 잡는지** 확인한다. 미검출이면 exit 1.

「검사기를 붙였다」는 통과 숫자로 말하지 않는다 — 문서를 일부러 틀리게 바꿔 놓고
검사기가 exit 1 을 내는지로 말한다. 되돌렸는데도 통과하지 않으면 그것도 실패다.

사용:
    python3 Tools/tongyi_protocol/mutation_check.py
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/tongyi_can_protocol/2026-08-05.md"
VERIFY = ROOT / "Tools/tongyi_protocol/verify_doc_claims.py"

# (라벨, 원문 조각, 바꿀 조각) — 각각 문서의 서로 다른 주장 갈래를 건드린다.
MUTATIONS = [
    # ── 인쇄 수치 변조 ──
    ("[실측] 캡처 규모", "253,510 프레임", "253,511 프레임"),
    ("[실측] 프레임율", "179.97 s | 1,409", "179.97 s | 1,509"),
    ("[실측] SDO 지연", "0.980 ms", "0.880 ms"),
    ("[실측] 쓰기 ack", "1.224 ms", "1.324 ms"),
    ("[실측] 폴링 건수", "18,560 (103.1 Hz)", "18,561 (103.1 Hz)"),
    ("[실측] 0x607A 분포", "6,319 (97.8 %)", "6,318 (97.8 %)"),
    ("[실측] 정착값", "7,882,001", "7,882,002"),
    ("[실측] 궤적 표본", "7,872,820", "7,872,821"),
    ("[실측] 버스 부하(정상)", "**70.5 %**", "**71.5 %**"),
    ("[실측] 스터핑", "+9.98 %", "+8.98 %"),
    ("[실측] 두절 무응답", "**3,389**", "**3,390**"),
    ("[실측] 호밍 타임스탬프", "**17.925 / 17.926**", "**17.925 / 17.927**"),
    ("[실측] 리밋 물림", "**47.025 / 47.025**", "**47.025 / 47.026**"),
    ("[실측] 구동 추종", "1,220.8", "1,220.9"),
    ("[실측] 평균 간격", "119.4 ms", "118.4 ms"),
    ("[실측] 다른 캡처 DI", "**`0x03`**", "**`0x05`**"),
    ("[실측] 드라이브 리드백", "`0x609A` Homing acceleration | 100", "`0x609A` Homing acceleration | 200"),
    # ── 인용 좌표 변조 ──
    ("[규격] V7.0 페이지", "§6.6.1 **page 149–150**", "§6.6.1 **page 148–150**"),
    ("[규격] [7.9] 페이지", "[7.9] §6.1 **page 120**", "[7.9] §6.1 **page 121**"),
    ("[규격] 부재 주장 페이지", "V7.0 **page 135**", "V7.0 **page 136**"),
    # ── 서술(부재 주장) 변조 — 초판이 틀렸던 바로 그 유형 ──
    ("[서술] 부재 주장 되살리기", "`0x4670` 보드레이트 주소(V7.0 **page 135**", "`0x4670` 은 V7.0 에 없다(page 999"),
    # ── EDS 주장 변조 ──
    ("[EDS] TPDO2 매핑", "`0x23000010`", "`0x23000011`"),
    ("[EDS] 변경 건수", "DefaultValue 18건 변경", "DefaultValue 17건 변경"),
    # ── 등급 변조 ──
    ("[등급] counts/° 순환 경고 제거", "순환이었다 — 인용 금지", "정확했다 — 그대로 인용 가능"),
    ("[등급] [설정] 표기 제거", "[설정] ⚠ **[실측] 이 아니다**", "[실측] 확정값"),
]


def run_verifier() -> int:
    return subprocess.run([sys.executable, str(VERIFY)], capture_output=True, text=True).returncode


def main() -> int:
    if not DOC.exists():
        print(f"문서 없음: {DOC}")
        return 2
    original = DOC.read_text(encoding="utf-8")
    digest = hashlib.sha256(original.encode()).hexdigest()

    print(f"대상 {DOC.relative_to(ROOT)}\n검사기 {VERIFY.relative_to(ROOT)}\n")
    base = run_verifier()
    if base != 0:
        print(f"✗ 기준선 실패 — 돌연변이 없이도 검사기가 exit {base} 다. 먼저 그것부터 고쳐라.")
        return 1
    print("기준선: 무변이 상태에서 통과 (exit 0)\n")

    undetected = []
    try:
        for label, old, new in MUTATIONS:
            if old not in original:
                undetected.append(f"{label} — 앵커 「{old}」 가 문서에 없다(문서 개정으로 앵커가 깨졌다)")
                print(f"  ⚠ {label:24s} 앵커 불일치: 「{old}」")
                continue
            DOC.write_text(original.replace(old, new, 1), encoding="utf-8")
            rc = run_verifier()
            mark = "✓ 검출" if rc != 0 else "✗ 미검출"
            print(f"  {mark} {label:24s} 「{old}」 → 「{new}」  (exit {rc})")
            if rc == 0:
                undetected.append(f"{label} — 「{old}」 를 「{new}」 로 바꿔도 통과했다")
    finally:
        DOC.write_text(original, encoding="utf-8")

    if hashlib.sha256(DOC.read_text(encoding='utf-8').encode()).hexdigest() != digest:
        print("\n✗ 복원 실패 — 문서가 원래대로 돌아가지 않았다.")
        return 1
    print("\n복원 확인: 원본과 동일 (sha256 일치)")

    restored = run_verifier()
    if restored != 0:
        print(f"✗ 복원 후 검사기가 exit {restored} — 되돌렸는데 통과하지 않는다.")
        return 1
    print("복원 후 재검증: 통과 (exit 0)")

    if undetected:
        print(f"\n미검출/앵커불일치 {len(undetected)}건:")
        for u in undetected:
            print(f"  ✗ {u}")
        return 1
    print(f"\n돌연변이 {len(MUTATIONS)}건 전부 검출됐다 — 검사기는 실제로 오류를 잡는다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
