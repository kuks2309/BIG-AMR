#!/usr/bin/env python3
"""주도권(arbitration) 코디네이터 — 트랜스포트와 분리된 별개 축 (ADR 2026-07-28).

권한은 백엔드마다 메커니즘이 다르다: socketcan/PCAN 은 커널 can-gw 게이트(+유저스페이스 포워더),
panda 는 펌웨어 SEER_GATE. 이를 AuthorityCoordinator(acquire/release) 계약으로 추상화한다.

  KernelCangwAuthority — 커널 can-gw 게이트 + Seer 쓰기 차단·가짜 ack (기존 RelayAuthority 개명).
  NoAuthority          — 무-중재(벤치/mock/--no-relay).

원본: can_relay/drive_gui.py(run_cangw·make_seer_gate_hook·_start/_stop_gate) + relay_core.py(Direction).

⚠ 결함 수정(코드리뷰 2026-07-26): acquire 부분실패 시 무조건 롤백(Seer 주도권 영구상실 방지, High) +
  멱등 release + gate_off rc 확인(실패 은폐 방지, Medium).

⚠ 실로봇. gate 제어에 root 필요(sudo -n → pkexec 폴백). scripts/relay_cangw.sh 참조.
"""
import abc
import os
import subprocess
import threading

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

    can.Message 를 다루므로 caller(socketcan 경로)가 이미 python-can 을 lazy import 한 뒤 쓴다.
    """
    import can

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
        import can
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


class AuthorityCoordinator(abc.ABC):
    """주도권 계약. with 진입=취득, 이탈=반환. 부분실패 시 무조건 롤백, release 멱등."""

    @abc.abstractmethod
    def acquire(self) -> "AuthorityCoordinator": ...

    @abc.abstractmethod
    def release(self) -> None: ...

    def __enter__(self) -> "AuthorityCoordinator":
        return self.acquire()

    def __exit__(self, *exc) -> bool:
        self.release()
        return False


class NoAuthority(AuthorityCoordinator):
    """무-중재 — 벤치/mock/--no-relay. Seer 게이트 없이 모터 버스만 쓰는 경우."""

    def __init__(self, log=None):
        self.log = log or (lambda *_: None)

    def acquire(self):
        self.log("[auth] NoAuthority (중재 없음 — 벤치/mock)")
        return self

    def release(self):
        pass


class KernelCangwAuthority(AuthorityCoordinator):
    """커널 can-gw 게이트 기반 PC 주도권 (구 RelayAuthority).

        with KernelCangwAuthority("can0", "can1"):
            drv = DirectDriver(transport); drv.start(); ...; drv.shutdown()
        # 블록 이탈 = 즉시 Seer 로 주도권 반환

    kernel_relay=True 이면 취득 전 커널 릴레이(can-gw start)도 올리고 반환 후 내린다.
    acquire 는 부분실패 시 이미 실행한 단계만 무조건 롤백하고 re-raise (Seer 주도권 영구상실 방지).
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
        self._gated = False
        self._released = False

    def acquire(self):
        self._released = False
        try:
            import can
            if self.kernel_relay:
                rc, out = run_cangw("start")
                if rc != 0:
                    raise RuntimeError("커널 릴레이 start 실패:\n" + out)
                self._started_kernel = True
            rc, out = run_cangw("gate_on")
            if rc != 0:
                raise RuntimeError("gate_on 실패:\n" + out)
            self._gated = True
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
        except Exception as e:
            # 부분실패 롤백 — 이미 켠 게이트/버스/커널만 되돌린다 (Seer 주도권 영구상실 방지)
            self.log(f"[auth] ⚠ 취득 실패 — 롤백: {e}")
            self.release()
            raise

    def release(self):
        if self._released:  # 멱등 — 중복 호출/취득 실패 롤백과 안전 공존
            return
        self._released = True
        self.pc_auth.clear()
        if self._fwd:
            self._fwd.running = False
            self._fwd.join(timeout=1)
            self._fwd = None
        for b in (self._rbus0, self._rbus1):
            if b:
                try:
                    b.shutdown()
                except Exception:
                    pass
        self._rbus0 = self._rbus1 = None
        gate_off_failed = False
        if self._gated:  # gate_on 이 성공했을 때만 gate_off (부분실패 시 불필요 호출 회피)
            rc, out = run_cangw("gate_off")
            self._gated = False
            if rc != 0:  # 실패 은폐 금지 — 커널 경로 미복원이면 Seer 제어 공백 지속
                gate_off_failed = True
                self.log(f"[auth] ⚠ gate_off 실패(rc={rc}) — 커널 경로 미복원, 수동 확인 필요: {out}")
        # gate_off 실패해도 커널 릴레이 stop 은 반드시 시도 (L2: early-return 으로 건너뛰지 않음)
        if self._started_kernel:
            run_cangw("stop")
            self._started_kernel = False
        if not gate_off_failed:
            self.log("[auth] Seer 로 주도권 반환 (gate_off)")


# 하위호환 별칭 — 구 relay_authority.RelayAuthority 호출부 유지
RelayAuthority = KernelCangwAuthority


if __name__ == "__main__":
    print(__doc__)
    print(f"relay_cangw.sh: {CANGW_SCRIPT or '(없음)'}")
