#!/usr/bin/env python3
"""리뷰 산출물의 '주장 품질'을 기계 검출한다.

2026-07-28 CAN Relay firmware 리뷰에 대한 10-에이전트 감사에서 실제로 잡힌 실패
유형만 대상으로 한다. **구조적으로 판정 가능한 것만 FAIL 로 처리**하고, 정규식으로
신뢰 있게 판정할 수 없는 것(무근거 수치 등)은 FAIL 이 아니라 '수동 확인 후보'로만
출력한다 — 오탐이 많은 게이트는 아무도 돌리지 않게 되어 없느니만 못하기 때문이다.

FAIL 항목 (구조적·고정밀):
  S1 인벤토리 번호 결번   — 표 `#` 번호가 연속이 아님 = 전수성 미충족(리뷰 SOP 룰 1 "누락 0")
                            실제 사례: §4-1 이 "42행 중 18개 발췌"로 24행 누락
  S2 severity 분포 불일치 — 선언 분포 ≠ 실제 findings 헤더 수
                            실제 사례: "High 16" 선언, 실제 20건
  S3 dangling 내부 참조   — "전체는 X" / "자세히는 X" 가 문서에 없는 절을 가리킴
                            실제 사례: "전체는 A4 인벤토리" — 그런 절이 없음
  S4 재현 불가 검증 스크립트 — 동반 스크립트에 하드코딩 절대경로(/tmp·/home)
                            실제 사례: verify.py·gen.py 가 스크래치패드 경로를 가리켜
                            저장소 사본이 아닌 임시 사본을 검증
  S5 장치 조회 없는 [동작] 확정 — `[동작]` 라벨을 쓰면서 같은 findings 블록에
                            장치 조회 근거가 없음. reverse_engineering SOP §6
                            ("동작 주장은 배포자산 대조 전 확정 금지")의 기계 검사.
                            실제 사례: 배포 *파일* md5 만 보고 "실기에 플래시된 적 없다"
                            고 확정 → 실기 조회 결과 정반대였음(2026-07-28-011)

ADVISORY 항목 (FAIL 아님, 사람이 확인):
  A1 '실측' 라벨 문장 목록 — 각 문장의 수치에 1차 출처가 있는지 사람이 대조할 것.
                            실제 사례: "실측 폴 부하 ≈900~1,000 fps"(출처 0건),
                            "227~243 Hz"(다른 측정에서 차용), "≈35 Hz"(분모 혼입)

사용:  python3 review-claim-lint.py <리뷰.md> [...]
       python3 review-claim-lint.py --advisory <리뷰.md>   # A1 목록도 출력
반환:  S* 위반 0 이면 exit 0
"""
import os
import re
import sys

SEV = re.compile(r"severity 분포: Critical (\d+) / High (\d+) / Medium (\d+) / Low (\d+) / Info (\d+)")
FINDING = re.compile(r"^\*\*.*\((Critical|High|Medium|Low|Info)[ ,)—]")
SECTION = re.compile(r"^#{1,3} (.+)$")
REF = re.compile(r"전체는 ([^\s.,)·]+)|자세[한히]는 ([^\s.,)·]+)")
ROW = re.compile(r"^\| (\d{3})(?:[~·](\d{3}))? \|")
BEHAVIOR = re.compile(r"\[동작\]")
# 동작 근거로 인정하는 것: ① 장치 직접 조회 ② 실기 캡처 로그 재집계
#   — 둘 다 "배포자산 대조"에 해당한다(reverse_engineering SOP §6).
#   문서·소스 인용만으로는 [동작] 을 확정할 수 없다.
DEVICE_EVIDENCE = re.compile(
    r"0xd2|0xd3|0xd4|0xd6|0xc3|get_signature|실기 실측|실기 조회|실기 판독|실기 캡처"
    r"|Log/[\w.\-]+\.jsonl|캡처 재집계|캡처 실측|캡처 전수")
MEASURE = re.compile(r"(?<![가-힣])실측(?![가-힣])|관측값|측정값")


def lint(path):
    text = open(path, encoding="utf-8").read()
    lines = text.split("\n")
    fails, advisory = [], []
    headings = {SECTION.match(l).group(1).strip() for l in lines if SECTION.match(l)}

    # ── S1 인벤토리 번호 결번 ──
    for lo, hi, label in ((201, 249, "자작 전역/상수"), (250, 299, "upstream 전역")):
        nums = set()
        for l in lines:
            m = ROW.match(l)
            if m and lo <= int(m.group(1)) <= hi:
                a = int(m.group(1))
                b = int(m.group(2)) if m.group(2) else a
                nums.update(range(a, b + 1))
        if nums:
            gaps = [n for n in range(min(nums), max(nums) + 1) if n not in nums]
            if gaps:
                fails.append(("S1", f"{label} 번호 결번 {gaps} — SOP 룰 1 '누락 0' 미충족"))

    # ── S2 severity 분포 ↔ 실제 헤더 수 ──
    m = SEV.search(text)
    if m:
        keys = ("Critical", "High", "Medium", "Low", "Info")
        declared = dict(zip(keys, map(int, m.groups())))
        actual = dict.fromkeys(keys, 0)
        for l in lines:
            f = FINDING.match(l)
            if f:
                actual[f.group(1)] += 1
        # 문서가 "Low N건 중 M건은 다른 절에" 라고 명시하면 그만큼 허용
        slack = {k: 0 for k in keys}
        sm = re.search(r"Low (\d+)건 중 (\d+)건", text)
        if sm:
            slack["Low"] = int(sm.group(2))
        for k in keys:
            if abs(declared[k] - actual[k]) > slack[k]:
                fails.append(("S2", f"severity 선언 {k}={declared[k]} ≠ 실제 헤더 {actual[k]}"))

    # ── S3 dangling 내부 참조 ──
    for i, l in enumerate(lines, 1):
        # 참조가 절 제목 안에 있으면 그 제목 자신은 대상 후보에서 제외한다
        # (그러지 않으면 "## … 전체는 A4 인벤토리" 가 스스로를 참조 대상으로 인정한다)
        own = SECTION.match(l).group(1).strip() if SECTION.match(l) else None
        pool = headings - {own} if own else headings
        for mm in REF.finditer(l):
            tgt = (mm.group(1) or mm.group(2)).strip("`§*")
            if len(tgt) < 2:
                continue
            if not any(tgt in h for h in pool):
                fails.append(("S3", f"{path}:{i} 참조 대상 절이 문서에 없음 → '{tgt}'"))

    # ── S4 동반 검증 스크립트의 하드코딩 절대경로 ──
    d = os.path.join(os.path.dirname(os.path.abspath(path)), "flow-src")
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            for j, l in enumerate(open(os.path.join(d, fn), encoding="utf-8"), 1):
                if re.search(r'["\'](?:/tmp/|/home/)[^"\']*["\']', l) and "__file__" not in l:
                    fails.append(("S4", f"flow-src/{fn}:{j} 하드코딩 절대경로 — 저장소에서 재현 불가"))

    # ── S5 [동작] 확정에 장치 조회 근거가 있는가 ──
    # findings 블록 = 헤더(**…(Severity)**) 부터 다음 헤더 직전까지.
    bounds = [i for i, l in enumerate(lines) if FINDING.match(l)] + [len(lines)]
    for k in range(len(bounds) - 1):
        blk = lines[bounds[k]:bounds[k + 1]]
        body = "\n".join(blk)
        if BEHAVIOR.search(body) and not DEVICE_EVIDENCE.search(body):
            fails.append(("S5", f"{path}:{bounds[k]+1} `[동작]` 확정에 장치 조회 근거 없음 "
                                f"— {blk[0].strip()[:70]}"))

    # ── A1 advisory: '실측' 라벨 문장 ──
    for i, l in enumerate(lines, 1):
        if SECTION.match(l) or FINDING.match(l) or l.lstrip().startswith(">"):
            continue
        if MEASURE.search(l):
            advisory.append((i, l.strip()[:110]))

    return fails, advisory


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_adv = "--advisory" in sys.argv
    if not args:
        print(__doc__)
        return 2
    total = 0
    for p in args:
        fails, advisory = lint(p)
        print(f"=== {p} — FAIL {len(fails)}건 / advisory {len(advisory)}건 ===")
        for code, msg in fails:
            print(f"  [{code}] {msg}")
        if show_adv:
            print(f"  --- A1 '실측' 문장 {len(advisory)}건 (수동으로 1차 출처 대조할 것) ---")
            for ln, s in advisory:
                print(f"      {p}:{ln}  {s}")
        total += len(fails)
    print(f"\nTOTAL FAIL {total}건 — {'PASS' if total == 0 else 'FAIL'}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
