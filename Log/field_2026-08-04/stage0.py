"""실기 1단계 — **읽기 전용**. CAN 송신 0건, safety mode·bitrate 변경 없음."""
import os, sys
sys.path.insert(0, "/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/amr_test_gui")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import gui

P = gui._panda_class()
print(f"판다 목록: {P.list()}")
p = P()                                    # gui.py 와 동일한 호출
try:
    h = p.health()
    print(f"fw           = {p.get_version()}")
    print(f"safety_mode  = {h['safety_mode']}  (30=SEER_GATE, 0=SILENT)")
    print(f"harness      = {h['car_harness_status']}")
    print(f"controls_allowed = {h.get('controls_allowed')}")
    for k in ("ignition_line", "ignition_can", "car_harness_status",
              "safety_param", "fault_status", "power_save_enabled"):
        if k in h:
            print(f"  {k:20s} = {h[k]}")
    print("--- CAN health (bus 0/1/2) ---")
    for bus in (0, 1, 2):
        try:
            c = p.can_health(bus)
            print(f"  bus{bus}: speed={c.get('can_speed')} kbps  state={c.get('bus_off')}"
                  f"  tec={c.get('total_tx_checksum_error_cnt', c.get('tx_error_cnt'))}"
                  f"  rec={c.get('receive_error_cnt')}  can_data_speed={c.get('can_data_speed')}")
        except Exception as exc:
            print(f"  bus{bus}: 조회 실패 {type(exc).__name__}: {exc}")
finally:
    p.close()
    print("판다 닫음 — 상태 변경 없음")
