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
  S6 검증 명령 없는 절대형 부정 — "한 줄도 없다"/"존재하지 않는다"/"막을 수단이 없다"
                            류의 **절대형** 부정 단정 주변에 확인 명령이 없음.
                            실제 사례: "우리가 못 막습니다" 를 인용 없이 단정했으나 차단
                            기계가 이미 존재했음(2026-07-28-005) · "gui.py 에 브링업이
                            한 줄도 없다" 가 거짓이었음(2026-07-29-003).
                            **주의**: 일반 부정("없다"·"않는다")은 대상이 아니다 —
                            오탐이 많아지면 게이트가 무시되므로 절대형만 잡는다.

ADVISORY 항목 (FAIL 아님, 사람이 확인):
  A1 '실측' 라벨 문장 목록 — 각 문장의 수치에 1차 출처가 있는지 사람이 대조할 것.
                            실제 사례: "실측 폴 부하 ≈900~1,000 fps"(출처 0건),
                            "227~243 Hz"(다른 측정에서 차용), "≈35 Hz"(분모 혼입)

검사 대상 (2026-07-29 확대):
  · `.md`  — S1~S6 전부. 리뷰 산출물·ADR·부채 registry 등
  · 그 외(`.py`·`.yaml`·`.h`·`.c` …) — **S6 만**. 리뷰가 인용하는 소스의 주석·docstring 이
    사각지대였다(2026-07-29-003). S1~S5 는 리뷰 문서 구조 전용이라 적용하지 않는다.

사용:  python3 review-claim-lint.py <리뷰.md> [...]
       python3 review-claim-lint.py --advisory <리뷰.md>   # A1 목록도 출력
       python3 review-claim-lint.py <소스.py> ...          # S6 만 적용
       python3 review-claim-lint.py --selftest             # S6 회귀 10건 (인라인 픽스처)
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

# ── S6 ─────────────────────────────────────────────────────────────────────
# 대상은 **절대형 부정**뿐이다. 일반 부정("없다"·"않는다")까지 잡으면 인벤토리의
# "전역 변수 없음"(SOP 룰 10 이 의무화한 표기)까지 걸려 오탐이 폭발한다.
# 아래 목록은 실제 사건(2026-07-28-005 · 2026-07-29-003)에서 나온 어형만 담는다.
ABSOLUTE_NEG = re.compile(
    r"한 줄도 없|하나도 없|전혀 없|어디에도 없|아무것도 없|아무 것도 없"
    r"|존재하지 않|실재하지 않"
    r"|불가능하다|불가능하며|불가능이다"
    # ⚠ 일반형 "할 수 없다"·"알 수 없다" 는 **일부러 뺐다.** 그것은 대개 인용된 사실에서
    #    끌어낸 *결과 서술*이라 오탐이 된다(실측: trnav-icp-odometry/2026-07-28.md:256
    #    "`exec_depend` 는 A, B 뿐 … rosdep 으로 환경을 재현할 수 없다" — 근거는 이미 있다).
    #    문서화된 실패 사례는 전부 *존재·차단능력* 형이므로 그쪽만 잡는다.
    r"|막을 수 없|멈출 수 없|못 막"
    r"|(?:장치|수단|경로|방법|기계|발행자|구독자|소비자)[가는이] (?:하나도 )?없")
# 근거로 인정하는 것 두 종류 — 리뷰 SOP 룰 8("추측 금지 — grep, LSP, 실측 인용")과 같은 범위다.
#   ① 실행 가능한 도구 호출 또는 그 결과 표기
#   ② `파일:줄` 인용 (`board/usb_comms.h:314-315`, 파일이 문맥상 확정된 경우의 `:321`)
# "확인했다"·"검토 결과" 같은 자기 진술은 인정하지 않는다 — 그게 정확히 실패 유형이다.
#
# ② 를 넣은 이유(2026-07-29 실측): ① 만 인정했더니 기존 통과 산출물
# `docs/code_review/can_relay_firmware/2026-07-28.md` 에 신규 FAIL 3건이 생겼고,
# 원문 대조 결과 **3건 전부 오탐**이었다(:559 `:321`/`:296-297`, :673 `:245`/`:349-351`,
# :737 `board/usb_comms.h:314-315`/`__init__.py:178` 로 이미 근거를 대고 있었다).
# 오탐이 남으면 게이트가 꺼지므로 SOP 와 같은 범위로 맞춘다.
VERIFY_CMD = re.compile(
    r"\bgrep\b|\brg\b|\bfind\b|\bls\b|\bgit\b|\bnm\b|objdump|readelf|strings\b"
    r"|python3 -c|pytest|\bwc -l\b|ros2 (?:topic|node|param|service|pkg)"
    r"|→ *0 *건|→ *0건|0 *건\)|exit=|확인 명령|근거 명령"
    r"|[\w./\-]+\.(?:py|c|h|hpp|cpp|cc|md|ya?ml|sh|json|jsonl|txt)\s*:\s*\d+"
    r"|`:\d+(?:[-~]\d+)?`")
FENCE = re.compile(r"^\s*(```|~~~)")


def _s6(path, lines):
    """절대형 부정 단정 주변에 확인 명령이 있는가.

    증거 창(window) = 앞 1줄 + 해당 줄 + 뒤 4줄. 근거를 바로 다음 줄에 붙이는
    통상 서술을 통과시키되, 근거 없이 문단을 넘겨 버리는 경우는 잡는다.
    """
    out, in_fence = [], False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue                      # 코드 블록 자체가 명령·출력이다
        if line.lstrip().startswith(">"):
            continue                      # 인용(타인 주장 재인용)은 대상 아님
        if not ABSOLUTE_NEG.search(line):
            continue
        # 따옴표 안의 부정은 대상 아님 — 남의 주장 재인용(판정 표)이거나
        # 패턴 자체를 논하는 메타 서술이다(예: `"안 된다·불가능하다" 에는 같은 기준을…`).
        # ⚠ 따옴표 종류별로 **쌍을 맞춰** 구간을 잡아야 한다. 예전처럼 임의 길이 하한만
        # 두면 `"된다" 만 … "안 된다·불가능하다"` 에서 짝이 어긋나 인용 구간을 놓쳤다.
        spans = [m.span() for m in re.finditer(
            r'"[^"]*"|\'[^\']*\'|「[^」]*」|『[^』]*』|“[^”]*”', line)]
        if any(a <= m.start() < b
               for m in ABSOLUTE_NEG.finditer(line) for a, b in spans):
            # 인용 밖에도 부정이 있으면 그건 여전히 대상이다
            if all(any(a <= m.start() < b for a, b in spans)
                   for m in ABSOLUTE_NEG.finditer(line)):
                continue
        window = "\n".join(lines[max(0, i - 1):i + 5])
        if not VERIFY_CMD.search(window):
            out.append(("S6", f"{path}:{i+1} 절대형 부정에 확인 명령 없음 "
                              f"— {line.strip()[:80]}"))
    return out


def lint(path, s6_only=False):
    text = open(path, encoding="utf-8").read()
    lines = text.split("\n")
    fails, advisory = [], []
    if s6_only:
        return _s6(path, lines), []
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

    # ── S6 검증 명령 없는 절대형 부정 ──
    fails.extend(_s6(path, lines))

    # ── A1 advisory: '실측' 라벨 문장 ──
    for i, l in enumerate(lines, 1):
        if SECTION.match(l) or FINDING.match(l) or l.lstrip().startswith(">"):
            continue
        if MEASURE.search(l):
            advisory.append((i, l.strip()[:110]))

    return fails, advisory


# ── S6 회귀 시험 (인라인 픽스처 — 외부 경로 의존 0, 저장소에서 그대로 재현) ──────
# S4 가 금지하는 하드코딩 절대경로를 쓰지 않기 위해 임시파일 대신 문자열로 검사한다.
S6_CASES = [
    # (이름, 본문, 기대 FAIL 수)
    ("사고 재현본 — 근거 없는 절대형 부정",
     "gui.py 에는 이 시퀀스가 한 줄도 없다 — 그 코드는 Seer 가 브링업한 축에 올라탄다.", 1),
    ("근거 병기 — 도구 호출",
     "gui.py 에는 이 시퀀스가 한 줄도 없다.\n근거: grep -nE '0x6060' gui.py → 0건", 0),
    ("근거 병기 — 파일:줄 인용 (리뷰 SOP 룰 8 과 동일 범위)",
     "대조할 방법이 없다 — `board/usb_comms.h:314-315` 는 두 버전만 반환한다.", 0),
    ("근거 병기 — 문맥 확정된 `:줄` 인용",
     "신선한 응답이 존재하지 않는다(`:296-297` 이 캐시를 갱신하기 전).", 0),
    ("인용 안의 부정 — 메타 서술은 대상 아님",
     '**"된다" 만 조심하고 "안 된다·불가능하다" 에는 같은 기준을 적용하지 않았다.**', 0),
    ("인용 밖 부정은 여전히 대상 — 인용 예외가 구멍이 되면 안 된다",
     '사용자는 "불가능하다" 라고 했지만, 실제로 이를 막는 장치가 없다.', 1),
    ("코드 블록 안은 대상 아님(명령·출력 자체다)",
     "```\ngrep foo bar  # 결과가 하나도 없다\n```", 0),
    ("인용문(> ) 은 대상 아님",
     "> 리뷰어 3: 브링업이 한 줄도 없다", 0),
    ("일반형 '할 수 없다' 는 대상 아님(결과 서술이라 오탐이 된다)",
     "exec_depend 는 두 개뿐이라 rosdep 으로 환경을 재현할 수 없다.", 0),
    ("일반 부정 '없다' 는 대상 아님(인벤토리 '없음' 표기 보호)",
     "전역 변수 / 모듈 상수 없음.", 0),
]


def selftest():
    bad = 0
    for name, body, expect in S6_CASES:
        got = len(_s6("<selftest>", body.split("\n")))
        ok = got == expect
        bad += 0 if ok else 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} (기대 {expect} / 실제 {got})")
    print(f"\nS6 selftest: {len(S6_CASES) - bad}/{len(S6_CASES)} PASS")
    return 0 if bad == 0 else 1


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_adv = "--advisory" in sys.argv
    if "--selftest" in sys.argv:
        return selftest()
    if not args:
        print(__doc__)
        return 2
    total = 0
    for p in args:
        # `.md` 는 S1~S6 전부, 그 외(소스)는 S6 만 — S1~S5 는 리뷰 문서 구조 전용이다.
        s6_only = not p.lower().endswith(".md")
        fails, advisory = lint(p, s6_only=s6_only)
        scope = "S6만" if s6_only else "S1~S6"
        print(f"=== {p} [{scope}] — FAIL {len(fails)}건 / advisory {len(advisory)}건 ===")
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
