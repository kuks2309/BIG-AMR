"""backend.py 단위 검증 — FakeBus 로 브링업 게이트·지령·워치독·E-stop·정착 게이트."""
import math
import os
import queue
import struct
import sys
import time
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from motor_control import protocol as P  # noqa: E402
from motor_control.backend import (  # noqa: E402
    BringupRefused,
    ModuleConfig,
    NodeSilent,
    TongyiSdoBackend,
)
from motor_control.kinematics import ModuleCommand  # noqa: E402

# ⚠ 주석 정정 (2026-07-27): 아래 값은 테스트 픽스처일 뿐 '조향 0° 절대 원점'이 아니다.
#   실기 호밍 완료 후 Seer 가 정착시킨 조향 0° 는 node3 7,882,020 / node4 7,859,062 counts
#   (= +137.45° / +137.05°, 57344 counts/°; EasyDRIVE steerOffset 138.000 / 137.250 대응)
#   — Log/homing_capture_220350.jsonl t=49.14. 여기 값과 +10,205 / +18,976 counts 차이가 있다(debt-007).
#   값 자체는 backend 게이트 산술 검증용이므로 실측 대조 전까지 변경하지 않는다(동작 불변).
HOME = {3: 7871815, 4: 7840086}
M_S_PER_UNIT = 4.0906e-5
COUNTS_PER_RAD = 57344.0 * 180.0 / math.pi
MODULES = [ModuleConfig(1, 3, HOME[3]), ModuleConfig(2, 4, HOME[4])]


class FakeBus:
    """SDO 읽기에 설정된 위치값으로 응답하는 가상 슬레이브 4대."""

    def __init__(self, positions, silent_nodes=()):
        self.sent = []
        self.rxq = queue.Queue()
        self.positions = dict(positions)
        self.silent = set(silent_nodes)

    def send(self, msg):
        self.sent.append(msg)
        node = msg.arbitration_id & 0x7F
        if node in self.silent:
            return
        if getattr(msg, "is_remote_frame", False):
            self.rxq.put(SimpleNamespace(arbitration_id=0x700 + node, data=b"\x7f",
                                         is_remote_frame=False))
            return
        data = bytes(msg.data)
        if not (0x601 <= msg.arbitration_id <= 0x604) or len(data) < 8:
            return
        idx = data[1] | (data[2] << 8)
        if data[0] == 0x40:  # 읽기 요청 → 0x43 응답
            val = self.positions.get(node, 0) if idx == P.OBJ_POSITION_ACTUAL else 0
            resp = bytes([0x43, data[1], data[2], data[3]]) + struct.pack("<i", val)
        else:  # 쓰기 → ack
            resp = bytes([0x60, data[1], data[2], data[3], 0, 0, 0, 0])
        self.rxq.put(SimpleNamespace(arbitration_id=0x580 + node, data=resp,
                                     is_remote_frame=False))

    def recv(self, timeout=None):
        try:
            return self.rxq.get(timeout=timeout)
        except queue.Empty:
            return None

    def shutdown(self):
        pass


def make_backend(bus, **kw):
    args = dict(m_s_per_unit=M_S_PER_UNIT, drive_sign=-1, counts_per_rad=COUNTS_PER_RAD,
                steer_sign=1, vel_limit_units=4889, cmd_timeout=0.15,
                steer_settle_tol_counts=int(3 * 57344), homing_tol_counts=int(5 * 57344),
                bringup_read_timeout=1.0)
    args.update(kw)
    return TongyiSdoBackend(bus, MODULES, **args)


def warm_positions():
    return {1: 100, 2: 200, 3: HOME[3], 4: HOME[4]}


def last_write(bus, node, index):
    for msg in reversed(bus.sent):
        d = bytes(msg.data) if not getattr(msg, "is_remote_frame", False) else b""
        if msg.arbitration_id == 0x600 + node and len(d) == 8 and d[0] in (0x23, 0x2B, 0x2F):
            if d[1] | (d[2] << 8) == index:
                return struct.unpack("<i", d[4:8])[0]
    return None


def all_writes(bus, node, index):
    out = []
    for msg in bus.sent:
        if getattr(msg, "is_remote_frame", False):
            continue
        d = bytes(msg.data)
        if msg.arbitration_id == 0x600 + node and len(d) == 8 and d[0] in (0x23, 0x2B, 0x2F) \
                and (d[1] | (d[2] << 8)) == index:
            out.append(struct.unpack("<i", d[4:8])[0])
    return out


def test_warm_bringup_writes_seer_init_sequence():
    bus = FakeBus(warm_positions())
    b = make_backend(bus)
    b.start()
    try:
        for n in (1, 2, 3, 4):
            assert P.CW_DRIVE_ENABLE in all_writes(bus, n, P.OBJ_CONTROLWORD)
            assert all_writes(bus, n, P.OBJ_GUARD_TIME) == [500]
        assert all_writes(bus, 1, P.OBJ_MODES) == [3]   # PV
        assert all_writes(bus, 3, P.OBJ_MODES) == [1]   # PP
        assert all_writes(bus, 3, P.OBJ_PROFILE_VELOCITY) == [30000]
    finally:
        b.shutdown()


def test_cold_bringup_refused_without_permission():
    # ⚠ 정정 (2026-07-27): 원 주석은 "콜드: 조향 실측 0 (기동 캡처 실측 상황)" 이었다.
    #   조향 0x6064 = 0 은 기동 직후 상태가 아니다 — 기동(t=0) 실측은 7,871,818 / 7,840,084 이고,
    #   0 이 되는 것은 0x60FB.4=1(RstStart) 이후의 **호밍 진행 중** 구간이다
    #   (Log/homing_capture_220350.jsonl t=18.15~49.07, 약 31 s 연속, 0x6041 bit15=0 동반).
    #   FakeBus 는 statusword 를 주지 않으므로 이 픽스처는 '콜드 부팅'이 아니라
    #   **'홈 대비 편차 > homing_tol' 케이스**로만 취급한다(backend.py:283-304 게이트 조건).
    bus = FakeBus({1: 0, 2: 0, 3: 0, 4: 0})
    b = make_backend(bus, allow_homing_motion=False)
    with pytest.raises(BringupRefused):
        b.start()
    b._running = False


def test_cold_bringup_allowed_with_permission():
    # ⚠ 정정 (2026-07-27): 함수명의 '콜드'는 실물 상태가 아니라 '홈 대비 편차 초과' 를 뜻한다
    #   (위 test_cold_bringup_refused_without_permission 주석 참조).
    #   또한 이 게이트를 통과시키는 것이 물리 스윙의 조건이 아니다 — 브링업은 웜 상태에서도
    #   0x60FB.4=1(RstStart)을 조건 없이 송신한다(backend.py:368, :294-296).
    bus = FakeBus({1: 0, 2: 0, 3: 0, 4: 0})
    b = make_backend(bus, allow_homing_motion=True)
    b.start()
    try:
        # 홈 스윙 지령은 TX 스레드가 생성 — 첫 write 까지 폴링 대기(느린 HW 레이스 방지)
        deadline = time.monotonic() + 1.0
        while last_write(bus, 3, P.OBJ_TARGET_POSITION) is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert last_write(bus, 3, P.OBJ_TARGET_POSITION) is not None  # 홈 스윙 지령 스트림
    finally:
        b.shutdown()


def test_estop_suppresses_steer_setpoint():
    """E-stop 중 조향 신규 setpoint(0x607A / CW 0x3F) 미발생 — 정지 중 물리 스윙 방지."""
    bus = FakeBus(warm_positions())
    b = make_backend(bus)
    b.start()
    try:
        b.estop(True)
        time.sleep(0.1)
        mark = len(bus.sent)
        time.sleep(0.15)
        for msg in bus.sent[mark:]:
            if getattr(msg, "is_remote_frame", False):
                continue
            d = bytes(msg.data)
            if msg.arbitration_id in (0x603, 0x604) and len(d) == 8:
                idx = d[1] | (d[2] << 8)
                assert idx != P.OBJ_TARGET_POSITION
                if idx == P.OBJ_CONTROLWORD:
                    assert (d[4] | (d[5] << 8)) != P.CW_STEER_SETPOINT
    finally:
        b.shutdown()


def test_setcommand_ignored_during_estop():
    """E-stop 중 도착한 지령은 무시 — 해제 직후 급발진 방지."""
    bus = FakeBus(warm_positions())
    b = make_backend(bus)
    b.start()
    try:
        b.estop(True)
        b.set_command([ModuleCommand(1, 0.1, 0.0), ModuleCommand(2, 0.1, 0.0)])
        snap = b.snapshot()
        assert snap["vel_units"][1] == 0 and snap["vel_units"][2] == 0
    finally:
        b.shutdown()


def test_silent_node_detected():
    bus = FakeBus(warm_positions(), silent_nodes={2})
    b = make_backend(bus, bringup_read_timeout=0.3)
    with pytest.raises(NodeSilent):
        b.start()
    b._running = False


def test_forward_command_streams_measured_units():
    bus = FakeBus(warm_positions())
    b = make_backend(bus)
    b.start()
    try:
        b.set_command([ModuleCommand(1, 0.1, 0.0), ModuleCommand(2, 0.1, 0.0)])
        time.sleep(0.1)
        u = last_write(bus, 1, P.OBJ_TARGET_VELOCITY)
        assert u is not None and abs(u - (-2445)) <= 1  # 0.1 m/s ≈ -2445 unit (실측)
        assert abs(last_write(bus, 3, P.OBJ_TARGET_POSITION) - HOME[3]) < 300
    finally:
        b.shutdown()


def test_watchdog_zeroes_velocity():
    bus = FakeBus(warm_positions())
    b = make_backend(bus, cmd_timeout=0.1)
    b.start()
    try:
        b.set_command([ModuleCommand(1, 0.1, 0.0), ModuleCommand(2, 0.1, 0.0)])
        time.sleep(0.35)  # 워치독 만료 후 여러 틱
        assert last_write(bus, 1, P.OBJ_TARGET_VELOCITY) == 0
    finally:
        b.shutdown()


def test_estop_latch():
    bus = FakeBus(warm_positions())
    b = make_backend(bus, cmd_timeout=10.0)
    b.start()
    try:
        b.set_command([ModuleCommand(1, 0.1, 0.0), ModuleCommand(2, 0.1, 0.0)])
        time.sleep(0.08)
        b.estop(True)
        time.sleep(0.08)
        assert last_write(bus, 1, P.OBJ_TARGET_VELOCITY) == 0
    finally:
        b.shutdown()


def test_steer_settle_gate_holds_drive():
    bus = FakeBus(warm_positions())  # 조향 실측은 홈에 고정(FakeBus 는 안 움직임)
    b = make_backend(bus, cmd_timeout=10.0)
    b.start()
    try:
        # 크랩 90° 지령 → 목표(홈+5.16M) vs 실측(홈) 편차 > tol → 구동 0 강제
        b.set_command([ModuleCommand(1, 0.1, math.pi / 2), ModuleCommand(2, 0.1, math.pi / 2)])
        time.sleep(0.15)
        assert last_write(bus, 1, P.OBJ_TARGET_VELOCITY) == 0
        assert abs(last_write(bus, 3, P.OBJ_TARGET_POSITION) - (HOME[3] + 5160960)) < 3000
        assert b.snapshot()["settling"] is True
    finally:
        b.shutdown()


def test_guard_rtr_streams():
    bus = FakeBus(warm_positions())
    b = make_backend(bus)
    b.start()
    try:
        time.sleep(0.15)
        rtrs = [m for m in bus.sent if getattr(m, "is_remote_frame", False)]
        assert {m.arbitration_id for m in rtrs} == {0x701, 0x702, 0x703, 0x704}
    finally:
        b.shutdown()


def _wait(pred, timeout=1.0):
    deadline = time.monotonic() + timeout
    while not pred() and time.monotonic() < deadline:
        time.sleep(0.01)
    return pred()


def test_freewheel_disables_drive_servo():
    """freewheel(True) → 구동 노드 servo-off(0x6040=CW_DISABLE) + 구동 지령 송신 정지."""
    bus = FakeBus(warm_positions())
    b = make_backend(bus, cmd_timeout=10.0)
    b.start()
    try:
        b.set_command([ModuleCommand(1, 0.1, 0.0), ModuleCommand(2, 0.1, 0.0)])
        time.sleep(0.08)
        b.freewheel(True)
        # 노드 2(전이 루프 마지막 송신)까지 기다리면 노드 1은 이미 완료 보장
        assert _wait(lambda: P.CW_DISABLE in all_writes(bus, 2, P.OBJ_CONTROLWORD))
        assert P.CW_DISABLE in all_writes(bus, 1, P.OBJ_CONTROLWORD)
        assert b.snapshot()["freewheel"] is True
        # servo-off 확정 후 구동 Target_velocity write 정지
        n1 = len(all_writes(bus, 1, P.OBJ_TARGET_VELOCITY))
        time.sleep(0.2)
        assert len(all_writes(bus, 1, P.OBJ_TARGET_VELOCITY)) == n1
    finally:
        b.shutdown()


def test_freewheel_release_reenables_drive():
    """freewheel(False) → 구동 노드 재-enable(0x86) + PV 모드(0x6060=3) 재설정."""
    bus = FakeBus(warm_positions())
    b = make_backend(bus, cmd_timeout=10.0)
    b.start()
    try:
        b.freewheel(True)
        assert _wait(lambda: P.CW_DISABLE in all_writes(bus, 2, P.OBJ_CONTROLWORD))
        b.freewheel(False)
        # 해제 후 구동 controlword 마지막 write = 재-enable(0x86). 노드 2까지 완료 대기
        assert _wait(lambda: all_writes(bus, 2, P.OBJ_CONTROLWORD)[-1] == P.CW_DRIVE_ENABLE)
        assert all_writes(bus, 1, P.OBJ_CONTROLWORD)[-1] == P.CW_DRIVE_ENABLE
        assert all_writes(bus, 1, P.OBJ_MODES)[-1] == 3   # PV 재설정
        assert all_writes(bus, 2, P.OBJ_MODES)[-1] == 3
        assert b.snapshot()["freewheel"] is False
    finally:
        b.shutdown()


def test_setcommand_ignored_during_freewheel():
    """freewheel 중 도착한 지령 무시 — 해제 직후 급발진 방지."""
    bus = FakeBus(warm_positions())
    b = make_backend(bus)
    b.start()
    try:
        b.freewheel(True)
        b.set_command([ModuleCommand(1, 0.1, 0.0), ModuleCommand(2, 0.1, 0.0)])
        snap = b.snapshot()
        assert snap["vel_units"][1] == 0 and snap["vel_units"][2] == 0
    finally:
        b.shutdown()


def test_freewheel_leaves_steer_holding():
    """freewheel(구동축만) 중에도 조향은 setpoint 계속 송신(현 위치 hold)."""
    bus = FakeBus(warm_positions())
    b = make_backend(bus, cmd_timeout=10.0)
    b.start()
    try:
        b.freewheel(True)
        # 구동축 servo-off 전이가 적용된 뒤부터 조향 지속성 측정(구동 노드 CW_DISABLE 대기)
        assert _wait(lambda: P.CW_DISABLE in all_writes(bus, 1, P.OBJ_CONTROLWORD))
        n3 = len(all_writes(bus, 3, P.OBJ_TARGET_POSITION))
        time.sleep(0.2)
        assert len(all_writes(bus, 3, P.OBJ_TARGET_POSITION)) > n3  # 조향 setpoint 지속
    finally:
        b.shutdown()
