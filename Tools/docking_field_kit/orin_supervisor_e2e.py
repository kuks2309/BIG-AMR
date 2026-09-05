"""배포 감시자 복귀 E2E — 드라이버 사망 자동 복귀 · 감시자 동반 재기동 pid 추론 · 수동 해제 비복귀.

배포 유닛(`amr-can-relay`·`amr-can-relay-supervisor`, 도메인 125)을 그대로 두고 MainPID 를
죽여 재기동을 일으킨다(Restart=always). 관측은 `/diagnostics` 와 감시자 저널.

  A. engage → RUNNING → 드라이버 kill → 두절 → RESTORE → 새 pid 로 engaged → RUNNING
     → 수동 해제 → IDLE 유지(복귀 없음)
  B. engage → RUNNING → 드라이버+감시자 동시 kill → 새 감시자가 기록 pid ≠ 현재 pid 로
     두절 추론(warn) → RESTORE → engaged → 해제
  C. engage → 감시자만 kill → RUNNING(복귀 호출 없음) → 해제 → 감시자만 kill → IDLE 유지

전제: 판다를 다른 프로세스가 쥐고 있지 않을 것(내구 런 종료 후). 조향·구동 지령은 넣지 않는다.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time

os.environ.setdefault("ROS_DOMAIN_ID", "125")
sys.path.insert(0, "/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/src/Comm/TCP_IP/seer_api")

import rclpy  # noqa: E402
from diagnostic_msgs.msg import DiagnosticArray  # noqa: E402
from rclpy.node import Node  # noqa: E402
from std_srvs.srv import SetBool  # noqa: E402

DRV = "amr-can-relay.service"
SUP = "amr-can-relay-supervisor.service"
OUT = "/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/docking_field_kit/logs/orin_supervisor_e2e.json"
T0 = time.monotonic()


class Observer(Node):
    def __init__(self):
        super().__init__("supervisor_e2e_observer")
        self.drv = {}; self.sup = {}
        self.drv_t = None; self.sup_t = None
        self.verdicts = []          # (t, verdict) 전이 기록
        self.sub = self.create_subscription(DiagnosticArray, "/diagnostics", self._on_diag, 10)
        self.sub2 = self.create_subscription(DiagnosticArray, "/relay_supervisor/status", self._on_diag, 10)
        self.cli = self.create_client(SetBool, "/can_relay_node/engage")
        self._th = threading.Thread(target=self._spin, daemon=True)
        self._th.start()

    def _spin(self):
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)

    def _on_diag(self, msg):
        now = time.monotonic()
        for st in msg.status:
            kv = {v.key: v.value for v in st.values}
            if st.name.startswith("can_relay:"):
                self.drv = kv; self.drv_t = now
            elif st.name.startswith("can_relay_supervisor"):
                self.sup = kv; self.sup_t = now
                v = kv.get("verdict")
                if v and (not self.verdicts or self.verdicts[-1][1] != v):
                    self.verdicts.append((round(now - T0, 1), v))

    def engage(self, on: bool):
        if not self.cli.wait_for_service(timeout_sec=10.0):
            return False, "engage 서비스 없음"
        req = SetBool.Request(); req.data = bool(on)
        fut = self.cli.call_async(req)
        t = time.monotonic()
        while not fut.done():
            if time.monotonic() - t > 10.0:
                return False, "engage 응답 없음(10 s)"
            time.sleep(0.05)
        r = fut.result(); return bool(r.success), r.message

    def wait_for(self, pred, timeout):
        t = time.monotonic()
        while time.monotonic() - t < timeout:
            if pred():
                return True
            time.sleep(0.2)
        return False


def main_pid(unit):
    return int(subprocess.check_output(["systemctl", "show", "-p", "MainPID", "--value", unit]).decode().strip() or 0)


def kill_driver_node(ob):
    """드라이버 **노드 프로세스**(진단 `pid`)를 SIGKILL — 크래시 재현. launch 가 종료되면 systemd 가 유닛을 재기동한다."""
    pid = int(ob.drv.get("pid") or 0)
    if pid > 0:
        os.kill(pid, 9)
    return {"driver_node": pid}


def kill_sup_node():
    """감시자 노드 프로세스를 SIGKILL(pgrep) — 감시자 크래시 재현."""
    out = subprocess.run(["pgrep", "-f", "^/usr/bin/python3 .*lib/can_relay/relay_supervisor"], capture_output=True, text=True).stdout.split()
    for p in out:
        os.kill(int(p), 9)
    return {"supervisor_node": [int(p) for p in out]}


def journal_since(unit, since):
    out = subprocess.run(["journalctl", "-u", unit, "--since", since, "--no-pager", "-o", "cat"],
                         capture_output=True, text=True).stdout.splitlines()
    pat = re.compile(r"→|복귀 지시|감시자가 없는 사이|감시 시작|두절|복귀 호출")
    return [re.sub(r"^\[relay_supervisor-\d+\] \[\w+\] \[[\d.]+\] \[relay_supervisor\]: ", "", l)[:160] for l in out if pat.search(l)]


def seer_probe():
    try:
        from seer_api.api import SeerApi
        s = SeerApi("192.168.44.82", timeout=3.0)
        al = s.get_alarms(); codes = []
        for k in ("errors", "warnings", "fatals"):
            for e in (al.get(k) or []):
                codes.append(e.get("code") if isinstance(e, dict) else e)
        return {"alarm_codes": codes, "no_52111": 52111 not in codes}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


def _stamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def engaged(ob):
    return ob.drv.get("engaged") == "True"


def path_a(ob):
    r = {"path": "A 드라이버 사망 → 자동 복귀"}; since = _stamp()
    ok, msg = ob.engage(True); r["engage"] = [ok, msg]
    r["running"] = ob.wait_for(lambda: engaged(ob) and ob.sup.get("verdict") == "RUNNING", 15)
    pid0 = ob.drv.get("pid"); r["pid_before"] = pid0
    ob.verdicts.clear()
    r["killed"] = kill_driver_node(ob); t_kill = time.monotonic()
    r["restored"] = ob.wait_for(lambda: engaged(ob) and ob.drv.get("pid") not in (None, pid0)
                                and ob.sup.get("verdict") == "RUNNING", 45)
    r["restore_after_s"] = round(time.monotonic() - t_kill, 1)
    r["pid_after"] = ob.drv.get("pid"); r["verdicts"] = list(ob.verdicts)
    r["restores_in_window"] = ob.sup.get("restores_in_window")
    ok, msg = ob.engage(False); r["release"] = [ok, msg]
    r["idle_after_release"] = ob.wait_for(lambda: ob.sup.get("verdict") == "IDLE", 10)
    time.sleep(8.0)
    r["stays_released"] = (not engaged(ob)) and ob.sup.get("verdict") == "IDLE"
    r["journal"] = journal_since(SUP, since); r["seer"] = seer_probe()
    r["PASS"] = all([r["engage"][0], r["running"], r["restored"], r["release"][0],
                     r["idle_after_release"], r["stays_released"], r["seer"].get("no_52111", False)])
    return r


def path_b(ob):
    r = {"path": "B 드라이버+감시자 동시 사망 → pid 추론 복귀"}; since = _stamp()
    ok, msg = ob.engage(True); r["engage"] = [ok, msg]
    r["running"] = ob.wait_for(lambda: engaged(ob) and ob.sup.get("verdict") == "RUNNING", 15)
    pid0 = ob.drv.get("pid"); r["pid_before"] = pid0
    time.sleep(2.5)                      # 감시자가 engaged·pid 를 state.json 에 적을 시간
    ob.verdicts.clear()
    r["killed"] = {**kill_driver_node(ob), **kill_sup_node()}; t_kill = time.monotonic()
    r["restored"] = ob.wait_for(lambda: engaged(ob) and ob.drv.get("pid") not in (None, pid0)
                                and ob.sup.get("verdict") == "RUNNING", 60)
    r["restore_after_s"] = round(time.monotonic() - t_kill, 1)
    r["pid_after"] = ob.drv.get("pid"); r["verdicts"] = list(ob.verdicts)
    r["journal"] = journal_since(SUP, since)
    r["pid_inference_logged"] = any("감시자가 없는 사이" in l for l in r["journal"])
    ok, msg = ob.engage(False); r["release"] = [ok, msg]
    r["idle_after_release"] = ob.wait_for(lambda: ob.sup.get("verdict") == "IDLE", 10)
    r["seer"] = seer_probe()
    r["PASS"] = all([r["engage"][0], r["running"], r["restored"], r["pid_inference_logged"],
                     r["release"][0], r["idle_after_release"], r["seer"].get("no_52111", False)])
    return r


def path_c(ob):
    r = {"path": "C 감시자만 재기동 — 복귀 없음(부정 대조)"}; since = _stamp()
    ok, msg = ob.engage(True); r["engage"] = [ok, msg]
    r["running"] = ob.wait_for(lambda: engaged(ob) and ob.sup.get("verdict") == "RUNNING", 15)
    pid0 = ob.drv.get("pid"); time.sleep(2.5)
    ob.verdicts.clear(); r["killed_sup_1"] = kill_sup_node()
    time.sleep(0.5); ob.sup = {}; ob.sup_t = None      # 죽은 감시자의 마지막 메시지(잔상)를 지운다
    r["sup_back_running"] = ob.wait_for(lambda: ob.sup.get("verdict") == "RUNNING", 30)
    r["sup_restart_seen"] = any("감시 시작" in l for l in journal_since(SUP, since))
    r["driver_pid_unchanged"] = ob.drv.get("pid") == pid0
    ok, msg = ob.engage(False); r["release"] = [ok, msg]
    r["idle_after_release"] = ob.wait_for(lambda: ob.sup.get("verdict") == "IDLE", 10)
    time.sleep(2.5)                      # 감시자가 engaged=false 를 기록할 시간
    r["killed_sup_2"] = kill_sup_node()
    time.sleep(0.5); ob.sup = {}; ob.sup_t = None
    ob.wait_for(lambda: ob.sup.get("verdict") is not None, 30)
    time.sleep(12.0)                     # 안정화(3 s)+여유 뒤에도 복귀가 없어야 한다
    r["stays_released"] = (not engaged(ob)) and ob.sup.get("verdict") == "IDLE"
    r["journal"] = journal_since(SUP, since)
    r["no_restore_call"] = not any("복귀 지시" in l for l in r["journal"])
    r["PASS"] = all([r["engage"][0], r["running"], r["sup_back_running"], r["sup_restart_seen"], r["driver_pid_unchanged"],
                     r["release"][0], r["idle_after_release"], r["stays_released"], r["no_restore_call"]])
    return r


def main():
    rclpy.init()
    ob = Observer()
    if not ob.wait_for(lambda: ob.drv and ob.sup, 15):
        print("진단 수신 없음 — 유닛 상태 확인"); sys.exit(2)
    if engaged(ob):
        print("이미 engaged — 먼저 해제"); ob.engage(False); time.sleep(3)
    results = []
    sel = {a.upper() for a in sys.argv[1:]} or {"A", "B", "C"}     # 인자로 경로 선택(예: C)
    try:
        for fn in (path_a, path_b, path_c):
            if fn.__name__[-1].upper() not in sel:
                continue
            r = fn(ob); results.append(r)
            print(json.dumps({k: v for k, v in r.items() if k != "journal"}, ensure_ascii=False), flush=True)
            for l in r["journal"]:
                print("   |", l)
            time.sleep(5.0)
    finally:
        if engaged(ob):
            ob.engage(False)
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        out = OUT if sel == {"A", "B", "C"} else OUT.replace(".json", "_" + "".join(sorted(sel)) + ".json")
        json.dump(results, open(out, "w"), ensure_ascii=False, indent=1)
        print("=== " + " · ".join(f"{r['path'][:1]}:{'PASS' if r.get('PASS') else 'FAIL'}" for r in results)
              + " === saved " + out)
        rclpy.shutdown(); ob._th.join(1.0)


if __name__ == "__main__":
    main()
