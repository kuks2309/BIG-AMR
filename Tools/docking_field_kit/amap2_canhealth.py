#!/usr/bin/env python3
"""amap-2 per-bus CAN 에러 진단 — firmware can_health(0xc3, bxCAN ESR) 사용.
라이브 트래픽 하에서 버스별 TEC/REC/LEC/BOFF/error-passive 를 샘플해 종단 수리 검증 + 재발 감시.
Seer 로그 54022(Ack/Bit/Stuff)와 대응: LEC(마지막 에러코드)로 에러 종류 식별.

사용: python3 amap2_canhealth.py [초]   (기본 10초)
"""
import sys, os, time
KIT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KIT)
from panda import Panda

SECS = int(sys.argv[1]) if len(sys.argv) > 1 else 10
# bxCAN ESR LEC(Last Error Code) 의미
LEC = {0: "no-error", 1: "stuff", 2: "form", 3: "ack", 4: "bit-recessive",
       5: "bit-dominant", 6: "crc", 7: "no-change"}

p = Panda()
p.set_safety_mode(0, 0)              # SILENT 리슨(비침습)
for b in (0, 2):
    p.set_can_speed_kbps(b, 250); p.set_can_enable(b, True)
time.sleep(0.3); p.can_recv()

a = {b: p.can_health(b) for b in (0, 2)}
frames = seer = motor = 0
t0 = time.time()
while time.time() - t0 < SECS:
    for (addr, _, dat, bus) in p.can_recv():
        frames += 1
        if 0x581 <= addr <= 0x584: motor += 1
        elif 0x601 <= addr <= 0x604: seer += 1
    time.sleep(0.003)
z = {b: p.can_health(b) for b in (0, 2)}

print("트래픽 %ds: frames=%d  Seer폴링=%d  모터응답=%d  (%.0f fps)" %
      (SECS, frames, seer, motor, frames / SECS))
bad = False
for bus, name in ((0, "bus0(Seer측)"), (2, "bus2(모터측)")):
    s, e = a[bus], z[bus]
    d_rec = e["receive_error_cnt"] - s["receive_error_cnt"]
    d_tec = e["transmit_error_cnt"] - s["transmit_error_cnt"]
    err_state = e["bus_off"] or e["error_passive"] or e["error_warning"]
    if err_state or d_rec > 0 or d_tec > 0:
        bad = True
    print("  %s: bus_off=%d ep=%d ew=%d lec=%s | REC %d->%d(Δ%d) TEC %d->%d(Δ%d) esr=0x%08x" % (
        name, e["bus_off"], e["error_passive"], e["error_warning"],
        LEC.get(e["last_error_code"], "?"),
        s["receive_error_cnt"], e["receive_error_cnt"], d_rec,
        s["transmit_error_cnt"], e["transmit_error_cnt"], d_tec, e["esr_reg"]))

if frames < 100:
    print("판정: 트래픽 적음 — 통신중인지 확인 필요")
elif bad:
    print("판정: ⚠ CAN 에러상태/증가 감지 — 종단·배선 재점검")
else:
    # 정정 2026-07-27 — 원 문구: "✅ 부하 하 per-bus 에러 0 = 종단/신호 정상 (Seer 단절오류 원인 해소 확인)"
    #   관측 조건이 판정문에 없어 "재발 없음"으로 읽혔다. 실제 관측 범위:
    #     · 기본 관측창 10초 1회 (:13 `SECS = ... else 10`)
    #     · 판다는 SILENT 리슨 = ACK 도 내지 않는 비침습 관찰 (:19)
    #     · :21 에서 250 kbps 를 명시 설정하므로 **부팅 기본 비트레이트 결함은 관측에서 가려진다**
    #       (docs/verified_facts/2026-07-27.md:50-52 "모든 호스트 도구가 set_can_speed_kbps(b,250) 을
    #        호출한다 … PC 소프트웨어가 붙어야만 버스가 성립")
    #   같은 킷의 amap2_canhealth_watchdog.py:4-6 도 "밤샘 CAN 단절오류 같은 재발" 포착에는
    #   연속 감시가 필요하다고 적는다 → 10초 표본으로 "원인 해소 확인"을 단정할 수 없다.
    print("판정: ✅ 관측창 %ds · SILENT 리슨(비침습) · 250 kbps 명시 설정 하에서 per-bus 에러 0." % SECS)
    print("      ⚠ 이는 재발 없음을 증명하지 않는다 — 지속 확인은 amap2_canhealth_watchdog.py 로 장시간 감시할 것.")
    print("      ⚠ 이 도구가 250 kbps 를 직접 설정하므로 판다 '부팅 기본' 비트레이트 건전성은 여기서 검사되지 않는다"
          " (verified_facts §A-1).")
p.close()
sys.exit(2 if bad else 0)
