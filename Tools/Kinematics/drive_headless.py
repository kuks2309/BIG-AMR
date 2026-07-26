#!/usr/bin/env python3
"""헤드리스 구동 진입점 — can-relay 연동 기구학 주행 (GUI 없음).

GUI 분리 원칙의 최종 조립 계층: 아래 3개를 엮어 GUI 없이 실차를 구동한다.
  chassis_kinematics  (수학) → direct_driver (CAN 구동) → relay_authority (Seer 주도권)

흐름:
  RelayAuthority.acquire()  # Seer 주도권 PC 로 전환 (--no-relay 면 생략, 벤치용)
    → DirectDriver.start()  # enable + 50Hz TX 루프
    → set_twist(vx,vy,ω)    # 기구학 연속 제어
    → DirectDriver.shutdown()
  RelayAuthority.release()  # Seer 로 주도권 반환

⚠ 실로봇 구동. 안전구역·E-STOP 상비. 첫 실차는 --demo 저속 크랩/스핀으로 방향부호 확인 후 사용.

사용:
    python3 drive_headless.py --demo                      # can1 구동 + can0 Seer 게이트, 저속 데모
    python3 drive_headless.py --demo --no-relay           # 게이트 없이 모터버스만 (Seer 미연결 벤치)
    python3 drive_headless.py --twist 0.05 0 0 --dur 2    # (vx,vy,ω) 2초 주행
    python3 drive_headless.py --motor can1 --seer can0 --demo
"""
import argparse
import sys
import time

from direct_driver import DirectDriver
from relay_authority import RelayAuthority


def drive(motor_iface, seer_iface, use_relay, commands, log=print):
    """commands: [(vx, vy, w, dur_s), ...] 순차 실행. use_relay=False 면 게이트 없이 모터버스만."""
    auth = None
    drv = None
    try:
        if use_relay:
            auth = RelayAuthority(seer_iface, motor_iface, log=log).acquire()
        drv = DirectDriver(motor_iface, log=log)
        drv.start()
        time.sleep(0.3)  # enable 안정화
        for vx, vy, w, dur in commands:
            drv.set_twist(vx, vy, w)
            time.sleep(dur)
        drv.set_twist(0, 0, 0)
        time.sleep(0.2)
        return True
    finally:
        if drv:
            drv.shutdown()
        if auth:
            auth.release()


def main(argv=None):
    ap = argparse.ArgumentParser(description="헤드리스 can-relay 기구학 주행")
    ap.add_argument("--motor", default="can1", help="모터 측 CAN 인터페이스 (기본 can1)")
    ap.add_argument("--seer", default="can0", help="Seer 측 CAN 인터페이스 (기본 can0)")
    ap.add_argument("--no-relay", action="store_true", help="Seer 게이트 생략(벤치 — 모터버스만)")
    ap.add_argument("--demo", action="store_true", help="저속 전진→좌크랩→제자리회전 데모")
    ap.add_argument("--twist", nargs=3, type=float, metavar=("VX", "VY", "W"), help="단일 (vx,vy,ω) 명령")
    ap.add_argument("--dur", type=float, default=2.0, help="--twist 지속시간 s (기본 2)")
    args = ap.parse_args(argv)

    if args.demo:
        commands = [(0.05, 0, 0, 1.5), (0, 0.05, 0, 1.5), (0, 0, 0.1, 1.5)]
    elif args.twist:
        commands = [(args.twist[0], args.twist[1], args.twist[2], args.dur)]
    else:
        ap.error("--demo 또는 --twist 중 하나를 지정하세요")

    print(f"구동: motor={args.motor} seer={args.seer} relay={'off' if args.no_relay else 'on'}")
    print(f"명령 시퀀스: {commands}")
    ok = drive(args.motor, args.seer, not args.no_relay, commands)
    print("완료" if ok else "실패")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
