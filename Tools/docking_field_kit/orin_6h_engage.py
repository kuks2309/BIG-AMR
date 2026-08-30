#!/usr/bin/env python3
"""FW 전환 커버 — engage 위주 6시간 내구 테스트.

각 사이클: engage(0xe8=1) → intercept ENGAGE_DWELL 유지(Seer 알람·per-bus 에러 주기 감시) →
disengage(0xe8=0) → PASS_DWELL. 반복.
핵심 지표: engage/intercept 유지 중 52111/52106 = 0 (커버 신뢰). disengage 52111은 기록만(물리모션 없음).
로그: ~/docking_reliability/cover_6h.log
실행: setsid nohup python3 orin_6h_engage.py &   (기본 6h, dwell 180s)
"""
import sys
import os
import time

sys.path.insert(0, "/home/nvidia/Project/CAN-Relay/docking_field_kit")
sys.path.insert(0, "/home/nvidia/T-Robot_seer_gui")
from panda import Panda
from seer_core.client import RobokitClient

DURATION = int(os.environ.get("REL_DURATION_S", 6 * 3600))
ENGAGE_DWELL = int(os.environ.get("ENGAGE_DWELL", 180))
PASS_DWELL = int(os.environ.get("PASS_DWELL", 15))
SAMPLE = 30
LASER = ("52102", "52103")
LOGDIR = os.path.expanduser("~/docking_reliability")
LOG = os.path.join(LOGDIR, "cover_6h.log")


def log(m):
    os.makedirs(LOGDIR, exist_ok=True)
    line = time.strftime("%m-%d %H:%M:%S ") + m
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def seer_can(c):
    al = c.call("status", 1050)
    e = [k for x in (al.get("errors") or []) for k in x
         if k not in ("desc", "times", "describe", "method", "reason") and k not in LASER]
    w = [k for x in (al.get("warnings") or []) for k in x
         if k not in ("desc", "times", "describe", "method", "reason")]
    return e, ("54301" in w)


def canh(p):
    out = []
    for b in (0, 2):
        h = p.can_health(b)
        out.append("b%d REC=%d TEC=%d ep=%d" % (b, h["receive_error_cnt"], h["transmit_error_cnt"], h["error_passive"]))
    return " ".join(out)


def drain(p, dt):
    resp = 0
    te = time.time() + dt
    while time.time() < te:
        for a, _, d, bs in p.can_recv():
            if 0x581 <= a <= 0x584 and bs == 2:
                resp += 1
        time.sleep(0.002)
    return resp


def main():
    p = Panda()
    p.set_safety_mode(30, 0)
    for b in (0, 2):
        p.set_can_speed_kbps(b, 250)
        p.set_can_enable(b, True)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")  # auth=Seer
    time.sleep(2.0)
    p.can_recv()
    c = RobokitClient("192.168.44.82", timeout=4.0)
    t0 = time.time()
    cyc = 0
    eng_fail = 0
    dis_events = 0
    log("=== 6h engage 내구 시작 (dwell=%ds, pass=%ds, dur=%ds) ===" % (ENGAGE_DWELL, PASS_DWELL, DURATION))
    try:
        while time.time() - t0 < DURATION:
            cyc += 1
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # engage
            ts = time.time()
            cyc_fail = False
            while (time.time() - ts < ENGAGE_DWELL) and (time.time() - t0 < DURATION):
                r = drain(p, SAMPLE)
                try:
                    e, cal = seer_can(c)
                except Exception as ex:
                    e, cal = ["<q>"], False
                bad = [x for x in e if x in ("52111", "52106")]
                if bad:
                    cyc_fail = True
                    log("  !! ENGAGE-COVER FAIL cyc%d: Seer CAN오류=%s (intercept 유지 중!)" % (cyc, bad))
                if (cyc % 5 == 1) or bad:
                    log("  cyc%d engage 유지: resp=%d Seer오류=%s calib=%s | %s" % (
                        cyc, r, e or "없음", "Y" if cal else "-", canh(p)))
            if cyc_fail:
                eng_fail += 1
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")  # disengage
            r2 = drain(p, PASS_DWELL)
            try:
                e2, _ = seer_can(c)
            except Exception:
                e2 = ["<q>"]
            dis = [x for x in e2 if x in ("52111", "52106")]
            if dis:
                dis_events += 1
            log("cyc%d 완료: disengage Seer오류=%s | 누적 engage_fail=%d dis=%d | %.2fh/%dh" % (
                cyc, dis or "없음", eng_fail, dis_events, (time.time() - t0) / 3600.0, DURATION // 3600))
    finally:
        try:
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
            p.set_safety_mode(0, 0)
            p.close()
        except Exception:
            pass
        try:
            c.close()
        except Exception:
            pass
        log("=== 종료: cyc=%d engage_fail=%d dis_events=%d 경과=%.2fh ===" % (
            cyc, eng_fail, dis_events, (time.time() - t0) / 3600.0))


if __name__ == "__main__":
    main()
