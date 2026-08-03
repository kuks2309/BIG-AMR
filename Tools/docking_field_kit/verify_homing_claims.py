#!/usr/bin/env python3
"""호밍 문서의 **파생 수치**를 `Log/` 원자료로 재계산해 대조한다.

## 왜 있는가

`docs/claude-mistake/2026-08-03-001_fanout-baseline-unverified.md`:
2026-08-03 15:40 에 에이전트 14명에게 정정 기준선을 배포했는데 그 기준선의
**파생 수치 2개가 틀렸고**(「13회 연속 성공」·「`0x6064`=0 은 1회 관측·재현 안 됨」)
42개 문서 70여 곳에 사실로 박혔다. 1차 측정(호밍 10/10)은 맞았지만 거기서 **파생한 집계**를
원자료로 재계산하지 않고 기억과 추론으로 썼다.

⇒ **원자료가 있는 수치는 원자료로 재계산해서 대조한다.** 사람이 세지 않는다.

## 검사 항목

| 항목 | 산출 방식 |
|---|---|
| 호밍 시도·성공·실패 | `Log/*_summary.json` 의 `runs[].final_state` + `Log/homing_edge_*.json` |
| 최장 연속 성공 | 위 회차를 시각순 정렬 후 마지막 실패 이후 성공 수 |
| 소요 평균·중앙·범위 | `runs[].elapsed` |
| WAIT(state 4) 체류 | `fsm_trace` 의 state4 진입 → state8 진입 차 |
| 정착값·σ | `runs[].post` 의 node3/node4 위치 (모표준편차·표본표준편차 병기) |
| `0x6064`=0 관측 캡처 수 | 캡처별 zero/total |

문서 대조는 `--docs` 로 켠다 — 위 재계산값과 **어긋나는 숫자**를 쓰는 문서를 찾아 보고한다.

사용:
  python3 verify_homing_claims.py                 # 재계산만
  python3 verify_homing_claims.py --docs          # 문서 대조까지 (어긋나면 exit 1)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
LOG = os.path.join(REPO, "Log")
DONE, ERR_TIMEOUT = 5, 6


def _trace(r: dict) -> list[dict]:
    """FSM 궤적. 키 이름이 산출 도구마다 다르다 — `transitions`(summary) / `fsm_trace`(edge)."""
    return r.get("transitions") or r.get("fsm_trace") or []


def _runs() -> list[dict]:
    """오늘 자산에서 **실제로 개시된** 호밍 회차만 모은다.

    ⚠ `baseline` 은 호밍이 아니라 레지스터 스냅샷이다(`orin_home_experiment.py` `snapshot()`).
      2026-08-03 에 이것을 성공 1회로 세어 「13회」가 나왔다 — 회차로 세지 않는다.
    ⚠ 궤적이 비면 개시되지 않은 것이다(수락 전 중단) — 시도로 세지 않는다.
    """
    out = []
    for path in sorted(glob.glob(os.path.join(LOG, "*_summary.json"))):
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        for i, r in enumerate(d.get("runs") or [], 1):
            if _trace(r):
                out.append({"src": f"{os.path.basename(path)}#{i:02d}", **r})
    for path in sorted(glob.glob(os.path.join(LOG, "homing_edge_*.json"))):
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        if _trace(d):
            out.append({"src": os.path.basename(path), **d})
    out.sort(key=lambda r: r["src"])
    return out


def _wait_dwell(r: dict) -> float | None:
    """WAIT(state 4) **체류** 시간. 개시 t=0 부터의 절대시각과 혼동하지 말 것."""
    t4 = t8 = None
    for e in _trace(r):
        st, t = e.get("state"), e.get("t")
        if st == 4 and t4 is None:
            t4 = t
        if st == 8 and t8 is None:
            t8 = t
    return None if (t4 is None or t8 is None) else t8 - t4


def _zero_captures() -> list[tuple[str, int, int, int, int]]:
    """`0x6064`=0 을 **직전 `0x6041` bit15 로 층화**해 센다.

    ⚠ 이 층화가 핵심이다. 두 관측은 전혀 다른 사안이다:
      - **bit15=0**(호밍 진행 중)의 0 → **정상·설계 동작**. 다수 캡처에서 재현되며 결함이 아니다.
      - **bit15=1**(호밍 아님)의 0 → **비정상**. `debt-036` 이 추적하는 것은 **이쪽뿐**이다.
    2026-08-03 에 이 둘을 섞어 세면 「7개 캡처에서 관측」 같은 오도된 수가 나온다.

    반환: (파일명, bit15=1 zero, bit15=1 total, bit15=0 zero, bit15=0 total)
    """
    out = []
    for path in sorted(glob.glob(os.path.join(LOG, "*260803*.jsonl"))):
        z1 = t1 = z0 = t0 = 0
        bit15: dict[int, int] = {}
        try:
            for line in open(path, encoding="utf-8", errors="replace"):
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                cid, data = d.get("id"), d.get("d")
                if cid is None or not data or not (0x581 <= cid <= 0x584):
                    continue
                b = bytes.fromhex(data) if isinstance(data, str) else bytes(data)
                if len(b) < 8:
                    continue
                node, idx = cid - 0x580, b[1] | (b[2] << 8)
                if idx == 0x6041:
                    bit15[node] = (int.from_bytes(b[4:6], "little") >> 15) & 1
                elif idx == 0x6064:
                    st = bit15.get(node)
                    if st is None:
                        continue          # 층화 불가 — 세지 않는다(추정 금지)
                    zero = int.from_bytes(b[4:8], "little", signed=True) == 0
                    if st == 1:
                        t1 += 1
                        z1 += zero
                    else:
                        t0 += 1
                        z0 += zero
        except Exception:
            continue
        if t1 or t0:
            out.append((os.path.basename(path), z1, t1, z0, t0))
    return out


def recompute() -> dict:
    runs = _runs()
    ok = [r for r in runs if r.get("final_state") == DONE]
    streak = 0
    for r in runs:
        streak = streak + 1 if r.get("final_state") == DONE else 0
    el = [r["elapsed"] for r in runs if r.get("final_state") == DONE and r.get("elapsed")]
    dw = [d for d in (_wait_dwell(r) for r in runs) if d is not None]
    pos = {3: [], 4: []}
    for r in runs:
        p = r.get("post") or {}
        for n in (3, 4):
            v = p.get(f"pos{n}") or p.get(str(n))
            if isinstance(v, int):
                pos[n].append(v)
    return {
        "runs": runs, "attempts": len(runs), "ok": len(ok),
        "fail": len(runs) - len(ok), "streak": streak,
        "elapsed": el, "dwell": dw, "pos": pos, "zero": _zero_captures(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", action="store_true", help="문서 대조까지 수행")
    args = ap.parse_args()
    m = recompute()

    print("=== 호밍 회차 (원자료 재계산) ===")
    for r in m["runs"]:
        st = r.get("final_state")
        print(f"  {r['src']:48s} state={st} "
              f"{'DONE' if st == DONE else ('ERR_TIMEOUT' if st == ERR_TIMEOUT else '?')}"
              f"  {r.get('elapsed')}")
    print(f"  ⇒ 시도 {m['attempts']} · 성공 {m['ok']} · 실패 {m['fail']} · "
          f"최장 연속 성공 {m['streak']}")

    if m["elapsed"]:
        e = m["elapsed"]
        print(f"\n=== 소요 ===\n  평균 {statistics.mean(e):.3f} · 중앙 {statistics.median(e):.3f} "
              f"· 범위 {min(e):.2f}~{max(e):.2f} (폭 {max(e) - min(e):.2f})")
    if m["dwell"]:
        d = m["dwell"]
        print(f"\n=== WAIT(state 4) 체류 ===\n  평균 {statistics.mean(d):.3f} "
              f"· 범위 {min(d):.2f}~{max(d):.2f}   ⚠ 개시~RESTORE 절대시각과 다름")
    print("\n=== 정착값 ===")
    for n in (3, 4):
        v = m["pos"][n]
        if len(v) >= 2:
            print(f"  node{n}: 중앙 {statistics.median(v):,.0f} · "
                  f"모σ {statistics.pstdev(v):.2f} · 표본σ {statistics.stdev(v):.2f} (n={len(v)})")
    print("\n=== 0x6064=0 관측 (직전 0x6041 bit15 로 층화) ===")
    print(f"  {'캡처':48s} {'bit15=1 (비정상·debt-036)':>26s} {'bit15=0 (호밍 중·정상)':>24s}")
    for name, z1, t1, z0, t0 in m["zero"]:
        if z1 or z0:
            print(f"  {name:48s} {f'{z1:,}/{t1:,}':>26s} {f'{z0:,}/{t0:,}':>24s}")
    n_cap = sum(1 for _, z1, _, _, _ in m["zero"] if z1)
    print(f"\n  ⇒ **bit15=1** 에서 0 이 나온 캡처 = {n_cap} 개  ← debt-036 이 추적하는 것")
    if n_cap > 1:
        print("     ⚠ 「단 1회 관측·재현 안 됨」 서술은 거짓")
    print(f"  ⇒ bit15=0(호밍 중) 의 0 은 "
          f"{sum(1 for _, _, _, z0, _ in m['zero'] if z0)} 개 캡처 — **정상**, 결함 아님")

    if not args.docs:
        return 0

    print("\n=== 문서 대조 ===")
    bad = []
    streak_pat = re.compile(r"(\d+)회 연속 성공")
    # 「물리 직진 앵커가 없다」 계열 — 2026-08-03 17:30 에 거짓으로 판정됐다.
    # 앵커는 실재한다(Seer steerOffset 교정 조향각 + 사용자 육안 확인). 부족한 것은
    # **정밀도**(≈±1° = ±57,344 c)이지 앵커 자체가 아니다.
    anchor_pat = re.compile(
        r"(물리 (?:직진 )?앵커[가는]? ?(?:부재|없|만들지 못)"
        r"|非-Seer 앵커[가는]? ?(?:부재|없|전무)"
        r"|물리 직진[^\n]{0,12}미확인)")
    # 같은 줄이나 근처에 정정 표시가 있으면 통과시킨다(이 저장소는 원문을 지우지 않고
    # 인접에 정정 블록을 다는 관례라, 원주장 문자열은 남아 있는 것이 정상이다).
    fixed_pat = re.compile(
        r"(재정정|❌|취소선|~~|거짓|철회|폐기|무효|오주장|틀렸|틀린"
        r"|재현된다|재현됨|앵커는 실재|정밀도 (?:부족|한계))")
    for root in ("docs", "src", "Tools"):
        for path in glob.glob(os.path.join(REPO, root, "**", "*.md"), recursive=True):
            if "user_instructions" in path:
                continue
            try:
                lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
            except Exception:
                continue
            rel = os.path.relpath(path, REPO)
            for i, line in enumerate(lines):
                ln = i + 1
                near = "\n".join(lines[max(0, i - 3):i + 9])
                # **과대주장만** 잡는다 — 「10회 연속 성공」(15:33 런 집합)은 참이므로 통과.
                # 정정 블록이 틀린 주장을 **인용**하는 경우도 통과(원문 보존 관례).
                for mt in streak_pat.finditer(line):
                    if int(mt.group(1)) > m["streak"] and not fixed_pat.search(near):
                        bad.append(f"{rel}:{ln} 「{mt.group(1)}회 연속 성공」 > 실제 최장 {m['streak']}")
                if n_cap > 1 and re.search(r"(단 1회|1회 관측)", line) and "6064" in line \
                        and not fixed_pat.search(near):
                    bad.append(f"{rel}:{ln} 「1회 관측」 — 실제 bit15=1 에서 {n_cap} 캡처 관측")
                if anchor_pat.search(line) and not fixed_pat.search(near):
                    bad.append(f"{rel}:{ln} 「물리 직진 앵커 부재」 오주장 — 앵커는 실재(정밀도 ≈±1°)")
    if bad:
        print(f"  ⚠ 불일치 {len(bad)}건")
        for b in bad[:40]:
            print("   ", b)
        return 1
    print("  불일치 0건 — PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
