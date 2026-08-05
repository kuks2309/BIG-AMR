"""실기 ROS2 — 원본과 **같은 시퀀스**(전진1s/정지2s/후진1s @50 mm/s)를 드라이버 계약대로.

⚠ `~/drive_mmps` 는 **raw 부호**다(sign=1 고정). 원본의 「전진 = raw 음수」와 맞추려면
   전진에 **-50.0** 을 보낸다 — `app.py:565` 의 `be.drive(sign*mmps)` 와 같은 값이다.
⚠ 드라이버는 `cmd_timeout_s=0.3` 워치독을 둔다 — **20 Hz 로 계속 발행**해야 유지된다.
"""
import csv, sys, time
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from std_srvs.srv import SetBool, Trigger
from sensor_msgs.msg import JointState
from trnav_msgs.msg import MotorStateArray

NS, MMPS, DUR, PAUSE, HZ = "/can_relay_node", 50.0, 1.0, 2.0, 20.0
rclpy.init()
n = Node("ros2_drive_test")
pub = n.create_publisher(Float64, f"{NS}/drive_mmps", 10)
cli_eng = n.create_client(SetBool, f"{NS}/engage")
cli_stop = n.create_client(Trigger, f"{NS}/stop")
state, joints, trace = {}, {}, []

def on_state(m):
    for s in m.motors:
        state[s.motor_id] = (s.fb_vel, s.fb_pos, s.motor_enabled)
def on_joint(m):
    for name, p in zip(m.name, m.position):
        joints[name] = p
n.create_subscription(MotorStateArray, "/motor/low_state", on_state, 10)
n.create_subscription(JointState, f"{NS}/joint_states", on_joint, 10)

def spin(sec, phase, cmd=None):
    t0 = time.monotonic(); nxt = 0.0
    while time.monotonic() - t0 < sec:
        rclpy.spin_once(n, timeout_sec=0.01)
        now = time.monotonic()
        if cmd is not None and now >= nxt:
            pub.publish(Float64(data=float(cmd))); nxt = now + 1.0 / HZ
        trace.append((now, phase, cmd,
                      state.get(1, (None,))[0], state.get(2, (None,))[0],
                      state.get(1, (None, None))[1], state.get(2, (None, None))[1]))

def call(cli, req, what):
    if not cli.wait_for_service(timeout_sec=10.0):
        raise SystemExit(f"{what} 서비스 없음 — 드라이버 미기동?")
    f = cli.call_async(req); rclpy.spin_until_future_complete(n, f, timeout_sec=210.0)
    r = f.result()
    print(f"  {what} → success={getattr(r,'success',None)} msg={getattr(r,'message','')}")
    return r

try:
    print("제어권 획득"); call(cli_eng, SetBool.Request(data=True), "engage(True)")
    spin(2.0, "engage")
    print(f"  조향 joint_states = { {k: round(v,5) for k,v in joints.items()} }")
    print(f"  motor_enabled = { {k: v[2] for k,v in state.items()} }")

    print(f"[{time.monotonic():.2f}] 전진(-50.0 발행 @20Hz)"); spin(DUR, "fwd", -MMPS)
    print(f"[{time.monotonic():.2f}] 정지(0.0)");             spin(PAUSE, "stop1", 0.0)
    print(f"[{time.monotonic():.2f}] 후진(+50.0)");           spin(DUR, "bwd", +MMPS)
    print(f"[{time.monotonic():.2f}] 정지(0.0)");             spin(2.0, "stop2", 0.0)
finally:
    try: call(cli_stop, Trigger.Request(), "stop")
    except Exception as e: print(f"  stop 실패: {e}")
    try: call(cli_eng, SetBool.Request(data=False), "engage(False)")
    except Exception as e: print(f"  반환 실패: {e}")

with open(sys.argv[1], "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["t_mono","phase","cmd","n1_vel","n2_vel","n1_pos","n2_pos"])
    w.writerows(trace)
print(f"\n트레이스 {len(trace)}행 저장")
rclpy.shutdown()
