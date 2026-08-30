#!/usr/bin/env python3
"""Seer CAN/모터 관련 알람 실시간 모니터 — SEER API 1050(robot_status_alarm) 폴링.

근거:
  - 클라이언트: T-Robot_seer_gui/seer_core/client.py (16B 헤더 0x5A + JSON, 응답=요청+10000)
  - 알람코드: T-Robot_seer_gui/references/seer/robokit-api/appendix/002-alarm-code.md
             (출처 SEER wiki https://seer-group.feishu.cn/wiki/ , 2026-07-10 추출)
읽기 전용 — 제어권(control owner) 미취득. status 포트(19204)만 조회.
용도: CAN 릴레이 재검증 중 Seer가 CAN/모터 관련 오류를 내는지 실시간 포착.
사용: python3 seer_can_monitor.py [seer_ip] [초]   (기본 192.168.44.82, 60초)
종료코드: 신규 CAN/모터 알람 발생 시 2, 없으면 0.
"""
import sys
import os
import time
import re

sys.path.insert(0, "/home/nvidia/T-Robot_seer_gui")
from seer_core.client import RobokitClient

# CAN/모터/컨트롤러 통신 계열 알람코드 (appendix 002 실측 추출)
CAN_CODES = {50204, 50301, 50305, 50405, 52001, 52002, 52010, 52106, 52111, 52116,
             52118, 52123, 52130, 52131, 52132, 52133, 52134, 52135, 52136, 52138,
             52139, 52155, 52156, 52160, 52163, 52195}
# 단어경계 정규식 — "can"이 "cannot"에 부분매칭되던 오탐 방지
CAN_RE = re.compile(r"\b(can|canopen|canbus|src\d*|dsp|odo)\b", re.I)
CAN_KW = ("motor", "driver", "chassis", "wheel", "steer", "baseplate",
          "encoder", "heart beat", "alive timer")


def alarm_codes(al, level):
    out = {}
    for a in (al.get(level) or []):
        for k in a:
            if k not in ("desc", "times", "describe", "method", "reason") and k.lstrip("-").isdigit():
                out[k] = a.get("desc", "")
    return out


def is_can(code, desc):
    try:
        if int(code) in CAN_CODES:
            return True
    except ValueError:
        pass
    d = desc or ""
    if CAN_RE.search(d):
        return True
    dl = d.lower()
    return any(kw in dl for kw in CAN_KW)


def snapshot(c):
    al = c.call("status", 1050)
    return {lvl: alarm_codes(al, lvl) for lvl in ("fatals", "errors", "warnings")}


def main():
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.44.82"
    secs = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    logdir = os.path.expanduser("~/docking_reliability")
    os.makedirs(logdir, exist_ok=True)
    logp = os.path.join(logdir, "seer_can_monitor.log")

    def log(m):
        line = time.strftime("%H:%M:%S ") + m
        print(line, flush=True)
        with open(logp, "a") as f:
            f.write(line + "\n")

    c = RobokitClient(ip, timeout=4.0)
    base = snapshot(c)
    base_can = [(l, k, v) for l in base for k, v in base[l].items() if is_can(k, v)]
    log("[baseline] fatals=%d errors=%d warnings=%d | CAN관련=%s" % (
        len(base["fatals"]), len(base["errors"]), len(base["warnings"]),
        base_can if base_can else "없음"))
    seen = set((l, k) for l in base for k in base[l])
    can_events = 0
    t0 = time.time()
    while time.time() - t0 < secs:
        try:
            snap = snapshot(c)
        except Exception as e:
            log("[poll err] %s" % e)
            time.sleep(0.5)
            continue
        for lvl in ("fatals", "errors", "warnings"):
            for k, v in snap[lvl].items():
                if (lvl, k) not in seen:
                    seen.add((lvl, k))
                    can = is_can(k, v)
                    if can:
                        can_events += 1
                    log("[NEW %s] %s code=%s desc=%s" % (
                        lvl.upper(), "⚠CAN/모터" if can else "  기타", k, v))
        time.sleep(0.4)
    log("[end] 신규 CAN/모터 알람 %d건 (%ds)" % (can_events, secs))
    c.close()
    sys.exit(2 if can_events else 0)


if __name__ == "__main__":
    main()
