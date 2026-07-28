#!/usr/bin/env python3
"""Tongyi 4축 AMR CAN 계층 — SDO 인코딩·조향/구동 지령·호밍·폴링.

**Qt 를 알지 못한다.** 결과는 생성자가 받은 콜백으로만 나간다(`log`·`on_frames`·
`on_homing_done`). 화면이 무엇을 하든 이 파일은 관여하지 않으며, 반대로 이 파일이
드라이브에 보내는 바이트는 화면 사정으로 바뀌지 않는다.

값·순서의 근거는 코드가 아니라 README.md 가 든다. 여기엔 의미만 적는다.
"""
from __future__ import annotations

import os
import sys
import threading
import time

from callbacks import emit

# ── 상수 ───────────────────────────────────────────────────────────────────
SEER_BUS, MOTOR_BUS = 0, 2          # 판다 버스 번호
SEER_GATE, CAN_KBPS = 30, 250       # safety_mode, 버스 속도
COUNTS_PER_DEG = 57344              # 조향 counts/도
STEER_HOME = {3: 7871815, 4: 7840086}   # 조향 0° 기준 counts (debt-007 미판정)
VEL_PER_MMPS, VEL_MAX_UNITS = 24.447, 4889   # 구동 raw 환산, 상한(≈0.2 m/s)
STEER_LIMIT_DEG = 90.0              # 조향 지령 허용 범위 ±90°

STEER_NODES = (3, 4)                # 조향축 — 기계적 원점이 있어 호밍 대상
DRIVE_NODES = (1, 2)                # 구동축 — 원점이 없어 호밍하지 않는다

# SDO abort 코드 — 드라이브가 쓰기를 거부한 사유. 진단 전용이며 동작에 관여하지 않는다.
_ABORT = {
    0x05040001: "명령 지정자 불량",
    0x06010002: "읽기 전용 객체에 쓰기",
    0x06020000: "객체 없음",
    0x06090011: "서브인덱스 없음",
    0x06090030: "값 범위 초과",
    0x06070010: "데이터 길이 불일치",
    0x08000020: "저장 불가",
    0x08000022: "현재 장치 상태에서 전송 불가",
}


# ── 순수 환산 (하드웨어 무의존 — 회귀 테스트가 여기를 고정한다) ─────────────
def steer_counts(node: int, deg: float):
    """가동범위 클램프 후 조향 절대위치 counts 를 낸다. 반환 `(적용된 각도, counts)`.

    범위 밖 각도는 보내지 않고 ±90° 로 자른다.
    """
    deg = max(-STEER_LIMIT_DEG, min(STEER_LIMIT_DEG, deg))
    return deg, int(round(STEER_HOME[node] + deg * COUNTS_PER_DEG))


def drive_units(mmps: float, raw_sign: int) -> int:
    """구동 속도 지령 raw(0x60FF) 환산 + 상한 클램프."""
    return max(-VEL_MAX_UNITS, min(VEL_MAX_UNITS,
                                   int(round(raw_sign * mmps * VEL_PER_MMPS))))


# 조그 방향표 — (조향각°, 구동 raw 부호, 직접실측 여부)
#   직접 실측 2건만이 1차 근거다:
#     ① 조향 홈(0°) + raw 음수 → 전진(+x)
#     ② 조향 +90° + raw 양수 → 왼쪽(+y)  (IMU ay 실증)
#   나머지는 ①② 를 만족하는 모델 -sign(raw)x(cos0, -sin0) 에서 **도출**한 값이다.
JOG = {
    "전진":     (0.0,  -1, True),    # ①
    "후진":     (0.0,  +1, True),    # ① 의 raw 부호 반전
    "좌 크랩":  (90.0, +1, True),    # ②
    "우 크랩":  (90.0, -1, True),    # ② 의 raw 부호 반전
    "좌전 45°": (-45.0, -1, False),  # 도출
    "우전 45°": (45.0,  -1, False),  # 도출
    "좌후 45°": (45.0,  +1, False),  # 도출
    "우후 45°": (-45.0, +1, False),  # 도출
}

_KIT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "docking_field_kit")


def panda_class():
    """comma.ai panda 라이브러리 로드 (필드킷 동봉본)."""
    if _KIT not in sys.path:
        sys.path.insert(0, _KIT)
    from panda import Panda
    return Panda


class TongyiCan:
    """판다(CAN relay) 경유 드라이브 제어. 화면·Qt 와 무관하다.

    소유하는 것: USB 핸들(`panda`), 제어권 상태(`running`), 폴링·조그·호밍 스레드,
    실측 조향각(`_meas_deg`), 상태워드(`_status`).

    콜백은 **어느 스레드에서든** 불릴 수 있다. 호출부가 스레드 경계를 책임진다
    (GUI 라면 Qt 시그널 emit 을 넘긴다). 창이 이미 파괴돼 콜백이 `RuntimeError` 를
    던지면 조용히 삼킨다 — 종료 중에 CAN 해제가 로그 때문에 깨지면 안 된다.
    """

    HOMING_SPEED = 2500        # 0x6099:00, 0.1 r/min 단위 → 250 r/min
    HOMING_TIMEOUT_S = 90.0    # 실측 소요 약 31 s
    HOMING_START_S = 10.0      # 개시(bit15=0) 를 기다리는 창
    HOMING_RETURN_S = 30.0     # 원점→0° 복귀 대기 상한 (실측 약 3 s — 정본 캡처·실기 일치)
    STEER_RESEND_HZ = 10.0     # 정착 전 setpoint 재송신 주기
    SETTLE_TIMEOUT_S = 6.0     # 조향 정착 대기 상한

    def __init__(self, log=None, on_frames=None, on_homing_done=None):
        self.panda = None
        self.running = False          # 제어권 보유 + 폴링 중
        self.homing = False
        self._th = None
        self._can_lock = threading.Lock()   # 폴링·조그가 버스를 공유한다
        self._jog_th = None
        self._jog_stop = False
        self._meas_deg = {3: None, 4: None}
        self._meas_at = {3: 0.0, 4: 0.0}   # 그 축 실측이 갱신된 시각(신선도 판정용)
        self._status = {}             # node -> 0x6041 상태워드 (호밍 완료 판정용)
        self._aborts = set()          # 이미 보고한 SDO 거부(같은 것 반복 방지)
        self._log_cb = log
        self._frames_cb = on_frames
        self._homing_done_cb = on_homing_done

    # ── 콜백 경계 (규약은 `callbacks.emit`) ──────────────────────────────
    def _log(self, msg: str) -> None:
        """로그 한 줄. 이름을 `MainWindow.log`(위젯에 쓴다)와 구분해 둔다."""
        emit(self._log_cb, msg)

    # ── 장치 ────────────────────────────────────────────────────────────
    @staticmethod
    def list_pandas():
        """연결 가능한 판다 시리얼 열거 — USB 를 열지 않는다(목록만)."""
        return panda_class().list()

    def open_usb(self) -> dict:
        """USB 를 연다. 상태만 읽으므로 모터에 영향이 없다. 반환은 health dict."""
        self.panda = panda_class()()
        return self.panda.health()

    def close_usb(self) -> None:
        if self.panda is not None:
            try:
                self.panda.close()
            except Exception:
                pass
            self.panda = None

    def take(self, on: bool) -> None:
        """제어권 획득/반환. 획득하면 Seer 로부터 릴레이를 가져오고 폴링을 시작한다."""
        if self.panda is None:
            return
        P = panda_class()
        if on:
            self._log("⚠ 제어권 획득 — 릴레이 intercept, Seer 에서 가져옴")
            self.panda.set_safety_mode(SEER_GATE, 0)
            for b in (SEER_BUS, MOTOR_BUS):
                self.panda.set_can_speed_kbps(b, CAN_KBPS)
                self.panda.set_can_enable(b, True)
            self.panda._handle.controlWrite(P.REQUEST_OUT, 0xe9, 1, 0, b"")   # auth=PC
            self.panda._handle.controlWrite(P.REQUEST_OUT, 0xe8, 1, 0, b"")   # intercept
            self.running = True
            self._th = threading.Thread(target=self._loop, daemon=True, name="poll")
            self._th.start()
            self._log("제어권 획득 완료 — 모터 값 폴링 시작")
        else:
            self._jog_stop = True
            try:
                self.drive(0)          # 반환 전 반드시 정지
            except Exception:
                pass
            self.running = False
            if self._th is not None:
                self._th.join(timeout=1.0)
                self._th = None
            self.panda._handle.controlWrite(P.REQUEST_OUT, 0xe9, 0, 0, b"")   # auth=Seer
            self.panda._handle.controlWrite(P.REQUEST_OUT, 0xe8, 0, 0, b"")   # passthrough
            self.panda.set_safety_mode(0, 0)
            self._log("제어권 반환 — passthrough (USB 유지)")

    # ── 지령 ────────────────────────────────────────────────────────────
    def sdo_write(self, node: int, idx: int, val: int, size: int, sub: int = 0):
        """SDO expedited 쓰기. 폴링 스레드와 버스를 공유하므로 락으로 직렬화한다.

        `sub` 는 서브인덱스 — 호밍 트리거 `0x60FB:04` 처럼 0 이 아닌 것이 있다.
        """
        cmd = {1: 0x2F, 2: 0x2B, 4: 0x23}[size]
        payload = (val & 0xFFFFFFFF).to_bytes(4, "little")[:size]
        data = bytes([cmd, idx & 0xFF, idx >> 8, sub]) + payload + b"\x00" * (4 - size)
        with self._can_lock:
            self.panda.can_send(0x600 + node, data[:8], MOTOR_BUS)

    def drive(self, units: int):
        """구동 노드에 속도 지령(0x60FF). units=0 이면 정지."""
        for n in DRIVE_NODES:
            self.sdo_write(n, 0x60FF, units, 4)

    def steer_axis(self, node: int, deg: float) -> float:
        """한 축에만 절대위치 지령(0x607A) + 즉시 적용(0x6040=0x3F). 환산은 `steer_counts`."""
        deg, counts = steer_counts(node, deg)
        self.sdo_write(node, 0x607A, counts, 4)
        self.sdo_write(node, 0x6040, 0x3F, 2)
        return deg

    def steer_to(self, deg: float) -> float:
        """조향 두 축에 절대위치 지령(0x607A) + 즉시 적용(0x6040=0x3F).

        범위 밖 각도는 보내지 않고 ±90° 로 자른다(`steer_counts`).
        **단계로 쪼개지 않는다** — 최종 절대 목표를 그대로 보내고 이동 프로파일은
        드라이브가 수행한다. 근거는 README.md §동작 규칙.
        """
        for n in STEER_NODES:
            deg = self.steer_axis(n, deg)
        return deg

    def meas_angle(self, node: int):
        """그 축의 실측 조향각(판다 직독). 없으면 None."""
        return self._meas_deg.get(node)

    # ── 조그 실행 (crab: 조향 → 정착 확인 → 구동) ──────────────────────
    def jog_busy(self) -> bool:
        return self._jog_th is not None and self._jog_th.is_alive()

    def stop_drive(self) -> None:
        """정지 — 구동 0. 조향은 현 위치를 유지한다.

        이름에 `drive` 를 박아 둔다. `SeerStatus.stop()` 은 폴링 스레드를 멈출 뿐인데,
        이쪽은 **바퀴를 세운다** — 두 `stop` 을 헷갈리면 사고가 난다.
        """
        self._jog_stop = True
        self.drive(0)

    def start_jog(self, label: str, steer_deg: float, raw_sign: int,
                  mmps: float, tol: float) -> None:
        """조그 실행을 별도 스레드로 띄운다. 속도·허용치는 호출부(화면)가 정한다."""
        self._jog_stop = False
        self._jog_th = threading.Thread(target=self._jog_run, name="jog", daemon=True,
                                        args=(label, steer_deg, raw_sign, mmps, tol))
        self._jog_th.start()

    def _jog_run(self, label: str, steer_deg: float, raw_sign: int,
                 mmps: float, tol: float):
        """crab 순서: 구동 0 → 조향 지령 → 정착 확인 → 구동."""
        try:
            self.drive(0)                                   # 조향 전 반드시 구동 0
            tgt = self.steer_to(steer_deg)
            self._log(f"조그 '{label}' — 조향 {tgt:+.0f}° 지령, 정착 대기")
            if not self.wait_settle(tgt, tol):
                self._log(f"조향 정착 실패(실측 N3 {self._meas_deg.get(3)} / "
                         f"N4 {self._meas_deg.get(4)}) — 구동 취소")
                self.drive(0)
                return
            if self._jog_stop:
                self.drive(0)
                return
            units = drive_units(mmps, raw_sign)
            self.drive(units)
            self._log(f"조향 정착 — 구동 raw={units:+d} ({mmps:.0f} mm/s)")
        except Exception as exc:
            self._log(f"조그 중단: {type(exc).__name__}: {exc}")
            try:
                self.drive(0)
            except Exception:
                pass

    def wait_settle(self, target: float, tol: float, timeout: float = None,
                    resend: bool = True) -> bool:
        """조향 정착 대기 — **두 축(N3·N4) 모두** 허용치 안에 들어와야 한다.

        crab 은 앞뒤가 같은 각이어야 성립하므로 한 축만 확인하면 뒷바퀴가 어긋난 채
        구동에 들어간다. 시간 초과면 False(= 추종 실패, 호출부가 구동을 취소한다).

        **정착 전까지 setpoint 를 재송신한다**(`resend`). 한 축이 첫 지령을 놓치면
        그 축은 영영 따라오지 않는다 — 2026-07-29 실기에서 45° 크랩 중 node4 가 그렇게
        멈춰 있었고, 구동은 이 정착 판정이 막았다. 구 GUI 는 setpoint 를 50 Hz 로 계속
        보내 이런 결손이 20 ms 만에 스스로 메워졌다. 그 성질을 **지령이 살아있는 동안**
        으로 좁혀 되살린 것이다(유휴 시에는 여전히 상태 읽기만 한다).

        **낡은 실측으로는 통과하지 않는다** — 대기 시작(`t0`) 이후에 갱신된 값만 본다.
        그러지 않으면 지령 전 자세가 우연히 목표 근처일 때 즉시 통과한다.

        A/B 실측(2026-07-29): 한 축에만 −10° 를 넣어 결손을 만든 뒤
        재송신 없음 → 6 s 내내 미복구 · 재송신 → 0.5 s 만에 양축 정착.
        """
        if timeout is None:
            timeout = self.SETTLE_TIMEOUT_S
        t0 = time.time()
        next_send = 1.0 / self.STEER_RESEND_HZ   # 첫 표본이 올 틈을 준 뒤 재송신 시작
        while time.time() - t0 < timeout:
            if self._jog_stop:
                return False
            # **대기 시작 이후에 들어온 표본만** 인정한다. 낡은 값을 그대로 보면 지령 전
            # 자세가 우연히 목표 근처일 때 즉시 통과해 버린다 — 실기에서 호밍 뒤
            # "조향 0° 복귀 확인" 이 거짓으로 난 원인이다(바퀴는 리밋에 있었다).
            # 탐색 구간처럼 실측이 끊기는 동안에는 통과하지 않고 계속 기다린다.
            cur = [self._meas_deg.get(n) if self._meas_at.get(n, 0.0) >= t0 else None
                   for n in STEER_NODES]
            if all(c is not None and abs(target - c) <= tol for c in cur):
                return True
            if resend and time.time() - t0 >= next_send:
                self.steer_to(target)
                next_send += 1.0 / self.STEER_RESEND_HZ
            time.sleep(0.05)
        return False

    # ── 조향 원점 복귀(호밍) ────────────────────────────────────────────
    def start_homing(self, tol: float) -> None:
        """호밍 실행을 별도 스레드로 띄운다. 확인 절차는 호출부(화면)가 맡는다."""
        self.homing = True
        threading.Thread(target=self._homing_run, name="homing", daemon=True,
                         args=(tol,)).start()

    def _homing_run(self, tol: float):
        """조향 노드 3·4 호밍 — 리밋 원점 확립 **뒤 조향 0° 복귀까지**.

        구동 노드(1·2)는 기계적 원점이 없어 호밍하지 않는다 — 조향축에만 지령한다.
        `0x6098`(homing method)은 **쓰지 않는다**. 드라이브 저장값을 그대로 쓰며,
        덮어쓰면 리셋 모드가 꺼져 호밍 자체가 동작하지 않는다.

        탐색 중에도 `0x6064` 는 **실제 엔코더 값을 보고한다**(2026-07-29 실기). 그래서 이
        구간의 각도 표시를 통째로 끄지 않는다 — 간헐적으로 섞이는 정확한 0 만 걸러낸다
        (`decode_frames`). 바퀴 그림이 호밍 스윙을 그대로 따라간다.

        **복귀를 우리가 직접 지령해야 하는 이유** — 호밍이 끝나는 지점(`0x6041` bit15
        0→1)에서 바퀴는 **원점(리밋)에 있다**(실기 캡처: 완료 직후 `0x6064`=596 counts
        ≈ +0.01°, 이후 3.0 s 만에 +137.45° 직진 도달). Seer 는 `0x607A` 를 ~50 Hz 로
        끊김 없이 스트리밍하므로 위치 루프가
        알아서 직진으로 되돌리지만, **우리는 유휴 시 상태 읽기만 하고 위치 목표를 물고
        있지 않다**(`_loop` 는 읽기 전용). 그래서 복귀를 1회 명시적으로 보낸다.
        보내지 않으면 바퀴가 리밋에 얹힌 채 남고, 그 방향 지령이 막힌다.
        """
        try:
            self._jog_stop = False
            self.drive(0)                        # 호밍 전 구동은 반드시 0
            self._status.clear()                 # 직전 상태워드를 완료로 오독하지 않도록
            for n in STEER_NODES:
                self.sdo_write(n, 0x6040, 0x86, 2)                 # 축 준비
                self.sdo_write(n, 0x6099, self.HOMING_SPEED, 4)    # 호밍 속도
                self.sdo_write(n, 0x60FB, 1, 1, sub=4)             # 여기서 움직이기 시작한다
            self._log("호밍 개시 — 조향 2축. 완료까지 30초 이상 걸립니다.")
            ok, why = self.wait_homed()
            if not ok:
                self._log(f"호밍 미확인 — {why}")
                return
            self._log(f"원점 도달 — {why} 이어서 조향 0° 로 복귀합니다(100° 이상 회전).")
            for n in STEER_NODES:
                self.steer_axis(n, 0.0)
            if self.wait_settle(0.0, tol, timeout=self.HOMING_RETURN_S):
                self._log("호밍 완료 — 조향 0° 복귀 확인")
            else:
                self._log(f"⚠ 원점은 확립됐으나 0° 복귀 미확인(실측 N3 {self._meas_deg.get(3)} / "
                          f"N4 {self._meas_deg.get(4)}) — 바퀴 자세를 육안으로 확인하세요.")
        except Exception as exc:
            self._log(f"호밍 중단: {type(exc).__name__}: {exc}")
        finally:
            self.homing = False
            emit(self._homing_done_cb)

    def wait_homed(self):
        """상태워드(0x6041) bit15 로 완료를 판정한다. 반환 `(성공, 사유)`.

        **bit15 가 1 인 것만 보면 안 된다** — 이전에 호밍을 마친 축은 시작 전부터 1 이라
        곧바로 "완료"로 읽힌다. 그래서 먼저 두 축이 0(진행 중)이 되는 것을 확인하고,
        그 다음에 1 로 돌아오는 것을 기다린다. 0 을 한 번도 못 보면 성공이라고 하지 않는다.
        """
        BIT15 = 1 << 15
        t0 = time.time()
        started = set()
        while time.time() - t0 < self.HOMING_START_S:
            for n in STEER_NODES:
                st = self._status.get(n)
                if st is not None and not (st & BIT15):
                    started.add(n)
            if started >= set(STEER_NODES):
                break
            time.sleep(0.1)
        if started < set(STEER_NODES):
            missing = sorted(set(STEER_NODES) - started)
            return False, (f"개시 신호(bit15=0)를 못 봤습니다 — 노드 {missing}. "
                           f"움직이지 않았는지 육안으로 확인하세요.")
        while time.time() - t0 < self.HOMING_TIMEOUT_S:
            if all((self._status.get(n) or 0) & BIT15 for n in STEER_NODES):
                return True, f"{time.time() - t0:.0f}초 소요."
            time.sleep(0.1)
        return False, f"{self.HOMING_TIMEOUT_S:.0f}초 안에 완료 신호가 오지 않았습니다."

    # ── 폴링 (모터 값 읽기 전용 — 지령은 보내지 않는다) ────────────────
    def _loop(self):
        """상태 읽기 루프 — `0x6064`(위치)·`0x606C`(속도)·`0x6078`(전류)·`0x6041`(상태워드).

        `0x6041` 은 화면에 띄우지 않고 호밍 완료 판정(bit15)에만 쓴다.

        ⚠ 읽기만 한다. `0x60FF`(속도지령)·`0x607A`(위치지령)는 보내지 않는다.

        **호밍 중에도 status 는 계속 읽는다.** 조향축(3·4)의 위치·상태워드를 빠른 주기로,
        나머지(구동축·속도·전류)는 `SLOW_EVERY` 주기마다 섞어 읽는다. 두 가지가 다 필요하다 —
        `0x6041` 이 끊기면 완료 판정이 서지 않고, `0x6064` 가 성기면 복귀 스윙을 놓친다
        (탐색 구간의 `0x6064` 응답은 대부분 0 이고 실값은 드물게 섞인다).
        """
        P = panda_class()
        FAST = [(n, idx) for n in STEER_NODES for idx in (0x6064, 0x6041)]
        FULL = [(n, idx) for n in (1, 2, 3, 4)
                for idx in (0x6064, 0x606C, 0x6078, 0x6041)]
        SLOW_EVERY = 8          # 호밍 중 전체 집합을 섞는 주기
        tick = 0
        while self.running:
            try:
                # heartbeat(0xf3) 를 매 루프 보낸다.
                # 끊기면 펌웨어가 fail-safe 로 intercept 를 푼다(임계는 초 단위).
                self.panda._handle.controlWrite(P.REQUEST_OUT, 0xf3, 0, 0, b"")
                if self.homing:
                    req = FAST if tick % SLOW_EVERY else FAST + FULL
                    gather, idle = 0.012, 0.008
                else:
                    req, gather, idle = FULL, 0.08, 0.12
                tick += 1
                with self._can_lock:
                    for n, idx in req:
                        self.panda.can_send(
                            0x600 + n,
                            bytes([0x40, idx & 0xFF, idx >> 8, 0, 0, 0, 0, 0]),
                            MOTOR_BUS)
                time.sleep(gather)
                out = {}
                for addr, _t, dat, bus in self.panda.can_recv():
                    if bus != MOTOR_BUS or not (0x581 <= addr <= 0x584) or len(dat) < 8:
                        continue
                    node = addr - 0x580
                    idx = dat[1] | (dat[2] << 8)
                    if dat[0] == 0x43:                       # 4 바이트 읽기 응답
                        val = int.from_bytes(dat[4:8], "little", signed=True)
                    elif dat[0] == 0x4B:                     # 2 바이트 읽기 응답
                        val = int.from_bytes(dat[4:6], "little", signed=True)
                    elif dat[0] == 0x80:                     # SDO abort — 드라이브가 거부했다
                        code = int.from_bytes(dat[4:8], "little")
                        key = (node, idx, dat[3], code)
                        if key not in self._aborts:          # 같은 거부는 1회만 (버스가 반복한다)
                            self._aborts.add(key)
                            self._log(
                                f"SDO 거부 N{node} 0x{idx:04X}:{dat[3]:02X} "
                                f"→ abort 0x{code:08X} ({_ABORT.get(code, '사유 미상')})")
                        continue
                    else:
                        continue
                    out.setdefault(node, {})[idx] = val
                if out:
                    emit(self._frames_cb, out)
            except Exception as exc:
                self.running = False
                self._log(f"폴링 중단: {type(exc).__name__}: {exc}")
                return
            time.sleep(idle)

    def decode_frames(self, data: dict):
        """폴링 프레임 → 상태 반영 + 표시값 산출. 반환 `({node: (deg, rpm, amp)}, 각도갱신여부)`.

        counts→도, 0.1 r/min, 0.01 A 환산이 여기 있다. 화면은 결과만 받아 그린다.

        **`0x6064` 가 정확히 0 인 표본은 버린다** — 실측 글리치다. 그대로 쓰면 바퀴 그림이
        −137° 로 튀어 실제 자세를 오해하게 만든다.

        근거(2026-07-29 실기, 우리 GUI 가 intercept 를 쥐고 직접 폴링):
        호밍 중에도 `0x6064` 는 **실제 엔코더 값을 계속 보고**하고(node3 7,871,817 /
        node4 7,840,084 대다수), 정확한 0 이 **간헐적으로** 섞인다. 그래서 호밍 구간의
        표시를 통째로 끄지 않는다. 리밋에 실제로 있을 때의 판독도 596·543 처럼 0 이
        아니므로, **정확한 0** 은 실위치가 아니라 sentinel 로 본다.

        ⚠ 2026-07-27 캡처(`Log/homing_capture_220350.jsonl`)에서는 같은 구간 3,105/3,105
        표본이 전부 0 이었다. 그것은 **Seer 의 폴링에 대한 응답**을 수동청취한 것이라
        우리 폴링 경로와 조건이 다르다 — 그 성질을 우리 경로로 옮긴 것이 잘못이었다
        (claude-mistake 2026-07-29-004). 간헐 0 의 발생원(드라이브 재기준 vs 두 마스터
        폴링 경합)은 **미확정**이다(debt-017) — 어느 쪽이든 0 필터로 해결된다.
        """
        rows, angles = {}, {}
        for node, vals in data.items():
            deg = rpm = amp = None
            if 0x6041 in vals:
                self._status[node] = vals[0x6041]
            raw = vals.get(0x6064)
            if raw is not None and node in STEER_HOME and raw != 0:
                deg = (raw - STEER_HOME[node]) / COUNTS_PER_DEG
                angles[node] = deg
                self._meas_deg[node] = deg
                self._meas_at[node] = time.time()
            if 0x606C in vals:
                rpm = vals[0x606C] / 10.0                    # 0.1 r/min
            if 0x6078 in vals:
                amp = vals[0x6078] / 100.0                   # 0.01 A
            rows[node] = (deg, rpm, amp)
        return rows, bool(angles)
