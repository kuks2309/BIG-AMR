#!/usr/bin/env python3
"""이식본(ROS2 GUI) 실기 구동 검증 — 전진 1초 · 후진 1초 · IMU 로 방향 확인.

ADR `docs/adr/2026-08-03-amr-test-gui-ros2-port.md` §Verification 게이트 4-b.
지령은 **이식본 GUI 가 쓰는 바로 그 경로**(`can_relay.ui.gui_node.RelayClient`)로 나간다 —
그래야 「GUI 를 통해 실제로 움직인다」가 검증된다.

## 안전 설계 (전부 실측 사고에서 나온 것)

1. **움직이기 전에 멈출 조건을 먼저 검사한다** — 피드백 신선도 · 조향각 0° 근처 · E-stop 미인가.
   하나라도 어긋나면 지령을 한 장도 내지 않고 끝낸다.
2. **속도·시간이 코드에 박혀 있다** — 기본 50 mm/s × 1.0 s ≈ **5 cm**. 인자로 늘릴 수 있으나
   상한(80 mm/s · 1.5 s)을 넘기면 거부한다.
3. **어떤 경로로 끝나도 정지·반환이 돈다** — `finally` 에서 drive 0 → `~/stop` → `~/engage false`.
4. **조향은 건드리지 않는다.** 전진/후진은 조향 0° 에서 성립하므로(JOG 표) 조향 지령을 내지 않고,
   현재 각이 0° 근처가 아니면 아예 시작하지 않는다.

산출물: `Log/port_drive_imu_<타임스탬프>.json` (IMU 원자료 + 구간 라벨 + 진단 스냅샷).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import threading
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_srvs.srv import SetBool, Trigger

from can_relay.ui.gui_node import RelayClient

MAX_MMPS = 80.0
MAX_SEC = 1.5
STEER_TOL_DEG = 5.0         # 전진은 조향 0° 에서 성립한다 — 이 밖이면 시작하지 않는다


class ImuRecorder(Node):
    """`/imu/data` 를 시각과 함께 모은다. 읽기 전용."""

    def __init__(self):
        super().__init__("port_drive_imu_recorder")
        self.samples: list = []
        self._label = "idle"
        self._lock = threading.Lock()
        self.create_subscription(Imu, "/imu/data", self._on_imu, 50)

    def _on_imu(self, msg: Imu):
        a = msg.linear_acceleration
        w = msg.angular_velocity
        with self._lock:
            self.samples.append({
                "t": time.monotonic(), "label": self._label,
                "ax": a.x, "ay": a.y, "az": a.z,
                "wx": w.x, "wy": w.y, "wz": w.z,
            })

    def label(self, name: str):
        with self._lock:
            self._label = name

    def by_label(self, name: str) -> list:
        with self._lock:
            return [s for s in self.samples if s["label"] == name]


def summarize(rows: list) -> dict:
    """구간 요약. 표본이 없으면 그 사실을 그대로 남긴다(0 으로 채우지 않는다)."""
    if not rows:
        return {"n": 0}
    out = {"n": len(rows)}
    for k in ("ax", "ay", "az", "wz"):
        vals = [r[k] for r in rows]
        out[k] = {"mean": statistics.fmean(vals),
                  "min": min(vals), "max": max(vals),
                  "sd": statistics.pstdev(vals) if len(vals) > 1 else 0.0}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mmps", type=float, default=50.0, help="바퀴 속도(mm/s)")
    ap.add_argument("--sec", type=float, default=1.0, help="각 구간 지속(초)")
    ap.add_argument("--dry-run", action="store_true",
                    help="지령을 내지 않고 전제조건 검사만 한다")
    args = ap.parse_args()
    if args.mmps > MAX_MMPS or args.sec > MAX_SEC:
        raise SystemExit(f"거부 — 상한 초과(mmps ≤ {MAX_MMPS}, sec ≤ {MAX_SEC})")

    rclpy.init()
    cli = RelayClient()
    imu = ImuRecorder()
    ex = MultiThreadedExecutor(num_threads=4)
    ex.add_node(cli)
    ex.add_node(imu)
    threading.Thread(target=ex.spin, daemon=True).start()

    report = {"mmps": args.mmps, "sec": args.sec, "aborted": None, "phases": {}}
    engaged = False
    try:
        # ── ① 제어권 ─────────────────────────────────────────────────
        ok, why = cli.call(cli.cli_engage, SetBool.Request(data=True), timeout_s=15.0)
        print(f"[1] 제어권 획득: {ok} — {why}", flush=True)
        if not ok:
            report["aborted"] = f"engage 실패: {why}"
            return
        engaged = True

        # ── ② 전제조건 (여기서 걸리면 한 장도 안 나간다) ─────────────
        t0 = time.monotonic()
        while time.monotonic() - t0 < 6.0:
            if cli.meas_angle(3) is not None and cli.meas_angle(4) is not None:
                break
            time.sleep(0.1)
        f, r = cli.meas_angle(3), cli.meas_angle(4)
        level, msg, fresh, kv = cli.diagnostics()
        report["precheck"] = {"steer_front_deg": f, "steer_rear_deg": r,
                              "diag_level": level, "diag": msg, "diag_fresh": fresh,
                              "diag_kv": kv}
        print(f"[2] 조향 실측 N3={f} N4={r} · 진단 lvl={level} '{msg}' fresh={fresh}",
              flush=True)
        if f is None or r is None:
            report["aborted"] = "조향 실측 미확보 — 피드백이 신선하지 않다"
            return
        if abs(f) > STEER_TOL_DEG or abs(r) > STEER_TOL_DEG:
            report["aborted"] = (f"조향이 0° 근처가 아니다 (N3 {f:+.2f}° · N4 {r:+.2f}°, "
                                 f"허용 ±{STEER_TOL_DEG}°) — 전진/후진 전제 불성립")
            return
        if str(kv.get("engaged", "")).lower() != "true":
            report["aborted"] = f"진단이 제어권 미보유로 보고한다: {kv}"
            return
        if args.dry_run:
            report["aborted"] = "dry-run — 지령 없음"
            print("[3] dry-run: 전제조건 통과, 지령을 내지 않고 종료", flush=True)
            return

        # ── ③ 기준선(정지) ───────────────────────────────────────────
        imu.label("rest_before")
        time.sleep(1.5)

        # ── ④ 전진 (JOG '전진' = 조향 0° + raw 음수 → mm/s 음수) ─────
        print(f"[4] 전진 {args.sec}s @ {args.mmps} mm/s (≈{args.mmps*args.sec/10:.1f} cm)",
              flush=True)
        imu.label("forward")
        t0 = time.monotonic()
        while time.monotonic() - t0 < args.sec:
            cli.send_drive(-args.mmps)          # 워치독(0.3s)보다 자주 갱신
            time.sleep(0.05)
        cli.send_drive(0.0)
        imu.label("rest_mid")
        time.sleep(2.0)

        # ── ⑤ 후진 ──────────────────────────────────────────────────
        print(f"[5] 후진 {args.sec}s @ {args.mmps} mm/s", flush=True)
        imu.label("backward")
        t0 = time.monotonic()
        while time.monotonic() - t0 < args.sec:
            cli.send_drive(+args.mmps)
            time.sleep(0.05)
        cli.send_drive(0.0)
        imu.label("rest_after")
        time.sleep(1.5)

        for name in ("rest_before", "forward", "rest_mid", "backward", "rest_after"):
            report["phases"][name] = summarize(imu.by_label(name))
        _l, _m, _f, kv2 = cli.diagnostics()
        report["diag_after"] = kv2
    finally:
        # ── ⑥ 어떤 경로로 끝나도 정지·반환 ──────────────────────────
        try:
            cli.send_drive(0.0)
            ok, why = cli.call(cli.cli_stop, Trigger.Request(), timeout_s=5.0)
            print(f"[6] 정지: {ok} — {why}", flush=True)
        except Exception as exc:
            print(f"[6] ⚠ 정지 실패: {type(exc).__name__}: {exc}", flush=True)
        if engaged:
            try:
                ok, why = cli.call(cli.cli_engage, SetBool.Request(data=False),
                                   timeout_s=10.0)
                print(f"[7] 제어권 반환: {ok} — {why}", flush=True)
            except Exception as exc:
                print(f"[7] ⚠ 반환 실패: {type(exc).__name__}: {exc}", flush=True)

        stamp = time.strftime("%y%m%d_%H%M%S")
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        out = os.path.join(repo, "Big-AMR", "Log") if os.path.isdir(
            os.path.join(repo, "Big-AMR", "Log")) else os.path.join(repo, "Log")
        os.makedirs(out, exist_ok=True)
        path = os.path.join(out, f"port_drive_imu_{stamp}.json")
        report["samples"] = imu.samples
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
        print(f"[8] 산출물 {path} (IMU {len(imu.samples)} 샘플)", flush=True)
        if report["aborted"]:
            print(f"⚠ 중단 사유: {report['aborted']}", flush=True)
        else:
            for name in ("rest_before", "forward", "rest_mid", "backward", "rest_after"):
                s = report["phases"].get(name, {})
                if s.get("n"):
                    print(f"   {name:12s} n={s['n']:3d} "
                          f"ax={s['ax']['mean']:+.4f} ay={s['ay']['mean']:+.4f} "
                          f"wz={s['wz']['mean']:+.4f}", flush=True)
        ex.shutdown()
        imu.destroy_node()
        cli.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
