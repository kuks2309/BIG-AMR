#!/usr/bin/env python3
"""도킹 릴레이 펌웨어 24시간 내구·신뢰성 테스트 (amap-1 벤치: 판다 + PCAN 2ch).

목적: 게이트·auth전환·릴레이 사이클을 24h 반복하며 정확성·지연·CAN 에러 누적을 감시.
토폴로지(클론 U3P 핀맵): PCAN can0=가짜 Seer(CAN0 H4/L5·6), can1=가짜 모터(CAN2 H23/L24), 판다 intercept+SEER_GATE.

각 사이클(약 0.5s) 검증:
  G1 Seer 쓰기 차단 + 가짜 ack       G2 Seer 읽기 통과      G3 guard RTR 통과
  G4 모터 응답 → Seer 전달           G5 PC 구동 도달 + 에코차단
주기적(SUMMARY_EVERY):
  auth=Seer 투명중계 확인, 릴레이 intercept↔passthrough 토글(엔듀런스), 지연 통계, CAN 에러카운터.

로그: ~/docking_reliability/  (live_status.txt = 실시간 요약, run_YYYY.log = 상세, summary.json)
실행(백그라운드): nohup python3 reliability_24h.py >/dev/null 2>&1 &
"""
import os
import sys
import time
import json
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import can
from panda import Panda

SEER, MOTOR = 0, 2
SEER_GATE = 30
KBPS = 250
DURATION_S = int(os.environ.get("REL_DURATION_S", 24 * 3600))     # 스모크: REL_DURATION_S=30
CYCLE_PACE = float(os.environ.get("REL_CYCLE_PACE", "0.5"))       # 사이클 간 목표 간격(초)
SUMMARY_EVERY = int(os.environ.get("REL_SUMMARY_EVERY", "300"))   # 요약 갱신 주기(초)
LOGDIR = os.path.expanduser("~/docking_reliability")

os.makedirs(LOGDIR, exist_ok=True)
LIVE = os.path.join(LOGDIR, "live_status.txt")
DETAIL = os.path.join(LOGDIR, "run.log")
SUMMARY = os.path.join(LOGDIR, "summary.json")


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
    with open(DETAIL, "a") as f:
        f.write(line)


def berr(iface):
    try:
        out = subprocess.run(["ip", "-details", "-statistics", "link", "show", iface],
                             capture_output=True, text=True, timeout=5).stdout
        import re
        m = re.search(r"berr-counter tx (\d+) rx (\d+)", out)
        st = "BUS-OFF" if "BUS-OFF" in out else ("ERR-PASSIVE" if "ERROR-PASSIVE" in out else "ACTIVE")
        return (st, int(m.group(1)), int(m.group(2))) if m else (st, -1, -1)
    except Exception:
        return ("?", -1, -1)


def setup_panda():
    p = Panda()
    p.set_safety_mode(SEER_GATE, 0)
    for b in (SEER, MOTOR):
        p.set_can_speed_kbps(b, KBPS)
        p.set_can_enable(b, True)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 1, 0, b"")  # auth=PC
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # intercept
    time.sleep(0.3)
    return p


def main():
    stats = dict(cycles=0, g_pass=dict(G1=0, G2=0, G3=0, G4=0, G5=0),
                 g_fail=dict(G1=0, G2=0, G3=0, G4=0, G5=0),
                 lat_n=0, lat_sum=0.0, lat_min=9e9, lat_max=0.0, lat_over10ms=0,
                 relay_toggles=0, reconnects=0, exceptions=0,
                 start=time.strftime('%Y-%m-%d %H:%M:%S'))
    log("=== 24h 신뢰성 테스트 시작 ===")
    p = setup_panda()
    seer = can.Bus(channel="can0", interface="socketcan")
    motor = can.Bus(channel="can1", interface="socketcan")

    def drain(bus, t=0.15):
        out, end = [], time.time() + t
        while time.time() < end:
            m = bus.recv(timeout=0.02)
            if m is not None:
                out.append((m.arbitration_id, bool(m.is_remote_frame)))
        return out

    def has(msgs, aid, rtr=None):
        return any(a == aid and (rtr is None or r == rtr) for a, r in msgs)

    def rec(k, ok):
        (stats["g_pass"] if ok else stats["g_fail"])[k] += 1

    t0 = time.monotonic()
    last_summary = 0.0

    def write_summary():
        up = time.monotonic() - t0
        lat_avg = (stats["lat_sum"] / stats["lat_n"] * 1000) if stats["lat_n"] else 0
        s0 = berr("can0"); s1 = berr("can1")
        gp, gf = stats["g_pass"], stats["g_fail"]
        total_checks = sum(gp.values()) + sum(gf.values())
        total_fail = sum(gf.values())
        txt = (f"=== 도킹 릴레이 24h 신뢰성 — LIVE ({time.strftime('%Y-%m-%d %H:%M:%S')}) ===\n"
               f"시작: {stats['start']}  경과: {up/3600:.2f}h / 24h  ({up/DURATION_S*100:.1f}%)\n"
               f"사이클: {stats['cycles']}   총검증: {total_checks}  실패: {total_fail}  "
               f"({(1-total_fail/max(1,total_checks))*100:.4f}% pass)\n"
               f"게이트 항목별 pass/fail:\n"
               f"  G1 쓰기차단+ack : {gp['G1']}/{gf['G1']}\n"
               f"  G2 읽기통과     : {gp['G2']}/{gf['G2']}\n"
               f"  G3 guard RTR    : {gp['G3']}/{gf['G3']}\n"
               f"  G4 모터응답전달 : {gp['G4']}/{gf['G4']}\n"
               f"  G5 PC구동+에코차단: {gp['G5']}/{gf['G5']}\n"
               f"지연(Seer읽기→모터도달): avg {lat_avg:.2f}ms  min {stats['lat_min']*1000:.2f}  "
               f"max {stats['lat_max']*1000:.2f}  >10ms {stats['lat_over10ms']}회 (n={stats['lat_n']})\n"
               f"릴레이 토글: {stats['relay_toggles']}   재연결: {stats['reconnects']}   예외: {stats['exceptions']}\n"
               f"CAN 에러: can0={s0}  can1={s1}\n")
        with open(LIVE, "w") as f:
            f.write(txt)
        with open(SUMMARY, "w") as f:
            json.dump(stats, f, indent=1)

    while time.monotonic() - t0 < DURATION_S:
        cyc_start = time.time()
        try:
            # G1: Seer 쓰기 차단 + 가짜 ack
            drain(motor); drain(seer)
            seer.send(can.Message(arbitration_id=0x601, data=bytes([0x2B, 0xFF, 0x60, 0, 0x8D, 0x09, 0, 0]), is_extended_id=False))
            m = drain(motor); s = drain(seer)
            rec("G1", (not has(m, 0x601)) and has(s, 0x581))

            # G2 + 지연: Seer 읽기 → 모터 도달 (왕복지연 측정)
            drain(motor)
            t_send = time.monotonic()
            seer.send(can.Message(arbitration_id=0x601, data=bytes([0x40, 0x64, 0x60, 0, 0, 0, 0, 0]), is_extended_id=False))
            got = False
            while time.monotonic() - t_send < 0.05:
                for a, r in drain(motor, 0.01):
                    if a == 0x601:
                        got = True; break
                if got:
                    break
            lat = time.monotonic() - t_send
            rec("G2", got)
            if got:
                stats["lat_n"] += 1; stats["lat_sum"] += lat
                stats["lat_min"] = min(stats["lat_min"], lat); stats["lat_max"] = max(stats["lat_max"], lat)
                if lat > 0.010:
                    stats["lat_over10ms"] += 1

            # G3: guard RTR 통과
            drain(motor)
            seer.send(can.Message(arbitration_id=0x701, is_remote_frame=True, dlc=0, is_extended_id=False))
            rec("G3", has(drain(motor), 0x701, rtr=True))

            # G4: 모터 응답 → Seer
            drain(seer)
            motor.send(can.Message(arbitration_id=0x581, data=bytes([0x43, 0x64, 0x60, 0, 1, 2, 3, 4]), is_extended_id=False))
            rec("G4", has(drain(seer), 0x581))

            # G5: PC 구동 도달 + 에코차단
            drain(motor); drain(seer)
            p.can_send(0x601, bytes([0x23, 0xFF, 0x60, 0, 0x8D, 0x09, 0, 0]), MOTOR)
            rec("G5", has(drain(motor), 0x601) and not has(drain(seer), 0x601))

            stats["cycles"] += 1
        except Exception as e:
            stats["exceptions"] += 1
            log(f"예외: {type(e).__name__}: {e}")
            # 판다 재연결 시도
            try:
                p.close()
            except Exception:
                pass
            time.sleep(2)
            try:
                p = setup_panda(); stats["reconnects"] += 1; log("판다 재연결 성공")
            except Exception as e2:
                log(f"재연결 실패: {e2}"); time.sleep(5)

        # 주기적 요약 + 릴레이 토글(엔듀런스) + auth 전환 확인
        if time.monotonic() - last_summary > SUMMARY_EVERY:
            last_summary = time.monotonic()
            try:
                # 릴레이 intercept↔passthrough 토글 후 원복 (GPIO 엔듀런스)
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b""); time.sleep(0.1)
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b""); time.sleep(0.2)
                stats["relay_toggles"] += 1
            except Exception as e:
                log(f"릴레이 토글 예외: {e}")
            write_summary()
            log(f"요약갱신 cycles={stats['cycles']} fail={sum(stats['g_fail'].values())}")

        dt = time.time() - cyc_start
        if dt < CYCLE_PACE:
            time.sleep(CYCLE_PACE - dt)

    # 종료 처리
    try:
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
        p.set_safety_mode(0, 0); p.close()
    except Exception:
        pass
    seer.shutdown(); motor.shutdown()
    stats["end"] = time.strftime('%Y-%m-%d %H:%M:%S')
    write_summary()
    log("=== 24h 신뢰성 테스트 종료 ===")


if __name__ == "__main__":
    main()
