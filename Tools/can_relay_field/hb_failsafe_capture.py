#!/usr/bin/env python3
"""심박 상실 → 펌웨어 fail-safe 의 버스 수준 관측 (판다 단독, ROS 불요).

판다는 양쪽 버스의 수신 프레임을 전부 호스트로 올리므로 별도 캡처 장비 없이
판다 자체가 계측기다. 절차:

  ① open + acquire — intercept·fail-safe 무장 (드라이버 노드와 동일 경로)
  ② 기준 구간: 심박을 정상 송신하며 버스별 트래픽 분포를 기록
  ③ 심박 중단 구간: 심박만 멈추고 수신은 계속 — 펌웨어 fail-safe 가 남기는
     버스 흔적을 시각과 함께 기록
  ④ release + close — passthrough 복원

관측 지표 (드라이브측 `MOTOR_BUS`=2 의 수신 = 드라이브가 실제로 보낸 프레임):
  - `0x580+node` SDO 응답 중 index `0x60FF`(목표속도) ACK — 펌웨어 정지 쓰기
    (`seer_stop_drives`)에 드라이브가 답한 것. 심박 중단 뒤에만 나타나야 한다.
  - bus2 전체 수신율의 급증 — 릴레이 개방으로 Seer 요청이 드라이브에 도달해
    응답 스트림이 개시된 것(intercept 중에는 Seer 가 차단되어 응답이 없다).

구동 지령을 일절 보내지 않는다(속도는 전 구간 0). 조향도 건드리지 않는다.
드라이버 노드(systemd 유닛)는 미획득 대기면 USB 를 열지 않으므로 공존 가능하나,
실행 전 `engaged=false` 인지 확인할 것(동시 개방은 USB 에서 거부된다).
"""
import sys
import time
from collections import Counter

from can_relay.link import MOTOR_BUS, SEER_BUS, PandaLink

BASELINE_S = 5.0        # 심박 정상 구간
SILENT_S = 15.0         # 심박 중단 관측 구간 (펌웨어 임계: 점화 off 1~2 s)
HB_PERIOD_S = 0.2


def sdo_60ff_ack(can_id: int, data: bytes) -> bool:
    """드라이브의 SDO download 응답이며 index 가 0x60FF 인가."""
    return (0x581 <= can_id <= 0x584 and len(data) >= 4
            and (data[0] & 0xE0) == 0x60 and data[1] == 0xFF and data[2] == 0x60)


def run() -> int:
    link = PandaLink(log=lambda m: print(f"[link] {m}"))
    link.open()
    link.acquire()
    t0 = time.monotonic()
    events = []             # (t, 구간, bus, can_id, data)
    hist = {"기준": Counter(), "중단": Counter()}

    def drain(phase: str):
        for can_id, data, bus in link.recv():
            hist[phase][(bus, can_id)] += 1
            if bus == MOTOR_BUS:
                events.append((time.monotonic() - t0, phase, can_id, bytes(data)))

    try:
        print(f"── 기준 구간 {BASELINE_S:.0f}s (심박 정상) ──")
        next_hb = 0.0
        end = time.monotonic() + BASELINE_S
        while time.monotonic() < end:
            now = time.monotonic()
            if now >= next_hb:
                link.heartbeat()
                next_hb = now + HB_PERIOD_S
            drain("기준")
            time.sleep(0.01)

        t_stop = time.monotonic() - t0
        print(f"── 심박 중단 @{t_stop:.2f}s — {SILENT_S:.0f}s 관측 ──")
        end = time.monotonic() + SILENT_S
        while time.monotonic() < end:
            drain("중단")
            time.sleep(0.01)
    finally:
        link.release()
        link.close()

    print("\n══ 버스별 트래픽 (구간 · bus · can_id · 건수) ══")
    for phase in ("기준", "중단"):
        span = BASELINE_S if phase == "기준" else SILENT_S
        total = {SEER_BUS: 0, MOTOR_BUS: 0}
        for (bus, cid), n in sorted(hist[phase].items()):
            total[bus] = total.get(bus, 0) + n
        for bus in sorted(total):
            print(f"  {phase} · bus{bus} 총 {total[bus]}건 ({total[bus]/span:.1f}/s)")
        for (bus, cid), n in sorted(hist[phase].items(), key=lambda kv: -kv[1])[:12]:
            print(f"    {phase} bus{bus} 0x{cid:03X} × {n}")

    print("\n══ 드라이브측(bus2) 사건 타임라인 (심박 중단 전후) ══")
    stop_acks = [(t, cid, d) for t, ph, cid, d in events
                 if ph == "중단" and sdo_60ff_ack(cid, d)]
    first_motor = [(t, cid) for t, ph, cid, d in events if ph == "중단"][:5]
    for t, cid, d in stop_acks[:12]:
        print(f"  {t:7.3f}s  0x{cid:03X}  {d.hex()}  ← 0x60FF ACK (펌웨어 정지 쓰기 응답)")
    if not stop_acks:
        print("  0x60FF ACK 미관측")
    print("  중단 구간 bus2 최초 수신 5건:",
          [(f"{t:.3f}s", f"0x{c:03X}") for t, c in first_motor] or "없음")
    base_rate = sum(n for (b, _), n in hist["기준"].items() if b == MOTOR_BUS) / BASELINE_S
    stop_rate = sum(n for (b, _), n in hist["중단"].items() if b == MOTOR_BUS) / SILENT_S
    print(f"\n  bus2 수신율: 기준 {base_rate:.1f}/s → 중단 {stop_rate:.1f}/s")
    print(f"  심박 중단 시각: t={t_stop:.2f}s (이후 사건의 상대 기준)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
