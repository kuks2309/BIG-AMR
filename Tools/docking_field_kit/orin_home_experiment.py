#!/usr/bin/env python3
"""조향 홈 확정 실험 — 반복 호밍 재현성 · GOZERO↔0° 편차 · 히스테리시스 측정.

지시: 2026-08-03 "정석으로 실험해서 기존 오류 모두 수정" (docs/user_instructions/user_instructions.md)
설계: docs/homing/2026-08-03-can-relay-homing-assets.md §5

측정 목표
  M1  반복 재현성   — 동일 조건 호밍 N회, 매회 정착 0x6064 의 분산
  M2  GOZERO 편차   — 펌웨어 GOZERO 목표(7882020/7859062)와 실측 홈(7871815/7840086)의 차
  M3  히스테리시스  — 같은 목표에 +방향 / −방향으로 접근했을 때 정착 위치 차 (--hysteresis)

왜 필요한가
  펌웨어 상수 SEER_HOME_ZERO_N3/N4 (safety_seer_gate.h:212-213) 는 「홈」이라는 이름이지만
  실제로는 **호밍 후 정착값**이며 0° 에서 +0.178° / +0.331° 벗어나 있다. 도달 허용오차가
  57344(=1.0°)라 펌웨어가 이 편차를 스스로 검출하지 못한다.
  ⇒ 본 실험은 그 상수를 **고치지 않은 채** 실측한다. 고치면 무엇을 재는지 알 수 없어진다.

호밍 실행 계약 (safety_seer_gate.h 실측)
  전제: pc_authority(0xe9=1) + safety_mode==30 + FSM terminal + 속도 100~3000(0=기본 2500)
  개시: USB 0xea wValue=1 wIndex=speed    취소: 0xea wValue=0
  상태: USB 0xeb → 8B (state, done_mask, seen_active, elapsed_lo, elapsed_hi, DI3, DI4, reached)
  대상: node 3·4 만 (구동축 node 1·2 는 호밍하지 않는다)

⚠ 안전
  · 호밍은 조향 2축을 −리밋까지 보낸 뒤 약 137° 복귀 스윙을 한다. **접지 상태면 차체가 움직인다.**
  · Ctrl-C 는 즉시 0xea 취소(0x60FB:04=0) → 제어권 반환을 수행한다.
  · ⚠ GOZERO_W 타임아웃(safety_seer_gate.h:466-467)은 취소 프레임을 내지 않는다 —
    이미 0x607A + 0x6040=0x3F 가 걸린 뒤라 축이 목표까지 계속 갈 수 있다.
  · 제어권 반환 시 Seer 가 자체 재호밍을 걸 수 있다(FIELD-RECORD-2026-07-25.md:44-57).

사용
  python3 orin_home_experiment.py --dry-run          # 제어권만 잡고 판독, 호밍 미개시
  python3 orin_home_experiment.py --repeat 5         # M1 + M2
  python3 orin_home_experiment.py --repeat 5 --hysteresis   # M1 + M2 + M3
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panda import Panda  # noqa: E402

SEER_BUS, MOTOR_BUS = 0, 2
SEER_GATE, CAN_KBPS, HEARTBEAT_S = 30, 250, 0.4
CPD = 57344.0
STEER_NODES = (3, 4)

# 값 정본: src/Comm/CAN/can_relay/config/machine/foil_a082.yaml (2026-08-03 정정 — §10)
HOME_0DEG = {3: 7871815, 4: 7840086}
# 펌웨어 GOZERO 목표: safety_seer_gate.h:212-213 (구값 — 본 실험의 측정 대상, 수정하지 않음)
FW_GOZERO = {3: 7882020, 4: 7859062}

STATE = {0: "IDLE", 1: "ENABLE", 2: "SET_SPEED", 3: "START", 4: "WAIT(원점탐색)",
         5: "DONE", 6: "ERR_TIMEOUT", 7: "ERR_ABORT", 8: "RESTORE",
         9: "GOZERO", 10: "ERR_GOZERO", 11: "GOZERO_W"}
TERMINAL = {0, 5, 6, 7, 10}
RD_RESP = {0x43, 0x47, 0x4B, 0x4F}

OBJ_POS = 0x6064        # Position actual value
OBJ_STATUS = 0x6041     # Statusword (bit15 = 호밍 완료)
OBJ_DIN = 0x6000        # Digital input (sub1: bit0 ServoEnable, bit1 +Lim, bit2 Alarm, bit3 −Lim)
OBJ_TARGET = 0x607A     # Target position
OBJ_CTRL = 0x6040       # Controlword
CW_SETPOINT = 0x3F


def s32(b: bytes) -> int:
    v = int.from_bytes(b[:4], "little")
    return v - (1 << 32) if v & 0x80000000 else v


class Rig:
    """제어권·heartbeat·SDO(Service Data Object)·로깅을 한 곳에서 관리.

    ## heartbeat 는 **전용 스레드**가 보낸다 (2026-08-03 정정)

    초판은 `_hb()` 를 SDO 호출 안에 인라인해 뒀다. 그래서 `time.sleep(settle)` 같은
    **작업 없는 구간에서 heartbeat 가 굶었고**, 펌웨어 fail-safe 임계(`HEARTBEAT_IGNITION_CNT_OFF`
    = 2 s, `board/main.c`)를 넘겨 매 회차 제어권이 조용히 풀렸다. 그 뒤로도 스크립트는
    이를 감지하지 못한 채 판독을 계속했고, `sdo_read` 가 `addr`·`index` 만 대조하므로
    **Seer 폴링에 대한 응답을 자기 응답으로 오인 채집**했다.

    올바른 패턴은 이미 저장소에 있었다 — `Tools/amr_test_gui/gui.py:819` 가 제어권 획득 즉시
    전용 `poll` 스레드를 띄우고 `:1023-1025` 가 **매 ≈0.2 s 무조건** `0xf3` 를 보낸다
    (같은 줄 주석: "끊기면 펌웨어가 fail-safe 로 intercept 를 푼다"). 그 패턴을 재사용한다.

    추가로 `assert_authority()` 로 **판독 전 제어권 생존을 확인**한다 — 조용한 오염을 막는
    유일한 방법이다(fail-safe 뒤 재획득은 `0xe9=1`→`0xe8=1` 순서로 다시 한다; 별도 래치는 없다).
    """

    def __init__(self, log_path: str):
        self.p = Panda()
        self.t0 = time.time()
        self.controlling = False
        self.log = open(log_path, "w")
        self.log_path = log_path
        self._io = threading.Lock()        # libusb 접근 직렬화(heartbeat ↔ CAN)
        self._hb_stop = threading.Event()
        self._hb_th = None
        self._hb_fail = 0

    # ---- heartbeat 전용 스레드 ----
    def _hb_loop(self):
        while not self._hb_stop.is_set():
            try:
                with self._io:
                    self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xf3, 0, 0, b"")
            except Exception:
                self._hb_fail += 1
            self._hb_stop.wait(HEARTBEAT_S)

    def assert_authority(self, tag: str = "") -> bool:
        """제어권이 살아 있는지 확인한다. 죽었으면 경고하고 False.

        판다 fail-safe 가 걸리면 `safety_mode` 가 0(SILENT)으로 되돌아간다.
        이 확인 없이 판독하면 Seer 트래픽을 자기 응답으로 오인한다.
        """
        try:
            with self._io:
                h = self.p.health()
        except Exception as exc:
            print(f"  ⚠ health 조회 실패{(' @'+tag) if tag else ''}: {exc}", flush=True)
            return False
        alive = (h.get("safety_mode") == SEER_GATE)
        if not alive:
            print(f"  ⚠⚠ 제어권 상실 감지{(' @'+tag) if tag else ''} — "
                  f"safety_mode={h.get('safety_mode')} (기대 {SEER_GATE}), "
                  f"heartbeat_lost={h.get('heartbeat_lost')}. "
                  f"이후 판독은 신뢰할 수 없다(Seer 응답 오인 위험).", flush=True)
        return alive

    def drain(self):
        """bus2 트래픽을 로그로 흘린다(수동 청취 기록)."""
        with self._io:
            frames = self.p.can_recv()
        for addr, _, dat, bus in frames:
            if bus != MOTOR_BUS or not dat:
                continue
            self.log.write(json.dumps({"t": round(time.time() - self.t0, 4),
                                       "id": addr, "d": bytes(dat).hex()}) + "\n")

    def sdo_read(self, node: int, index: int, sub: int = 0, timeout: float = 0.5):
        """SDO 읽기 1건 → 값(int) 또는 None. 검증된 구현(orin_read_homing_params.py:121) 재사용."""
        req = bytes([0x40, index & 0xFF, (index >> 8) & 0xFF, sub, 0, 0, 0, 0])
        with self._io:
            # ★ 요청 직전 수신 버퍼를 비운다 (2026-08-03 정정).
            #   제어권 보유 중에도 Seer 의 폴이 bus2 로 전달되므로(cmd==0x40 → bus_fwd=2)
            #   같은 노드·같은 객체의 응답이 **두 벌** 흐른다. 비우지 않으면 이전 응답을
            #   내 요청의 답으로 오인해 간헐적으로 엉뚱한 값을 잡는다(실측 확인).
            for _a, _t, _d, _b in self.p.can_recv():
                if _b == MOTOR_BUS and _d:
                    self.log.write(json.dumps({"t": round(time.time() - self.t0, 4),
                                               "id": _a, "d": bytes(_d).hex()}) + "\n")
            self.p.can_send(0x600 + node, req, MOTOR_BUS)
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._io:
                frames = self.p.can_recv()
            for addr, _, dat, bus in frames:
                if bus != MOTOR_BUS or not dat:
                    continue
                d = bytes(dat)
                self.log.write(json.dumps({"t": round(time.time() - self.t0, 4),
                                           "id": addr, "d": d.hex()}) + "\n")
                if addr != (0x580 + node) or len(d) < 8:
                    continue
                if (d[1] | (d[2] << 8)) != index or d[3] != sub:
                    continue
                if d[0] in RD_RESP:
                    return s32(d[4:8])
                if d[0] == 0x80:
                    return None
            time.sleep(0.002)
        return None

    def sdo_write(self, node: int, index: int, sub: int, value: int, size: int):
        cmd = {1: 0x2F, 2: 0x2B, 4: 0x23}[size]
        v = value & 0xFFFFFFFF
        req = bytes([cmd, index & 0xFF, (index >> 8) & 0xFF, sub,
                     v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF])
        with self._io:
            self.p.can_send(0x600 + node, req, MOTOR_BUS)

    def pos_median(self, node: int, n: int = 5) -> int | None:
        """0x6064 를 n회 읽어 중앙값. 단발 판독 흔들림 제거."""
        vals = [v for v in (self.sdo_read(node, OBJ_POS) for _ in range(n)) if v is not None]
        return int(statistics.median(vals)) if vals else None

    def homing_state(self):
        with self._io:
            r = self.p._handle.controlRead(Panda.REQUEST_IN, 0xeb, 0, 0, 8)
        return {"state": r[0], "done_mask": r[1], "seen_active": r[2],
                "elapsed_s": r[3] | (r[4] << 8), "di3": r[5], "di4": r[6],
                "reached_mask": r[7]}

    # ---- 제어권 ----
    def take(self, settle: float = 1.0):
        print(">>> 제어권 획득 (safety=30 · auth=PC · intercept)", flush=True)
        with self._io:
            self.p.set_safety_mode(SEER_GATE, 0)
            self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 1, 0, b"")
            self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")
        self.controlling = True
        # ★ heartbeat 전용 스레드 — gui.py:819/:1023-1025 패턴. 작업 유무와 무관하게 계속 뛴다.
        self._hb_stop.clear()
        self._hb_th = threading.Thread(target=self._hb_loop, name="hb", daemon=True)
        self._hb_th.start()
        time.sleep(settle)
        self.drain()
        if not self.assert_authority("take"):
            print("  ⚠ 제어권 획득 직후 확인에 실패했다 — 계속하면 판독이 오염된다.", flush=True)

    def release(self):
        if not self.controlling:
            return
        self._hb_stop.set()
        if self._hb_th is not None:
            self._hb_th.join(timeout=1.0)
        if self._hb_fail:
            print(f"[release] ⚠ heartbeat 송신 실패 {self._hb_fail}건 — 구간 판독 신뢰도 확인 필요",
                  flush=True)
        try:
            with self._io:
                self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
                self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
                self.p.set_safety_mode(0, 0)
            print("[release] 제어권 반환 + passthrough 복귀", flush=True)
            print("⚠ Seer 가 재호밍을 개시할 수 있습니다 — 조향축 스윙 주의", flush=True)
        except Exception as exc:
            print(f"[release] ⚠ 실패: {exc} — heartbeat 소실로 fail-safe 복귀 예정", flush=True)
        finally:
            self.controlling = False

    def cancel_homing(self):
        try:
            with self._io:
                self.p._handle.controlRead(Panda.REQUEST_IN, 0xea, 0, 0, 1)
            print("[cancel] 0xea 취소 전송 (0x60FB:04=0)", flush=True)
        except Exception as exc:
            print(f"[cancel] ⚠ 실패: {exc}", flush=True)

    def close(self):
        try:
            self.log.close()
        except Exception:
            pass
        try:
            self.p.close()
        except Exception:
            pass


def snapshot(rig: Rig, tag: str) -> dict:
    """조향 2축의 위치·상태워드·DI 를 한 번에 채집.

    ⚠ 채집 전 **제어권 생존을 확인**한다. 제어권이 풀린 상태에서 판독하면
    Seer 폴링 응답을 자기 응답으로 오인한다(2026-08-03 적대적 검증 F2).
    """
    s = {"tag": tag, "t": round(time.time() - rig.t0, 3),
         "authority_ok": rig.assert_authority(tag)}
    for n in STEER_NODES:
        s[f"pos{n}"] = rig.pos_median(n)
        sw = rig.sdo_read(n, OBJ_STATUS)
        s[f"sw{n}"] = sw
        s[f"bit15_{n}"] = None if sw is None else (sw >> 15) & 1
        di = rig.sdo_read(n, OBJ_DIN, 1)
        s[f"di{n}"] = di
        s[f"nlim{n}"] = None if di is None else (di >> 3) & 1
    return s


def fmt_snap(s: dict) -> str:
    out = []
    for n in STEER_NODES:
        p = s.get(f"pos{n}")
        d = f"{(p - HOME_0DEG[n]) / CPD:+7.3f}°" if p is not None else "   ?    "
        out.append(f"node{n}={p if p is not None else '?'} ({d} vs 0°) "
                   f"bit15={s.get(f'bit15_{n}')} −Lim={s.get(f'nlim{n}')}")
    return " | ".join(out)


def run_homing(rig: Rig, speed: int, timeout: float) -> dict:
    """호밍 1회. FSM 을 0xeb 로 추적하고 종료 상태를 반환."""
    with rig._io:
        ok = rig.p._handle.controlRead(Panda.REQUEST_IN, 0xea, 1, speed, 1)
    if ok[0] != 1:
        return {"accepted": False, "final_state": None}
    print(f"    0xea 수락 (speed={speed})", flush=True)

    last = None
    t_start = time.time()
    deadline = t_start + timeout
    transitions = []
    while time.time() < deadline:
        rig.drain()
        st = rig.homing_state()
        if st["state"] != last:
            el = time.time() - t_start
            transitions.append({"t": round(el, 2), **st})
            print(f"    [{el:6.2f}s] state={st['state']} {STATE.get(st['state'], '?'):<14s} "
                  f"원점={st['done_mask']:#04x} 도달={st['reached_mask']:#04x} "
                  f"DI3={st['di3']:#04x} DI4={st['di4']:#04x}", flush=True)
            last = st["state"]
        if st["state"] in TERMINAL and st["state"] != 0:
            return {"accepted": True, "final_state": st["state"],
                    "elapsed": round(time.time() - t_start, 2), "transitions": transitions}
        time.sleep(0.1)

    print("    ⚠ 스크립트 타임아웃 — 취소 전송", flush=True)
    rig.cancel_homing()
    return {"accepted": True, "final_state": -1,
            "elapsed": round(time.time() - t_start, 2), "transitions": transitions}


def do_hysteresis(rig: Rig, delta_deg: float, settle: float) -> list:
    """같은 목표에 +방향/−방향으로 접근시켜 정착 차를 측정한다.

    기준 목표 = 펌웨어 GOZERO 목표(호밍 직후 축이 있는 지점). 거기서 ±delta 로 벗어났다가
    같은 목표로 되돌아오는 왕복을 각 방향 1회씩 수행한다.
    """
    d = int(delta_deg * CPD)
    results = []
    for sign, name in ((+1, "plus"), (-1, "minus")):
        print(f"\n  [M3] {name} 방향 접근 (Δ={sign * delta_deg:+.1f}°)", flush=True)
        # 1) 목표에서 sign*delta 만큼 벗어난다
        for n in STEER_NODES:
            rig.sdo_write(n, OBJ_TARGET, 0, FW_GOZERO[n] + sign * d, 4)
            rig.sdo_write(n, OBJ_CTRL, 0, CW_SETPOINT, 2)
        time.sleep(settle)
        rig.drain()
        away = snapshot(rig, f"hyst_{name}_away")
        print(f"    이탈: {fmt_snap(away)}", flush=True)

        # 2) 같은 목표로 되돌아온다 — 접근 방향이 sign 의 반대가 된다
        for n in STEER_NODES:
            rig.sdo_write(n, OBJ_TARGET, 0, FW_GOZERO[n], 4)
            rig.sdo_write(n, OBJ_CTRL, 0, CW_SETPOINT, 2)
        time.sleep(settle)
        rig.drain()
        back = snapshot(rig, f"hyst_{name}_back")
        print(f"    복귀: {fmt_snap(back)}", flush=True)
        results.append({"approach": name, "away": away, "back": back})
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=0, help="호밍 반복 횟수 (M1/M2)")
    ap.add_argument("--hysteresis", action="store_true", help="히스테리시스 측정 추가 (M3)")
    ap.add_argument("--delta-deg", type=float, default=5.0, help="M3 이탈 각도")
    ap.add_argument("--speed", type=int, default=2500, help="호밍 속도 0.1r/min (100~3000)")
    ap.add_argument("--timeout", type=float, default=180.0, help="회당 호밍 대기 상한 초")
    ap.add_argument("--settle", type=float, default=3.0, help="정착 대기 초")
    ap.add_argument("--gap", type=float, default=5.0, help="회차 사이 대기 초")
    ap.add_argument("--dry-run", action="store_true", help="제어권만 잡고 판독 — 호밍 미개시")
    ap.add_argument("--out", default=None, help="캡처 jsonl 경로")
    args = ap.parse_args()

    if not args.dry_run and args.repeat <= 0 and not args.hysteresis:
        ap.error("--repeat N 또는 --hysteresis 또는 --dry-run 중 하나는 필요합니다")
    if args.speed != 0 and not (100 <= args.speed <= 3000):
        ap.error("--speed 는 0(기본 2500) 또는 100~3000 이어야 합니다 (펌웨어가 거부합니다)")

    stamp = time.strftime("%y%m%d_%H%M%S")
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    out = args.out or os.path.join(repo, "Log", f"home_experiment_{stamp}.jsonl")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    rig = Rig(out)
    print(f"판다 연결: fw={rig.p.get_version()}", flush=True)
    h = rig.p.health()
    print(f"health: safety_mode={h.get('safety_mode')} heartbeat_lost={h.get('heartbeat_lost')} "
          f"uptime={h.get('uptime')}s", flush=True)
    print(f"캡처: {out}", flush=True)

    records = {"meta": {"stamp": stamp, "fw": rig.p.get_version(), "speed": args.speed,
                        "repeat": args.repeat, "hysteresis": args.hysteresis,
                        "home_0deg": HOME_0DEG, "fw_gozero": FW_GOZERO},
               "runs": [], "hysteresis": []}

    try:
        rig.take()

        base = snapshot(rig, "baseline")
        print(f"\n기준선: {fmt_snap(base)}", flush=True)
        records["baseline"] = base

        if args.dry_run:
            st = rig.homing_state()
            print(f"\nFSM: state={st['state']} ({STATE.get(st['state'], '?')})", flush=True)
            print("--dry-run — 호밍을 개시하지 않고 종료합니다.", flush=True)
        else:
            for i in range(1, args.repeat + 1):
                print(f"\n=== 호밍 {i}/{args.repeat} ===", flush=True)
                pre = snapshot(rig, f"run{i}_pre")
                print(f"  전: {fmt_snap(pre)}", flush=True)

                res = run_homing(rig, args.speed, args.timeout)
                if not res["accepted"]:
                    print("  ⚠ 0xea 거부 — 전제조건 확인(권한/모드/terminal/속도). 중단.", flush=True)
                    break

                time.sleep(args.settle)
                rig.drain()
                post = snapshot(rig, f"run{i}_post")
                print(f"  후: {fmt_snap(post)}", flush=True)
                print(f"  종료상태={res['final_state']} "
                      f"({STATE.get(res['final_state'], '타임아웃')}) {res.get('elapsed')}s",
                      flush=True)

                records["runs"].append({"i": i, "pre": pre, "post": post, **res})
                if i < args.repeat:
                    time.sleep(args.gap)

            if args.hysteresis:
                print("\n=== M3 히스테리시스 ===", flush=True)
                records["hysteresis"] = do_hysteresis(rig, args.delta_deg, args.settle)

    except KeyboardInterrupt:
        print("\n⚠ 사용자 중단 — 호밍 취소 후 제어권 반환", flush=True)
        rig.cancel_homing()
    finally:
        rig.release()
        summary_path = out.replace(".jsonl", "_summary.json")
        with open(summary_path, "w") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        rig.close()
        print(f"\n요약: {summary_path}", flush=True)
        report(records)


def report(rec: dict):
    runs = [r for r in rec["runs"] if r.get("final_state") == 5]
    if not runs:
        print("\n(DONE 도달 회차 없음 — 통계 생략)", flush=True)
        return
    print("\n" + "=" * 78, flush=True)
    print(f"M1/M2 결과 — DONE {len(runs)}/{len(rec['runs'])} 회", flush=True)
    print("=" * 78, flush=True)
    for n in STEER_NODES:
        vals = [r["post"][f"pos{n}"] for r in runs if r["post"].get(f"pos{n}") is not None]
        if not vals:
            print(f"  node{n}: 판독 실패", flush=True)
            continue
        med = statistics.median(vals)
        sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        print(f"\n  node{n} 정착값 {len(vals)}개: {vals}", flush=True)
        print(f"    중앙값     : {med:.0f}  (분산 σ={sd:.1f} counts = {sd / CPD:.4f}°)", flush=True)
        print(f"    실측 0° 대비: {med - HOME_0DEG[n]:+.0f} counts "
              f"= {(med - HOME_0DEG[n]) / CPD:+.4f}°   [M2]", flush=True)
        print(f"    FW GOZERO 대비: {med - FW_GOZERO[n]:+.0f} counts "
              f"= {(med - FW_GOZERO[n]) / CPD:+.4f}°", flush=True)

    for hy in rec.get("hysteresis", []):
        print(f"\n  M3 {hy['approach']} 방향 복귀:", flush=True)
        for n in STEER_NODES:
            b = hy["back"].get(f"pos{n}")
            if b is not None:
                print(f"    node{n}: {b}  (FW GOZERO 대비 {b - FW_GOZERO[n]:+.0f} counts)",
                      flush=True)
    hys = rec.get("hysteresis", [])
    if len(hys) == 2:
        print("\n  M3 히스테리시스(= +접근 − −접근):", flush=True)
        for n in STEER_NODES:
            a = hys[0]["back"].get(f"pos{n}")
            b = hys[1]["back"].get(f"pos{n}")
            if a is not None and b is not None:
                print(f"    node{n}: {a - b:+.0f} counts = {(a - b) / CPD:+.4f}°", flush=True)


if __name__ == "__main__":
    main()
