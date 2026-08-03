#!/usr/bin/env python3
"""조향 스윕 + 3채널 동시 판독 — Seer 1005 의 전달함수를 실측한다.

지시: 2026-08-03 "seer에서 현재 교정된 조향값을 읽을 수 있음, 제어하면서 움직이고 확인하면 됨(자동화 가능)"

## 무엇을 판정하려는가

`docs/homing/2026-08-03-can-relay-homing-assets.md` §11~§12 가 남긴 공백 하나를 닫는다.

- **1040 `motor_info.position` 은 `0x6064` 의 아핀 변환이다** — 정지 상태 30 s 동시 샘플링에서
  CAN 의 6-counts 디더를 **정확히 6.0000 counts 간격**으로 추종했고 기울기 × 57,344 = 1.0000000.
  ⇒ 1040 으로는 CAN 과 교차검증이 성립하지 않는다(같은 데이터를 두 번 읽는 것).
- **1005 `steer_angles` 는 다른 채널이다** — 같은 시각 1040 이 +35 counts 를 보고할 때
  1005 는 **정확히 0.0** 이었고 디더를 전혀 잡지 않았다.
  그러나 **분해능·산출 방식이 벤더 문서에 없고**(`005-query-robot-speed.md:40`),
  **정지 상태에서는 1040 과 구분되지 않는다.**

⇒ **조향을 실제로 움직여 1005 의 계단을 관측해야** 전달함수가 나온다. 본 도구가 그것을 한다.

판정 산출:
  · 1005 가 CAN 에 대해 **선형인가** — 기울기 ×57,344 가 1.0 이면 같은 엔코더 유래
  · 1005 의 **양자화 단위** — 계단 폭(counts)
  · 1005 와 1040 의 **영점 차이** — 다르면 1005 는 별도 캘리브레이션을 거친 값
  · `r_steer_angles`(지령) vs `steer_angles`(실측) 분리

이 결과가 §11-5 의 「물리 직진에 대한 非-Seer 앵커 부재」를 부분적으로 메울 수 있다.
**단, 1005 가 결국 같은 엔코더를 거칠게 반올림한 것으로 드러나면 앵커가 아니다** — 그 판정도 본 도구가 한다.

## 조향 지령 경로 — GUI 의 검증된 패턴을 그대로 쓴다

`Tools/amr_test_gui/gui.py:441-444` `_steer_axis()`:
    0x607A = counts  (절대위치)  →  0x6040 = 0x3F  (즉시 적용)
enable 시퀀스는 보내지 않는다. 이 두 프레임만으로 실기에서 조향이 움직이는 것이 확인돼 있다.
**단계로 쪼개지 않는다** — 최종 절대 목표를 그대로 보내고 프로파일은 드라이브가 수행한다
(`docs/claude-mistake/2026-07-28-003` — 단계 램프는 실재하지 않는 메커니즘이었다).

## ⚠ 안전

· **조향 2축이 실제로 움직인다. 접지 상태면 차체가 움직인다.** 주변 확보 필수.
· 지령은 **홈 기준 ±`--range`** 로 제한하고, 절대 상한은 **±90°**(`STEER_LIMIT_DEG`)로 이중 클램프한다.
· heartbeat 는 **전용 스레드**가 보낸다(`Rig`) — 무작업 구간에서도 제어권이 풀리지 않는다.
· 매 측정점에서 **제어권 생존을 확인**한다. 풀렸으면 즉시 중단한다.
· Ctrl-C / 예외 / 정상 종료 어느 경로든 **홈으로 복귀시킨 뒤** 제어권을 반환한다.
· 구동륜에는 아무것도 보내지 않는다(`0x60FF` 미송신).

사용:
  python3 orin_steer_sweep_1005.py --dry-run             # 지령 미송신, 판독만
  python3 orin_steer_sweep_1005.py --range 5 --step 1    # 홈 기준 ±5° 를 1° 간격
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from orin_home_experiment import (  # noqa: E402
    CPD, FW_GOZERO, HOME_0DEG, OBJ_CTRL, OBJ_POS, OBJ_TARGET, STEER_NODES, CW_SETPOINT, Rig,
)

SEER_GUI = "/home/nvidia/T-Robot_seer_gui"
SEER_IP = "192.168.44.82"
STEER_LIMIT_DEG = 90.0          # 절대 상한 — gui.py:50 과 동일


def seer_client(ip: str):
    if SEER_GUI not in sys.path:
        sys.path.insert(0, SEER_GUI)
    from seer_core.client import RobokitClient
    return RobokitClient(ip)


def read_seer(cli) -> dict:
    """1040(모터별) + 1005(섀시 조향각) 를 한 번에 읽어 도(°)로 돌려준다."""
    out = {"a1040": {}, "a1005": {}, "cmd1005": {}}
    try:
        d = cli.call("status", 1040)
        for m in (d.get("motor_info") or []):
            node, pos = m.get("can_id"), m.get("position")
            if node in STEER_NODES and pos is not None:
                out["a1040"][int(node)] = float(pos) * 180.0 / math.pi
        if not out["a1040"]:
            # can_id 가 없는 펌웨어 — type==1(조향) 순서를 STEER_NODES 에 대응시킨다.
            st = [m for m in (d.get("motor_info") or []) if m.get("type") == 1]
            for node, m in zip(STEER_NODES, st):
                if m.get("position") is not None:
                    out["a1040"][node] = float(m["position"]) * 180.0 / math.pi
    except Exception as exc:
        out["err1040"] = f"{type(exc).__name__}: {exc}"
    try:
        s = cli.call("status", 1005)
        ang = s.get("steer_angles") or ([s["steer"]] if s.get("steer") is not None else [])
        for node, rad in zip(STEER_NODES, ang):          # 모델 파일 순서 = [front, rear]
            out["a1005"][node] = float(rad) * 180.0 / math.pi
        for node, rad in zip(STEER_NODES, s.get("r_steer_angles") or []):
            out["cmd1005"][node] = float(rad) * 180.0 / math.pi
    except Exception as exc:
        out["err1005"] = f"{type(exc).__name__}: {exc}"
    return out


def steer_counts(node: int, deg: float) -> int:
    """홈 기준 각도 → 절대 counts. ±90° 이중 클램프."""
    deg = max(-STEER_LIMIT_DEG, min(STEER_LIMIT_DEG, deg))
    return int(round(HOME_0DEG[node] + deg * CPD))


def command_steer(rig: Rig, deg: float):
    """GUI 와 동일: 0x607A(절대) → 0x6040=0x3F(즉시 적용). 두 축 동시."""
    for n in STEER_NODES:
        rig.sdo_write(n, OBJ_TARGET, 0, steer_counts(n, deg), 4)
        rig.sdo_write(n, OBJ_CTRL, 0, CW_SETPOINT, 2)


def measure(rig: Rig, cli, deg_cmd: float, samples: int, tag: str) -> dict:
    """한 지점에서 3채널을 채집한다."""
    rec = {"tag": tag, "deg_cmd": deg_cmd, "t": round(time.time() - rig.t0, 3),
           "authority_ok": rig.assert_authority(tag), "can": {}, "s1040": {}, "s1005": {},
           "s1005_cmd": {}}
    for n in STEER_NODES:
        rec["can"][n] = rig.pos_median(n, samples)
    acc = {"a1040": {n: [] for n in STEER_NODES},
           "a1005": {n: [] for n in STEER_NODES},
           "cmd1005": {n: [] for n in STEER_NODES}}
    for _ in range(samples):
        r = read_seer(cli)
        for key in acc:
            for n, v in (r.get(key) or {}).items():
                acc[key][n].append(v)
        time.sleep(0.05)
    for n in STEER_NODES:
        for src, key in (("s1040", "a1040"), ("s1005", "a1005"), ("s1005_cmd", "cmd1005")):
            vals = acc[key][n]
            rec[src][n] = statistics.median(vals) if vals else None
    return rec


def fmt(rec: dict) -> str:
    parts = []
    for n in STEER_NODES:
        c = rec["can"].get(n)
        d40 = rec["s1040"].get(n)
        d05 = rec["s1005"].get(n)
        cs = f"{c:,}" if c is not None else "?"
        parts.append(f"n{n} CAN={cs} 1040={d40:+.6f}° 1005={d05:+.6f}°"
                     if None not in (d40, d05) else f"n{n} CAN={cs} (Seer 판독 실패)")
    return " | ".join(parts)


def analyze(recs: list, out_path: str):
    """전달함수 산출 — 1005 가 CAN 에 대해 선형인가, 양자화 단위는 얼마인가."""
    print("\n" + "=" * 78, flush=True)
    print("전달함수 분석", flush=True)
    print("=" * 78, flush=True)
    good = [r for r in recs if r.get("authority_ok")]
    if len(good) < 2:
        print("  측정점이 2개 미만 — 분석 생략", flush=True)
        return
    for n in STEER_NODES:
        pts = [(r["can"][n], r["s1040"].get(n), r["s1005"].get(n))
               for r in good if r["can"].get(n) is not None]
        pts = [(c, a, b) for c, a, b in pts if a is not None and b is not None]
        if len(pts) < 2:
            print(f"\n  node{n}: 유효 측정점 부족", flush=True)
            continue
        cs = [p[0] for p in pts]
        print(f"\n  node{n} — 측정점 {len(pts)}개, CAN 이동폭 {max(cs)-min(cs):,} counts "
              f"({(max(cs)-min(cs))/CPD:+.3f}°)", flush=True)

        for label, idx in (("1040", 1), ("1005", 2)):
            xs = [p[0] for p in pts]
            ys = [p[idx] for p in pts]
            uniq = sorted(set(ys))
            n_pts = len(xs)
            mx, my = sum(xs) / n_pts, sum(ys) / n_pts
            den = sum((x - mx) ** 2 for x in xs)
            if den == 0:
                print(f"    {label}: CAN 이 움직이지 않아 기울기 산출 불가", flush=True)
                continue
            slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
            gain = abs(slope) * CPD
            # 계단 폭 = 인접 상이값 차의 최소
            steps = [round(abs(b - a) * CPD) for a, b in zip(uniq, uniq[1:])]
            q = min(steps) if steps else None
            print(f"    {label}: 상이값 {len(uniq):3d}개 · 기울기 {slope:+.9f} °/count "
                  f"→ |기울기|×57,344 = {gain:.6f}", flush=True)
            if q is not None:
                print(f"          최소 계단 ≈ {q:,} counts ({q/CPD:.6f}°)", flush=True)
            if len(uniq) == 1:
                print(f"          ⚠ 값이 전혀 변하지 않았다 — 이동폭이 {label} 분해능보다 작다",
                      flush=True)
            elif abs(gain - 1.0) < 0.01:
                print(f"          ⇒ **`0x6064` 와 같은 스케일** — 동일 엔코더 유래로 강하게 시사",
                      flush=True)
            else:
                print(f"          ⇒ 스케일이 다르다 — 별도 산출 경로 가능성", flush=True)

        # 영점 비교: 각 채널이 0° 라 부르는 counts
        for label, idx in (("1040", 1), ("1005", 2)):
            zs = [p[0] + p[idx] * CPD for p in pts]
            print(f"    {label} 영점 추정: 중앙 {statistics.median(zs):,.0f}c "
                  f"(폭 {max(zs)-min(zs):,.0f}c)", flush=True)
        print(f"    참고 — 채택 정본 홈 {HOME_0DEG[n]:,}c · 펌웨어 GOZERO {FW_GOZERO[n]:,}c",
              flush=True)
    print(f"\n  원자료: {out_path}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--range", type=float, default=5.0, help="홈 기준 ±범위(도)")
    ap.add_argument("--step", type=float, default=1.0, help="측정 간격(도)")
    ap.add_argument("--settle", type=float, default=2.5, help="지령 후 정착 대기(초)")
    ap.add_argument("--samples", type=int, default=8, help="지점당 샘플 수")
    ap.add_argument("--ip", default=SEER_IP)
    ap.add_argument("--dry-run", action="store_true", help="지령을 보내지 않고 현 위치만 판독")
    ap.add_argument("--yes", action="store_true", help="확인 프롬프트 생략")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if abs(args.range) > 20.0:
        ap.error("--range 는 20° 이하로 제한한다(접지 상태 안전). 더 필요하면 코드에서 근거와 함께 올릴 것")
    if args.step <= 0:
        ap.error("--step 은 양수여야 한다")

    pts = []
    d = -abs(args.range)
    while d <= abs(args.range) + 1e-9:
        pts.append(round(d, 4))
        d += args.step
    if 0.0 not in pts:
        pts.append(0.0)
    pts = sorted(set(pts))

    stamp = time.strftime("%y%m%d_%H%M%S")
    repo = os.path.abspath(os.path.join(HERE, "..", ".."))
    out = args.out or os.path.join(repo, "Log", f"steer_sweep_1005_{stamp}.jsonl")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    if not args.dry_run and not args.yes:
        print(f"⚠ 조향 2축이 실제로 움직인다 (홈 기준 {pts[0]:+.1f}° ~ {pts[-1]:+.1f}°, "
              f"{len(pts)}개 지점).", flush=True)
        print("  접지 상태면 차체가 움직인다. 주변 확보를 확인했는가?", flush=True)
        if input("  진행하려면 'yes' 입력: ").strip().lower() != "yes":
            print("중단했다."); return

    rig = Rig(out.replace(".jsonl", "_can.jsonl"))
    try:
        cli = seer_client(args.ip)
        print(f"Seer {args.ip} 연결 · 판다 fw={rig.p.get_version()}", flush=True)
    except Exception as exc:
        print(f"Seer 연결 실패: {exc}"); rig.close(); return

    recs = []
    try:
        rig.take()
        base = measure(rig, cli, 0.0, args.samples, "baseline")
        recs.append(base)
        print(f"\n기준선: {fmt(base)}", flush=True)

        if args.dry_run:
            print("--dry-run — 지령을 보내지 않고 종료한다.", flush=True)
        else:
            for i, deg in enumerate(pts, 1):
                if not rig.assert_authority(f"pt{i}"):
                    print("  ⚠ 제어권 상실 — 스윕을 중단한다.", flush=True)
                    break
                print(f"\n[{i}/{len(pts)}] 지령 {deg:+.2f}°", flush=True)
                command_steer(rig, deg)
                time.sleep(args.settle)
                rig.drain()
                rec = measure(rig, cli, deg, args.samples, f"pt{i}")
                recs.append(rec)
                print(f"    {fmt(rec)}", flush=True)
    except KeyboardInterrupt:
        print("\n⚠ 사용자 중단", flush=True)
    finally:
        try:
            if not args.dry_run and rig.controlling:
                print("\n>>> 홈(0°)으로 복귀", flush=True)
                command_steer(rig, 0.0)
                time.sleep(args.settle)
                rig.drain()
                back = measure(rig, cli, 0.0, args.samples, "return_home")
                recs.append(back)
                print(f"    {fmt(back)}", flush=True)
        except Exception as exc:
            print(f"⚠ 복귀 실패: {exc}", flush=True)
        rig.release()
        with open(out, "w", encoding="utf-8") as fh:
            for r in recs:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        rig.close()
        analyze(recs, out)


if __name__ == "__main__":
    main()
