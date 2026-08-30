#!/usr/bin/env python3
"""relay engage 시 버스별 통신 갭 분리 측정.

가설(사용자 정정): CAN0(Seer)는 항상 판다에 연결 → 갭 ~0. CAN2(모터)만 릴레이 스위칭 →
판다 CAN2 startup 시간만큼 갭. bus0 갭≈0 & bus2 갭=대부분 이면 확정.
auth=Seer 투명, 0xf3 미전송, 종료 시 강제 passthrough.
"""
import sys
import time

sys.path.insert(0, "/home/nvidia/Project/CAN-Relay/docking_field_kit")
from panda import Panda


def main():
    p = Panda()
    p.set_safety_mode(30, 0)
    for b in (0, 2):
        p.set_can_speed_kbps(b, 250)
        p.set_can_enable(b, True)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")  # auth=Seer
    time.sleep(0.3)
    p.can_recv()
    arr = {0: [], 2: []}
    t0 = time.time()
    did = False
    tog = None
    try:
        while time.time() - t0 < 2.5:
            now = time.time()
            for addr, _, dat, bus in p.can_recv():
                if bus in arr:
                    arr[bus].append(now)
            if not did and now - t0 > 1.0:
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # engage
                tog = time.time() - t0
                did = True
    finally:
        try:
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
            p.set_safety_mode(0, 0)
            p.close()
        except Exception:
            pass

    print("engage @ t=%.3fs" % tog)
    for bus in (0, 2):
        ts = arr[bus]
        if len(ts) < 3:
            print("bus%d: 프레임 부족(%d)" % (bus, len(ts)))
            continue
        gaps = [(ts[i - 1] - t0, (ts[i] - ts[i - 1]) * 1000) for i in range(1, len(ts))]
        med = sorted(dt for _, dt in gaps)[len(gaps) // 2]
        near = [(t, dt) for t, dt in gaps if tog - 0.05 <= t <= tog + 0.8]
        mx = max((dt for _, dt in near), default=0)
        mx_at = [t for t, dt in near if dt == mx]
        nm = "Seer" if bus == 0 else "Motor"
        print("bus%d(%-5s): 정상간격 중앙값 %.2fms | **engage 후 최대갭 %.1fms** @t=%.3f (정상의 %.0f배)" % (
            bus, nm, med, mx, mx_at[0] if mx_at else 0, mx / med if med else 0))


if __name__ == "__main__":
    main()
