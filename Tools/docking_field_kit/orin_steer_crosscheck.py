#!/usr/bin/env python3
"""조향 절대위치 교차검증 — CAN 0x6064 ↔ Seer API 1040 동시 기록.

## 무엇을 판정하려는가

1. **절대 엔코더 재현성** — 전원을 껐다 켜도 조향 엔코더가 같은 값을 주는가.
   `can_relay` 의 homing method 35(상류식)가 이 전제 위에 있다
   (`docs/adr/2026-08-01-can-relay-home-calibration-method35.md`).
2. **CAN ↔ Seer 정합** — debt-007 이 남긴 미판정 관측의 판정.
   registry 원문: "Seer 1040 position≈0 · 육안 직진인데 **판다 read 0x6064 는 ≈0**
   … 같은 시점 **구동 노드는 판다 read 와 Seer 1040 이 절댓값 일치**했다(**조향만 어긋남**)".
   반면 `Log/*.jsonl` 5종은 조향 0x6064 를 일관되게 7.87M 로 보여 준다. 둘 다 맞을 수는 없다.
3. **`steer_home_offset` 실측** — Seer 가 물리각(rad)을 주므로, 호밍 없이
   "0° 에 해당하는 counts" 를 역산할 수 있다. 3톤 차체를 잭업하지 않아도 된다.

## ⚠ 제어권을 잡으면 이 측정은 **무의미해진다** (설계의 핵심)

펌웨어가 제어권 획득 시 자동으로 emulate 로 들어간다:

    bool emulate = cover || pc_authority;        // safety_seer_gate.h:164

emulate 중에는 모터의 SDO 응답(`0x581~0x584`)과 guard 가 **Seer 로 전달되지 않고**
(`bus_fwd = -1`, `:188-190`), 판다 캐시가 대신 답한다(`seer_cache_reply` `:167-172`,
guard 위조 `:176-181`). 전환 순간도 `cover` 가 덮는다.

⇒ 제어권을 쥔 채 Seer 1040 을 읽으면 **모터 실측이 아니라 판다 캐시**를 보는 것이고,
   CAN 과 Seer 가 일치해도 "같은 출처를 두 번 읽은 것"일 뿐 교차검증이 아니다.
   **반드시 제어권 없이(SILENT passthrough) 측정해야 두 경로가 독립이다.**

> 이 관점은 debt-007 의 미판정 관측을 재검토하게 만든다 — 그 관측 시점에 판다가
> 제어권을 쥐고 있었다면 "Seer 1040 ≈ 0" 은 독립 관측이 아니었을 수 있다.
> 본 도구는 그 조건을 배제한 상태에서만 기록한다.

## 안전 — 아무것도 내보내지 않는다

- 판다는 **SAFETY_SILENT** 로 둔다. 펌웨어 `board/main.c` 의 `case SAFETY_SILENT` 가
  `set_intercept_relay(false)` 와 `can_silent = ALL_CAN_SILENT` 를 건다.
  `false` 는 intercept 해제(= passthrough)이므로 **Seer↔모터 직결이 유지**된다
  (USB 계약도 같다 — `0xe8` wValue 0=passthrough / 1=intercept).
  ⚠ 범위 주의: "송신이 물리적으로 불가능하다"고까지는 말하지 않는다. 확인한 것은
  `main.c:85` 가 `can_silent` 플래그를 세우는 것까지다.
  본 스크립트가 송신 API 를 **호출하지 않는다**는 것은 별도 근거이며, 아래 명령으로
  재현한다(문자열 grep 은 이 주석 자신을 잡으므로 **구문 트리**로 센다 — 0건):

      python3 - <<'X'
      import ast
      t = ast.parse(open("orin_steer_crosscheck.py").read())
      tx = {"can_send", "can_send_many", "controlWrite", "sdo_write", "send"}
      hits = [n.lineno for n in ast.walk(t) if isinstance(n, ast.Call)
              and (getattr(n.func, "attr", None) or getattr(n.func, "id", None)) in tx]
      print("송신 호출:", len(hits), hits)
      X
- SDO 읽기 요청도 보내지 않는다. Seer 가 이미 0x6064 를 ~100 Hz 로 폴하므로
  **그 응답을 엿듣기만** 한다.
- Seer 는 status 포트(19204) API 만 호출한다 — 제어권 불요, 읽기 전용.
- 이미 다른 도구가 제어권(intercept)을 쥐고 있으면 **실행을 거부**한다.

## 사용

    # ① 전원 차단 전
    python3 orin_steer_crosscheck.py --secs 30 --tag before
    # ② 전원 차단 → 재투입 → Seer 기동 완료 대기
    # ③ 전원 재투입 후
    python3 orin_steer_crosscheck.py --secs 30 --tag after
    # ④ 비교
    python3 orin_steer_crosscheck.py --compare Log/steer_xcheck_before.jsonl \
                                               Log/steer_xcheck_after.jsonl

산출물: `Log/steer_xcheck_<tag>.jsonl` (레코드마다 `t`·`src`·`node`·`value`)
"""
import argparse
import json
import math
import os
import statistics
import sys
import threading
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SEER_GUI = "/home/nvidia/T-Robot_seer_gui"
SEER_IP = "192.168.44.82"

MOTOR_BUS = 2               # 판다 bus 2 = 드라이브 측
STEER_NODES = (3, 4)
OBJ_POSITION_ACTUAL = 0x6064
COUNTS_PER_DEG = 57344.0    # 실측 근거: 홈↔90° Δ = 5,160,960 counts = 90.00°


# ── 판다 수동청취 ─────────────────────────────────────────────────────────
def _panda_class():
    for root, mod in ((os.path.join(REPO, "Tools", "docking_field_kit"), "panda"),
                      (os.path.join(REPO, "Tools", "Can_Relay", "panda-firmware"), "python")):
        if os.path.isdir(os.path.join(root, mod)):
            if root not in sys.path:
                sys.path.insert(0, root)
            try:
                return __import__(mod, fromlist=["Panda"]).Panda
            except Exception:
                continue
    raise RuntimeError("panda 라이브러리를 찾지 못했다")


def can_listener(stop, sink, log):
    """0x581~0x584 의 0x6064 read reply 만 골라 기록한다. **송신 0건.**"""
    Panda = _panda_class()
    p = Panda()
    health = p.health()
    log(f"판다 health: safety_mode={health.get('safety_mode')} "
        f"controls_allowed={health.get('controls_allowed')}")
    # SEER_GATE(30) 이면 다른 도구가 제어권을 쥐고 있을 수 있다. 그 상태에서는
    # emulate 가 켜져 Seer 가 **판다 캐시**를 보므로 교차검증이 성립하지 않는다.
    # 게다가 남의 제어 상태를 흔드는 것이기도 하다 — 두 이유 모두로 중단한다.
    if health.get("safety_mode") == 30:
        log("⚠ 판다가 SEER_GATE(30) — 제어권 보유 가능성. emulate 중이면 Seer 가 캐시를")
        log("   보므로 교차검증이 무의미하다. 제어권을 반환한 뒤 다시 실행할 것. 중단.")
        stop.set()
        return
    p.set_safety_mode(0, 0)          # SILENT = 송신 불가 + 릴레이 passthrough 유지
    for bus in (0, MOTOR_BUS):
        p.set_can_speed_kbps(bus, 250)
        p.set_can_enable(bus, True)
    log("판다 SILENT 탭 시작 — 송신하지 않는다")
    t0 = time.monotonic()
    while not stop.is_set():
        try:
            for addr, _ts, dat, bus in p.can_recv():
                if bus != MOTOR_BUS or not (0x581 <= addr <= 0x584):
                    continue
                b = bytes(dat)
                if len(b) < 8 or b[0] != 0x43:          # 4바이트 read reply 만
                    continue
                if (b[1] | (b[2] << 8)) != OBJ_POSITION_ACTUAL:
                    continue
                node = addr - 0x580
                if node not in STEER_NODES:
                    continue
                sink({"t": round(time.monotonic() - t0, 4), "src": "can",
                      "node": node,
                      "value": int.from_bytes(b[4:8], "little", signed=True)})
        except Exception as exc:
            log(f"CAN 청취 오류: {type(exc).__name__}: {exc}")
            break
        time.sleep(0.01)
    try:
        p.close()
    except Exception:
        pass


# ── Seer 폴링 ─────────────────────────────────────────────────────────────
def seer_poller(stop, sink, log, ip):
    """Seer 조향각 2채널을 동시에 기록한다. 읽기 전용(status 포트 19204).

    ## 두 채널을 함께 받는 이유 (2026-08-03 실측)

    - **1040 `motor_info.position`** (`src="seer"`) — **`0x6064` 의 아핀 변환이다.**
      30 s 동시 샘플링에서 CAN 의 6-counts 디더를 **정확히 6.0000 counts 간격**으로 추종했다.
      ⇒ 이 채널로는 CAN 과 교차검증이 성립하지 않는다(같은 데이터를 두 번 읽는 것).
        `0° = CAN + Seer°×57344` 는 항등식이 되어 자세와 무관하게 Seer 영점 상수를 돌려준다.

    - **1005 `steer_angles`** (`src="seer1005"`) — **다른 채널이다.**
      같은 시각 1040 이 node4 +0.000605°(≈35 counts)를 보고할 때 1005 는 **정확히 0.0** 이었고,
      102 샘플 전부 단일값이라 6-counts 디더를 **전혀 따라가지 않았다.**
      벤더 정의는 "The **current** steering angle of the multi-steering wheel robot, …
      sorted according to the order in the model file, unit: rad"
      [references/seer/robokit-api/robot-status-api/005-query-robot-speed.md:40].
      ⇒ 배열 순서는 모델 파일 순서 = 듀얼이면 `[front, rear]`.

    ## ⚠ 1005 에 대해 아직 모르는 것 (인용 시 반드시 병기)

    - **분해능·산출 방식이 벤더 문서에 없다.** 원시 엔코더인지, 감속비 보정·융합을 거친 값인지
      미기재다. 정지 상태에서는 두 채널을 구분할 수 없으므로 **전달함수를 아직 못 구했다.**
    - 현재 말할 수 있는 하한뿐: 1040 이 35 counts 이탈을 보고하는 자세에서 1005 가 0.0 이므로,
      같은 영점·단순 반올림을 가정하면 **양자화 > 70 counts(0.0012°)**. **상한은 미지.**
    - ⇒ **조향을 실제로 움직여 1005 의 계단을 관측해야 확정된다.** 서보가 살아나면
      이 도구를 스윕 중에 돌려 세 채널(CAN·1040·1005)의 전달함수를 한 번에 얻는다.

    `r_steer_angles`(수신 지령)도 함께 기록한다 — 실측(`steer_angles`)과 지령을 가르기 위해서다.
    """
    if SEER_GUI not in sys.path:
        sys.path.insert(0, SEER_GUI)
    try:
        from seer_core.client import RobokitClient
        cli = RobokitClient(ip)
    except Exception as exc:
        log(f"Seer 연결 불가: {type(exc).__name__}: {exc} — CAN 만 기록한다")
        return
    log(f"Seer {ip} 폴링 시작 (status 1040 + 1005)")
    t0 = time.monotonic()
    warned_1005 = False
    while not stop.is_set():
        now = lambda: round(time.monotonic() - t0, 4)  # noqa: E731
        try:
            d = cli.call("status", 1040)
            for m in (d.get("motor_info") or d.get("motors") or []):
                node = m.get("can_id")
                pos = m.get("position")
                if node not in STEER_NODES or pos is None:
                    continue
                sink({"t": now(), "src": "seer",
                      "node": int(node), "value": float(pos) * 180.0 / math.pi})
        except Exception as exc:
            log(f"Seer 1040 폴링 실패: {type(exc).__name__}: {exc}")
        try:
            s = cli.call("status", 1005)
            # 모델 파일 순서 = [front, rear] → STEER_NODES 순서에 그대로 대응시킨다.
            angles = s.get("steer_angles")
            if not angles and s.get("steer") is not None:
                angles = [s["steer"]]          # 단일 조향륜 섀시
            if angles:
                for node, rad in zip(STEER_NODES, angles):
                    sink({"t": now(), "src": "seer1005",
                          "node": int(node), "value": float(rad) * 180.0 / math.pi})
            elif not warned_1005:
                log("⚠ 1005 에 steer_angles/steer 가 없다 — 조향 섀시가 아니거나 필드 미제공")
                warned_1005 = True
            cmd = s.get("r_steer_angles")
            if cmd:
                for node, rad in zip(STEER_NODES, cmd):
                    sink({"t": now(), "src": "seer1005_cmd",
                          "node": int(node), "value": float(rad) * 180.0 / math.pi})
        except Exception as exc:
            log(f"Seer 1005 폴링 실패: {type(exc).__name__}: {exc}")
        time.sleep(0.2)


# ── 집계 ──────────────────────────────────────────────────────────────────
def summarize(path):
    """{(src, node): [값…]} 로 모아 중앙값·표준편차를 낸다."""
    acc = defaultdict(list)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("src") in ("can", "seer", "seer1005", "seer1005_cmd"):
                acc[(r["src"], r["node"])].append(r["value"])
    out = {}
    for k, v in acc.items():
        out[k] = {"n": len(v), "median": statistics.median(v),
                  "stdev": statistics.pstdev(v) if len(v) > 1 else 0.0,
                  "min": min(v), "max": max(v)}
    return out


def report(path):
    s = summarize(path)
    print(f"\n━━━ {os.path.basename(path)}")
    for node in STEER_NODES:
        can, seer = s.get(("can", node)), s.get(("seer", node))
        if can:
            print(f"  node{node} CAN  n={can['n']:5d} 중앙 {can['median']:>12,.0f}c "
                  f"(σ={can['stdev']:.0f}, 폭 {can['max']-can['min']:,.0f}c)")
        if seer:
            print(f"  node{node} Seer n={seer['n']:5d} 중앙 {seer['median']:>12.3f}° "
                  f"(σ={seer['stdev']:.3f}°)")
        if can and seer:
            # 0° 에 해당하는 counts = 현재 counts **+** 현재 각도 × counts/도.
            #
            # ⚠ 부호 주의 — 처음에 `−` 로 썼고 그것이 **틀렸다**(2026-08-02 정정).
            #   Seer 각도와 CAN counts 는 **음의 상관**이다: counts 가 늘면 Seer 각도가 준다.
            #   실측 2점 회귀(2026-08-01 18:0x ↔ 2026-08-02 19:42, 하루 간격):
            #     node3  ΔCAN −2,818c ↔ ΔSeer +0.0488°  → 기울기 −1.732e-5 °/c
            #     node4  ΔCAN   +191c ↔ ΔSeer −0.0035°  → 기울기 −1.832e-5 °/c
            #   |기울기|×57,344 = 0.993 / 1.051 ≈ 1 이므로 스케일은 COUNTS_PER_DEG 로 맞고
            #   부호만 반대였다.
            #   `−` 로 역산하면 두 측정의 0° 추정이 node3 5,616c(0.098°) 어긋나는데,
            #   `+` 로 하면 20c(0.0003°) / 10c(0.0002°) 로 수렴한다 — 부호가 맞다는 증거다.
            #   ⚠ node4 의 기울기는 ΔSeer 가 0.0035° 뿐이라 **부호는 일치하나 스케일 정밀도는 낮다**.
            #
            # ⚠⚠ **범위 정정 2026-08-03 (10인 적대적 검증)** — 아래 "0° 추정"은
            #   **물리 측정이 아니라 항등식이다.** 1040 의 각도는 같은 `0x6064` 의 아핀 변환이며
            #   (30 s 동시 샘플링에서 CAN 6-counts 디더를 정확히 6.0000 counts 간격으로 추종),
            #   기울기 × COUNTS_PER_DEG = 1.0000000(7자리)이라 위 식에서 CAN 항이 소거된다:
            #       0°_est = CAN + (C₀ − CAN) = C₀   (Seer 내부 영점 상수)
            #   실제로 0.049°(2,825c) 떨어진 자세의 2026-08-02 로그도 소수 4자리까지 같은 값을 낸다.
            #   ⇒ 이 값은 **Seer 영점 상수의 대수적 복원**이지 "물리적 0° 실측"이 아니다.
            #     반복 실행이 일치하는 것도 재현성 증거가 아니라 동어반복이다.
            #     내비게이션이 Seer 좌표계를 쓰므로 이 값에 맞추는 것은 옳지만,
            #     **물리적 직진과 같은지는 非-Seer 앵커(휠 평면 직접 계측 등)로만 확정된다.**
            #   근거: docs/homing/2026-08-03-can-relay-homing-assets.md §11-1
            off = can["median"] + seer["median"] * COUNTS_PER_DEG
            print(f"       → Seer 영점 상수 {off:>12,.0f}c "
                  f"(= {can['median']:,.0f} + {seer['median']:.4f}° × {COUNTS_PER_DEG:,.0f})")
            print(f"          ⚠ 항등식이다 — 자세와 무관하게 같은 값이 나온다(물리 0° 아님)")

    # 1005 는 1040 과 다른 채널이다. 전달함수 미확정이므로 **원값만** 싣는다.
    for node in STEER_NODES:
        a = s.get(("seer1005", node))
        c = s.get(("seer1005_cmd", node))
        if a:
            print(f"  node{node} 1005 steer_angles   n={a['n']:5d} 중앙 {a['median']:>10.6f}° "
                  f"(σ={a['stdev']:.6f}°, 상이폭 {a['max']-a['min']:.6f}°)")
        if c:
            print(f"  node{node} 1005 r_steer(지령)  n={c['n']:5d} 중앙 {c['median']:>10.6f}°")
    if any(s.get(("seer1005", n)) for n in STEER_NODES):
        print("       ⚠ 1005 의 분해능·산출 방식은 벤더 문서에 없다(미확정). 정지 상태에서는")
        print("         1040 과 구분되지 않는다 — **조향을 움직여 계단을 관측해야** 전달함수가 나온다.")
    return s


def compare(a, b):
    missing = [p for p in (a, b) if not os.path.isfile(p)]
    if missing:
        print(f"⚠ 파일이 없다: {missing}\n"
              f"   --tag before / --tag after 로 각각 먼저 기록해야 한다.")
        return 2
    sa, sb = report(a), report(b)
    print("\n═══ 전원 사이클 전후 비교 ═══")
    verdict = []
    for node in STEER_NODES:
        for src, unit, tol in (("can", "c", 1000), ("seer", "°", 0.05)):
            ka, kb = sa.get((src, node)), sb.get((src, node))
            if not (ka and kb):
                print(f"  node{node} {src:<4} — 한쪽에 데이터가 없어 비교 불가")
                continue
            d = kb["median"] - ka["median"]
            ok = abs(d) <= tol
            verdict.append(ok)
            extra = f" ({d/COUNTS_PER_DEG:+.4f}°)" if src == "can" else ""
            print(f"  node{node} {src:<4} 차이 {d:>+12,.3f}{unit}{extra}  "
                  f"{'재현' if ok else '⚠ 불일치'} (허용 ±{tol}{unit})")
    if verdict:
        print(f"\n  판정: {'재현성 확인' if all(verdict) else '⚠ 재현 안 됨 — method 35 사용 금지'}")
        print("  ⚠ 이 판정은 **전원을 실제로 차단했을 때만** 유효하다. 전원을 끄지 않았다면")
        print("     '안 움직였다'는 사실만 말해 주며 재현성 근거가 아니다.")
    return 0 if all(verdict) else 2


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--secs", type=int, default=30)
    ap.add_argument("--tag", default="run")
    ap.add_argument("--ip", default=SEER_IP)
    ap.add_argument("--outdir", default=os.path.join(REPO, "Log"))
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    a = ap.parse_args()

    if a.compare:
        return compare(*a.compare)

    os.makedirs(a.outdir, exist_ok=True)
    path = os.path.join(a.outdir, f"steer_xcheck_{a.tag}.jsonl")
    lock = threading.Lock()
    fh = open(path, "w", encoding="utf-8")

    def sink(rec):
        with lock:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def log(m):
        print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

    stop = threading.Event()
    threads = [threading.Thread(target=can_listener, args=(stop, sink, log), daemon=True),
               threading.Thread(target=seer_poller, args=(stop, sink, log, a.ip), daemon=True)]
    for t in threads:
        t.start()
    log(f"{a.secs}초 기록 → {path}  (송신 0건, 읽기 전용)")
    try:
        time.sleep(a.secs)
    except KeyboardInterrupt:
        log("사용자 중단")
    stop.set()
    for t in threads:
        t.join(timeout=3)
    fh.close()
    report(path)
    log(f"완료 — {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
