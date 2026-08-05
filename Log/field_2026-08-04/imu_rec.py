"""/imu/data 를 CSV 로 기록. SIGTERM 까지 계속."""
import csv, signal, sys, time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu

out = open(sys.argv[1], "w", newline="")
wr = csv.writer(out); wr.writerow(["t_mono", "ax", "ay", "az", "gx", "gy", "gz"])
rclpy.init()
n = Node("imu_rec")
n.create_subscription(Imu, "/imu/data", lambda m: wr.writerow([
    f"{time.monotonic():.4f}",
    m.linear_acceleration.x, m.linear_acceleration.y, m.linear_acceleration.z,
    m.angular_velocity.x, m.angular_velocity.y, m.angular_velocity.z]), 50)
signal.signal(signal.SIGTERM, lambda *_: (out.flush(), out.close(), rclpy.shutdown(), sys.exit(0)))
try:
    rclpy.spin(n)
except Exception:
    pass
finally:
    try: out.flush(); out.close()
    except Exception: pass
