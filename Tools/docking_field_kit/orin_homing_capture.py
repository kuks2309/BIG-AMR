#!/usr/bin/env python3
"""조향 호밍 판별 캡처 — CAN2 단절로 통신오류를 유발하고 재호밍을 수동 청취한다.

목적: 조향축 원점 복귀가 어느 방식인지 실기로 판정한다.
  - Home 36/37 (기계 하드스톱, 리밋 스위치 없음)
      → 하드스톱 접촉 시 **0x6078 전류가 정격까지 상승 + 속도 0 이 2초 지속** 후 종료.
        [IxLII/IxLs/IxH Servo Driver Handbook V7.0, §4.6, page 122]
  - Home 1/2 (리밋 스위치)
      → 스위치 신호에서 감속 정지. 전류 평탄구간 없음. [같은 문서, §4.6, page 116]
        DI 리밋 상태는 0x6000.01 에 반영된다 — bit1 = Positive Limit, bit3 = Negative Limit.
        [같은 문서, Appendix I(Object Dictionary), page 197]
        (page 116 에는 0x6000 언급이 없다 — 비트맵 출처는 Appendix I 이다.)
  공통: 0x6041 bit15 = 0(호밍 진행 중) → 1(완료). [같은 문서, §6.9, page 171]

⚠ 정정 (2026-07-27): 위 "어느 방식인지" 판별은 **실기 판독으로 종결됐다.**
  - 방식은 **Home 1 (음(−)의 리밋 트리거 신호)** 로 확정 — 전 노드 0x6098 = 1 직접 판독.
    조향축에 리밋 스위치가 **실재**한다. Handbook 기본 RstMode 도 1 [같은 문서, §4.6, page 116].
    ⇒ Home 36/37(기계 하드스톱) 가설은 폐기한다.
  - 0x6098 은 Seer 도 우리도 쓰지 않는다 — 본 캡처 전 구간에서 write·read 모두 0회
    (Log/homing_capture_220350.jsonl, 253,510 프레임 전수). 드라이브 저장값이 그대로 쓰인다.
    Home 35 를 쓰면 RstMode 가 0(호밍 꺼짐)으로 리셋되므로 [같은 문서, §4.6, page 122]
    타사 코드의 method write 를 그대로 베끼면 Seer 호밍이 죽는다.
  - 호밍 개시 트리거는 0x60FB.4 = RstStart ("0-Reset off, 1-Reset on")
    [같은 문서, §6.9, page 171]. 벤더 미상 오브젝트가 아니다.
  - 콜드부팅 시의 약 137° 조향 스윙은 **이상거동이 아니다** — 호밍 완료 후 원점(리밋)에서
    조향 0° 로 복귀하는 설계된 이동이다. 목표 node3 = 7,882,020 / node4 = 7,859,062 counts
    (= +137.45° / +137.05°, 57344 counts/°; Log/homing_capture_220350.jsonl t=49.14,
    EasyDRIVE steerOffset 138.000 / 137.250 과 대응).
  - 구동축(node 1·2)은 호밍하지 않는다 — 호밍 프레임이 조향 노드로만 나갔다(같은 캡처).

**본 스크립트는 CAN 버스에 한 프레임도 송신하지 않는다.** `can_send` 미사용.
조작하는 것은 판다 하네스 릴레이(intercept on/off)뿐이며, 종료 시 finally 로 반드시 passthrough 복귀.

제어권 프로토콜은 Tools/amr_test_gui/gui.py:713-730(획득/해제) 과 동일:
(⚠ 2026-07-28: 원 인용 amr_test_gui/amr_test_gui/panda_can_bus.py 는 구 GUI 폐기로 삭제 — docs/adr/2026-07-28-old-gui-removal.md)
  take    = safety_mode 30(SEER_GATE) + CAN0/2 enable(250 kbps) + 0xe9=1(auth=PC) + 0xe8=1(intercept)
            + heartbeat 0.4 s(0xf3)
  release = 0xe9=0 + 0xe8=0 + safety_mode 0
버스 배선: CAN0=Seer, CAN2=모터.

⚠ 단절 구간 동안 드라이브가 Node Guarding(500 ms × LifeFactor 1) 타임아웃으로 폴트에 들어가면
  홀딩토크를 잃을 수 있다. 접지 상태에서는 평지·주변확보 확인 후 실행할 것.

사용:
  python3 orin_homing_capture.py --dry              # 릴레이 미조작, 수동 청취만(위험 0)
  python3 orin_homing_capture.py --cut 3 --watch 90 # 3초 단절 후 90초 관측
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panda import Panda  # noqa: E402

SEER_BUS, MOTOR_BUS = 0, 2
SEER_GATE = 30
CAN_KBPS = 250
HEARTBEAT_S = 0.4
COUNTS_PER_DEG = 57344.0          # 1차 source: References/motor_configuration/frontsteer1.png
                                  #   (encoderLine 16384) + frontsteer2.png (reductionRatio 315)
                                  #   → 16384 × 4 × 315 / 360 = 57344
                                  # 교차검산: EasyDRIVE steerOffset(138.000/137.250) ↔ 호밍 후
                                  #   정착 counts(7,882,020/7,859,062) 왕복이 두 노드 모두
                                  #   C ≈ 57344 로 닫힌다 ✓ (파생: motor-config-analysis.md)
STEER_NODES = (3, 4)

SDO_RD_RESP = {0x43: 4, 0x47: 3, 0x4B: 2, 0x4F: 1}
SDO_WR_CMD = {0x2F: 1, 0x2B: 2, 0x27: 3, 0x23: 4}
OBJ_NAME = {0x6041: "statusword", 0x603F: "error", 0x6064: "pos", 0x6078: "current",
            0x606C: "vel", 0x607A: "target_pos", 0x6098: "homing_method",
            0x6099: "homing_speed", 0x607C: "homing_offset", 0x60FB: "RstStart",
            0x6040: "controlword", 0x6060: "modes", 0x6000: "digital_in"}
WATCHED_WRITES = (0x6098, 0x60FB, 0x6099, 0x607C, 0x6040, 0x6060, 0x607A)


def s32(b: bytes) -> int:
    v = int.from_bytes(b[:4], "little")
    return v - (1 << 32) if v & 0x80000000 else v


def s16(v: int) -> int:
    v &= 0xFFFF
    return v - (1 << 16) if v & 0x8000 else v


class Tracker:
    """노드별 최신 피드백 + 호밍 판별에 필요한 이벤트를 누적한다."""

    def __init__(self):
        self.node = {}          # n -> dict(pos,status,current,error,...)
        self.events = []        # (t, kind, text)
        self.cur_series = {}    # n -> [(t, current)]
        self.pos_series = {}    # n -> [(t, pos)]

    def st(self, n):
        return self.node.setdefault(n, {"pos": None, "status": None, "current": None,
                                        "error": None, "bit15": None, "bit10": None})

    def ev(self, t, kind, text):
        self.events.append((t, kind, text))
        print(f"  [{t:7.3f}] {kind:12s} {text}", flush=True)

    def on_resp(self, t, node, idx, val):
        s = self.st(node)
        if idx == 0x6064:
            s["pos"] = val
            self.pos_series.setdefault(node, []).append((t, val))
        elif idx == 0x6078:
            c = s16(val)
            s["current"] = c
            self.cur_series.setdefault(node, []).append((t, c))
        elif idx == 0x6041:
            sw = val & 0xFFFF
            b15 = 1 if sw & 0x8000 else 0
            b10 = 1 if sw & 0x0400 else 0
            if s["bit15"] is not None and b15 != s["bit15"]:
                self.ev(t, "BIT15", f"node{node} 호밍상태 {s['bit15']}→{b15} "
                                    f"({'완료' if b15 else '진행중'}) sw=0x{sw:04x}")
            s["bit15"], s["bit10"], s["status"] = b15, b10, sw
        elif idx == 0x603F:
            e = val & 0xFFFF
            if s["error"] is not None and e != s["error"]:
                self.ev(t, "ERRCODE", f"node{node} 0x{s['error']:04x}→0x{e:04x}")
            s["error"] = e
        elif idx == 0x6000:
            # ⚠ 정정 (2026-07-27): 0x6000 은 **배열 오브젝트**이고 실입력은 **sub 1** 이다
            #   (sub 0 = 항목 수 = 2). 여기 찍히는 값도 전부 sub 1 응답이다.
            #   폭도 32비트가 아니라 **UINT8** — 캡처 응답이 전건 cmd 0x4F(1바이트 expedited)다
            #   (Log/homing_capture_220350.jsonl: node1~4 sub1 0x4F 응답 1,680건, 그 외 0건).
            #   따라서 아래 08x 출력은 실제 페이로드보다 넓게 보이는 표기이며,
            #   "0x00000001 → 0x00000009" 같은 32비트 서술이 여기서 파생됐다. 실값은 0x01 → 0x09.
            #   비트: bit0 = Servo Enable, bit1 = +Limit, bit2 = Alarm, bit3 = −Limit
            #   [Handbook V7.0, Appendix I(Object Dictionary), page 197]
            #   실측: node3/4 만 0x01 → 0x09 (t=47.0249 / 47.0254), 구동축(node1·2)은 전 구간 0x01.
            #   ⇒ 표기 폭(0xFF)과 bit0/bit2 디코드 추가는 로그 포맷 변경이라 이번 정정에서
            #     손대지 않았다(needs_code_change 로 보고).
            self.ev(t, "DIGITAL_IN", f"node{node} 0x6000=0x{val & 0xFFFFFFFF:08x} "
                                     f"(bit1 +Limit={(val >> 1) & 1}, bit3 -Limit={(val >> 3) & 1})")

    def summary(self):
        print("\n=== 노드 최종 상태 ===", flush=True)
        for n in sorted(self.node):
            s = self.node[n]
            pos = s["pos"]
            deg = f"{pos / COUNTS_PER_DEG:+9.2f}°" if pos is not None else "   ?    "
            print(f"  node{n}: pos={str(pos):>12s} ({deg})  sw={s['status']} "
                  f"bit15={s['bit15']} bit10={s['bit10']} err={s['error']} cur={s['current']}",
                  flush=True)
        for n in STEER_NODES:
            ps = self.pos_series.get(n, [])
            if len(ps) >= 2:
                vs = [p for _, p in ps]
                span = (max(vs) - min(vs)) / COUNTS_PER_DEG
                print(f"  node{n} 위치 이동폭: {span:.2f}° "
                      f"(min={min(vs)}, max={max(vs)}, n={len(vs)})", flush=True)
            cs = self.cur_series.get(n, [])
            if cs:
                vs = [abs(c) for _, c in cs]
                print(f"  node{n} 전류 |max|={max(vs)} (n={len(cs)}) — 하드스톱 판별용", flush=True)


def sniff(p, tracker, seconds, label, log_fp, t0):
    """지정 시간 동안 CAN2(모터) 프레임을 수동 청취한다. 송신 없음."""
    print(f"\n--- {label} ({seconds}s) ---", flush=True)
    end = time.time() + seconds
    count = 0
    while time.time() < end:
        try:
            frames = p.can_recv()
        except Exception as exc:
            tracker.ev(time.time() - t0, "RXERR", f"{type(exc).__name__}: {exc}")
            time.sleep(0.05)
            continue
        for addr, _, dat, bus in frames:
            if bus != MOTOR_BUS or not dat:
                continue
            t = time.time() - t0
            count += 1
            dat = bytes(dat)
            log_fp.write(json.dumps({"t": round(t, 4), "phase": label,
                                     "id": addr, "d": dat.hex()}) + "\n")
            if 0x581 <= addr <= 0x584 and len(dat) >= 8:
                cmd, idx, sub = dat[0], dat[1] | (dat[2] << 8), dat[3]
                node = addr - 0x580
                if cmd in SDO_RD_RESP:
                    tracker.on_resp(t, node, idx, s32(dat[4:8]))
                elif cmd == 0x80:
                    tracker.ev(t, "SDO_ABORT", f"node{node} idx=0x{idx:04x}.{sub}")
            elif 0x601 <= addr <= 0x604 and len(dat) >= 4:
                cmd, idx, sub = dat[0], dat[1] | (dat[2] << 8), dat[3]
                node = addr - 0x600
                if cmd in SDO_WR_CMD and idx in WATCHED_WRITES:
                    val = s32(dat[4:8]) if len(dat) >= 8 else None
                    tracker.ev(t, "WRITE", f"node{node} 0x{idx:04x}.{sub} "
                                           f"({OBJ_NAME.get(idx, '?')}) = {val}")
            elif 0x081 <= addr <= 0x084:
                tracker.ev(t, "EMCY", f"node{addr - 0x080} {dat.hex()}")
            elif 0x701 <= addr <= 0x704 and len(dat) >= 1:
                pass  # guard 응답 — 빈도만 raw 로그에
    print(f"  ({label}: {count} frames)", flush=True)
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="릴레이 미조작, 수동 청취만")
    ap.add_argument("--base", type=float, default=5.0, help="단절 전 기준 청취 초")
    ap.add_argument("--cut", type=float, default=3.0, help="CAN2 단절 유지 초")
    ap.add_argument("--watch", type=float, default=90.0, help="복구 후 관측 초")
    ap.add_argument("--out", default=None, help="raw 로그 경로(.jsonl)")
    args = ap.parse_args()

    out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   f"homing_capture_{int(time.time())}.jsonl")
    p = Panda()
    print(f"판다 연결: fw={p.get_version()} out={out}", flush=True)
    p.set_safety_mode(0, 0)                      # SILENT — 송신 불가 상태로 시작
    for b in (SEER_BUS, MOTOR_BUS):
        p.set_can_speed_kbps(b, CAN_KBPS)
        p.set_can_enable(b, True)
    time.sleep(0.3)
    p.can_recv()                                 # 버퍼 비우기

    tracker = Tracker()
    t0 = time.time()
    controlling = False
    hb_stop = False

    def heartbeat_once():
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xf3, 0, 0, b"")

    with open(out, "w") as log_fp:
        try:
            sniff(p, tracker, args.base, "baseline", log_fp, t0)
            if args.dry:
                print("\n--dry: 릴레이 미조작으로 종료합니다.", flush=True)
            else:
                print("\n>>> CAN2 단절 (intercept ON) — 드라이브 Node Guarding 타임아웃 유발",
                      flush=True)
                p.set_safety_mode(SEER_GATE, 0)
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 1, 0, b"")   # auth=PC
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")   # intercept ON
                controlling = True
                tracker.ev(time.time() - t0, "CUT_ON", "intercept ON (CAN2 단절)")
                # 단절 중에도 heartbeat 를 유지해야 펌웨어가 SILENT 로 되돌리지 않는다
                cut_end = time.time() + args.cut
                while time.time() < cut_end:
                    heartbeat_once()
                    sniff(p, tracker, min(HEARTBEAT_S, max(0.05, cut_end - time.time())),
                          "cut", log_fp, t0)
                print("\n>>> CAN2 복구 (passthrough) — 재호밍 관측 시작", flush=True)
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")   # auth=Seer
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")   # passthrough
                p.set_safety_mode(0, 0)
                controlling = False
                tracker.ev(time.time() - t0, "CUT_OFF", "passthrough 복귀")
                sniff(p, tracker, args.watch, "watch", log_fp, t0)
        finally:
            if controlling:
                try:
                    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
                    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
                    p.set_safety_mode(0, 0)
                    print("[finally] 제어권 반환 + passthrough 복귀", flush=True)
                except Exception as exc:
                    print(f"[finally] ⚠ release 실패: {exc} — heartbeat 소실로 "
                          f"판다 fail-safe(passthrough) 복귀 예정", flush=True)
            _ = hb_stop
            try:
                p.close()
            except Exception:
                pass

    tracker.summary()
    print(f"\nraw 로그: {out}", flush=True)
    print("판정 기준(원안): 조향 노드 전류 |max| 가 정격 수준으로 2초가량 평탄하면 Home 36/37"
          "(기계 하드스톱, 리밋 스위치 없음). 0x6000 bit1/bit3 변화가 보이면 Home 1/2"
          "(리밋 스위치). 어느 쪽도 없으면 재호밍 자체가 발생하지 않은 것.", flush=True)
    print("⚠ 정정 (2026-07-27): 위 판별은 종결됐다 — 전 노드 0x6098 = 1 실기 직접 판독으로 "
          "**Home 1(음의 리밋 트리거)** 확정이며 조향축에 리밋 스위치가 실재한다 "
          "[Handbook V7.0 §4.6 page 116, 기본 RstMode=1]. 전류 평탄구간 기준은 폐기된 "
          "Home 36/37 가설용이었으므로 더 이상 판별식이 아니다.", flush=True)
    print("  0x6000 은 배열 오브젝트라 실입력은 sub 1(UINT8)이고 bit0=ServoEnable, bit3=−Limit — "
          "실측 0x01→0x09 전이(Log/homing_capture_220350.jsonl t=47.0249/47.0254, node3·4 한정, "
          "구동축 무변화). 본 스크립트의 남은 용도는 방식 판별이 아니라 리밋 물림/해제 시각과 "
          "0x6041 bit15 전이 시각의 대조다.", flush=True)
    print("  호밍은 원점 경유 후 **조향 0° 복귀까지**다 — 관측되는 약 137° 스윙은 이상거동이 "
          "아니라 설계된 복귀 이동이다(목표 node3 7,882,020 / node4 7,859,062 counts, "
          "Log/homing_capture_220350.jsonl t=49.14). 구동축(node1·2)은 호밍하지 않는다.",
          flush=True)


if __name__ == "__main__":
    main()
