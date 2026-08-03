#!/usr/bin/env python3
"""조향 2국면 대조 — can_relay 제어권 / Seer 제어권을 번갈아 쓰며 위치를 비교한다.

지시(2026-08-03 13:08): "can relay 로 제어권 획득하고 위치 읽고 / can relay 제어권 seer로 주고
api로 조향 명령 주고 위치 읽고 / 이렇게 비교하면 되는데"

## 왜 국면을 나누는가 — 한 국면에서는 원리적으로 불가능하다

판다가 제어권(`pc_authority`)을 쥐면 **emulate** 가 켜져, Seer 의 `0x6064`·`0x6041`·`0x606C`·`0x6078`
폴에 **판다의 얼어붙은 스냅샷**이 대신 답한다(`safety_seer_gate.h:71-74, 88-96`).
2026-08-03 13:05 실측이 이를 증명했다 — 조향을 **10.000° (573,434 counts) 움직였는데도**
Seer 1040·1005 가 **한 자리도 변하지 않았다**.

⇒ 움직이려면 제어권이 필요하고, Seer 를 읽으려면 제어권이 없어야 한다. **상호 배타다.**
   그래서 두 국면으로 나눈다.

## 국면 설계

**A 국면 — can_relay 가 제어권 보유**
  · 조향 지령: `0x607A`(절대) → `0x6040=0x3F`  (GUI `gui.py:441-444` 검증 경로)
  · 판독: CAN `0x6064` (모터 실응답, bus2 직접)
  · Seer 판독은 **무의미**(freeze) — 기록은 하되 판정에 쓰지 않는다.
  ⇒ 산출: **우리 지령각 ↔ CAN counts** 대응 (57,344 counts/° 검증)

**B 국면 — Seer 가 제어권 보유 (판다는 SILENT·passthrough, 송신 0건)**
  · 조향 지령: **Seer API 2010**(Open Loop Motion, 포트 19205).
    ⚠ 벤더 문서 상단: *"Controls only through vx, vy and w for multi-steering wheel."*
    `steer`/`real_steer` 는 **단일 조향륜 전용**이라 이 기체(듀얼)에서는 못 쓴다.
    ⇒ **vy(횡방향)** 로 크랩을 유도해 Seer 가 스스로 조향각을 만들게 한다.
  · 판독: CAN `0x6064`(수동 청취) + Seer 1005 `steer_angles` + 1040 — **셋 다 살아 있다**
  ⇒ 산출: **CAN counts ↔ Seer 1005 각도** 전달함수 (이것이 목표다)

**대조**: A 의 (지령각↔counts) 와 B 의 (counts↔1005) 를 이어 붙이면
`docs/homing/2026-08-03-can-relay-homing-assets.md` §11-5 가 남긴
「물리 직진에 대한 非-Seer 앵커」 질문에 답할 수 있다 —
1005 의 기울기 ×57,344 가 1.0 이면 같은 엔코더 유래(앵커 아님), 다르면 별도 경로.

## ⚠ 안전

· **A·B 모두 조향 2축이 실제로 움직인다. 접지 상태면 차체가 움직인다.** 주변 확보 필수.
· B 국면은 **Seer 가 로봇을 주행시킨다**(2010 은 개루프 속도 지령이다). vy 를 작게, duration 을 짧게.
  어느 종료 경로든 **API 2000(Stop Open Loop Motion)** 을 보낸다.
· A 국면은 홈 기준 `--range` 제한 + 절대 ±90° 이중 클램프. 종료 시 홈 복귀.
· heartbeat 는 `Rig` 의 전용 스레드가 담당(GUI `gui.py:819` 패턴). 매 판독 전 제어권 생존 확인.
· 구동륜에는 **우리가** 아무것도 보내지 않는다(A 국면 `0x60FF` 미송신).

사용:
  python3 orin_steer_two_phase.py --dry-run          # 지령 0건, 두 국면 판독만
  python3 orin_steer_two_phase.py --phase a          # A 국면만
  python3 orin_steer_two_phase.py --phase b --vy 0.02
  python3 orin_steer_two_phase.py --yes              # A → B 연속
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
    CPD, HOME_0DEG, OBJ_CTRL, OBJ_POS, OBJ_TARGET, STEER_NODES, CW_SETPOINT, Rig,
)
from orin_steer_sweep_1005 import (  # noqa: E402
    SEER_IP, STEER_LIMIT_DEG, read_seer, seer_client, steer_counts,
)

API_MOTION = 2010          # Open Loop Motion   (control, 19205)
API_STOP = 2000            # Stop Open Loop Motion


# ── 공통 판독 ─────────────────────────────────────────────────────────────
def read_can(rig: Rig, samples: int) -> dict:
    return {n: rig.pos_median(n, samples) for n in STEER_NODES}


def read_can_passive(p, samples: int, dwell: float = 0.5) -> dict:
    """송신 없이 bus2 를 청취해 0x6064 중앙값을 낸다(B 국면 전용)."""
    acc = {n: [] for n in STEER_NODES}
    end = time.time() + dwell
    while time.time() < end:
        for addr, _, dat, bus in p.can_recv():
            if bus != 2 or not dat:
                continue
            d = bytes(dat)
            if not (0x583 <= addr <= 0x584) or len(d) < 8 or d[0] not in (0x43, 0x47, 0x4B, 0x4F):
                continue
            if (d[1] | (d[2] << 8)) != OBJ_POS:
                continue
            v = int.from_bytes(d[4:8], "little")
            acc[addr - 0x580].append(v - (1 << 32) if v & 0x80000000 else v)
        time.sleep(0.005)
    return {n: (int(statistics.median(v)) if v else None) for n, v in acc.items()}


# 정착 판정 허용폭. 조향 디더는 실측 6 counts 이므로 그 10배를 잡는다.
SETTLE_TOL_COUNTS = 60


def settled_read(read_can_fn, cli, samples: int) -> dict:
    """CAN → Seer → CAN 재판독으로 **정착을 확인한 뒤** 한 점을 만든다.

    ## 왜 필요한가 (2026-08-03 13:1x 실측 결함)

    초판은 각 측정점에서 CAN 을 읽고 **그 다음** Seer 를 읽었다. 조향이 이동 중이면
    **CAN 은 이동 전 · Seer 는 이동 후**를 잡아 서로 다른 시점이 한 점으로 묶인다.
    실제로 2국면 실험 burst1 이 (CAN=홈, 1005=−90.01) 로 짝지어져 회귀 기울기가
    1.0 대신 **0.499** 로 나왔고, `orin_steer_straighten.py` 1회차에서도 재현됐다
    (CAN +90.000° ↔ 1005 −0.115°).

    ⇒ Seer 판독 **전후로 CAN 을 두 번** 읽어 그 사이 축이 움직였는지 본다.
      `SETTLE_TOL_COUNTS` 를 넘으면 `transient=True` 로 표시하고 **회귀에서 제외**한다.
      값을 버리지 않고 기록은 남긴다 — 이동 구간 자체가 관측 대상일 수 있다.
    """
    can1 = read_can_fn()
    seer = seer_median(cli, samples)
    can2 = read_can_fn()
    drift = {}
    transient = False
    for n in STEER_NODES:
        a, b = can1.get(n), can2.get(n)
        if a is None or b is None:
            transient = True
            continue
        drift[n] = b - a
        if abs(b - a) > SETTLE_TOL_COUNTS:
            transient = True
    return {"can": can2, "can_before": can1, "drift": drift,
            "transient": transient, **seer}


def seer_median(cli, samples: int) -> dict:
    acc = {"a1040": {n: [] for n in STEER_NODES},
           "a1005": {n: [] for n in STEER_NODES},
           "cmd1005": {n: [] for n in STEER_NODES}}
    for _ in range(samples):
        r = read_seer(cli)
        for key in acc:
            for n, v in (r.get(key) or {}).items():
                acc[key][n].append(v)
        time.sleep(0.05)
    out = {}
    for src, key in (("s1040", "a1040"), ("s1005", "a1005"), ("s1005_cmd", "cmd1005")):
        out[src] = {n: (statistics.median(v) if v else None) for n, v in acc[key].items()}
    return out


def fmt(can: dict, seer: dict, note: str = "") -> str:
    parts = []
    for n in STEER_NODES:
        c = can.get(n)
        a05 = (seer.get("s1005") or {}).get(n)
        a40 = (seer.get("s1040") or {}).get(n)
        cs = f"{c:,}" if c is not None else "?"
        s5 = f"{a05:+.6f}°" if a05 is not None else "?"
        s4 = f"{a40:+.6f}°" if a40 is not None else "?"
        parts.append(f"n{n} CAN={cs} 1005={s5} 1040={s4}")
    return " | ".join(parts) + (f"   {note}" if note else "")


# ── A 국면 ────────────────────────────────────────────────────────────────
def phase_a(rig: Rig, cli, pts, settle, samples, recs, dry):
    print("\n" + "=" * 78, flush=True)
    print("A 국면 — can_relay 제어권. 우리가 조향을 움직이고 CAN 을 읽는다.", flush=True)
    print("  ⚠ 이 구간의 Seer 판독은 emulate freeze 라 **판정에 쓰지 않는다**(기록만).", flush=True)
    print("=" * 78, flush=True)
    rig.take()
    try:
        m = settled_read(lambda: read_can(rig, samples), cli, samples)
        recs.append({"phase": "A", "tag": "baseline", "deg_cmd": 0.0,
                     "authority_ok": rig.assert_authority("A/base"), **m})
        print(f"기준선: {fmt(m['can'], m)}"
              + ("  ⚠transient" if m["transient"] else ""), flush=True)
        if dry:
            print("--dry-run — A 국면 지령 생략", flush=True)
            return
        for i, deg in enumerate(pts, 1):
            if not rig.assert_authority(f"A/pt{i}"):
                print("  ⚠ 제어권 상실 — A 국면 중단", flush=True)
                break
            for n in STEER_NODES:
                rig.sdo_write(n, OBJ_TARGET, 0, steer_counts(n, deg), 4)
                rig.sdo_write(n, OBJ_CTRL, 0, CW_SETPOINT, 2)
            time.sleep(settle)
            rig.drain()
            m = settled_read(lambda: read_can(rig, samples), cli, samples)
            recs.append({"phase": "A", "tag": f"pt{i}", "deg_cmd": deg,
                         "authority_ok": True, **m})
            print(f"[A {i}/{len(pts)}] 지령 {deg:+.2f}°  {fmt(m['can'], m)}"
                  + ("  ⚠transient" if m["transient"] else ""), flush=True)
    finally:
        if not dry and rig.controlling:
            print("\n>>> A 국면 종료 — 홈 복귀", flush=True)
            for n in STEER_NODES:
                rig.sdo_write(n, OBJ_TARGET, 0, steer_counts(n, 0.0), 4)
                rig.sdo_write(n, OBJ_CTRL, 0, CW_SETPOINT, 2)
            time.sleep(settle)
        rig.release()


# ── B 국면 ────────────────────────────────────────────────────────────────
def phase_b(rig: Rig, cli, vy, bursts, duration_ms, settle, samples, recs, dry):
    print("\n" + "=" * 78, flush=True)
    print("B 국면 — Seer 제어권. 판다는 SILENT·passthrough(송신 0건).", flush=True)
    print("  ⇒ CAN·1005·1040 **셋 다 살아 있다**. 여기서 나온 값이 판정 대상이다.", flush=True)
    print("=" * 78, flush=True)
    rig.p.set_safety_mode(0, 0)          # SILENT — 릴레이 passthrough, 송신 불가
    for b in (0, 2):
        rig.p.set_can_speed_kbps(b, 250)
        rig.p.set_can_enable(b, True)
    time.sleep(0.4)
    rig.p.can_recv()

    m = settled_read(lambda: read_can_passive(rig.p, samples), cli, samples)
    recs.append({"phase": "B", "tag": "baseline", "vy": 0.0, **m})
    print(f"기준선: {fmt(m['can'], m)}"
          + ("  ⚠transient" if m["transient"] else ""), flush=True)
    if dry:
        print("--dry-run — B 국면 지령 생략", flush=True)
        return
    try:
        for i in range(1, bursts + 1):
            sign = 1 if i % 2 else -1        # 좌우 번갈아 — 한쪽으로 계속 가지 않게
            cmd = {"vy": sign * vy, "duration": duration_ms}
            r = cli.call("control", API_MOTION, cmd)
            time.sleep(duration_ms / 1000.0 + settle)
            m = settled_read(lambda: read_can_passive(rig.p, samples), cli, samples)
            recs.append({"phase": "B", "tag": f"burst{i}", "vy": sign * vy,
                         "ret_code": r.get("ret_code"), **m})
            print(f"[B {i}/{bursts}] vy={sign*vy:+.3f} ret={r.get('ret_code')}  "
                  f"{fmt(m['can'], m)}" + ("  ⚠transient" if m["transient"] else ""), flush=True)
    finally:
        try:
            cli.call("control", API_STOP, {})
            print(">>> B 국면 종료 — 2000(Stop Open Loop Motion) 송신", flush=True)
        except Exception as exc:
            print(f"⚠ 정지 송신 실패: {exc} — duration 만료로 자동 정지 예정", flush=True)


# ── 분석 ──────────────────────────────────────────────────────────────────
def analyze(recs, out):
    print("\n" + "=" * 78, flush=True)
    print("전달함수 분석", flush=True)
    print("=" * 78, flush=True)
    a = [r for r in recs if r["phase"] == "A" and r.get("authority_ok")
         and not r.get("transient")]
    b = [r for r in recs if r["phase"] == "B" and not r.get("transient")]
    drop_a = sum(1 for r in recs if r["phase"] == "A" and r.get("transient"))
    drop_b = sum(1 for r in recs if r["phase"] == "B" and r.get("transient"))
    if drop_a or drop_b:
        print(f"  ⚠ transient 제외: A {drop_a}점 · B {drop_b}점 "
              f"(Seer 판독 전후 CAN 이 {SETTLE_TOL_COUNTS}c 초과 이동 — 이동 중 판독)",
              flush=True)

    for n in STEER_NODES:
        print(f"\n── node{n}", flush=True)
        pa = [(r["deg_cmd"], r["can"][n]) for r in a if r["can"].get(n) is not None]
        if len(pa) >= 2:
            xs = [p[0] for p in pa]
            ys = [p[1] for p in pa]
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            den = sum((x - mx) ** 2 for x in xs)
            if den:
                sl = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
                print(f"  A: 지령각→CAN 기울기 {sl:,.1f} counts/° "
                      f"(기대 {CPD:,.0f} · 비 {sl/CPD:.6f})", flush=True)
        else:
            print("  A: 측정점 부족", flush=True)

        pb = [(r["can"][n], (r.get("s1005") or {}).get(n), (r.get("s1040") or {}).get(n))
              for r in b if r["can"].get(n) is not None]
        pb = [(c, x, y) for c, x, y in pb if x is not None]
        if len(pb) >= 2:
            cs = [p[0] for p in pb]
            span = max(cs) - min(cs)
            print(f"  B: 측정점 {len(pb)}개 · CAN 이동폭 {span:,} counts ({span/CPD:+.4f}°)",
                  flush=True)
            for label, idx in (("1005", 1), ("1040", 2)):
                ys = [p[idx] for p in pb if p[idx] is not None]
                xs = [p[0] for p in pb if p[idx] is not None]
                uniq = sorted(set(ys))
                if len(xs) < 2:
                    continue
                mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
                den = sum((x - mx) ** 2 for x in xs)
                if den == 0:
                    print(f"     {label}: CAN 미이동 — 기울기 산출 불가", flush=True)
                    continue
                sl = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
                gain = abs(sl) * CPD
                steps = [round(abs(q - p) * CPD) for p, q in zip(uniq, uniq[1:])]
                print(f"     {label}: 상이값 {len(uniq)}개 · |기울기|×57,344 = {gain:.6f}"
                      + (f" · 최소 계단 ≈ {min(steps):,}c" if steps else ""), flush=True)
                if len(uniq) == 1:
                    print(f"        ⚠ 값 불변 — 이동폭이 {label} 분해능보다 작다", flush=True)
                elif abs(gain - 1.0) < 0.02:
                    print(f"        ⇒ **`0x6064` 와 같은 스케일 — 같은 엔코더 유래. 독립 앵커 아님**",
                          flush=True)
                else:
                    print(f"        ⇒ 스케일이 다르다 — **별도 산출 경로 가능성**", flush=True)
        else:
            print("  B: 측정점 부족(조향이 안 움직였거나 Seer 판독 실패)", flush=True)
    print(f"\n  원자료: {out}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["a", "b", "ab"], default="ab")
    ap.add_argument("--range", type=float, default=5.0, help="A 국면 홈 기준 ±범위(도)")
    ap.add_argument("--step", type=float, default=2.5, help="A 국면 간격(도)")
    ap.add_argument("--vy", type=float, default=0.02, help="B 국면 횡속도(m/s)")
    ap.add_argument("--bursts", type=int, default=6, help="B 국면 지령 횟수(좌우 번갈아)")
    ap.add_argument("--duration", type=int, default=500, help="B 국면 지령 지속(ms)")
    ap.add_argument("--settle", type=float, default=2.0)
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--ip", default=SEER_IP)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if abs(args.range) > 20.0:
        ap.error("--range 는 20° 이하(접지 안전)")
    if abs(args.vy) > 0.10:
        ap.error("--vy 는 0.10 m/s 이하(3톤 차체)")

    pts, d = [], -abs(args.range)
    while d <= abs(args.range) + 1e-9:
        pts.append(round(d, 4)); d += args.step
    pts = sorted(set(pts + [0.0]))

    stamp = time.strftime("%y%m%d_%H%M%S")
    repo = os.path.abspath(os.path.join(HERE, "..", ".."))
    out = args.out or os.path.join(repo, "Log", f"steer_two_phase_{stamp}.jsonl")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    if not args.dry_run and not args.yes:
        print("⚠ 조향이 움직인다. B 국면은 **Seer 가 로봇을 주행**시킨다(vy 개루프).", flush=True)
        if input("  진행하려면 'yes': ").strip().lower() != "yes":
            print("중단"); return

    rig = Rig(out.replace(".jsonl", "_can.jsonl"))
    recs = []
    try:
        cli = seer_client(args.ip)
        own = cli.control_owner()
        print(f"판다 fw={rig.p.get_version()} · Seer 제어권 locked={own.get('locked')}", flush=True)
        if own.get("locked"):
            print("⚠ Seer 제어권이 잠겨 있다 — B 국면 지령이 거부될 수 있다.", flush=True)
        if args.phase in ("a", "ab"):
            phase_a(rig, cli, pts, args.settle, args.samples, recs, args.dry_run)
        if args.phase in ("b", "ab"):
            phase_b(rig, cli, args.vy, args.bursts, args.duration,
                    args.settle, args.samples, recs, args.dry_run)
    except KeyboardInterrupt:
        print("\n⚠ 사용자 중단", flush=True)
        try:
            cli.call("control", API_STOP, {})
        except Exception:
            pass
    finally:
        rig.release()
        with open(out, "w", encoding="utf-8") as fh:
            for r in recs:
                fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        rig.close()
        analyze(recs, out)


if __name__ == "__main__":
    main()
