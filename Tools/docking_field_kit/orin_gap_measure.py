#!/usr/bin/env python3
"""relay 전환 갭 실측 + 300ms 커버 실증 — 0xe8 토글 순간의 통신 outage 와 커버 동작.

① 전환 갭: 프레임 도착 시각을 촘촘히(tight loop) 기록하며 engage/disengage 토글 →
   토글 전후 도착 간격의 최대 갭 = 전환 통신 outage.
② 커버 실증(2026-07-28 추가): 판다는 자기 송신 프레임을 호스트로 되돌려주고
   (board/drivers/bxcan.h:104-118, returned=1), 호스트 라이브러리가 이를 bus+=128 로
   표시한다(panda/python/__init__.py:86). 따라서 **bus==128 인 0x581~0x584 프레임
   = 판다가 bus0(Seer 쪽)으로 낸 캐시 응답**이다. engage 직후 300ms(SEER_COVER_US)
   동안 이것이 나타났다가 멈추는지를 실측해 커버 동작을 확정한다.

auth=Seer 투명, 0xf3 미전송, 종료 시 강제 passthrough.

⚠ disengage 시 Seer 가 노드 상실로 판단해 재호밍을 걸 수 있다 — 접지 상태면 조향축이 움직인다.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panda import Panda

SEER_COVER_S = 0.300   # board/safety/safety_seer_gate.h:3  SEER_COVER_US 300000U


def main():
    p = Panda()
    p.set_safety_mode(30, 0)
    for b in (0, 2):
        p.set_can_speed_kbps(b, 250)
        p.set_can_enable(b, True)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")  # auth=Seer
    time.sleep(0.3)
    p.can_recv()

    ev = []          # 프레임 받은 순간의 (t, n)
    frames = []      # (t, addr, bus)  — 커버 실증용 전수 기록
    toggles = []     # (t, action)
    ts_sample = []   # 프레임 타임스탬프 필드 표본
    t0 = time.time()
    did_on = did_off = False
    try:
        while time.time() - t0 < 3.0:
            fr = p.can_recv()
            now = time.time()
            if fr:
                ev.append((now, len(fr)))
                for m in fr:
                    frames.append((now - t0, m[0], m[3]))
                if len(ts_sample) < 6:
                    for m in fr[:2]:
                        ts_sample.append(m[1])
            rel = now - t0
            if not did_on and rel > 1.0:
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # engage
                toggles.append((time.time() - t0, "ENGAGE(pass->intc)"))
                did_on = True
            elif not did_off and rel > 2.0:
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")  # disengage
                toggles.append((time.time() - t0, "DISENGAGE(intc->pass)"))
                did_off = True
    finally:
        try:
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
            p.set_safety_mode(0, 0)
            p.close()
        except Exception:
            pass

    print("프레임 타임스탬프 필드 표본:", ts_sample, "(0만 있으면 μs타임스탬프 없음 → Python시각 사용)")
    print("총 %d 수신이벤트, %.0f fps 평균" % (len(ev), len(ev) / 3.0))
    # 도착 간격
    gaps = [(ev[i - 1][0] - t0, (ev[i][0] - ev[i - 1][0]) * 1000) for i in range(1, len(ev))]
    if not gaps:
        print("이벤트 부족"); return
    typical = sorted(g[1] for g in gaps)[len(gaps) // 2]
    print("정상 도착간격(중앙값) = %.2f ms" % typical)
    for tt, act in toggles:
        # 토글 시각 이후 첫 갭들 중 최대
        near = [(t, dt) for t, dt in gaps if tt - 0.05 <= t <= tt + 0.5]
        mx = max((dt for _, dt in near), default=0)
        print("★ %-22s @t=%.3fs → 전환 갭 최대 = %.1f ms (정상간격의 %.0f배)" % (
            act, tt, mx, mx / typical if typical else 0))
    print("전체 최대 갭 = %.1f ms" % max(dt for _, dt in gaps))

    # ---- ② 커버 실증 : bus==128 인 0x581~0x584 = 판다가 bus0 로 낸 캐시 응답 ----
    print("\n=== 커버(300ms) 실증 ===")
    print("관측된 bus 값 분포:", {b: sum(1 for _, _, x in frames if x == b)
                                 for b in sorted({x for _, _, x in frames})})
    panda_tx0 = [(t, a) for t, a, b in frames if b == 128 and 0x581 <= a <= 0x584]
    print("판다 bus0 송신(0x581~584) 총 %d건" % len(panda_tx0))
    for tt, act in toggles:
        if "ENGAGE(pass" not in act:
            continue
        def rate(lo, hi):
            n = sum(1 for t, _ in panda_tx0 if lo <= t < hi)
            return n, n / (hi - lo)
        pre_n, pre_r = rate(tt - SEER_COVER_S, tt)          # engage 전 (passthrough)
        cov_n, cov_r = rate(tt, tt + SEER_COVER_S)          # 커버창 (emulate on)
        aft_n, aft_r = rate(tt + SEER_COVER_S, tt + 2 * SEER_COVER_S)  # 커버 후 (intercept 투명)
        inside = [t for t, _ in panda_tx0 if tt <= t < tt + SEER_COVER_S]
        print("★ engage @t=%.3fs   (구간 폭 %.0f ms)" % (tt, SEER_COVER_S * 1000))
        print("   engage 전(passthrough)      : %4d건  %7.1f 건/s" % (pre_n, pre_r))
        print("   커버창(emulate on)          : %4d건  %7.1f 건/s   %s" % (
            cov_n, cov_r, ("첫 %+.1f ms / 끝 %+.1f ms" % ((inside[0] - tt) * 1000,
                                                         (inside[-1] - tt) * 1000)) if inside else ""))
        print("   커버 후(intercept 투명)     : %4d건  %7.1f 건/s" % (aft_n, aft_r))
        if cov_r > 3 * max(aft_r, pre_r, 1e-9):
            print("   ⇒ 커버 동작 확인 — 커버창에서만 판다가 Seer 에게 대신 답한다")
        else:
            print("   ⇒ 커버 구간이 구별되지 않음 — 판다 bus0 송신이 투명 중계분과 섞였을 수 있다")


if __name__ == "__main__":
    main()
