#!/usr/bin/env python3
"""amap-2 per-bus CAN 에러 워치독 — firmware can_health(0xc3) 연속 감시.

비침습 리슨(SILENT). 1초마다 버스별 에러상태를 점검하고, 이상(bus_off/error_passive/
error_warning 또는 REC/TEC 증가) 발생 시 즉시 타임스탬프 로깅 → 밤샘 CAN 단절오류 같은
재발을 판다측에서 바로 포착(원래 목표: 판다도 Seer처럼 잡기). INTERVAL 마다 정상 요약도 기록.

로그: ~/docking_reliability/amap2_canhealth_watchdog.log
환경변수: WD_INTERVAL(정상 요약 주기 초, 기본 60)
실행(백그라운드): setsid nohup python3 amap2_canhealth_watchdog.py >/dev/null 2>&1 &
"""
import sys, os, time
KIT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KIT)
from panda import Panda

INTERVAL = int(os.environ.get("WD_INTERVAL", "60"))
LOGDIR = os.path.expanduser("~/docking_reliability")
LOG = os.path.join(LOGDIR, "amap2_canhealth_watchdog.log")
LEC = {0: "no-error", 1: "stuff", 2: "form", 3: "ack", 4: "bit-recessive",
       5: "bit-dominant", 6: "crc", 7: "no-change"}


def log(m):
    os.makedirs(LOGDIR, exist_ok=True)
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + m
    with open(LOG, "a") as f:
        f.write(line + "\n")
    print(line, flush=True)


def is_err(h, prev):
    return (h["bus_off"] or h["error_passive"] or h["error_warning"] or
            h["receive_error_cnt"] > prev["receive_error_cnt"] or
            h["transmit_error_cnt"] > prev["transmit_error_cnt"])


def main():
    p = Panda()
    p.set_safety_mode(0, 0)                 # SILENT 리슨(비침습)
    for b in (0, 2):
        p.set_can_speed_kbps(b, 250); p.set_can_enable(b, True)
    time.sleep(0.3); p.can_recv()
    log("[watchdog] 시작 (can_health per-bus, 이상 즉시 로깅, 요약 %ds)" % INTERVAL)

    prev = {b: p.can_health(b) for b in (0, 2)}
    frames = seer = motor = 0
    err_events = 0
    last_check = last_sum = time.time()
    while True:
        for (addr, _, dat, bus) in p.can_recv():
            frames += 1
            if 0x581 <= addr <= 0x584: motor += 1
            elif 0x601 <= addr <= 0x604: seer += 1
        now = time.time()
        if now - last_check >= 1.0:          # 1초마다 에러 점검
            for bus in (0, 2):
                h = p.can_health(bus)
                if is_err(h, prev[bus]):
                    err_events += 1
                    log("⚠ bus%d 에러: bus_off=%d ep=%d ew=%d lec=%s REC=%d(prev %d) TEC=%d(prev %d) esr=0x%08x" % (
                        bus, h["bus_off"], h["error_passive"], h["error_warning"],
                        LEC.get(h["last_error_code"], "?"),
                        h["receive_error_cnt"], prev[bus]["receive_error_cnt"],
                        h["transmit_error_cnt"], prev[bus]["transmit_error_cnt"], h["esr_reg"]))
                prev[bus] = h
            last_check = now
        if now - last_sum >= INTERVAL:
            dt = now - last_sum
            h0, h2 = p.can_health(0), p.can_health(2)
            log("[ok] %.0ffps Seer폴링=%d 모터응답=%d 누적이상=%d | bus0 REC=%d TEC=%d ep=%d | bus2 REC=%d TEC=%d ep=%d" % (
                frames / dt, seer, motor, err_events,
                h0["receive_error_cnt"], h0["transmit_error_cnt"], h0["error_passive"],
                h2["receive_error_cnt"], h2["transmit_error_cnt"], h2["error_passive"]))
            frames = seer = motor = 0
            last_sum = now
        time.sleep(0.03)


if __name__ == "__main__":
    main()
