#!/usr/bin/env python3
"""릴레이 구동 백엔드 — 단일 제어 스레드.

## 설계 규칙 (전부 실측 사고에서 나온 것)

1. **구동 지령은 주기 재송신한다.** 단발 송신은 프레임 하나가 유실되면 그대로
   끝이고, 지령원이 사라져도 드라이브가 마지막 값을 물고 계속 간다.
2. **워치독이 지령을 만료시킨다.** `cmd_timeout` 안에 갱신이 없으면 속도 0 으로
   수렴한다. 갱신은 "유효한 지령"일 때만 인정한다 — NaN 을 계속 퍼블리시하는
   노드가 워치독을 무한 연장하지 못하게 한다.
3. **정지 경로는 어떤 상태에서도 거부되지 않는다.** 폴링이 죽었든 제어권이
   흔들리든 `stop()` 은 항상 받아들여지고, 다음 틱이 아니라 즉시 시도한다.
4. **조향 클램프는 counts 를 만드는 지점에 있다**(`safety.steer_deg_to_counts`).
   상위 계층에만 두면 다른 상위가 붙었을 때 보호가 사라진다.
5. **호밍 중 위치를 믿지 않는다.** bit15=0 구간에서 0x6064 는 0 으로 고정되며
   각도로 환산하면 ≈−137° 가 상위로 흘러간다.
6. **호밍은 자동으로 하지 않는다.** 물리 스윙 100°+ 이므로 명시 요청으로만 수행한다.
   **취소는 된다** — `home()` 은 판다 펌웨어 시퀀서(USB `0xea`/`0xeb`)를 쓰고
   `cancel_home()` 이 취소 프레임(`0x60FB:04=0`)을 내게 한다
   (`Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:312-316`
   `seer_home_cancel_frames()`). SDO 직접 송신 경로로도 같은 프레임을 낼 수는 있으나
   그쪽 취소는 **호스트가 살아 있을 때만** 성립하므로 쓰지 않는다(정정 2026-08-03).
7. **버스 헬스(0xc3)는 읽기 전용**이라 제어 경로에 영향이 없다. 실패해도 지령·정지는
   그대로 돌고, 기능 부재와 일시적 실패를 구분한다(전자만 영구 비활성).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import protocol as P
from . import safety as S
from .link import (BaseLink, HEARTBEAT_PERIOD_S, HOMING_OK, LinkError,
                   MOTOR_BUS, SEER_BUS)


@dataclass
class NodeState:
    """노드 하나의 최신 피드백. `last_seen` 은 신선도 판정에 쓴다."""

    position: Optional[int] = None
    position_prev: Optional[int] = None      # 직전 폴 표본 — 정지 판정용
    statusword: Optional[int] = None
    velocity_raw: Optional[int] = None
    current_raw: Optional[int] = None
    digital_input: Optional[int] = None
    last_seen: float = 0.0
    aborts: int = 0
    last_abort: Optional[int] = None

    def fresh(self, now: float, ttl: float) -> bool:
        return self.last_seen > 0.0 and (now - self.last_seen) <= ttl

    def stationary(self, tol: int) -> Optional[bool]:
        """연속 두 표본이 `tol` 안이면 정지. 표본이 부족하면 **None(모름)**.

        「모름」을 정지로 치지 않는 것이 요점이다 — 판정 못 하면 지령을 내지 않는다.
        """
        if self.position is None or self.position_prev is None:
            return None
        return abs(self.position - self.position_prev) <= tol


@dataclass
class RelayConfig:
    """배선·한계·주기. 값의 근거는 각 필드 주석과 safety.py 에 있다."""

    drive_nodes: tuple = (1, 2)
    steer_nodes: tuple = (3, 4)
    bus: int = MOTOR_BUS
    cmd_hz: float = 20.0            # 지령 재송신 주기
    poll_hz: float = 5.0            # 피드백 폴링 주기(gui.py 실측 주기와 동일)
    cmd_timeout_s: float = 0.3      # 워치독. 이 안에 갱신 없으면 속도 0
    feedback_ttl_s: float = 1.0     # 이보다 오래된 피드백은 없는 것으로 친다
    health_hz: float = 1.0          # per-bus CAN 에러 상태(0xc3) 폴링 주기
    steer_limit_deg: float = S.STEER_LIMIT_DEG
    #   저수준 체인(`/motor/low_cmd`)용 상한. 크랩이 90° 자세에서 path follow 여유로
    #   ±115° 까지 요구하므로 그만큼 열어 둔다(2026-08-05, foil_a082.yaml 근거 주석 참조).
    steer_limit_bench_deg: float = S.STEER_LIMIT_DEG
    #   **벤치 직접 지령**(`~/steer_deg`·`~/steer_axis_deg`)용 상한. 사람이 손으로 넣는
    #   값이라 넓힐 이유가 없어 90° 를 유지한다. 체인 상한을 열어도 이쪽은 따라 열리지 않는다
    #   — can_relay 는 지령 출처를 모르므로(raw counts 만 받는다) 「크랩일 때만」을 판정할
    #   수 없고, 대신 **경로**로 나눈다. 그 결과 사람이 넣는 경로에는 90° 가드가 남는다.
    vel_max_units: int = S.VEL_MAX_UNITS
    # 스케일도 기체마다 다르다 — 캘리브레이션 YAML 이 준다.
    # ⚠ 상류 QD(Carrier AGV)는 48,332.8 counts/도로 우리(57,344)와 다르다.
    steer_counts_per_deg: float = S.COUNTS_PER_DEG
    drive_units_per_mmps: float = S.VEL_PER_MMPS
    steer_home: dict = field(default_factory=dict)
    #   ⚠ 비어 있으면 조향 지령이 **거부**된다. 코드 기본값을 두지 않는 것이 설계다 —
    #   정본은 `config/machine/<기체>.yaml`. (2026-08-02 사용자 지시)
    settle_tol_deg: float = 3.0
    allow_bringup: bool = False     # 구동/조향 init 시퀀스 송신 여부(실기 미검증)

    # ── 호밍 (장비별 캘리브레이션 — config/machine/<기체>.yaml) ──────────
    homing_method: str = "firmware"
    #   ⚠ 기본값은 **안전한 쪽**이다. "35"(재영점)는 2026-08-01 실기에서 기각됐다 —
    #   제어권 반환 순간 Seer 가 130.55° 오독하고 조향을 능동 구동했다.
    #   설정이 안 실렸을 때 기각된 방식으로 떨어지면 안 된다.
    homing_enabled: bool = False    # ⚠ home_offset 실측 확정 전까지 False
    steer_home_offset: dict = field(default_factory=dict)   # {node: 절대 counts}
    home_reach_tol_counts: int = 50         # 상류 can_open.hpp:489 와 동일
    home_profile_vel: int = 2500            # 상류 HomeVelocity 와 동일
    home_search_range: tuple = (-10_000_000, 10_000_000)
    require_homed_for_steer: bool = True
    stationary_tol_counts: int = 200
    #   `NodeState.stationary` 의 정지 판정 허용치. 200 counts = 0.0035°.
    #   ⚠ 2026-08-05 이후 조향 정지 경로는 이 값을 쓰지 않는다(프레임을 안 보낸다).
    #   근거: 마스터(Seer) 캡처에서 `0x607A ≈ 현재 실측` 송신 12,396건이 전부 |Δ| ≤ 200 c 대역이다
    #   (`Log/homing_capture_220350.jsonl`, 재현 `Tools/docking_field_kit/master_command_census.py`).
    #   즉 **실측으로 확인된 사용 상황의 폭**을 그대로 임계로 쓴다 — 임의로 고른 수가 아니다.
    #   매뉴얼 §Home 35 "only effective when the motor is powered on" —
    #   전원 사이클마다 재호밍이 필요하므로 완료 전 조향 지령을 막는다(상류 home_comp 와 같은 역할).
    tx_fail_halt: int = 10          # 연속 **송신** 실패가 이만큼이면 심박을 끊는다
    #   그래야 펌웨어 fail-safe(구동 0 + 릴레이 개방)가 걸린다. 지령을 못 내보내는
    #   상태에서 심박만 유지하면 정지 수단이 사라진다.
    #   ⚠ 세는 대상은 **송신 실패뿐**이다. 수신·진단 쪽 예외까지 세면 읽기 경로의
    #   일시 오류가 로봇을 세우면서 원인은 "송신 실패"로 잘못 표시된다(2026-08-03 리뷰 M2).


class RelayBackend:
    """제어 스레드 하나가 송신·수신·심박을 모두 담당한다.

    스레드를 나누지 않는 이유: 판다 USB 핸들을 여러 스레드가 경합하면 heartbeat
    전송이 실패해 펌웨어가 릴레이를 스스로 풀어 버린 이력이 있다.
    """

    def __init__(self, link: BaseLink, cfg: RelayConfig,
                 log: Optional[Callable[[str], None]] = None):
        self.link = link
        self.cfg = cfg
        self._log = log or (lambda _m: None)

        self.nodes: dict[int, NodeState] = {
            n: NodeState() for n in tuple(cfg.drive_nodes) + tuple(cfg.steer_nodes)
        }

        self._lock = threading.Lock()
        self._drive_units = 0
        self._drive_units_by_node: dict[int, int] = {}   # 노드별 raw 속도(H5)
        self._pvel_noted: dict[int, int] = {}            # 미반영 고지를 낸 profile_vel
        self._steer_counts: dict[int, int] = {}
        self._steer_target_deg: Optional[float] = None
        self._last_cmd_time = 0.0
        self._estop = False
        self._fault: Optional[str] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._homing = False
        self._homed = False         # 이번 전원 사이클에서 호밍이 완료됐는가
        self._homing_status: dict = {}
        # 버스별 bxCAN 에러 상태. 링크가 지원하지 않으면 비어 있고, 그 사실을
        # `health_supported=False` 로 드러낸다(조용히 숨기지 않는다).
        self._bus_health: dict = {}
        self._health_supported: Optional[bool] = None
        self._health_error: Optional[str] = None

        self.tx_count = 0
        self.rx_count = 0
        self.watchdog_trips = 0
        self._tx_fail_streak = 0        # 연속 **송신** 실패 횟수 (심박 중단 판단용)
        self._loop_fail_streak = 0      # 송신 외 루프 예외(수신·파싱 등) 연속 횟수
        self._hb_suppressed = False     # 심박을 의도적으로 끊은 상태인가

    # ── 수명주기 ──────────────────────────────────────────────────────
    def start(self):
        if self._running:
            raise RuntimeError("이미 기동돼 있다 — 두 번 부르면 버스 writer 가 둘이 된다")
        if not self.link.engaged:
            raise RuntimeError("제어권을 먼저 획득해야 한다")
        if self.cfg.allow_bringup:
            self._write_bringup()
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="can_relay",
                                        daemon=True)
        self._thread.start()
        self._log("백엔드 기동")

    def shutdown(self):
        """정지를 **먼저** 보내고 스레드를 내린다. 순서가 반대면 안 된다.

        두 번 불러도 안전하다 — 노드 종료 경로가 `~/engage false` 와 겹친다.
        """
        if not self._running and self._thread is None and self._drive_units == 0:
            return
        self.stop("shutdown")
        if self.link.engaged:
            self.release_steer_target("shutdown")   # 우리 조향 목표를 놓고 나간다
            try:
                self._send(self._drive_frames(0))
            except Exception as exc:
                self._log(f"종료 정지 송신 실패: {type(exc).__name__}: {exc}")
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None
        self._log("백엔드 종료")

    # ── 지령 ──────────────────────────────────────────────────────────
    def set_drive_mmps(self, mmps: float, sign: int = 1):
        """구동 속도 지령. 비유한 값은 **거부**하고 워치독을 갱신하지 않는다."""
        if self._estop:
            return
        units = S.drive_mmps_to_units(mmps, sign, self.cfg.vel_max_units,
                                      self.cfg.drive_units_per_mmps)
        with self._lock:
            self._drive_units = units
            self._last_cmd_time = time.monotonic()

    # ── 조향 0° 기준이 유효한가 ────────────────────────────────────────
    def homed_effective(self) -> bool:
        """조향 지령을 보내도 되는가 — **호밍의 출처를 가리지 않는다**.

        인정하는 근거 2가지:
          ① 이번 프로세스에서 우리가 호밍했다(`self._homed`).
          ② **드라이브가 스스로 「호밍 완료」를 보고한다**(`0x6041` bit15).
             **Seer 가 호밍한 경우가 여기 잡힌다.**

        ⚠ 예전에는 ①만 봤다. 그래서 Seer 가 이미 호밍해 둔 상태(bit15=1)인데도 조향이 통째로
          거부돼, 실기에서 바퀴가 **한 카운트도 움직이지 않았다**(2026-08-04 실측:
          호밍 전 판독 N3·N4 = `0x9450` → bit15 이미 1).
          「0° 기준을 모른다」는 전제 자체도 같은 날 반증됐다 — 판다 직독 조향과 Seer 판독이
          0° 로 교차 일치했고(−0.0° ↔ +0.0°) 정본 YAML 과 ±6 counts 였다.

        ⚠ **신선한 피드백일 때만** 인정한다. 낡은 상태워드로 「호밍됐다」고 하면 통신이 끊긴
          뒤에도 조향이 열린다.
        """
        if self._homed:
            return True
        now = time.monotonic()
        nodes = [self.nodes.get(n) for n in self.cfg.steer_nodes]
        if not nodes or any(st is None for st in nodes):
            return False
        for st in nodes:
            if not st.fresh(now, self.cfg.feedback_ttl_s):
                return False
            if S.is_homed(st.statusword) is not True:
                return False
        return True

    def _not_homed_reason(self) -> str:
        """거부 사유 — 무엇이 모자라 막혔는지 운용자가 알 수 있게 적는다."""
        now = time.monotonic()
        detail = []
        for n in self.cfg.steer_nodes:
            st = self.nodes.get(n)
            if st is None or st.last_seen <= 0.0:
                # 한 번도 못 받은 것과 낡은 것은 원인이 다르다 — 배선/기동 문제 vs 통신 두절.
                detail.append(f"N{n} 피드백 없음")
            elif not st.fresh(now, self.cfg.feedback_ttl_s):
                detail.append(f"N{n} 피드백 낡음({now - st.last_seen:.1f}s 경과)")
            elif S.is_homed(st.statusword) is not True:
                sw = st.statusword
                detail.append(f"N{n} bit15=0"
                              + ("(상태워드 미수신)" if sw is None else f"(0x{sw & 0xFFFF:04X})"))
        return ("조향 0° 기준을 확인할 수 없다 — 우리가 호밍한 적이 없고 드라이브도 "
                "호밍 완료(0x6041 bit15)를 보고하지 않는다: " + ", ".join(detail)
                + ". `~/home` 를 수행하거나, Seer 가 호밍한 뒤 다시 시도할 것")

    def set_steer_deg(self, deg: float):
        """조향 절대각 지령. ±limit 로 잘라서 보낸다(거부가 아니라 클램프).

        호밍 중에는 받지 않는다 — 드라이브 내부 루틴이 축을 쥐고 있다.
        """
        if self._homing:
            raise S.UnsafeCommand("호밍 진행 중에는 조향 지령을 보내지 않는다")
        if self._estop:
            raise S.UnsafeCommand("E-stop 인가 중 — 조향 지령을 보내지 않는다")
        if self.cfg.require_homed_for_steer and not self.homed_effective():
            raise S.UnsafeCommand(self._not_homed_reason())
        applied = None
        counts = {}
        for n in self.cfg.steer_nodes:
            applied, c = S.steer_deg_to_counts(n, deg, self.cfg.steer_home,
                                               self.cfg.steer_limit_bench_deg,
                                               self.cfg.steer_counts_per_deg)
            counts[n] = c
        with self._lock:
            self._steer_counts = counts
            self._steer_target_deg = applied
            self._last_cmd_time = time.monotonic()
        if applied is not None and abs(applied - float(deg)) > 1e-9:
            self._log(f"조향 지령 {deg:+.1f}° → ±{self.cfg.steer_limit_bench_deg:.0f}° "
                      f"클램프 적용 {applied:+.1f}°")
        return applied

    def set_steer_axis_deg(self, node: int, deg: float) -> float:
        """**한 축에만** 조향 절대각 지령. 반환 = 클램프 적용된 각도.

        `set_steer_deg` 는 조향 전축에 같은 각을 준다(crab). 시험 GUI 의 축별 슬라이더처럼
        앞뒤를 따로 세우려면 축 하나만 움직이는 경로가 필요하다
        (ADR `docs/adr/2026-08-03-amr-test-gui-ros2-port.md` §Decision ⓑ).

        **안전 게이트는 `set_steer_deg` 와 완전히 같다** — 축이 하나라고 보호를 빼지 않는다:
        호밍 중 거부 · E-stop 거부 · 호밍 미완료 거부 · ±limit 클램프.
        배선에 없는 노드는 거부한다(구동축에 위치 지령이 가면 안 된다).

        ⚠ 이 경로로 축을 따로 세우면 두 축의 각이 달라질 수 있으므로 **단일 목표각을
        주장하지 않는다**(`_steer_target_deg = None`). 그래서 `settled()` 는 이 경로 뒤에
        False 를 돌려준다 — 축별 정착 판정은 호출부가 `steer_angles_deg()` 로 직접 한다.
        """
        if self._homing:
            raise S.UnsafeCommand("호밍 진행 중에는 조향 지령을 보내지 않는다")
        if self._estop:
            raise S.UnsafeCommand("E-stop 인가 중 — 조향 지령을 보내지 않는다")
        if self.cfg.require_homed_for_steer and not self.homed_effective():
            raise S.UnsafeCommand(self._not_homed_reason())
        node = int(node)
        if node not in self.cfg.steer_nodes:
            raise S.UnsafeCommand(
                f"node{node} 는 조향축이 아니다 — 조향 노드는 "
                f"{list(self.cfg.steer_nodes)} 뿐이다")
        applied, counts = S.steer_deg_to_counts(node, deg, self.cfg.steer_home,
                                                self.cfg.steer_limit_bench_deg,
                                                self.cfg.steer_counts_per_deg)
        with self._lock:
            self._steer_counts = dict(self._steer_counts)
            self._steer_counts[node] = counts
            self._steer_target_deg = None       # 축별 경로에서는 각도를 주장하지 않는다
            self._last_cmd_time = time.monotonic()
        if abs(applied - float(deg)) > 1e-9:
            self._log(f"조향 지령 N{node} {deg:+.1f}° → ±{self.cfg.steer_limit_bench_deg:.0f}° "
                      f"클램프 적용 {applied:+.1f}°")
        return applied

    def set_motor_cmds(self, cmds) -> list:
        """모터 계층 지령(raw)을 받는다 — 상류 `MotorCmdArray` 계약.

        `cmds` 는 `(motor_id, mode, target_vel, target_pos, profile_vel)` 시퀀스.
        단위는 **raw** 다(0.1 rpm / pulse) — SI 환산은 상류 translator 소유이므로
        여기서 하지 않는다. 기구학도 하지 않는다.

        안전은 raw 단위로 그대로 건다 — 계층이 내려갔다고 보호가 사라지면 안 된다:
          · 조향 위치는 홈 기준 ±`steer_limit_deg` 를 counts 로 환산해 클램프
          · 구동 속도는 ±`vel_max_units` 클램프
          · 호밍 미완료 시 조향 지령 거부(매뉴얼 §Home 35 — 전원 사이클마다 필요)
        반환: 거부·클램프된 항목의 사유 목록(빈 리스트면 전부 그대로 수리).
        """
        notes = []
        drive, steer = {}, {}
        limit_c = int(round(self.cfg.steer_limit_deg * self.cfg.steer_counts_per_deg))
        for mid, mode, tvel, tpos, pvel in cmds:
            mid, mode = int(mid), int(mode)
            if mode == P.MODE_DISABLED:
                notes.append(f"node{mid} mode=DISABLED — 지령 무시")
                continue
            if mid in self.cfg.drive_nodes:
                # H6: mode 를 반드시 본다. 구동축에 POSITION 이 오면 target_pos 를
                #     속도로 쓰거나 그 반대가 되어 의도와 다른 물리 동작이 난다.
                if mode != P.MODE_VELOCITY:
                    notes.append(f"node{mid} 구동축에 mode={P.MODE_NAME.get(mode, mode)} "
                                 f"— VELOCITY 만 허용, 거부")
                    continue
                if not S.finite(tvel):
                    notes.append(f"node{mid} target_vel 비유한 — 거부")
                    continue
                v = max(-self.cfg.vel_max_units, min(self.cfg.vel_max_units, int(tvel)))
                if v != int(tvel):
                    notes.append(f"node{mid} target_vel {tvel}→{v} 클램프")
                # H5: 노드별로 따로 담는다. 예전에는 첫 값 하나로 양 구동륜을 뭉개서
                #     제자리 선회(node1=+v, node2=−v) 지령이 조용히 직진이 됐다.
                drive[mid] = v
            elif mid in self.cfg.steer_nodes:
                # H6: 조향축에 VELOCITY 가 오면 미설정 target_pos(=0)를 위치로 읽어
                #     홈에서 0 counts 로, 즉 클램프 한계까지 스윙한다.
                if mode != P.MODE_POSITION:
                    notes.append(f"node{mid} 조향축에 mode={P.MODE_NAME.get(mode, mode)} "
                                 f"— POSITION 만 허용, 거부")
                    continue
                if self.cfg.require_homed_for_steer and not self._homed:
                    notes.append(f"node{mid} 호밍 미완료 — 조향 거부")
                    continue
                if not S.finite(tpos):
                    notes.append(f"node{mid} target_pos 비유한 — 거부")
                    continue
                if mid not in self.cfg.steer_home:
                    notes.append(f"node{mid} 조향 홈 미설정 — 캘리브레이션 config 필요, 거부")
                    continue
                # 상류가 보내는 `target_pos` 는 **홈(직진 0°) 기준 상대 counts** 다.
                # 여기서 기체 원점을 더해 절대 counts 로 만든다 — `set_steer_deg` 가
                # `steer_deg_to_counts`(safety.py:85 `home + deg×counts_per_deg`)로 하는 것과
                # 같은 일이며, 실기 검증된 그 원점을 raw 경로가 재사용하는 것이다.
                #
                # ⚠ 상류가 원점을 더하게 두지 않는 이유: 홈 counts 의 정본은
                #   `config/machine/<기체>.yaml` 하나다. 상류 config 에 복제하면 정본이 둘이 되고,
                #   기체를 바꿀 때 한쪽만 갱신되면 그 오차가 그대로 바퀴로 나간다.
                #
                # 이 변환이 없으면 0°(직진) 지령이 상대 0 counts 로 들어와 절대 0 으로 읽히고,
                # 아래 클램프 하한(home−limit)까지 잘려 **−90° 로 지령된다**(2026-08-05 리뷰 Critical).
                home = int(self.cfg.steer_home[mid])
                target = home + int(tpos)
                lo, hi = home - limit_c, home + limit_c
                c = max(lo, min(hi, target))
                if c != target:
                    notes.append(f"node{mid} target_pos {tpos}→{c - home} 클램프(±"
                                 f"{self.cfg.steer_limit_deg:.0f}°, 홈 기준)")
                # profile_vel 은 **반영하지 않는다** — 조향은 PP 모드라 실제 속도는
                # 드라이브에 마지막으로 기록된 0x6081 이 결정한다. 매 지령마다 0x6081 을
                # 덧붙이는 것은 실기 미검증 변경이라 HIL 게이트 전까지 하지 않는다(debt-038).
                # 조용히 버리지 않고 상위가 알 수 있게 남긴다(2026-08-03 리뷰 M1).
                # ⚠ `notes` 에 넣지 않는다 — 반환 목록은 **거부·클램프 사유** 전용이고
                #   호출부가 그것을 `rejected_commands` 로 센다. 정보 고지를 섞으면
                #   정상 지령이 거부로 집계된다. 로그로만, 그것도 **값이 바뀔 때 한 번**
                #   남긴다(20~50 Hz 로 같은 말이 쌓이지 않게).
                if S.finite(pvel) and int(pvel) > 0 and \
                        self._pvel_noted.get(mid) != int(pvel):
                    self._pvel_noted[mid] = int(pvel)
                    self._log(f"node{mid} profile_vel={int(pvel)} 미반영 — 조향 프로파일 "
                              f"속도는 브링업/호밍 설정이 소유한다(debt-038)")
                steer[mid] = c
            else:
                notes.append(f"motor_id {mid} 는 배선에 없다 — 무시")
        with self._lock:
            if drive and self._estop:
                # 조향과 대칭으로 사유를 남긴다 — 예전에는 구동만 조용히 사라져
                # 상위에서 "수리됨"과 구분할 수 없었다(2026-08-03 리뷰 M5).
                notes.append("E-stop 인가 중 — 구동 지령 거부")
                drive = {}
            if drive:
                self._drive_units_by_node = dict(drive)
                # 하위호환 표기(단일값 진단용) — 값이 갈리면 최댓값 절대치를 보인다.
                self._drive_units = max(drive.values(), key=abs)
            if steer and self._estop:
                notes.append("E-stop 인가 중 — 조향 지령 거부")
                steer = {}
            if steer:
                self._steer_counts = steer
                self._steer_target_deg = None      # raw 경로에서는 각도를 주장하지 않는다
            if drive or steer:
                self._last_cmd_time = time.monotonic()
        return notes

    def motor_states(self) -> list:
        """`MotorStateArray` 용 노드별 raw 피드백. 신뢰 불가 값은 그대로 드러낸다."""
        now = time.monotonic()
        out = []
        with self._lock:
            for n in sorted(self.nodes):
                st = self.nodes[n]
                fresh = st.fresh(now, self.cfg.feedback_ttl_s)
                # 조향축 위치는 **홈 기준 상대 counts** 로 올린다 — 지령과 같은 좌표계다
                # (`set_motor_cmds` 가 `home + tpos` 로 받는 것의 역방향).
                # 절대 counts 를 그대로 올리면 상류가 직진(7,871,815c)을 137.3° 로 읽는다.
                pos = int(st.position or 0)
                if n in self.cfg.steer_home:
                    pos -= int(self.cfg.steer_home[n])
                out.append({
                    "motor_id": n,
                    "fb_vel": int(st.velocity_raw or 0),
                    "fb_pos": pos,
                    "error_code": int(st.last_abort or 0) & 0xFFFF,
                    "amps": int(st.current_raw or 0),
                    "voltage": 0,                   # 0x6079 미폴 — 0 으로 둔다
                    # 필드 뜻 그대로 **드라이브 자신의 보고**(0x6041 bit15)를 싣는다.
                    # 예전에는 우리 프로세스 변수 `self._homed` 를 실어, Seer 가 호밍해 둔
                    # 상태(bit15=1)인데도 `home_comp=False` 로 나갔다(2026-08-04 실기 확인).
                    "home_comp": bool(S.is_homed(st.statusword)),
                    "homing": bool(self._homing),
                    "motor_enabled": bool(fresh and not self._estop),
                    "can_reset": not fresh,
                })
        return out

    def release_steer_target(self, reason: str = "") -> bool:
        """**우리가 걸어 둔 조향 목표를 놓는다.** 조향축에 프레임은 보내지 않는다.

        옛 이름 `hold_steer_at_measured` / `halt_steer`. 그 함수는 현재 실측 위치를 새 조향
        목표(`0x607A`)로 써 넣어 축을 붙들었다. **2026-08-05 그 송신을 제거했다** — 근거:

        1. **어느 문서·구현에도 없는 방식이었다.** 벤더 Handbook V7.0 §위치 모드(PP) 절차는
           정지를 `0x6040` 으로 낸다(`:8467-8469` — `0x03 Pause` · `0x0F Recovery` · `0x05 Stop`).
           상류 `TR_Nav_ros2_ws` 도 그대로 쓴다(`can_open.hpp:36-37,468-469`).
           마스터 Seer 는 정지 명령 없이 **목표를 28 ms 마다 연속 재송신**할 뿐이다
           (캡처 253,510 프레임: `0x03`·`0x05` 0회).
           경위는 `docs/claude-mistake/2026-08-05-001`.
        2. **원래 목적을 수행하지 못했다.** 2026-08-04 에 「마스터가 이동 중엔 안 쓴다」를 근거로
           정지 확인된 축에만 보내도록 제한했는데, 이 함수가 생긴 이유가 **움직이는 축을
           세우는 것**이었다. 제한 뒤에는 **이미 멈춘 축에 「거기 있어라」** 를 보내는 것만 남았다.
        3. **그 무의미한 쓰기가 유일한 위험 통로였다.** engage 직후 위치가 0 으로 고정 보고되는
           구간(실측 132 ms)에 걸리면 목표가 0 이 되어 축을 **+69.3°** 돌린다(debt-040).

        ⚠ **`0x6040` 정지 명령 채택은 아직 보류다.** `0x03`(Quick Stop)의 실제 거동은
        `0x605A`(quick_stop_option_code)가 정하는데, 실기 판독 결과 **4축 모두 0** 이고
        매뉴얼은 그 값의 의미를 **정의하지 않는다**(PDF `-layout` 재추출로도 표 없음).
        문서로 확정되기 전에는 넣지 않는다 — 같은 실수를 반복하지 않는다.
        `0x05`(Disable Voltage = 서보 오프)는 쓰지 않는다(사용자 확인 2026-08-05).

        ⚠ **드라이브가 이미 받은 목표까지는 못 세운다.** 그 축은 직전 목표까지 계속 회전한다
        (사용자 확인 2026-08-04). 급정지는 node guarding 폴 중단 또는 하드웨어 E-STOP 이다.

        반환: 놓을 목표가 있었으면 True, 없었으면 False.
        """
        with self._lock:
            had = bool(self._steer_counts)
            self._steer_counts = {}
            self._steer_target_deg = None
        self._halt_note = "" if had else "걸어 둔 조향 목표가 없었다"
        self._log("조향 목표 해제 — 재송신 중단"
                  + ("" if had else " (걸어 둔 목표 없음)")
                  + (f" ({reason})" if reason else ""))
        return had

    def stop(self, reason: str = ""):
        """구동 정지. **어떤 상태에서도 받아들인다.**

        ⚠ **조향은 세우지 않는다.** `_drive_frames(0)` 은 `drive_nodes` 전용이라
        조향축에는 프레임이 한 장도 나가지 않고, 제어 루프가 직전 조향 목표를 계속
        재송신한다. 즉 "현 위치 유지"가 아니라 **"직전 목표까지 계속 회전"** 이다
        (2026-08-01 실기에서 이 오해로 사고가 났다).
        우리 조향 목표를 놓으려면 `release_steer_target()` 또는 `stop_all()` 을 쓸 것.
        """
        with self._lock:
            self._drive_units = 0
            self._drive_units_by_node = {}
            self._last_cmd_time = time.monotonic()
        # 즉시 송신은 best-effort 다. 제어권이 없으면 우리 프레임은 어차피 게이트에
        # 막히므로 시도하지 않는다 — 지령 자체(속도 0)는 위에서 이미 확정됐다.
        if self.link.engaged:
            try:
                self._send(self._drive_frames(0))
            except Exception as exc:
                self._log(f"즉시 정지 송신 실패(루프가 재시도한다): "
                          f"{type(exc).__name__}: {exc}")
        if reason:
            self._log(f"정지 — {reason}")

    def stop_all(self, reason: str = "") -> bool:
        """구동을 0 으로 하고, **정지 상태로 확인된 조향축은 현재 위치에 붙잡는다.**

        ⚠ **조향축에 프레임을 보내지 않는다.** `release_steer_target` 은 2026-08-05 결정으로
        **우리 조향 목표의 재송신을 멈출 뿐**이다 — 「현재 위치를 목표로 덮어쓰기」는 벤더 매뉴얼·
        상류 구현·마스터 캡처 어디에도 없는 방식이라 제거했다(`docs/claude-mistake/2026-08-05-001`).
        따라서 **드라이브가 이미 받은 목표까지는 못 세우며, 축은 직전 PP 목표까지 계속 회전한다.**

        반환 `True` 는 **「조향축을 실제로 잡았다」**는 뜻이고, `False` 는 못 잡았다는 뜻이다.
        사유는 `halt_note()` 로 꺼낸다 — 「실측 미확보」와 「이동 중 보류」는 다른 사건이라
        운용자가 구분할 수 있어야 한다.

        구동 정지는 어떤 경우에도 수행된다(`stop()` 은 상태와 무관하게 받아들여진다).
        """
        self.stop(reason)
        return self.release_steer_target(reason)

    def estop(self, engage: bool):
        """소프트 E-stop 래치. ⚠ 하드웨어 E-STOP 을 대체하지 않는다.

        조향축은 PP 모드라 직전 목표까지 계속 회전한다 — 이 함수는 구동만 세운다.
        """
        self._estop = bool(engage)
        if engage:
            self.stop("estop")
            # 조향도 세운다 — 예전에는 구동만 세우고 조향 setpoint 를 계속 밀어넣었다.
            self.release_steer_target("estop")
        self._log(f"E-stop {'인가' if engage else '해제'}")

    # ── 호밍 (명시 요청 전용) ─────────────────────────────────────────
    def _home_method35(self, poll_s: float, timeout_s: float) -> tuple[bool, str]:
        """CiA402 homing method 35 — 상류 `amr_canopen_motor_driver` 와 같은 절차.

            1) `0x607A = home_offset` · `0x6081` · `0x6040=0x3F`  → 절대 위치로 이동
            2) 도착 확인: statusword bit10 ∧ |0x6064 − home_offset| < tol
            3) `SDO 0x6098 = 35` → 현재 위치를 홈으로(각도가 0 이 된다)

        1단계 **전에** 두 가지를 막는다:
          · `homing_enabled=False` — home_offset 이 실측 확정되지 않았다
          · 현재 위치가 `home_search_range` 밖 — 엔코더 기준이 달라졌을 수 있다
        둘 다 "바퀴를 움직이기 전에" 걸린다.

        취소는 전 구간 가능하다 — `0x607A` 를 우리가 쓰므로 정지 지령으로 끊을 수 있다.
        """
        cfg = self.cfg
        if not cfg.homing_enabled:
            return False, ("호밍 비활성 — `steer_home_offset` 이 실측 확정되지 않았다. "
                           "그 기체의 직진 자세에서 0x6064 를 읽어 캘리브레이션 YAML 에 "
                           "기입하고 `homing_enabled: true` 로 바꿀 것")
        missing = [n for n in cfg.steer_nodes if n not in cfg.steer_home_offset]
        if missing:
            return False, f"steer_home_offset 에 노드 {missing} 값이 없다"

        now = time.monotonic()
        with self._lock:
            pos = {n: (self.nodes[n].position
                       if self.nodes[n].fresh(now, cfg.feedback_ttl_s) else None)
                   for n in cfg.steer_nodes}
        for n in cfg.steer_nodes:
            ok, why = S.home_search_allowed(pos[n], cfg.home_search_range)
            if not ok:
                return False, f"노드 {n} 호밍 거부 — {why}"

        self._homing = True
        self._homed = False
        try:
            frames = []
            for n in cfg.steer_nodes:
                frames.extend(P.home35_move_frames(
                    n, int(cfg.steer_home_offset[n]), cfg.home_profile_vel, cfg.bus))
            self._send(frames)
            self._log(f"호밍(method 35) 1단계 — 절대이동 {dict(cfg.steer_home_offset)}")

            t0 = time.monotonic()
            reached: set = set()
            while len(reached) < len(cfg.steer_nodes):
                if not self._running:
                    self.stop("호밍 중 백엔드 종료")
                    self.release_steer_target("호밍 중 백엔드 종료")
                    return False, "백엔드가 내려갔다 — 조향 정지 지령 송신"
                if time.monotonic() - t0 > timeout_s:
                    self.stop("호밍 타임아웃")
                    ok_h = self.release_steer_target("호밍 타임아웃")
                    with self._lock:
                        rem = {n: (None if self.nodes[n].position is None else
                                   self.nodes[n].position - int(cfg.steer_home_offset[n]))
                               for n in cfg.steer_nodes}
                    return False, (f"{timeout_s:.0f}초 안에 도착하지 못했다 "
                                   f"(도착 {sorted(reached)}, 잔차 {rem}) — "
                                   f"조향 정지 {'송신' if ok_h else '실패'}")
                nowm = time.monotonic()
                with self._lock:
                    for n in cfg.steer_nodes:
                        st = self.nodes[n]
                        if not st.fresh(nowm, cfg.feedback_ttl_s):
                            continue
                        if P.home35_reached(st.statusword, st.position,
                                            cfg.steer_home_offset[n],
                                            cfg.home_reach_tol_counts):
                            reached.add(n)
                time.sleep(poll_s)

            self._log("호밍 2단계 — 0x6098=35 (현재 위치를 홈으로, 각도 0)")
            with self._lock:
                before = {n: self.nodes[n].aborts for n in cfg.steer_nodes}
                # C3: 재영점으로 좌표계가 바뀌므로 **구 절대목표를 반드시 버린다.**
                #     안 버리면 다음 틱에 그 값이 새 좌표계에서 수십 도로 재해석돼 나간다.
                self._steer_counts = {}
                self._steer_target_deg = None
            frames = []
            for n in cfg.steer_nodes:
                frames.extend(P.home35_set_frames(n, cfg.bus))
            self._send(frames)

            # C4: 보내고 끝내지 않는다 — abort 여부와 실제 재영점을 확인한 뒤에만 잠금을 푼다.
            time.sleep(max(0.3, poll_s * 3))
            with self._lock:
                aborted = [n for n in cfg.steer_nodes
                           if self.nodes[n].aborts > before.get(n, 0)]
                newpos = {n: self.nodes[n].position for n in cfg.steer_nodes}
            if aborted:
                self.release_steer_target("0x6098 거부")
                return False, (f"드라이브가 0x6098=35 를 거부했다 (노드 {aborted}) — "
                               f"홈 미설정. 조향 잠금 유지")
            far = {n: v for n, v in newpos.items()
                   if v is None or abs(v) > cfg.home_reach_tol_counts * 20}
            if far:
                self.release_steer_target("재영점 미확인")
                return False, (f"0x6098=35 후에도 0x6064 가 0 근처가 아니다 {far} — "
                               f"재영점 미확인. 조향 잠금 유지")
            self._homed = True
            return True, (f"method 35 완료 — 현재 위치가 홈(0°). 0x6064={newpos}. "
                          f"⚠ 전원 사이클마다 다시 해야 한다")
        finally:
            self._homing = False

    def cancel_home(self) -> tuple[bool, str]:
        """진행 중인 호밍을 취소한다.

        펌웨어가 `0x60FB:04 = 0` 취소 프레임을 낸다
        (`safety_seer_gate.h:312-316` `seer_home_cancel_frames`). 취소는 펌웨어에서
        **항상 수리**되므로(전제조건 없음) 어떤 상태에서도 요청할 수 있다.
        """
        if str(self.cfg.homing_method) == "35":
            # method 35 는 우리가 `0x607A` 를 쓰므로 우리가 멈춘다. 이동 중 정지는
            # 구동 0 + 조향 setpoint 중단으로 성립한다(펌웨어 관여 없음).
            self._homing = False
            self.stop("호밍 취소")
            ok_h = self.release_steer_target("호밍 취소")
            self._log("호밍 취소 — method 35")
            return ok_h, ("취소 수리 — 조향 정지 지령 송신" if ok_h else
                          "⚠ 취소 요청했으나 조향 정지 지령을 못 보냈다(실측 위치 미확보)")
        try:
            ok = self.link.homing_cancel()
        except (NotImplementedError, LinkError) as exc:
            return False, f"취소 요청 실패: {type(exc).__name__}: {exc}"
        self._log("호밍 취소 요청" + ("" if ok else " — 펌웨어가 거부"))
        return bool(ok), "취소 요청 수리" if ok else "펌웨어가 취소를 거부"

    def home(self, speed: int = 0, poll_s: float = 0.2,
             timeout_s: float = 180.0) -> tuple[bool, str]:
        """조향 호밍. **물리 스윙 100°+ 가 발생한다** — 이동구역 확인 후 호출할 것.

        **펌웨어 시퀀서(`0xea`/`0xeb`)를 쓴다** — SDO 로 `0x60FB:04=1` 을 직접 보내지 않는다.
        이유는 하나: 그래야 `cancel_home()` 이 **호스트 생사와 무관하게** 성립한다.
        펌웨어는 권한·모드 상실을 감지하면 스스로 취소를 낸다(`safety_seer_gate.h:360`).
        ⚠ 정정 2026-08-03: 종전 주석의 「직접 송신 경로에는 취소 수단이 없어 하드웨어 E-STOP
        밖에 남지 않는다」는 **과장이었다** — 취소 프레임은 `0x60FB:04` 에 0 을 쓰는 SDO 하나라
        직접 경로로도 낼 수 있다. 차이는 가능 여부가 아니라 **보증 주체**다
        (`safety_seer_gate.h:312-316` 이 펌웨어 측 취소 프레임을 내는 자리다).

        `speed=0` 이면 펌웨어 기본값(2500 = 250 r/min)을 쓴다. 그 외에는 100~3000 만
        허용된다(`safety_seer_gate.h:207-208`).

        ⚠ 폴백을 두지 않는다. 펌웨어가 시퀀서를 지원하지 않으면 **실패로 보고**하고
        SDO 직접 송신으로 내려가지 않는다 — 덜 안전한 경로로 조용히 미끄러지는 것이
        정확히 tech-debt-shortcut 이기 때문이다.
        """
        if self._homing:
            return False, "이미 호밍 중"
        if not self._running:
            return False, "백엔드가 기동돼 있지 않다"
        self.stop("호밍 전 구동 0")
        if str(self.cfg.homing_method) == "35":
            return self._home_method35(poll_s, timeout_s)
        with self._lock:
            for st in self.nodes.values():
                st.statusword = None    # 직전 상태워드를 완료로 오독하지 않도록
        self._homing = True
        try:
            try:
                accepted = self.link.homing_start(speed)
            except (NotImplementedError, LinkError) as exc:
                return False, (f"펌웨어 호밍 시퀀서를 쓸 수 없다 "
                               f"({type(exc).__name__}: {exc}). SDO 직접 송신으로 "
                               f"대체하지 않는다 — 그 경로엔 취소 수단이 없다")
            if not accepted:
                return False, ("펌웨어가 호밍을 거부했다 — 전제조건 미충족"
                               "(제어권·safety_mode 30·이전 호밍 종료·속도 범위)")
            self._log("호밍 개시 — 펌웨어 시퀀서. 취소는 cancel_home()")
            t0 = time.monotonic()
            last = None
            while True:
                st = self.link.homing_status()
                self._homing_status = st
                if st.get("state_name") != last:
                    last = st.get("state_name")
                    self._log(f"호밍 상태 {last} (경과 {st.get('elapsed_s')}s)")
                if st.get("terminal"):
                    ok = st.get("state") in HOMING_OK
                    self._homed = bool(ok)
                    return ok, (f"{st.get('state_name')} "
                                f"({st.get('elapsed_s')}s, "
                                f"reached_mask=0x{st.get('reached_mask', 0):02X})")
                if time.monotonic() - t0 > timeout_s:
                    self.cancel_home()
                    return False, f"{timeout_s:.0f}초 초과 — 취소 요청함"
                if not self._running:
                    self.cancel_home()
                    return False, "백엔드가 내려갔다 — 취소 요청함"
                time.sleep(poll_s)
        finally:
            self._homing = False

    # ── 상태 ──────────────────────────────────────────────────────────
    def snapshot(self) -> dict:
        now = time.monotonic()
        with self._lock:
            nodes = {}
            for n, st in self.nodes.items():
                nodes[n] = {
                    "position": st.position,
                    "statusword": st.statusword,
                    "velocity_raw": st.velocity_raw,
                    "current_raw": st.current_raw,
                    "digital_input": st.digital_input,
                    "fresh": st.fresh(now, self.cfg.feedback_ttl_s),
                    "homed": S.is_homed(st.statusword),
                    "aborts": st.aborts,
                    "last_abort": st.last_abort,
                }
            return {
                "drive_units": self._drive_units,
                "drive_units_by_node": dict(self._drive_units_by_node),
                "steer_target_deg": self._steer_target_deg,
                "estop": self._estop,
                "homing": self._homing,
                "homed": self._homed,                 # 우리가 호밍했는가
                "homed_effective": self.homed_effective(),  # 드라이브 보고 포함(Seer 호밍)
                "homing_method": str(self.cfg.homing_method),
                "fault": self._fault,
                "running": self._running,
                "engaged": self.link.engaged,
                "tx": self.tx_count,
                "rx": self.rx_count,
                "watchdog_trips": self.watchdog_trips,
                "tx_fail_streak": self._tx_fail_streak,
                "loop_fail_streak": self._loop_fail_streak,
                "hb_suppressed": self._hb_suppressed,
                "nodes": nodes,
                "bus_health": dict(self._bus_health),
                "health_supported": self._health_supported,
                "health_error": self._health_error,
                "homing_status": dict(self._homing_status),
            }

    def halt_note(self) -> str:
        """직전 `release_steer_target` 이 놓을 목표가 없었다면 그 사유. 있었으면 빈 문자열."""
        return self._halt_note

    def bus_fault(self) -> Optional[str]:
        """버스가 정상이 아니면 사유 1줄, 정상이면 None.

        `bus_off` 는 노드가 버스에서 떨어진 것이라 최우선이다. `error_passive` 는
        에러 카운터가 128 을 넘어 송신이 제한된 상태다.
        """
        with self._lock:
            health = dict(self._bus_health)
        for bus, h in sorted(health.items()):
            if h.get("bus_off"):
                return f"bus{bus} BUS-OFF (REC={h.get('rec')} TEC={h.get('tec')})"
        for bus, h in sorted(health.items()):
            if h.get("error_passive"):
                return f"bus{bus} error-passive (REC={h.get('rec')} TEC={h.get('tec')})"
        for bus, h in sorted(health.items()):
            if h.get("error_warning"):
                return f"bus{bus} error-warning (REC={h.get('rec')} TEC={h.get('tec')})"
        return None

    def steer_angles_deg(self) -> dict:
        """축별 조향 실측각. **믿을 수 없는 축은 None** 이다.

        믿을 수 없는 경우: 상태워드 미확보 / 호밍 진행 중(bit15=0) / 피드백 만료.
        """
        now = time.monotonic()
        out = {}
        with self._lock:
            for n in self.cfg.steer_nodes:
                st = self.nodes.get(n)
                if st is None or not st.fresh(now, self.cfg.feedback_ttl_s):
                    out[n] = None
                    continue
                if not S.position_trustworthy(st.statusword) or st.position is None:
                    out[n] = None
                    continue
                home = self.cfg.steer_home.get(n)
                out[n] = None if home is None else \
                    (st.position - home) / self.cfg.steer_counts_per_deg
        return out

    def settled(self) -> bool:
        target = self._steer_target_deg
        if target is None:
            return False
        measured = {n: v for n, v in self.steer_angles_deg().items()
                    if v is not None}
        return S.settled(target, measured, self.cfg.steer_nodes,
                         self.cfg.settle_tol_deg)

    # ── 내부 ──────────────────────────────────────────────────────────
    def _drive_frames(self, units) -> list:
        """구동 프레임. `units` 가 dict 면 **노드별 값**, 정수면 전 노드 동일.

        노드별을 지원하는 이유: 제자리 선회는 두 구동륜이 반대 부호여야 성립한다.
        예전에는 첫 값 하나로 뭉개서 선회 지령이 조용히 직진이 됐다(H5).
        """
        if isinstance(units, dict):
            return [P.drive_velocity_frame(n, int(v), self.cfg.bus)
                    for n, v in sorted(units.items()) if n in self.cfg.drive_nodes]
        return [P.drive_velocity_frame(n, int(units), self.cfg.bus)
                for n in self.cfg.drive_nodes]

    def _send(self, frames):
        frames = list(frames)
        if not frames:
            return
        self.link.send(frames)
        self.tx_count += len(frames)

    def _write_bringup(self):
        """브링업 시퀀스. ⚠ 실기 검증 이력이 없는 구간이다(기본 비활성)."""
        frames = []
        for n in self.cfg.drive_nodes:
            frames.extend(P.drive_init_frames(n, self.cfg.bus))
        for n in self.cfg.steer_nodes:
            frames.extend(P.steer_init_frames(n, self.cfg.bus))
        self._send(frames)
        self._log(f"브링업 {len(frames)} 프레임 송신 (⚠ 실기 미검증 경로)")

    def _loop(self):
        cfg = self.cfg
        cmd_iv = 1.0 / cfg.cmd_hz
        poll_iv = 1.0 / cfg.poll_hz
        health_iv = 1.0 / cfg.health_hz if cfg.health_hz > 0 else float("inf")
        next_poll = 0.0
        next_hb = 0.0
        next_health = 0.0
        while self._running:
            now = time.monotonic()
            try:
                # ⚠ 심박은 "지령이 실제로 나가고 있을 때"만 보낸다.
                #   판다 경유에서 유일한 정지 근간은 **심박 상실 → 펌웨어 fail-safe** 다.
                #   송신이 죽었는데 심박만 계속 뛰면 fail-safe 가 무장 해제된 채
                #   드라이브가 마지막 지령을 물고 간다(2026-08-01 can_send_errs 1,712만).
                if now >= next_hb:
                    if self._tx_fail_streak >= self.cfg.tx_fail_halt:
                        if not self._hb_suppressed:
                            self._hb_suppressed = True
                            self._log(f"⚠ 송신 연속 실패 {self._tx_fail_streak}회 — "
                                      f"심박 중단. 펌웨어 fail-safe 에 정지를 넘긴다")
                    else:
                        self.link.heartbeat()
                        self._hb_suppressed = False
                    next_hb = now + HEARTBEAT_PERIOD_S

                # 워치독 — 유효 지령이 끊기면 속도 0 으로 수렴한다.
                with self._lock:
                    stale = (now - self._last_cmd_time) > cfg.cmd_timeout_s
                    if stale or self._estop:
                        units = 0
                    elif self._drive_units_by_node:
                        units = dict(self._drive_units_by_node)
                    else:
                        units = self._drive_units
                    steer = dict(self._steer_counts)
                    if stale and (self._drive_units != 0 or self._drive_units_by_node):
                        self._drive_units = 0
                        self._drive_units_by_node = {}
                        self.watchdog_trips += 1
                        self._log("워치독 — 지령 만료, 속도 0")

                frames = self._drive_frames(units)
                # E-stop 중에는 조향 setpoint 를 **밀어넣지 않는다**. 예전에는 units 만
                # 0 으로 만들고 `0x607A` 는 계속 보냈다 — 근거는 회귀
                # `test_estop_stops_resending_steer_setpoints` 가 고정한다
                # (E-stop 후 0.3s 동안 `0x607A` 송신 증가분 0 을 단언).
                if not self._homing and not self._estop:
                    for n, counts in steer.items():
                        frames.extend(P.steer_target_frames(n, counts, cfg.bus))
                if now >= next_poll:
                    frames.extend(P.poll_frames(
                        tuple(cfg.drive_nodes) + tuple(cfg.steer_nodes), cfg.bus))
                    next_poll = now + poll_iv
                # 송신 실패만 따로 센다 — 이 카운터가 심박 중단(=정지)을 결정하므로
                # 수신·진단 쪽 예외를 섞으면 읽기 경로 오류가 로봇을 세운다(리뷰 M2).
                try:
                    self._send(frames)
                except Exception:
                    self._tx_fail_streak += 1
                    raise
                self._tx_fail_streak = 0
                self._drain()
                if now >= next_health:
                    self._poll_bus_health()
                    next_health = now + health_iv
                self._fault = None
                self._loop_fail_streak = 0
            except Exception as exc:
                # LinkError 도 Exception 하위다 — 따로 적으면 "구분해서 다룬다"는
                # 인상만 주고 동작은 같다. 광범위 포획인 것을 그대로 적는다(리뷰 L3).
                # 조용히 죽지 않는다 — 상태에 남겨 진단이 집어낼 수 있게 한다.
                if self._tx_fail_streak == 0:
                    self._loop_fail_streak += 1
                    kind, streak = "루프", self._loop_fail_streak
                else:
                    kind, streak = "송신", self._tx_fail_streak
                self._fault = f"{type(exc).__name__}: {exc} "\
                              f"({kind} 연속 {streak}회)"
                self._log(f"제어 루프 오류: {self._fault}")
                time.sleep(0.05)
            time.sleep(max(0.0, cmd_iv - (time.monotonic() - now)))

    def _poll_bus_health(self):
        """버스별 bxCAN 에러 상태(0xc3)를 읽는다.

        **읽기 전용이라 제어 경로에 영향이 없다** — 실패해도 지령·정지는 그대로 돈다.

        실패를 두 가지로 나눈다. 섞으면 일시적 오류 하나로 진단이 영구히 꺼진다:
          · `NotImplementedError` — 링크가 이 기능 자체를 갖지 않는다 → **영구 비활성**
          · 그 외 예외 — 일시적일 수 있다 → 계속 재시도하되 **사유가 바뀔 때만 로그**
        """
        if self._health_supported is False:
            return                          # 기능 부재로 확정된 경우만 건너뛴다
        health = {}
        for bus in (SEER_BUS, self.cfg.bus):
            try:
                health[bus] = self.link.can_health(bus)
            except NotImplementedError:
                self._health_supported = False
                self._health_error = "링크가 can_health 를 지원하지 않는다"
                self._log(f"버스 헬스 폴링 영구 비활성 — {self._health_error}")
                return
            except Exception as exc:
                why = f"{type(exc).__name__}: {exc}"
                if why != self._health_error:
                    self._health_error = why
                    self._log(f"버스 헬스 폴링 실패(재시도 계속) — {why}")
                return
        with self._lock:
            self._bus_health = health
        if self._health_error is not None:
            self._log("버스 헬스 폴링 회복")
        self._health_error = None
        self._health_supported = True

    def _drain(self):
        """수신 처리. 판다는 fwd 여부와 무관하게 모든 프레임을 올려 준다."""
        for can_id, data, bus in self.link.recv():
            if bus != self.cfg.bus:
                continue
            resp = P.parse_sdo_response(can_id, data)
            if resp is None or resp.node not in self.nodes:
                continue
            self.rx_count += 1
            st = self.nodes[resp.node]
            with self._lock:
                st.last_seen = time.monotonic()
                if resp.kind == "abort":
                    st.aborts += 1
                    st.last_abort = resp.value
                    self._log(
                        f"SDO 거부 N{resp.node} 0x{resp.index:04X}:{resp.sub:02X} "
                        f"→ 0x{resp.value:08X} ({P.abort_text(resp.value)})")
                    continue
                if resp.kind != "read":
                    continue
                if resp.index == P.OBJ_POSITION_ACTUAL:
                    st.position_prev = st.position
                    st.position = resp.value
                elif resp.index == P.OBJ_STATUSWORD:
                    st.statusword = resp.value & 0xFFFF
                elif resp.index == P.OBJ_VELOCITY_ACTUAL:
                    st.velocity_raw = resp.value
                elif resp.index == P.OBJ_CURRENT_ACTUAL:
                    st.current_raw = resp.value
                elif resp.index == P.OBJ_DIGITAL_INPUT and resp.sub == 1:
                    st.digital_input = resp.value
