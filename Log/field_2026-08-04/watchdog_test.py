"""`--backend ros2` 가 실제로 하는 것 = `drive()` **단발 발행**. 워치독이 끄는가?"""
import csv, sys, time
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from std_srvs.srv import SetBool, Trigger
from trnav_msgs.msg import MotorStateArray

NS = "/can_relay_node"
rclpy.init(); n = Node("wd_test")
pub = n.create_publisher(Float64, f"{NS}/drive_mmps", 10)
eng = n.create_client(SetBool, f"{NS}/engage"); stp = n.create_client(Trigger, f"{NS}/stop")
st, tr = {}, []
n.create_subscription(MotorStateArray, "/motor/low_state",
                      lambda m: st.update({s.motor_id: s.fb_vel for s in m.motors}), 10)
def spin(sec, tag):
    t0 = time.monotonic()
    while time.monotonic() - t0 < sec:
        rclpy.spin_once(n, timeout_sec=0.01)
        tr.append((time.monotonic() - t0, tag, st.get(1), st.get(2)))
def call(c, r, w):
    c.wait_for_service(timeout_sec=10.0)
    f = c.call_async(r); rclpy.spin_until_future_complete(n, f, timeout_sec=60.0)
    print(f"  {w} → {f.result().success}")
try:
    call(eng, SetBool.Request(data=True), "engage"); spin(2.0, "idle")
    print("단발 발행 -50.0 (재발행 없음)")
    t_cmd = time.monotonic(); pub.publish(Float64(data=-50.0))
    spin(2.5, "after")
finally:
    call(stp, Trigger.Request(), "stop"); call(eng, SetBool.Request(data=False), "release")
rows = [r for r in tr if r[1] == "after" and r[2] is not None]
peak = max((abs(r[2]) for r in rows), default=0)
zero_at = next((r[0] for r in rows if abs(r[2]) < 20 and r[0] > 0.15), None)
print(f"\n최대 실속도 {peak}  ·  20 미만으로 떨어진 시각 {zero_at}")
with open(sys.argv[1], "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["dt","tag","n1_vel","n2_vel"]); w.writerows(tr)
rclpy.shutdown()
