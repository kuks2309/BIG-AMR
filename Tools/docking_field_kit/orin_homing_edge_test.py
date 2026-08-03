#!/usr/bin/env python3
"""호밍 에지 검증 — 「이미 홈이면 무동작 즉시 완료」 가설을 실기로 가른다.

설계 근거: `docs/homing/2026-08-03-can-relay-homing-assets.md` §15-4 · §15-6, `docs/debt/registry.md` debt-035

## 무엇을 가르려는가

2026-08-03 09:58 호밍이 **ERR_TIMEOUT(120 s)** 으로 끝났고 축이 안 움직였다.
판독(§15)에서 **막을 요인이 하나도 없음**이 확인됐다 —
`0x6098`=1(호밍 활성) · `0x6060`/`0x6061`=1(PP(Profile Position)) · `0x603F`=0(오류 없음) ·
`0x6000:01`=0x01(리밋 미접촉) · `0x60FB:04`=0(RstStart 미고착).
그런데 **`0x6041` bit15(Home attend)=1** 이었고 **축이 홈에서 0.0006° 이내**였다.

Handbook §4.6:
> *"When the motor is **already in the resetting position**, the resetting is triggered again,
>   and the driver **directly outputs the resetting end signal**."*

⇒ **가설**: 이미 홈이라 무동작 즉시 완료 → bit15 가 **1→0 으로 떨어지지 않음**
  → 펌웨어 WAIT 의 **하강 에지 검출기**(`safety_seer_gate.h:391-402`)가 영구 대기 → 타임아웃.

**가르는 법**: 조향을 홈에서 **충분히 떼어놓고** 호밍을 건다.
- 호밍이 **성공**(bit15 하강 에지 관측 + FSM DONE) → **가설 확정**. 해법은 「이미 홈」 종료 조건 추가.
- 또 **타임아웃**(에지 없음) → **가설도 반증**. 원인 재탐색.

## 관측 정밀도 — 이것이 이 도구의 존재 이유

09:58 회차는 `0x6041` 을 **125 s 에 788 샘플(≈6 Hz)** 만 기록해 **짧은 에지를 놓칠 수 있었다.**
본 도구는 호밍 구간 내내 `0x6041` 을 **직접 SDO(Service Data Object) 읽기로 고속 폴링**하고
**모든 bit15 전이를 시각과 함께 기록**한다. 펌웨어 FSM 은 `0xeb` 로 병행 관측한다.

## ⚠ 안전

· **호밍은 조향축을 −리밋까지 보낸 뒤 약 137° 복귀시킨다. 접지 상태면 차체가 움직인다.** 주변 확보 필수.
· 사전 이동(`--offset`, 기본 10°)은 홈 기준이며 ±90° 이중 클램프. 상한 20°.
· 어느 종료 경로(정상·예외·Ctrl-C)든 **호밍 취소(`0xea` wValue=0) → 홈 복귀 → 제어권 반환**.
· ⚠ GOZERO_W 타임아웃은 취소 프레임을 내지 않는다(`safety_seer_gate.h:466-467`) —
  그 단계에서 중단하면 축이 목표까지 계속 갈 수 있다.
· heartbeat 는 `Rig` 전용 스레드(GUI `gui.py:819` 패턴). 매 국면 제어권 생존 확인.
· 구동륜에는 아무것도 보내지 않는다.

사용:
  python3 orin_homing_edge_test.py --dry-run        # 사전 이동·호밍 없이 현재 상태만
  python3 orin_homing_edge_test.py --offset 10 --yes
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from orin_home_experiment import (  # noqa: E402
    CPD, HOME_0DEG, OBJ_CTRL, OBJ_POS, OBJ_STATUS, OBJ_TARGET, STATE, STEER_NODES,
    TERMINAL, CW_SETPOINT, Rig,
)
from orin_steer_sweep_1005 import steer_counts  # noqa: E402
from panda import Panda  # noqa: E402


def snap(rig: Rig):
    """조향 2축의 위치·statusword·bit15 를 한 번에."""
    import statistics
    out = {}
    for n in STEER_NODES:
        # ★ 단발 판독 금지 (2026-08-03) — 제어권 보유 중에도 Seer 폴 응답이 섞여
        #   간헐적으로 틀린 값이 나온다(45 s 수동청취 4,589 샘플과 불일치 실측).
        ps = [v for v in (rig.sdo_read(n, OBJ_POS) for _ in range(5)) if v is not None]
        ss = [v for v in (rig.sdo_read(n, OBJ_STATUS) for _ in range(5)) if v is not None]
        pos = int(statistics.median(ps)) if ps else None
        sw = int(statistics.mode(ss)) if ss else None
        out[n] = {"pos": pos, "sw": sw,
                  "bit15": None if sw is None else (sw >> 15) & 1,
                  "deg": None if pos is None else (pos - HOME_0DEG[n]) / CPD}
    return out


def fmt(s: dict) -> str:
    return " | ".join(
        f"n{n} {v['deg']:+.3f}° sw={v['sw']:#06x} bit15={v['bit15']}"
        if v["sw"] is not None and v["deg"] is not None else f"n{n} ?"
        for n, v in s.items())


def move_to(rig: Rig, deg: float, settle: float):
    for n in STEER_NODES:
        rig.sdo_write(n, OBJ_TARGET, 0, steer_counts(n, deg), 4)
        rig.sdo_write(n, OBJ_CTRL, 0, CW_SETPOINT, 2)
    time.sleep(settle)
    rig.drain()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offset", type=float, default=10.0, help="호밍 전 홈에서 떼어놓을 각도(도)")
    ap.add_argument("--speed", type=int, default=2500, help="호밍 속도(100~3000)")
    ap.add_argument("--timeout", type=float, default=180.0, help="호밍 관측 상한(초)")
    ap.add_argument("--settle", type=float, default=4.0, help="사전 이동 정착 대기(초)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if abs(args.offset) > 20.0:
        ap.error("--offset 은 20° 이하(접지 안전)")
    if args.speed != 0 and not (100 <= args.speed <= 3000):
        ap.error("--speed 는 0 또는 100~3000 (펌웨어가 거부한다)")

    stamp = time.strftime("%y%m%d_%H%M%S")
    repo = os.path.abspath(os.path.join(HERE, "..", ".."))
    out = args.out or os.path.join(repo, "Log", f"homing_edge_{stamp}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    if not args.dry_run and not args.yes:
        print(f"⚠ 조향을 {args.offset:+.1f}° 로 옮긴 뒤 **호밍**을 건다.", flush=True)
        print("  호밍은 −리밋까지 갔다가 약 137° 복귀한다. 접지면 차체가 움직인다.", flush=True)
        if input("  진행하려면 'yes': ").strip().lower() != "yes":
            print("중단"); return

    rig = Rig(out.replace(".json", "_can.jsonl"))
    rec = {"stamp": stamp, "offset_deg": args.offset, "speed": args.speed,
           "sw_trace": [], "fsm_trace": []}
    try:
        rig.take()
        rec["before"] = snap(rig)
        print(f"현재:  {fmt(rec['before'])}", flush=True)

        if args.dry_run:
            print("--dry-run — 이동·호밍 없이 종료", flush=True)
            return

        print(f"\n>>> 1단계: 조향을 홈에서 {args.offset:+.1f}° 로 이동", flush=True)
        move_to(rig, args.offset, args.settle)
        rec["preposition"] = snap(rig)
        print(f"이동 후: {fmt(rec['preposition'])}", flush=True)

        far = [abs(v["deg"]) for v in rec["preposition"].values() if v["deg"] is not None]
        if not far or max(far) < abs(args.offset) * 0.5:
            print("  ⚠ 조향이 목표만큼 이동하지 않았다 — 호밍을 걸지 않고 중단한다.", flush=True)
            return

        print(f"\n>>> 2단계: 호밍 개시 (0xea, speed={args.speed}) — "
              f"0x6041 고속 폴링으로 bit15 전이를 추적한다", flush=True)
        with rig._io:
            ok = rig.p._handle.controlRead(Panda.REQUEST_IN, 0xea, 1, args.speed, 1)
        rec["accepted"] = (ok[0] == 1)
        if ok[0] != 1:
            print("  ⚠ 0xea 거부 — 전제조건 확인(권한/모드/terminal/속도). 중단.", flush=True)
            return
        print("  0xea 수락", flush=True)

        t0 = time.time()
        last_bit = {n: rec["preposition"][n]["bit15"] for n in STEER_NODES}
        last_state = None
        n_poll = 0
        deadline = t0 + args.timeout
        while time.time() < deadline:
            el = round(time.time() - t0, 4)
            for n in STEER_NODES:
                sw = rig.sdo_read(n, OBJ_STATUS, timeout=0.15)
                if sw is None:
                    continue
                n_poll += 1
                b = (sw >> 15) & 1
                if b != last_bit[n]:
                    ev = {"t": el, "node": n, "sw": sw, "bit15": b,
                          "edge": f"{last_bit[n]}→{b}"}
                    rec["sw_trace"].append(ev)
                    print(f"    ★ [{el:7.3f}s] node{n} bit15 {last_bit[n]}→{b} "
                          f"(sw={sw:#06x})", flush=True)
                    last_bit[n] = b
            st = rig.homing_state()
            if st["state"] != last_state:
                rec["fsm_trace"].append({"t": el, **st})
                print(f"    [{el:7.3f}s] FSM state={st['state']} "
                      f"{STATE.get(st['state'], '?'):<14s} 원점={st['done_mask']:#04x} "
                      f"도달={st['reached_mask']:#04x} DI3={st['di3']:#04x} DI4={st['di4']:#04x}",
                      flush=True)
                last_state = st["state"]
            if st["state"] in TERMINAL and st["state"] != 0:
                rec["final_state"] = st["state"]
                rec["elapsed"] = round(time.time() - t0, 2)
                print(f"\n>>> 종료 상태 {st['state']} ({STATE.get(st['state'])}) "
                      f"— {rec['elapsed']}s", flush=True)
                break
        else:
            rec["final_state"] = -1
            rec["elapsed"] = round(time.time() - t0, 2)
            print("\n>>> 스크립트 타임아웃 — 취소 전송", flush=True)
            rig.cancel_homing()
        rec["poll_count"] = n_poll
        rec["poll_hz"] = round(n_poll / max(rec["elapsed"], 0.001) / len(STEER_NODES), 1)
        time.sleep(2.0)
        rig.drain()
        rec["after"] = snap(rig)
        print(f"호밍 후: {fmt(rec['after'])}", flush=True)

    except KeyboardInterrupt:
        print("\n⚠ 사용자 중단 — 호밍 취소", flush=True)
        rig.cancel_homing()
    finally:
        try:
            if rig.controlling and not args.dry_run:
                print("\n>>> 홈 복귀", flush=True)
                move_to(rig, 0.0, args.settle)
                rec["returned"] = snap(rig)
                print(f"복귀 후: {fmt(rec['returned'])}", flush=True)
        except Exception as exc:
            print(f"⚠ 복귀 실패: {exc}", flush=True)
        rig.release()
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2)
        rig.close()
        print(f"\n산출: {out}", flush=True)

        # ── 판정 ──
        print("\n" + "=" * 78, flush=True)
        print("판정 — 「이미 홈이면 무동작 즉시 완료」 가설", flush=True)
        print("=" * 78, flush=True)
        falls = [e for e in rec["sw_trace"] if e["edge"] == "1→0"]
        rises = [e for e in rec["sw_trace"] if e["edge"] == "0→1"]
        print(f"  0x6041 폴링: {rec.get('poll_count', 0)}회 "
              f"(노드당 ≈{rec.get('poll_hz', 0)} Hz) — 09:58 회차는 ≈6 Hz 였다", flush=True)
        print(f"  bit15 하강(1→0): {len(falls)}건 · 상승(0→1): {len(rises)}건", flush=True)
        fs = rec.get("final_state")
        # ⚠ 판정은 **offset 조건을 함께 본다** (2026-08-03 정정).
        #   초판은 `final_state` 만 보고 「홈에서 떼어놓으니 동작했다」를 무조건 출력해,
        #   `--offset 0`(홈 그대로) 회차에서도 같은 문구를 찍었다 — 정반대 결론을 낼 관측인데도.
        #   그 오출력이 §15-4·§16 오귀속을 굳히는 데 일조했다(§17-5).
        at_home = abs(args.offset) < 0.5
        if fs == 5 and at_home:
            print("\n  ★ **홈 상태에서 호밍 성공(DONE)** — 축이 홈에 있어도 정상 동작했다.", flush=True)
            print("    ⇒ 「축이 이미 홈이라 무동작 즉시 완료 → 하강 에지 미발생」 가설은 **반증**된다.",
                  flush=True)
            if falls:
                print(f"    (하강 에지가 {len(falls)}건 실제로 발생했고 축이 리밋까지 주행했다)",
                      flush=True)
            print("    ⇒ 호밍 실패의 원인을 다른 데서 찾아야 한다 — 유력 후보는"
                  " `0x6064`=0 래치(debt-036).", flush=True)
        elif fs == 5:
            print(f"\n  ★ **호밍 성공(DONE)** — 홈에서 {args.offset:+.1f}° 떼어놓은 상태였다.",
                  flush=True)
            print("    ⚠ 이것만으로는 「오프셋이 원인」이라 말할 수 없다 —"
                  " `--offset 0` 대조군을 함께 돌려야 갈린다(§17-3 오귀속 사례).", flush=True)
        elif fs in (6, -1):
            if falls:
                print("\n  ⚠ **하강 에지는 있었는데 타임아웃**했다 — 가설이 설명하지 못한다."
                      " 원인 재탐색 필요.", flush=True)
            else:
                print("\n  ⚠ **홈에서 떼어놨는데도 하강 에지가 없고 타임아웃**했다.", flush=True)
                print("    ⇒ **가설 반증**. 「이미 홈」이 원인이 아니다 — 드라이브가 RstStart 에"
                      " 아예 반응하지 않는다는 뜻이므로 원인 재탐색 필요.", flush=True)
        elif fs is not None:
            print(f"\n  종료 상태 {fs} ({STATE.get(fs)}) — 위 두 갈래 어느 쪽도 아니다."
                  " 원자료를 직접 볼 것.", flush=True)
        print("\n  ⚠ 1회 관측이다. 확정 전 최소 1회 재현을 권한다.", flush=True)


if __name__ == "__main__":
    main()
