#!/usr/bin/env python3
"""헤드리스 구동 진입점 — 백엔드 추상화 + can-relay 연동 기구학 주행 (GUI 없음).

계층 조립 최종층(ADR 2026-07-28): 아래 4계층을 엮어 GUI 없이 구동한다.
  chassis_kinematics(수학) → can_protocol(코덱) → can_transport(백엔드) → direct_driver(구동)
  + authority(주도권)

안전 기본값: **--live 미지정이면 dry-run(mock)** — 실 하드웨어 미접촉, 프레임만 기록.
실 구동은 --live + --backend 명시 + preflight 통과 후에만 트랜스포트를 arm 한다.

백엔드(--backend): mock(기본 dry-run) · socketcan(실차 성숙, 커널 can-gw 게이트) · pcan(직결, 미검증).
  panda 하드웨어 릴레이는 Phase 6-9(별도 HIL 승인) — 아직 미배선.

⚠ 실로봇 구동. 안전구역·E-STOP 상비. 첫 실차는 저속 크랩/스핀으로 방향부호 확인 후 사용.

사용:
    python3 drive_headless.py --demo                          # dry-run(mock) 데모 — 무-하드웨어
    python3 drive_headless.py --demo --live --backend socketcan   # 실차: can1 구동 + can0 Seer 게이트
    python3 drive_headless.py --twist 0.05 0 0 --dur 2 --live --backend socketcan
    python3 drive_headless.py --demo --live --backend pcan --motor PCAN_USBBUS1   # PCAN 직결(미검증)
"""
import argparse
import sys
import time

from direct_driver import DirectDriver


def build_stack(backend, motor, seer, live, log=print):
    """(transport, authority) 조립. --live 아니면 mock 강제(dry-run). 반환 트랜스포트는 open+preflight, 미-arm."""
    from can_transport import open_transport
    from authority import KernelCangwAuthority, NoAuthority

    if not live or backend == "mock":
        if backend != "mock" and not live:
            log(f"[stack] --live 미지정 → dry-run(mock) 강제 (요청 backend={backend})")
        return open_transport("mock").open(), NoAuthority(log=log)

    tp = open_transport(f"{backend}:{motor}").open()
    rep = tp.preflight()
    log(f"[stack] preflight({backend}:{motor}): {rep.summary()}")
    if not rep:
        tp.shutdown()
        raise SystemExit("preflight 실패 — arm 중단(실 하드웨어 미접촉)")
    # 커널 can-gw 게이트는 socketcan 경로 전용. pcan 직결·기타는 무-중재(NoAuthority).
    auth = KernelCangwAuthority(seer, motor, log=log) if backend == "socketcan" else NoAuthority(log=log)
    return tp, auth


def drive(transport, authority, commands, log=print):
    """authority 취득 → transport arm → DirectDriver 로 commands 순차 실행 → 정지·반환.

    commands: [(vx, vy, w, dur_s), ...]. 예외/종료 시 무조건 정지(vel0)+주도권 반환.
    """
    drv = None
    try:
        authority.acquire()
        transport.arm()
        drv = DirectDriver(transport, log=log)
        drv.start()
        time.sleep(0.3)  # enable 안정화
        for vx, vy, w, dur in commands:
            drv.set_twist(vx, vy, w)
            time.sleep(dur)
        drv.set_twist(0, 0, 0)
        time.sleep(0.2)
        return True
    finally:
        if drv is not None:
            drv.shutdown()          # vel0 송신 + transport disarm/shutdown
        else:
            transport.disarm(); transport.shutdown()
        authority.release()


def main(argv=None):
    ap = argparse.ArgumentParser(description="헤드리스 백엔드추상 기구학 주행")
    ap.add_argument("--backend", default="mock", choices=["mock", "socketcan", "pcan"],
                    help="CAN 백엔드 (기본 mock=dry-run)")
    ap.add_argument("--live", action="store_true", help="실 하드웨어 구동(미지정 시 dry-run mock 강제)")
    ap.add_argument("--motor", default="can1", help="모터 측 채널 (socketcan can1 / pcan PCAN_USBBUS1)")
    ap.add_argument("--seer", default="can0", help="Seer 측 채널 (socketcan 게이트용)")
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

    mode = "LIVE" if args.live else "DRY-RUN(mock)"
    print(f"구동[{mode}]: backend={args.backend} motor={args.motor} seer={args.seer}")
    print(f"명령 시퀀스: {commands}")
    transport, authority = build_stack(args.backend, args.motor, args.seer, args.live)
    ok = drive(transport, authority, commands)
    # dry-run(mock)이면 기록된 프레임 요약
    sent = getattr(transport, "sent", None)
    if sent is not None:
        print(f"[dry-run] 송신 프레임 {len(sent)}건 · arb-ids={[hex(i) for i in transport.sent_ids()]}")
    print("완료" if ok else "실패")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
