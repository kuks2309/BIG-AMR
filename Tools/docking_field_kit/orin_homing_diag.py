#!/usr/bin/env python3
"""호밍 실패 원인 판독 — 드라이브가 왜 무동작으로 끝났는지 벤더 레지스터로 확인한다.

## 무엇을 판정하려는가

2026-08-03 09:58 실기 호밍이 **ERR_TIMEOUT(120 s)** 으로 끝났고 축이 전혀 움직이지 않았다
(`docs/homing/2026-08-03-can-relay-homing-assets.md` §8). 내 최초 진단
「`Switch on disabled` 라서 못 움직인다」는 **적대적 검증에서 반증**됐다(§11-2) —
2026-07-27 성공 로그가 **같은 statusword·같은 프레임 시퀀스**로 호밍에 성공했기 때문이다.

성립하는 대안 가설(Handbook §4.6 원문):
    *"When the motor is already in the resetting position, the resetting is triggered again,
      and the driver **directly outputs the resetting end signal**."*
⇒ 드라이브가 자신을 **이미 원점**으로 판단 → 무동작 즉시 종료 → `0x6041` bit15 **하강 에지 미발생**
  → 펌웨어 에지 검출기(`safety_seer_gate.h:391-402`)가 영구 대기 → 호스트 120 s 타임아웃.

**이 가설을 직접 검증하는 레지스터가 존재한다.**

## ★ 인덱스 정정 — 벤더 객체는 `0x20F1~0x20F5` 다

적대적 검증 보고가 인용한 `0x448E`/`0x4490`/`0x4491` 은 **Handbook 내부 레지스터 주소**이지
CANopen 인덱스가 아니다. EDS(Electronic Data Sheet) 실물에서 이름으로 역인덱싱한 결과:

    0x20F1  SelfSofRst.uwRstMode       ← 호밍 방식(벤더 미러)
    0x20F2  SelfSofRst.uwRstStart
    0x20F3  SelfSofRst.uwRstEnd        ← **호밍 종료 신호** (가설의 핵심)
    0x20F4  SelfSofRst.uwRstErr        ← **호밍 오류 코드**
    0x20F5  SelfSofRst.uwRstStartSpd
    0x60FBsub4  RstStart               ← 우리가 개시에 쓰는 것

근거: `References/Tongyi-Motor-Controller/canopen/EDS_extracted/Servo_Driver_20200805.eds`
(`ParameterName=` 를 섹션 헤더로 역추적). ⚠ 이 인덱스로 읽어 ABORT 가 나면 그것도 결과다 —
「Handbook 주소 ≠ CANopen 인덱스」가 확인되는 셈이므로 그대로 보고한다.

또 하나: EDS 의 `[6098] Homing_method` **DefaultValue = 0x0**(= homing 비활성)이다.
펌웨어는 `0x6098` 을 **쓰지도 읽지도 않으므로**(§11-3 F4) 드라이브 저장값이 그대로 쓰인다.
저장값이 0 이면 **호밍이 애초에 비활성**이고 그것만으로 실패가 설명된다.

## ⚠ 안전 — 모터를 움직이는 프레임은 한 개도 보내지 않는다

· SDO(Service Data Object) **읽기(`0x40`)만** 송신한다. 쓰기(`0x2F`/`0x2B`/`0x23`) 0건.
· 특히 `0x6098`·`0x20F1` 에 **쓰지 않는다** — 드라이브 상주 설정이라 되돌리기 어렵고,
  `0x6098=35` 는 RstMode 를 0 으로 리셋해 Seer 주도 호밍을 죽인다(2026-08-01 실기 기각).
· 제어권은 획득한다 — Seer 가 폴링 중인 노드에 SDO 를 끼워 넣으면 in-flight 트랜잭션이 깨져
  Seer 가 노드 상실(52111)로 판단할 수 있다. intercept 상태면 판다가 Seer 에게 캐시로 대신
  답하므로 노드를 잃지 않는다(`orin_read_homing_params.py:35-40` 과 같은 근거).
· ⚠ **제어권 반환 시 Seer 가 재호밍을 걸 수 있다** — 접지 상태면 조향이 움직인다.
· heartbeat 는 `Rig` 전용 스레드가 담당(GUI `gui.py:819` 패턴).

사용:
  python3 orin_homing_diag.py            # 조향 2축 판독
  python3 orin_homing_diag.py --all      # 구동축까지 4축
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from orin_home_experiment import CPD, HOME_0DEG, Rig, STEER_NODES  # noqa: E402

# (index, sub, 이름, 해석기키)
OBJECTS = [
    (0x6098, 0, "0x6098 Homing_method",        "method"),
    (0x20F1, 0, "0x20F1 uwRstMode",            "method"),
    (0x20F2, 0, "0x20F2 uwRstStart",           "raw"),
    (0x20F3, 0, "0x20F3 uwRstEnd",             "rstend"),
    (0x20F4, 0, "0x20F4 uwRstErr",             "rsterr"),
    (0x20F5, 0, "0x20F5 uwRstStartSpd",        "raw"),
    (0x6099, 0, "0x6099 Homing_speed",         "raw"),
    (0x607C, 0, "0x607C Homing_offset",        "raw"),
    (0x609A, 0, "0x609A Homing_accel",         "raw"),
    (0x6041, 0, "0x6041 Statusword",           "status"),
    (0x6000, 1, "0x6000:01 Digital_input",     "din"),
    (0x6064, 0, "0x6064 Position_actual",      "pos"),
    (0x60FB, 2, "0x60FB:02 Turn_value",        "raw"),
    (0x60FB, 3, "0x60FB:03 slAbsAngle",        "raw"),
    (0x60FB, 4, "0x60FB:04 RstStart",          "rststart"),
    (0x6060, 0, "0x6060 Modes_of_operation",   "mode"),
    (0x6061, 0, "0x6061 Modes_display",        "mode"),
    (0x603F, 0, "0x603F Error_code",           "hex"),
]

METHOD = {0: "0 = **호밍 비활성**", 1: "1 = Home 1 (음의 리밋 트리거)",
          2: "2 = Home 2 (양의 리밋)", 35: "35 = 현위치 재영점"}
MODE = {1: "1 = PP(Profile Position)", 3: "3 = PV(Profile Velocity)",
        6: "6 = Homing", 8: "8 = CSP"}


def describe(kind: str, v: int, node: int) -> str:
    if kind == "method":
        return METHOD.get(v, f"{v} (Home {v})" if 1 <= v <= 37 else f"{v} — 정의 밖")
    if kind == "mode":
        return MODE.get(v, str(v))
    if kind == "status":
        sw = v & 0xFFFF
        st = sw & 0x6F
        name = {0x40: "Switch on disabled", 0x21: "Ready to switch on", 0x23: "Switched on",
                0x27: "Operation enabled", 0x07: "Quick stop active", 0x0F: "Fault reaction",
                0x08: "Fault"}.get(st, "?")
        return (f"0x{sw:04x}  bit15(Home attend)={(sw >> 15) & 1} "
                f"bit10(Target reached)={(sw >> 10) & 1} → {name}")
    if kind == "din":
        return (f"0x{v:02x}  ServoEnable={v & 1} +Limit={(v >> 1) & 1} "
                f"Alarm={(v >> 2) & 1} −Limit={(v >> 3) & 1}")
    if kind == "pos":
        home = HOME_0DEG.get(node)
        return f"{v:,}" + (f"  (홈 대비 {(v - home) / CPD:+.4f}°)" if home else "")
    if kind == "rstend":
        return f"{v}  " + ("← **호밍 종료 신호 서 있음**" if v else "(종료 신호 없음)")
    if kind == "rsterr":
        return f"{v}  " + ("← **호밍 오류 있음**" if v else "(오류 없음)")
    if kind == "rststart":
        return f"{v}  " + ("← RstStart 가 **1 로 남아 있다**(에지 재발생 불가)" if v else "(0 = 정상)")
    if kind == "hex":
        return f"0x{v:04x}" + ("  ← **오류 코드 있음**" if v else "  (오류 없음)")
    return f"{v:,}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="구동축(1·2)까지 판독")
    ap.add_argument("--settle", type=float, default=1.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    nodes = (1, 2, 3, 4) if args.all else STEER_NODES
    repo = os.path.abspath(os.path.join(HERE, "..", ".."))
    stamp = time.strftime("%y%m%d_%H%M%S")
    out = args.out or os.path.join(repo, "Log", f"homing_diag_{stamp}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    rig = Rig(out.replace(".json", "_can.jsonl"))
    result = {"stamp": stamp, "fw": rig.p.get_version(), "nodes": {}}
    try:
        rig.take(args.settle)
        print(f"판다 fw={result['fw']}\n", flush=True)
        for node in nodes:
            role = "조향" if node in STEER_NODES else "구동"
            print(f"── node{node} ({role}) " + "─" * 50, flush=True)
            rig.assert_authority(f"node{node}")
            vals = {}
            for idx, sub, name, kind in OBJECTS:
                v = rig.sdo_read(node, idx, sub)
                key = f"{idx:04X}.{sub}"
                vals[key] = v
                if v is None:
                    print(f"  {name:<32s} : 무응답/ABORT", flush=True)
                else:
                    print(f"  {name:<32s} : {describe(kind, v, node)}", flush=True)
            result["nodes"][node] = vals
            print(flush=True)
    finally:
        rig.release()
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
        rig.close()
        print(f"산출: {out}", flush=True)

    # ── 판정 ──
    print("\n" + "=" * 78, flush=True)
    print("판정", flush=True)
    print("=" * 78, flush=True)
    for node in nodes:
        if node not in STEER_NODES:
            continue
        v = result["nodes"].get(node, {})
        m6098, m20f1 = v.get("6098.0"), v.get("20F1.0")
        rstend, rsterr = v.get("20F3.0"), v.get("20F4.0")
        rststart = v.get("60FB.4")
        sw = v.get("6041.0")
        print(f"\n  node{node}:", flush=True)
        if m6098 == 0 or m20f1 == 0:
            print("    ★ **호밍 방식이 0(비활성)이다 — 이것만으로 호밍 실패가 설명된다.**", flush=True)
        elif m6098 is not None:
            print(f"    호밍 방식 = {m6098} — 비활성은 아니다.", flush=True)
        if m6098 is not None and m20f1 is not None and m6098 != m20f1:
            print(f"    ⚠ `0x6098`({m6098}) 와 `0x20F1`({m20f1}) 가 다르다 — 어느 쪽이 유효한지 미판정.",
                  flush=True)
        if rstend:
            print("    ★ **RstEnd 가 서 있다** — 드라이브가 호밍을 「이미 끝났다」고 보고 있다."
                  " 가설(무동작 즉시 종료)과 정합.", flush=True)
        if rsterr:
            print(f"    ★ **RstErr = {rsterr}** — 드라이브가 호밍 오류를 들고 있다.", flush=True)
        if rststart:
            print("    ★ **RstStart 가 1 로 남아 있다** — 다음 개시에서 0→1 에지가 생기지 않는다"
                  "(적대적 검증 H11 가설).", flush=True)
        if sw is not None and ((sw >> 15) & 1):
            print("    bit15(Home attend)=1 — 드라이브는 「원점 확립됨」 상태다."
                  " 이 상태에서 재개시하면 하강 에지가 안 나올 수 있다.", flush=True)
    print("\n  ⚠ 위 판정은 **읽은 값의 해석**이다. 실제 거동 확정에는 재호밍 1회 관측이 필요하다.",
          flush=True)


if __name__ == "__main__":
    main()
