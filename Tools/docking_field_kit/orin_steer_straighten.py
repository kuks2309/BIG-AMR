#!/usr/bin/env python3
"""조향 원위치(직진) 복원 — Seer 에게 맡긴다.

## 왜 이 도구가 필요한가 (2026-08-03 13:1x 실측)

2국면 실험(`orin_steer_two_phase.py`) B 국면에서 Seer 에 `vy` 개루프 지령을 주자
Seer 가 조향을 **크랩 90°** 로 돌렸다. 실험 종료 후 조향이 그 자세로 남았는데,
**can_relay 로 홈에 보내도 제어권을 반환하는 순간 Seer 가 다시 90° 로 되돌린다** —
Seer 가 자기 조향 설정값을 쥐고 있기 때문이다(node4 는 복귀했다가 원복, node3 은 복귀 중이었다).

⇒ **조향 자세의 최종 권한은 Seer 에 있다.** 되돌리려면 Seer 에게 「직진하라」고 말해야 한다.
   `vx`(전진) 지령을 받으면 Seer 는 바퀴를 스스로 0° 로 편다.

## ⚠ 안전

· **로봇이 실제로 전진한다.** `--vx` 기본 0.02 m/s · `--duration` 500 ms →
  버스트당 약 1 cm. 바퀴가 90°→0° 로 도는 동안은 거의 제자리다.
· 조향이 `--tol` 이내로 펴지면 **즉시 중단**하고 API 2000(Stop Open Loop Motion)을 보낸다.
· 어느 종료 경로(정상·예외·Ctrl-C)든 **finally 에서 2000 을 보낸다.**
· 판다는 **SAFETY_SILENT · passthrough** — 송신 0건. 우리는 청취만 한다.
  (제어권을 잡으면 emulate 로 Seer 판독이 얼어붙고, 애초에 Seer 가 조향을 못 편다.)
· `--vx` 상한 0.05 m/s, `--max-iter` 상한 40 으로 코드에서 제한한다.

사용:
  python3 orin_steer_straighten.py --dry-run     # 현재 자세만 판독, 지령 0건
  python3 orin_steer_straighten.py --yes
"""
from __future__ import annotations

import argparse
import math
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from panda import Panda  # noqa: E402
from orin_steer_sweep_1005 import SEER_IP, seer_client  # noqa: E402
from orin_home_experiment import CPD, HOME_0DEG, OBJ_POS, STEER_NODES  # noqa: E402

API_MOTION = 2010
API_STOP = 2000
MOTOR_BUS = 2
RD_RESP = {0x43, 0x47, 0x4B, 0x4F}


def read_steer(p, dwell: float = 1.0) -> dict:
    """송신 없이 bus2 를 청취해 조향 `0x6064` 중앙값을 낸다."""
    acc = {n: [] for n in STEER_NODES}
    end = time.time() + dwell
    while time.time() < end:
        for addr, _, dat, bus in p.can_recv():
            if bus != MOTOR_BUS or not dat:
                continue
            d = bytes(dat)
            if not (0x583 <= addr <= 0x584) or len(d) < 8 or d[0] not in RD_RESP:
                continue
            if (d[1] | (d[2] << 8)) != OBJ_POS:
                continue
            v = int.from_bytes(d[4:8], "little")
            acc[addr - 0x580].append(v - (1 << 32) if v & 0x80000000 else v)
        time.sleep(0.005)
    return {n: (int(statistics.median(v)) if v else None) for n, v in acc.items()}


def degs(st: dict) -> dict:
    return {n: (st[n] - HOME_0DEG[n]) / CPD for n in STEER_NODES if st.get(n) is not None}


def show(st: dict, s1005: dict | None = None) -> str:
    d = degs(st)
    out = " ".join(f"n{n}={v:+.3f}°" for n, v in d.items())
    if s1005 is not None:
        ang = [round(x * 180 / math.pi, 3) for x in (s1005.get("steer_angles") or [])]
        out += f"  1005={ang}°  is_stop={s1005.get('is_stop')}"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vx", type=float, default=0.02, help="전진 속도(m/s)")
    ap.add_argument("--duration", type=int, default=500, help="버스트 지속(ms)")
    ap.add_argument("--max-iter", type=int, default=20)
    ap.add_argument("--tol", type=float, default=0.5, help="직진 판정 허용각(도)")
    ap.add_argument("--ip", default=SEER_IP)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    if not (0 < args.vx <= 0.05):
        ap.error("--vx 는 0 초과 0.05 m/s 이하(3톤 차체)")
    if not (1 <= args.max_iter <= 40):
        ap.error("--max-iter 는 1~40")

    p = Panda()
    p.set_safety_mode(0, 0)                 # SILENT · passthrough — 송신 0건
    for b in (0, MOTOR_BUS):
        p.set_can_speed_kbps(b, 250)
        p.set_can_enable(b, True)
    time.sleep(0.3)
    p.can_recv()
    cli = seer_client(args.ip)

    st = read_steer(p, 1.5)
    s = cli.call("status", 1005)
    print(f"현재: {show(st, s)}", flush=True)

    d = degs(st)
    if d and max(abs(v) for v in d.values()) < args.tol:
        print("이미 직진 자세다 — 할 일 없음.", flush=True)
        p.close()
        return
    if args.dry_run:
        print("--dry-run — 지령을 보내지 않고 종료한다.", flush=True)
        p.close()
        return
    if not args.yes:
        print(f"⚠ Seer 에 vx={args.vx} m/s 를 {args.duration} ms 씩 보낸다. "
              f"**로봇이 전진한다**(버스트당 약 {args.vx*args.duration/1000*100:.1f} cm).", flush=True)
        if input("  진행하려면 'yes': ").strip().lower() != "yes":
            print("중단"); p.close(); return

    try:
        for i in range(1, args.max_iter + 1):
            r = cli.call("control", API_MOTION, {"vx": args.vx, "duration": args.duration})
            time.sleep(args.duration / 1000.0 + 1.0)
            st = read_steer(p, 0.8)
            s = cli.call("status", 1005)
            print(f"  [{i}/{args.max_iter}] ret={r.get('ret_code')}  {show(st, s)}", flush=True)
            d = degs(st)
            if d and max(abs(v) for v in d.values()) < args.tol:
                print("  ⇒ 조향이 직진 자세에 도달했다.", flush=True)
                break
        else:
            print("  ⚠ 상한 반복까지 직진에 도달하지 못했다.", flush=True)
    except KeyboardInterrupt:
        print("\n⚠ 사용자 중단", flush=True)
    finally:
        try:
            cli.call("control", API_STOP, {})
            print(">>> API 2000 (Stop Open Loop Motion) 송신", flush=True)
        except Exception as exc:
            print(f"⚠ 정지 송신 실패: {exc} — duration 만료로 자동 정지 예정", flush=True)
        time.sleep(1.0)
        fin = read_steer(p, 1.5)
        s = cli.call("status", 1005)
        print(f"최종: {show(fin, s)}", flush=True)
        p.close()


if __name__ == "__main__":
    main()
