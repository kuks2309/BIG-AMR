"""실기 재확인(정정판) — 스핀을 **전용 스레드**에 둬서 서비스 호출 중에도 관측이 끊기지 않게 한다.

앞선 실행은 메인 루프에서 spin_once 를 돌려, 블로킹 서비스 호출 5초 동안 관측이 통째로
멈췄다(그 뒤 첫 표본은 묵은 값). 여기서는 실제 GUI 와 같이 executor 를 스레드에 둔다.
"""
import csv, sys, threading, time
import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_srvs.srv import SetBool
from trnav_msgs.msg import MotorStateArray
sys.path.insert(0, "/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/src/Comm/CAN/can_relay")
from can_relay.ui.backend_ros2 import RelayClient, Ros2Backend

rclpy.init()
client = RelayClient()
obs = Node("hold_obs2"); st = {}
obs.create_subscription(MotorStateArray, "/motor/low_state",
                        lambda m: st.update({s.motor_id: s.fb_vel for s in m.motors}), 10)
eng = obs.create_client(SetBool, "/can_relay_node/engage")
ex = MultiThreadedExecutor(); ex.add_node(client); ex.add_node(obs)
threading.Thread(target=ex.spin, daemon=True).start()          # ← 실제 GUI 와 같은 구조
be = Ros2Backend.__new__(Ros2Backend); be.node = client
tr = []

def rec(sec, tag):
    t0 = time.monotonic()
    while time.monotonic() - t0 < sec:
        tr.append((round(time.monotonic() - T0, 3), tag, st.get(1), st.get(2)))
        time.sleep(0.02)

eng.wait_for_service(timeout_sec=15.0)
f = eng.call_async(SetBool.Request(data=True))
while not f.done(): time.sleep(0.05)
print(f"engage → {f.result().success}")
T0 = time.monotonic(); rec(1.0, "idle")
try:
    print("send_drive(-50.0) 단발"); client.send_drive(-50.0); rec(1.5, "hold_fwd")
    t_stop = time.monotonic() - T0
    print(f"stop() @ {t_stop:.2f}s →", be.stop());              rec(1.5, "after_stop1")
    print("send_drive(+50.0) 단발"); client.send_drive(+50.0);  rec(1.5, "hold_bwd")
    t_stop2 = time.monotonic() - T0
    print(f"stop() @ {t_stop2:.2f}s →", be.stop());             rec(1.5, "after_stop2")
finally:
    try: be.stop()
    except Exception as e: print("stop 실패", e)
    f = eng.call_async(SetBool.Request(data=False))
    t0 = time.monotonic()
    while not f.done() and time.monotonic() - t0 < 20: time.sleep(0.05)
    print(f"release → {f.result().success if f.result() else 'timeout'}")
with open(sys.argv[1], "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["t","tag","n1","n2"]); w.writerows(tr)
print(f"stop 지령 시각: {t_stop:.2f}s / {t_stop2:.2f}s")
rclpy.shutdown()
