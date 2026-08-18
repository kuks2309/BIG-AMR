#!/usr/bin/env python3
"""`<ns>/engage` 를 광고하되 **절대 응답하지 않는** 스텁.

`call_async` future 가 미완료로 남는 조건을 결정론적으로 만든다 — 실기에서 그 조건은
서비스 응답 왕복(~7 ms) 안에 서버가 죽는 경우라 밖에서 타이밍을 맞출 수 없다.
"""
import sys, time
import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool

class Deaf(Node):
    def __init__(self, ns):
        super().__init__("deaf_engage")
        self.create_service(SetBool, f"/{ns}/engage", self._never)
    def _never(self, req, res):
        time.sleep(10_000)      # 응답하지 않는다
        return res

def main():
    rclpy.init()
    n = Deaf(sys.argv[1] if len(sys.argv) > 1 else "can_relay_node")
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally:
        n.destroy_node()
        rclpy.ok() and rclpy.shutdown()

if __name__ == "__main__":
    main()
