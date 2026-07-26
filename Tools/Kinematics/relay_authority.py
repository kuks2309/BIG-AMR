#!/usr/bin/env python3
"""can-relay 주도권 코디네이터 — PC 마스터 전환/반환 (GUI 에서 분리한 헤드리스 로직).

GUI 분리 원칙: drive_gui.py 의 GUI 클래스 내부에 있던 _start_gate/_stop_gate 주도권 전환
로직을 PyQt 없이 추출. 헤드리스 스크립트·GUI 어느 쪽이든 동일하게 import 해서 쓴다.

can-relay 구조 (docs/adr/2026-07-09-relay-authority-arbitration.md):
  평시   : 커널 can-gw 가 can0(Seer)↔can1(모터) 양방향 포워딩 (저지연).
  PC주도 : gate_on → Seer→모터 커널 경로 제거, 유저스페이스 게이트가 대신.
           게이트는 Seer 의 SDO 쓰기만 차단 + 가짜 ack 합성(재초기화 루프 방지),
           읽기·guard RTR 는 통과(Seer 가 단절 E6 로 판정하지 않음).
  반환   : gate_off → 커널 경로 복원, 즉시 Seer 로 주도권 반환.
  모터→Seer 방향은 항상 커널(-f 600~780 로 PC 명령 에코 차단).

원본: can_relay/drive_gui.py(run_cangw·make_seer_gate_hook·_start/_stop_gate) + relay_core.py(Direction).

⚠ 실로봇. gate 제어에 root 필요(sudo -n → pkexec 폴백). sudoers NOPASSWD 등록 권장
  (인증창 지연 = Seer 측 제어 공백). scripts/relay_cangw.sh 참조.
"""
import os
import subprocess
import threading
import time

import can

_HERE = os.path.dirname(os.path.abspath(__file__))
CANGW_SCRIPT = next((p for p in (os.path.join(_HERE, "scripts", "relay_cangw.sh"),) if os.path.isfile(p)), None)


def run_cangw(action, timeout=30):
    """커널 can-gw 릴레이 스크립트 실행 (start/gate_on/gate_off/stop). 반환 (rc, output).

    sudoers 에 NOPASSWD 등록돼 있으면 무프롬프트(sudo -n), 아니면 pkexec 인증창 폴백.
    """
    if CANGW_SCRIPT is None:
        return (127, "relay_cangw.sh 를 찾을 수 없음")
    try:
        p = subprocess.run(["sudo", "-n", "bash", CANGW_SCRIPT, action],
                           capture_output=True, text=True, timeout=timeout)
        if p.returncode == 0:
            return (0, p.stdout.strip())
        p = subprocess.run(["pkexec", "bash", CANGW_SCRIPT, action],
                           capture_output=True, text=True, timeout=timeout)
        return (p.returncode, (p.stdout + p.stderr).strip())
    except Exception as e:
        return (1, str(e))


def make_seer_gate_hook(pc_auth, ack_send=None):
    """Seer→모터 릴레이 훅 — 주도권 PC(pc_auth set) 동안 Seer 의 SDO 쓰기만 차단 + 가짜 ack 합성.

    읽기(0x40)·guard RTR 는 항상 통과 → Seer 가 단절(E6)로 판정하지 않음. 차단한 쓰기에는
    쓰기 성공 응답(0x60)을 Seer측에 합성해 돌려준다 — 실측(cap_20260709_163020): ack 없이
    차단만 하면 Seer 가 쓰기 무응답을 감지해 재초기화 루프에 빠지고 반환 후 ~68s 지연.
    (ADR 2026-07-09-relay-authority-arbitration Risk 1 → 2단계 보완)
    """
    def hook(msg):
        if (pc_auth.is_set() and 0x601 <= msg.arbitration_id <= 0x604
                and not getattr(msg, "is_remote_frame", False)
                and msg.dlc >= 4 and msg.data[0] in (0x23, 0x27, 0x2B, 0x2F)):
            if ack_send is not None:
                ack_send(can.Message(
                    arbitration_id=0x580 + (msg.arbitration_id - 0x600),
                    data=bytes([0x60, msg.data[1], msg.data[2], msg.data[3], 0, 0, 0, 0]),
                    is_extended_id=False))
            return None
        return msg
    return hook


class _Forwarder(threading.Thread):
    """단방향 포워더: src 수신 → (훅) → dst 송신 (relay_core.Direction 의 최소 이식, RTR 보존)."""

    def __init__(self, src, dst, name, hook=None):
        super().__init__(name=name, daemon=True)
        self.src, self.dst, self.hook = src, dst, hook
        self.count = self.dropped = self.errors = 0
        self.running = True

    def run(self):
        while self.running:
            try:
                msg = self.src.recv(timeout=0.5)
            except can.CanError:
                self.errors += 1
                continue
            if msg is None or msg.is_error_frame:
                continue
            if self.hook is not None:
                msg = self.hook(msg)
                if msg is None:
                    self.dropped += 1
                    continue
            out = can.Message(arbitration_id=msg.arbitration_id, is_extended_id=msg.is_extended_id,
                              is_remote_frame=msg.is_remote_frame, dlc=msg.dlc, data=msg.data)  # RTR 보존
            try:
                self.dst.send(out)
            except can.CanError:
                self.errors += 1
                continue
            self.count += 1


class RelayAuthority:
    """PC 주도권 컨텍스트 매니저 — with 진입 시 취득(gate_on+게이트 기동), 이탈 시 반환(gate_off).

        with RelayAuthority("can0", "can1"):
            drv = DirectDriver("can1"); drv.start(); ...; drv.shutdown()
        # 블록 이탈 = 즉시 Seer 로 주도권 반환

    kernel_relay=True 이면 취득 전 커널 릴레이(can-gw start)도 올리고 반환 후 내린다
    (릴레이가 이미 가동 중이면 False 로 두고 게이트만 전환).
    """

    def __init__(self, seer_iface="can0", motor_iface="can1", kernel_relay=False, log=None):
        self.seer_iface = seer_iface
        self.motor_iface = motor_iface
        self.kernel_relay = kernel_relay
        self.log = log or (lambda *_: None)
        self.pc_auth = threading.Event()
        self._fwd = None
        self._rbus0 = self._rbus1 = None
        self._started_kernel = False

    def acquire(self):
        if self.kernel_relay:
            rc, out = run_cangw("start")
            if rc != 0:
                raise RuntimeError("커널 릴레이 start 실패:\n" + out)
            self._started_kernel = True
        rc, out = run_cangw("gate_on")
        if rc != 0:
            raise RuntimeError("gate_on 실패:\n" + out)
        self._rbus0 = can.Bus(channel=self.seer_iface, interface="socketcan", receive_own_messages=False)
        self._rbus1 = can.Bus(channel=self.motor_iface, interface="socketcan", receive_own_messages=False)

        def ack_to_seer(m):
            try:
                if self._rbus0:
                    self._rbus0.send(m)
            except can.CanError:
                pass

        self.pc_auth.set()
        self._fwd = _Forwarder(self._rbus0, self._rbus1, "seer->motor(gate)",
                               hook=make_seer_gate_hook(self.pc_auth, ack_send=ack_to_seer))
        self._fwd.start()
        self.log(f"[auth] PC 주도권 취득 (gate_on, {self.seer_iface}->{self.motor_iface})")
        return self

    def release(self):
        self.pc_auth.clear()
        if self._fwd:
            self._fwd.running = False
            self._fwd.join(timeout=1)
            self._fwd = None
        for b in (self._rbus0, self._rbus1):
            if b:
                b.shutdown()
        self._rbus0 = self._rbus1 = None
        run_cangw("gate_off")
        if self._started_kernel:
            run_cangw("stop")
            self._started_kernel = False
        self.log("[auth] Seer 로 주도권 반환 (gate_off)")

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *exc):
        self.release()
        return False


if __name__ == "__main__":
    print(__doc__)
    print(f"relay_cangw.sh: {CANGW_SCRIPT or '(없음)'}")
