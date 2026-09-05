"""ROS 실행기 정체 주입 실기 검증 — 백엔드 심박 중단 시 조향 재송신 0 + 펌웨어 fail-safe 복원.

실노드(`CanRelayNode`)를 이 하네스가 직접 spin 하다가 spin 을 멈추는 것으로 정체를
만든다(진단 타이머가 서서 `mark_ros_alive` 가 끊긴다 — 코드가 정의한 「정체」 그대로).

절차: engage → 홈 확인(미홈이면 `~/home`) → 조향 +5° → 3 s 관측 → spin 중단 →
  · 백엔드: `hb_suppressed` 전이 시각, 그 뒤 0x607A 송신 수(기대 0)
  · 펌웨어: 0xec(state·source·result·pc_authority), health.safety_mode(기대 SILENT=0)
  · Seer: steer_angles(기대 ≈0)·알람(52111 부재)
→ 반환·정리. 배포 노드(도메인 125)와 겹치지 않게 도메인 126 으로 돈다.
"""
import json
import os
import sys
import threading
import time

os.environ.setdefault("ROS_DOMAIN_ID", "126")
DEPLOY = "/home/nvidia/Project/Ford-CATL-AMR/Big-AMR-deploy"
sys.path.insert(0, os.path.join(DEPLOY, "Tools/Can_Relay/panda-firmware"))
sys.path.insert(0, "/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/src/Comm/TCP_IP/seer_api")

import rclpy  # noqa: E402
from rclpy.executors import MultiThreadedExecutor  # noqa: E402
from std_srvs.srv import SetBool, Trigger  # noqa: E402
from python import Panda  # noqa: E402
from can_relay.driver_node import CanRelayNode  # noqa: E402

CFG = os.path.join(DEPLOY, "src/Comm/CAN/can_relay/config/can_relay.yaml")
MACHINE = os.path.join(DEPLOY, "src/Comm/CAN/can_relay/config/machine/foil_a082.yaml")
STEER_DEG = 5.0
OUT = "/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/docking_field_kit/logs/orin_ros_stall_test.json"


def seer_probe():
    try:
        from seer_api.api import SeerApi
        s = SeerApi("192.168.44.82", timeout=3.0)
        ang = s.get_speed().get("steer_angles")
        al = s.get_alarms()
        codes = []
        for k in ("errors", "warnings", "fatals"):
            for e in (al.get(k) or []):
                codes.append(e.get("code") if isinstance(e, dict) else e)
        return {"steer_angles_rad": ang, "alarm_codes": codes}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


def fw_status(link):
    p = link._panda
    with link._lock:
        h = p.health()
        r = bytes(p._handle.controlRead(Panda.REQUEST_IN, 0xec, 0, 0, 6))
    return {"safety_mode": h.get("safety_mode"), "ho_state": r[0], "ho_source": r[1],
            "ho_result": r[2], "pending_silent": r[3], "ticks": r[4], "pc_authority": r[5]}


def main():
    rclpy.init(args=["--ros-args", "--params-file", CFG, "--params-file", MACHINE])
    node = CanRelayNode()
    ex = MultiThreadedExecutor()
    ex.add_node(node)
    alive = threading.Event(); alive.set()
    stopped = threading.Event()

    def spin():
        while alive.is_set():
            ex.spin_once(timeout_sec=0.1)
        stopped.set()
    th = threading.Thread(target=spin, daemon=True); th.start()

    be = node.backend
    steer_tx = {"n": 0}
    orig_send = be._send

    def counting_send(frames):
        frames = list(frames)
        for f in frames:
            data = getattr(f, "data", None)
            if data is None and isinstance(f, (tuple, list)) and len(f) >= 2:
                data = f[1]
            if data and len(data) >= 3 and data[1] == 0x7A and data[2] == 0x60:
                steer_tx["n"] += 1
        return orig_send(frames)
    be._send = counting_send

    rec = {"t0": time.time(), "steps": []}
    t0 = time.monotonic()

    def log(step, **kw):
        kw["t"] = round(time.monotonic() - t0, 2); kw["step"] = step
        rec["steps"].append(kw); print(json.dumps(kw, ensure_ascii=False), flush=True)

    res = SetBool.Response(); req = SetBool.Request(); req.data = True
    node._srv_engage(req, res); log("engage", ok=res.success, msg=res.message)
    if not res.success:
        alive.clear(); stopped.wait(2); node.destroy_node(); rclpy.shutdown(); sys.exit(2)
    try:
        time.sleep(2.0)
        homed = be.homed_effective(); log("homed_check", homed=homed)
        if not homed:
            r = Trigger.Response(); node._srv_home(None, r)
            log("home", ok=r.success, msg=r.message)
            time.sleep(1.0)
            if not be.homed_effective():
                log("abort", why="홈 미확보 — 조향 지령을 넣지 않는다"); raise SystemExit(3)
        be.set_steer_deg(STEER_DEG)
        time.sleep(3.0)
        n_alive = steer_tx["n"]
        snap = be.snapshot()
        log("steer_alive", steer_tx=n_alive, hb_suppressed=snap["hb_suppressed"],
            angles=be.steer_angles_deg(), fw=fw_status(node.link))

        # ── 정체 주입 ────────────────────────────────────────────────
        alive.clear(); stopped.wait(2.0); t_stall = time.monotonic()
        log("stall_injected")
        t_sup = None; n_at_sup = None
        deadline = t_stall + 15.0
        while time.monotonic() < deadline:
            snap = be.snapshot()
            if t_sup is None and snap["hb_suppressed"]:
                t_sup = time.monotonic(); time.sleep(0.25); n_at_sup = steer_tx["n"]
                log("hb_suppressed", after_s=round(t_sup - t_stall, 2),
                    note=snap.get("hb_block_note"), steer_tx_at=n_at_sup)
            time.sleep(0.1)
        n_end = steer_tx["n"]
        fw = fw_status(node.link)
        log("after_stall", hb_suppressed=snap["hb_suppressed"], steer_tx_end=n_end,
            steer_tx_after_suppress=(None if n_at_sup is None else n_end - n_at_sup),
            fw=fw, angles=be.steer_angles_deg(), fault=snap.get("fault"))
        seer = seer_probe(); log("seer", **seer)

        verdict = {
            "hb_suppressed_within_3s": t_sup is not None and (t_sup - t_stall) <= 3.0,
            "no_steer_resend_after_suppress": n_at_sup is not None and n_end - n_at_sup == 0,
            "fw_released": fw["pc_authority"] == 0 and fw["ho_state"] == 0 and fw["safety_mode"] == 0,
            "fw_restore_reached": fw["ho_source"] == 2 and fw["ho_result"] == 1,
            "seer_steer_zero": (isinstance(seer.get("steer_angles_rad"), list)
                                and all(abs(a) < 0.02 for a in seer["steer_angles_rad"])),
            "no_52111": 52111 not in (seer.get("alarm_codes") or []),
        }
        log("verdict", **verdict, PASS=all(verdict.values()))
    finally:
        req.data = False; res = SetBool.Response()
        try:
            node._srv_engage(req, res); log("release", ok=res.success, msg=res.message)
        except Exception as exc:  # noqa: BLE001
            log("release", error=f"{type(exc).__name__}: {exc}")
        node.destroy_node(); rclpy.shutdown()
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        json.dump(rec, open(OUT, "w"), ensure_ascii=False, indent=1); print("saved", OUT)


if __name__ == "__main__":
    main()
