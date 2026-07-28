"""AmrTestController — backend 수명주기 + 램프 조정. Qt 무의존(단위 테스트 가능).

설계 원칙:
  - 프로토콜·안전게이트는 정본 `TongyiSdoBackend` 가 소유한다. 본 클래스는 조정만 한다.
  - backend 는 `drive_sign=+1`·`steer_sign=+1` **항등 변환**으로 구성한다
    (ADR 2026-07-27-amr-test-gui §3) → 조향 counts = home + deg×57344, 구동 raw = units 그대로.
    방향 의미는 전부 `modes.py` 인용 테이블이 소유한다.
  - 조향 지령은 **반드시** `SteerRamp` 를 통과한다. 목표각을 직접 송신하는 경로는 없다.
"""
from __future__ import annotations

import math
import threading
import time

from . import modes as M
from .constants import (COUNTS_PER_DEG, COUNTS_PER_M, COUNTS_PER_RAD,
                        DEFAULT_SPEED_MMPS, DRIVE_NODES, DRIVE_TO_STEER,
                        HOMING_TOL_DEG, M_S_PER_UNIT, RAMP_STEP_DEG,
                        RAMP_STEP_TIMEOUT_S, STEER_HOME_COUNTS, STEER_NODES,
                        STEER_SETTLE_TOL_DEG, VEL_MAX_UNITS, VEL_PER_MMPS,
                        WHEEL_X, WHEEL_Y, counts_to_deg, mmps_to_units, units_to_mps)
from .motor_control_import import (BringupRefused, ModuleCommand, ModuleConfig,
                                   NodeSilent, TongyiSdoBackend)
from .ramp import FAULT, RAMPING, SETTLED, SteerRamp

ROLE = {1: "FrontWalk(구동)", 2: "RearWalk(구동)", 3: "FrontSteer(조향)", 4: "RearSteer(조향)"}

# 피드백 신선도 임계 — 이보다 오래된 조향 실측은 '없는 것'으로 취급한다.
# backend TX 루프는 격틱(50 Hz의 절반 = 25 Hz)마다 전 노드 0x6064 를 읽으므로 정상 갱신 주기는 40 ms.
# ⚠ 이 게이트가 없으면 RX 만 죽은 상태(판다 버퍼 기아·freeze)에서 `pos` 가 마지막 값으로 굳고,
#   backend 는 pos 를 None 으로 되돌리지 않으므로 램프가 영원히 SETTLED·구동 허용으로 남는다.
FEEDBACK_STALE_S = 0.5


class AmrTestController:
    """GUI 와 정본 backend 사이의 유일한 조정 계층."""

    def __init__(self, *, logger=print):
        self.log = logger
        self.backend: TongyiSdoBackend | None = None
        self.bus = None
        # 조향축마다 독립 램프. 전륜(node3)·후륜(node4)을 따로 지령할 수 있어야 하므로
        # (사용자 지시 2026-07-27 "전륜 후륜 나누어서 작동하게") 스칼라 1개가 아니라 축별로 둔다.
        # 축별 램프는 **각자 자기 축의 실측만** 보므로, 한 축이 뒤처지면 그 축만 전진을 멈춘다.
        self.ramps = {n: SteerRamp(step_deg=RAMP_STEP_DEG, settle_tol_deg=STEER_SETTLE_TOL_DEG,
                                   step_timeout_s=RAMP_STEP_TIMEOUT_S) for n in STEER_NODES}
        self._lock = threading.Lock()
        self._mode = M.STOP
        self._speed_mmps = DEFAULT_SPEED_MMPS
        self._slider_deg = {n: 0.0 for n in STEER_NODES}
        self._estop = False
        self._last_units = 0
        self._last_error = ""
        # 구동 실측 속도: 0x6064 변위/시간. backend 는 속도 오브젝트(0x606C)를 폴하지 않으므로
        # 엔코더 변위에서 도출한다(driver_node 의 오도메트리와 같은 방식). EMA 로 폴링 지터 완화.
        self._prev_drive: dict[int, tuple[int, float]] = {}
        self._meas_mmps: dict[int, float] = {n: 0.0 for n in DRIVE_NODES}
        # 조향 홈 기준 — **런타임 값**. config 상수는 초기값일 뿐이다.
        # ⚠ config 의 "전원 사이클 불변" 서술과 2026-07-27 관측은 **미판정 모순(debt-007)** 이다.
        #   [관측] 전원 재인가 후 조향 0x6064 가 ≈0 인데 바퀴는 물리적으로 직진이었다
        #     (Seer 1040 position≈0·calib=True·육안 0° 3중 확인).
        #   ⚠ 2026-07-27 정정(원 주석은 이 관측을 ~~"실측으로 **반증**됐다"~~ 고 단정했다):
        #     정본 src/Actuators/motor_control/config/tongyi_amr.yaml:26-29 는 반증이 아니라
        #     **미판정** 이라고 명시한다 — "둘 중 하나가 틀렸다: (a) 판다의 조향 0x6064 read 가
        #     오염됐다 (b) 호밍 후 드라이브가 위치 기준을 0 으로 재설정한다 … 미판정 상태이므로
        #     어느 쪽으로도 값을 고치지 않는다."
        #     또한 "전원 재인가 후 0x6064 ≈ 0" 자체는 설계 정본이 **정상으로 예측한 값**이다
        #     (docs/ros2_driver/2026-07-09-design-inputs.md:56 "부팅 직후 전 노드 0x6064 ≈ 0
        #      (홈값 아님, 정상)", :81 "매 기동 시 브링업 스윙 필요"). 같은 :56 은 137.3° 스윙도
        #     매 기동의 정규 절차로 적는다 → "반증"·"137° 스윙 = 사고와 같은 값"은 근거보다 강한 단정.
        #   판정에 필요한 측정: 전원 재인가 직후 (a) 판다 read 0x6064 (b) Seer 1040 position
        #     (c) 육안 조향각 을 조향·구동 노드 동시에 채취해 조향만 어긋나는지 재확인.
        #   [안전 조치는 유지] 어느 쪽이 참이든 상수 홈을 무비판 신뢰하면 위험하므로
        #   홈은 `capture_home()` 으로 실측 캡처할 수 있어야 한다(동작 변경 없음).
        self.steer_home: dict[int, int] = dict(STEER_HOME_COUNTS)
        self.home_source = "config(전원사이클 거동 미판정 — debt-007, 실측 캡처 권장)"

    # ── 수명주기 ────────────────────────────────────────────────────────────
    def connect(self, bus_factory, *, allow_homing_motion: bool = False):
        """bus_factory() 로 버스를 만들고 backend 를 브링업한다.

        실패 시 버스를 반드시 정리(release)하고 예외를 그대로 올린다 — 부분 취득 상태를 남기지 않는다.
        """
        if self.backend is not None:
            raise RuntimeError("이미 연결되어 있습니다")
        bus = bus_factory()
        backend = None
        try:
            # 홈은 런타임 값을 쓴다 — 이전에 실측 캡처했다면 재연결에도 유지된다.
            modules = [ModuleConfig(d, s, self.steer_home[s])
                       for d, s in zip(DRIVE_NODES, STEER_NODES)]
            backend = TongyiSdoBackend(
                bus, modules,
                m_s_per_unit=M_S_PER_UNIT,
                drive_sign=+1,                      # 항등 — 부호 의미는 modes.py 소유
                counts_per_rad=COUNTS_PER_RAD,
                steer_sign=+1,                      # 항등 — counts = home + deg×57344
                vel_limit_units=VEL_MAX_UNITS,
                cmd_hz=50.0,
                cmd_timeout=0.2,
                steer_settle_tol_counts=int(STEER_SETTLE_TOL_DEG * COUNTS_PER_DEG),
                allow_homing_motion=allow_homing_motion,
                homing_tol_counts=int(HOMING_TOL_DEG * COUNTS_PER_DEG),
                logger=self.log)
            backend.start()
        except Exception:
            # backend 를 정리하지 않으면 `_running=True` 인 채 RX 스레드가 살아남고,
            # release 된 버스의 recv 가 즉시 None 을 돌려주면 backend._rx_loop 가 sleep 없이
            # busy-spin 한다(리뷰 #H4). 반드시 backend 부터 내린다 — bus 도 함께 닫힌다.
            if backend is not None:
                try:
                    backend.shutdown()              # _running=False + join + bus.shutdown()
                except Exception:
                    pass
            try:
                bus.shutdown()                      # backend 미생성 경로의 release 보장(중복 무해)
            except Exception:
                pass
            raise
        # 램프는 backend 공표 **이전**에 초기화한다 — 공표 후에는 GUI tick 이 즉시 ramp 를
        # 만지기 시작하므로, 워커 스레드의 reset() 과 겹치는 창이 열린다(리뷰 #M6).
        for r in self.ramps.values():
            r.reset()
        with self._lock:
            self.bus = bus
            self.backend = backend
            self._mode = M.STOP
            self._last_error = ""
            estopped = self._estop        # ⚠ E-stop 을 지우지 않는다(리뷰 #H3)
        if estopped:
            # 브링업 중 눌린 E-STOP 은 backend 가 없어 래치가 안 걸렸다 → 지금 적용한다.
            backend.estop(True)
            self.log("[controller] 연결 완료 — ⚠ 브링업 중 눌린 E-STOP 을 backend 에 적용함.")
        else:
            self.log("[controller] 연결 완료 — 모드 STOP, 조향 홈.")

    def disconnect(self):
        """정지 → backend.shutdown()(버스 release·close 포함). 중복 호출 무해."""
        with self._lock:
            backend, self.backend, self.bus = self.backend, None, None
            self._mode = M.STOP
        if backend is None:
            return
        try:
            backend.estop(True)                     # 종료 직전 속도 0 확정
            time.sleep(0.1)
        except Exception:
            pass
        try:
            backend.shutdown()
        except Exception as exc:
            self.log(f"[controller] ⚠ shutdown 예외: {exc}")
        self.log("[controller] 연결 해제 (제어권 반환).")

    @property
    def connected(self) -> bool:
        return self.backend is not None

    # ── 지령 입력 ───────────────────────────────────────────────────────────
    def set_mode(self, key: str):
        """주행 모드 전환. 모드가 바뀌면 **양 조향축 목표**가 그 모드의 인용 각도로 재설정된다.

        ⚠ 전륜/후륜 개별 각도는 `조향만` 모드에서만 허용한다. 주행 모드(8방위)는 실측·도출로
        방향이 확정된 **양축 동일각** 자세뿐이므로, 비대칭 조향으로 구동하는 미검증 기동을
        애초에 지령할 수 없게 한다.
        """
        mode = M.BY_KEY[key]
        with self._lock:
            self._mode = mode
        targets = {}
        for n in STEER_NODES:
            targets[n] = self._slider_deg[n] if mode.key == "steer_only" else mode.steer_deg
            self.ramps[n].set_target(targets[n])
        tgt_txt = " ".join(f"N{n}={targets[n]:+.1f}°" for n in STEER_NODES)
        self.log(f"[controller] 모드={mode.label} 조향목표 {tgt_txt} 근거={mode.basis}")

    def set_speed_mmps(self, mmps: float):
        with self._lock:
            self._speed_mmps = max(0.0, float(mmps))

    def set_steer_slider_deg(self, deg: float, node: int | None = None):
        """조향 슬라이더 값. `조향만` 모드에서만 램프 목표로 반영된다.

        node=None 이면 양 조향축에 동일 적용(동기), 지정하면 그 축만(전륜/후륜 개별).
        """
        targets = STEER_NODES if node is None else (node,)
        for n in targets:
            self._slider_deg[n] = float(deg)
        with self._lock:
            is_steer_mode = self._mode.key == "steer_only"
        if is_steer_mode:
            for n in targets:
                self.ramps[n].set_target(deg)

    # ── 조향 홈 기준 ────────────────────────────────────────────────────────
    def _deg(self, node: int, counts: int) -> float:
        """조향 절대 counts → 홈 기준 각도. **런타임 홈**을 쓴다(상수 아님)."""
        return (counts - self.steer_home[node]) / COUNTS_PER_DEG

    def capture_home(self) -> dict:
        """현재 조향 위치를 홈으로 캡처한다.

        ⚠ **운전자가 바퀴가 물리적으로 직진임을 확인한 뒤에만** 호출해야 한다 —
        이 값이 이후 모든 조향 지령의 기준이 되므로, 틀리면 그만큼 통째로 어긋난다.

        엔코더가 전원 사이클에서 리셋될 수 있음이 2026-07-27 실측으로 확인됐기에
        하드코딩 상수 대신 실측 캡처 경로를 둔다.
        """
        backend = self.backend
        if backend is None:
            raise RuntimeError("연결되지 않았습니다 — 제어권 획득 후 캡처하세요")
        nodes = backend.snapshot()["nodes"]
        now = time.monotonic()
        captured = {}
        for n in STEER_NODES:
            st = nodes.get(n)
            if st is None or st.pos is None:
                raise RuntimeError(f"node{n} 조향 위치 피드백이 없습니다")
            if not st.last_seen or (now - st.last_seen) > FEEDBACK_STALE_S:
                raise RuntimeError(f"node{n} 피드백이 낡았습니다({now - st.last_seen:.1f}s) — 캡처 거부")
            captured[n] = st.pos
        old = dict(self.steer_home)
        self.steer_home = captured
        self.home_source = "실측 캡처(운전자가 직진 확인)"
        for m in backend.modules:                    # backend 의 지령 기준도 함께 갱신
            if m.steer_node in captured:
                m.steer_home = captured[m.steer_node]
        for n in STEER_NODES:                        # 캡처 직후 목표를 0(=현재)으로 정렬
            self.ramps[n].reset()
            self.ramps[n].set_target(0.0)
            self._slider_deg[n] = 0.0
        delta = {n: round((captured[n] - old[n]) / COUNTS_PER_DEG, 1) for n in STEER_NODES}
        self.log(f"[controller] 조향 홈 캡처 — {captured} (이전 대비 {delta}°)")
        return captured

    def estop(self, engage: bool):
        """최우선 정지. backend 래치(속도 0 + 조향 신규 setpoint 억제)를 그대로 사용한다."""
        with self._lock:
            self._estop = bool(engage)
            backend = self.backend
            if engage:
                self._mode = M.STOP
        if backend is not None:
            backend.estop(bool(engage))
        self.log(f"[controller] E-STOP {'ENGAGED' if engage else 'released'}")

    def home(self):
        """조향 홈(0°) + 정지. 램프를 통과하므로 단계 전진은 그대로 유지된다."""
        self.set_mode("home")

    def reset_fault(self):
        """램프 FAULT 래치 해제 — 운전자 명시 확인. 두 축 모두 해제한다."""
        for r in self.ramps.values():
            r.reset()
        with self._lock:
            self._mode = M.STOP
        self.log("[controller] 램프 FAULT 해제 — 모드 STOP 으로 복귀.")

    # ── 주기 tick ───────────────────────────────────────────────────────────
    def tick(self) -> dict:
        """CMD_HZ 주기로 호출. 램프 진행 + 지령 송신 + 상태 스냅샷 반환."""
        with self._lock:
            backend, mode, speed, estopped = self.backend, self._mode, self._speed_mmps, self._estop
        if backend is None:
            return self._status(None, None, 0)

        snap = backend.snapshot()
        nodes = snap["nodes"]
        self._update_measured_speed(nodes)
        now = time.monotonic()
        outs = {}
        for n in STEER_NODES:
            if estopped:
                # E-stop 중 backend 는 조향 setpoint 를 억제하므로 실측이 지령을 따라올 수 없다.
                # 램프를 진행시키면 4 s 뒤 반드시 spurious FAULT 가 난다(리뷰 #M3) → 동결.
                outs[n] = self.ramps[n].freeze(now)
            else:
                outs[n] = self.ramps[n].tick(self._axis_measurement(n, nodes), now)

        # 한 축이 FAULT 면 **나머지 축도 홈으로 되돌린다**. 비대칭 조향 자세로 방치하면
        # 차량이 검증된 적 없는 기하로 남는다 — FAULT 축은 즉시 0°, 정상 축은 단계 램프로 0°.
        if any(o.state == FAULT for o in outs.values()):
            for n in STEER_NODES:
                if outs[n].state != FAULT:
                    self.ramps[n].set_target(0.0)

        # 구동은 **양 축이 모두** 정착했을 때만 허용한다(한 축이라도 미정착·FAULT 면 금지).
        drive_allowed = all(o.drive_allowed for o in outs.values())
        units = 0
        if not estopped and drive_allowed and mode.raw_sign != 0:
            units = mode.raw_sign * mmps_to_units(speed)
        self._last_units = units

        # 모듈별로 자기 조향축의 지령각을 싣는다(전륜·후륜 개별 지령 지원).
        backend.set_command([
            ModuleCommand(d, units_to_mps(units),
                          math.radians(outs[DRIVE_TO_STEER[d]].commanded_deg))
            for d in DRIVE_NODES])
        return self._status(snap, outs, units)

    def _axis_measurement(self, steer_node: int, nodes) -> float | None:
        """축별 램프 입력 실측각 — **그 축 자신의** 0x6064 만 본다.

        축마다 독립 램프를 두므로(전륜/후륜 개별 지령) 한 축이 뒤처지면 그 축만 전진을 멈춘다.
        구동은 `tick()` 에서 **양 축이 모두 정착**해야 허용되므로, 2026-07-27 node4 사례처럼
        한 축만 못 따라오는 상황에서 구동이 나가는 일은 여전히 차단된다.

        None(피드백 미수신)을 돌려주는 조건은 둘이다:
          ① 값이 아직 없음(`pos is None`) — 브링업 직후
          ② **값이 낡음**(`last_seen` 이 FEEDBACK_STALE_S 초과) — RX 가 죽어 마지막 값이 굳은 경우.
             ②가 없으면 backend 가 pos 를 None 으로 되돌리지 않으므로 램프의 피드백-소실 FAULT
             경로가 통합에서 **도달 불가**가 된다(리뷰 #H1).
        """
        st = nodes.get(steer_node)
        if st is None or st.pos is None:
            return None
        if not st.last_seen or (time.monotonic() - st.last_seen) > FEEDBACK_STALE_S:
            return None
        return self._deg(steer_node, st.pos)

    @staticmethod
    def _worst_detail(outs: dict) -> str:
        """FAULT 축 우선, 없으면 미정착 축의 사유. 어느 축인지 라벨을 붙인다."""
        for n, o in outs.items():
            if o.state == FAULT:
                return f"N{n}: {o.detail}"
        for n, o in outs.items():
            if not o.drive_allowed and o.detail:
                return f"N{n}: {o.detail}"
        first = next(iter(outs.values()), None)
        return first.detail if first else ""

    @staticmethod
    def _aggregate_state(outs: dict) -> str:
        """두 축 상태를 하나로 — 나쁜 쪽이 이긴다(FAULT > RAMPING > SETTLED)."""
        states = [o.state for o in outs.values()]
        if FAULT in states:
            return FAULT
        if all(s == SETTLED for s in states):
            return SETTLED
        return RAMPING

    def _update_measured_speed(self, nodes):
        """구동 노드 0x6064 변위 → mm/s (EMA α=0.35). 엔코더 네이티브 부호 그대로 유지한다.

        raw 지령 부호와 엔코더 변위 부호의 관계는 실측으로 확정된 바 없으므로 **변환하지 않는다** —
        운전자가 두 값을 나란히 보고 판단한다(단정 금지).
        """
        now = time.monotonic()
        for n in DRIVE_NODES:
            st = nodes.get(n)
            if st is None or st.pos is None:
                continue
            prev = self._prev_drive.get(n)
            self._prev_drive[n] = (st.pos, now)
            if prev is None:
                continue
            dt = now - prev[1]
            if dt < 1e-3:
                continue
            mmps = (st.pos - prev[0]) / COUNTS_PER_M / dt * 1000.0
            self._meas_mmps[n] = 0.65 * self._meas_mmps[n] + 0.35 * mmps

    def _wheels(self, nodes, outs: dict, units: int) -> list[dict]:
        """휠 모듈별 시각화 상태 — 위치·조향(지령/실측)·구동(지령/실측). 축별 램프 결과를 싣는다."""
        wheels = []
        for d in DRIVE_NODES:
            s = DRIVE_TO_STEER[d]
            st = nodes.get(s)
            meas_deg = self._deg(s, st.pos) if (st and st.pos is not None) else None
            o = outs.get(s) if outs else None
            wheels.append({
                "drive_node": d, "steer_node": s,
                "x": WHEEL_X[d], "y": WHEEL_Y,
                "label": "Front" if WHEEL_X[d] > 0 else "Rear",
                "steer_cmd_deg": o.commanded_deg if o else self.ramps[s].commanded_deg,
                "steer_target_deg": self.ramps[s].target_deg,
                "steer_state": o.state if o else "-",
                "steer_meas_deg": meas_deg,
                "raw_units": units,
                "cmd_mmps": round(units / VEL_PER_MMPS, 1),
                "meas_mmps": round(self._meas_mmps.get(d, 0.0), 1),
                "drive_pos": nodes[d].pos if (d in nodes and nodes[d].pos is not None) else None,
            })
        return wheels

    def _status(self, snap, outs, units: int) -> dict:
        rows = []
        if snap is not None:
            for n in sorted(snap["nodes"]):
                st = snap["nodes"][n]
                rows.append({
                    "node": n, "role": ROLE.get(n, "?"),
                    "pos": st.pos,
                    "deg": round(self._deg(n, st.pos), 2) if (st.pos is not None and n in STEER_NODES) else None,
                    "status": st.status, "error": st.error,
                    "current": st.current, "aborts": st.aborts,
                    "age_s": round(time.monotonic() - st.last_seen, 1) if st.last_seen else None,
                })
        with self._lock:
            mode = self._mode
            estopped = self._estop
        return {
            "connected": snap is not None,
            "mode": mode,
            "estop": estopped,
            "ramp_state": self._aggregate_state(outs) if outs else "-",
            # 상세는 나쁜 쪽(FAULT>미정착) 축의 사유를 보여준다 — 문제 축을 즉시 알 수 있게.
            "ramp_detail": self._worst_detail(outs) if outs else "",
            "ramp_cmd_deg": (max((o.commanded_deg for o in outs.values()), key=abs)
                             if outs else self.ramps[STEER_NODES[0]].commanded_deg),
            "ramp_target_deg": max((self.ramps[n].target_deg for n in STEER_NODES), key=abs),
            "steer_home": dict(self.steer_home),
            "home_source": self.home_source,
            "per_axis": ({n: {"cmd": outs[n].commanded_deg, "state": outs[n].state,
                              "target": self.ramps[n].target_deg} for n in outs} if outs else {}),
            "drive_allowed": all(o.drive_allowed for o in outs.values()) if outs else False,
            "fault": bool(outs) and self._aggregate_state(outs) == FAULT,
            "settled": bool(outs) and self._aggregate_state(outs) == SETTLED,
            "raw_units": units,
            "raw_mmps": round(units / VEL_PER_MMPS, 1) if units else 0.0,
            "nodes": rows,
            "wheels": self._wheels(snap["nodes"], outs, units) if snap else [],
            "tx": snap["tx"] if snap else 0,
            "rx": snap["rx"] if snap else 0,
            "backend_settling": snap["settling"] if snap else False,
            "bus_tx_errors": getattr(self.bus, "tx_errors", 0),
            "bus_rx_errors": getattr(self.bus, "rx_errors", 0),
            "bus_controlling": getattr(self.bus, "controlling", None),
        }


__all__ = ["AmrTestController", "BringupRefused", "NodeSilent", "ROLE"]
