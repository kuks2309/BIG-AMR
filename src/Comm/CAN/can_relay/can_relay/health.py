#!/usr/bin/env python3
"""노드 health 판정 — 순수 함수만. ROS·하드웨어·파일쓰기 무의존.

`safety.py` 와 같은 규율이다. 감시 노드의 **모든 판단**을 여기 모아 두고, `supervisor.py`
는 관측을 모아 넘기고 결과를 실행하는 껍데기만 담당한다.

분리 이유는 두 가지다:
  1. `conftest.py` 가 규정한 대로 **설치·소싱 없이** 회귀가 돌아야 한다. rclpy 뒤에 판정이
     갇히면 미소싱 환경에서 전 분기가 검증되지 않는다.
  2. 판정이 흩어지면 「무엇이 로봇의 제어권을 다시 잡게 했는가」가 로그에서 갈린다.

읽기(`/proc`·`boot_id`)는 여기 두되 쓰기는 두지 않는다 — 관측은 판정의 입력이고,
부작용은 호출부 책임이다.

## 재기동이 지우는 상태를 여기서 다시 세운다

`RelayBackend._home_failed`(실패한 호밍 뒤 조향을 잠그는 래치)는 **인스턴스 변수**라
프로세스가 죽으면 사라진다. 그 래치가 없던 시절에는 자동 재기동도 없었으므로 문제가
아니었으나, 자동 재기동을 붙이는 순간 「죽었다 살아나면 잠금이 풀린다」가 된다.
드라이브의 `0x6041` bit15 는 실패한 호밍 뒤에도 1 로 남으므로 새 프로세스는 조향을
열어 준다. 그래서 `decide()` 가 **관측된 `home_failed` 를 복귀 차단 사유로 든다.**
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Optional

BOOT_ID_PATH = "/proc/sys/kernel/random/boot_id"
PROC_ROOT = "/proc"
COMM_MAX = 15   # `/proc/<pid>/comm` 의 길이 한계. `system_health` 와 같은 제약이다.

# 판정 — `decide()` 의 반환 첫 값
WAIT = "WAIT"           # 진단을 아직 한 번도 못 받았다 / 임계 안의 공백
RUNNING = "RUNNING"     # 제어권 보유 중
IDLE = "IDLE"           # 살아 있으나 제어권 미획득
DEAD = "DEAD"           # 진단 두절 + 프로세스 없음(또는 확인 불가)
ZOMBIE = "ZOMBIE"       # 진단 두절 + 프로세스 생존
RESTORE = "RESTORE"     # 복귀 조건 충족 — `~/engage true` 를 부른다
HOLD = "HOLD"           # 복귀 조건 미충족 — 사유를 남기고 대기


@dataclass
class SupervisorConfig:
    """판정 임계. 하드웨어에 의존하지 않는다."""

    diag_timeout_s: float = 3.0
    #   진단이 이보다 끊기면 두절로 본다. 진단은 1 Hz 이므로 3 주기다.
    #   ⚠ 백엔드 심박 억제 임계(`ros_alive_timeout_s`, 2.0 s)보다 **길어야 한다** —
    #     짧으면 감시자가 먼저 두절을 선언하고, 정작 정지는 아직 걸리지 않은 구간이 생긴다.
    zombie_after_s: float = 45.0
    #   진단 두절이 이보다 길고 **프로세스가 살아 있으면** 좀비로 본다.
    #   `diag_timeout_s` 와 나누는 이유: 재기동 직후에는 프로세스가 이미 있고 진단은 아직
    #   없어 그 구간이 좀비처럼 보인다. 정상 재기동마다 ERROR 를 내면 경보가 무의미해진다.
    #   값의 근거: 실기 재기동에서 프로세스 등장 → 첫 진단까지 **30 s** 가 걸렸다
    #   (2026-08-15 실측, `ros2 launch` + 오버레이 소싱 포함). 그보다 여유를 둔다.
    #   진짜 좀비는 무기한 조용하므로 늦게 판정해도 놓치지 않는다 —
    #   **정지는 백엔드 심박 억제가 하고 이 판정은 관측용**이다.
    restore_enabled: bool = True
    restart_limit: int = 3
    restart_window_s: float = 120.0
    #   이 창 안에 복귀를 `restart_limit` 회 넘게 시도했으면 멈춘다. 반복 engage/release 는
    #   죽은 채 있는 것보다 나쁘다 — 그때마다 Seer 에게서 버스를 뺏었다 놓는다.


@dataclass
class Observation:
    """한 판정 시점의 관측. `decide()` 를 순수 함수로 두기 위한 입력 묶음."""

    cur: Optional[dict] = None
    #   현재 진단에서 뽑은 상태. `None` = 지금 진단이 없다
    diag_age: Optional[float] = None
    #   마지막 진단 수신 후 경과(초). `None` = 한 번도 못 받았다
    proc_alive: Optional[bool] = None
    #   대상 프로세스 존재. `None` = 확인하지 못했다(모름을 사망으로 단정하지 않는다)
    was_down: bool = False
    #   마지막 관측 이후 **진단 두절을 겪었는가**. 이것이 「재기동으로 제어권을 잃었다」와
    #   「사람이 내렸다」를 가른다 — 수동 해제는 진단이 끊기지 않으므로 복귀시키지 않는다
    restarts_in_window: int = 0


def boot_id(path: str = BOOT_ID_PATH) -> str:
    """부팅 식별자. 읽지 못하면 빈 문자열(대조를 포기하되 기록은 계속한다)."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except OSError:
        return ""


def default_state_dir() -> str:
    """상태 기록 디렉터리. 재부팅 시 사라지는 곳을 우선한다.

    systemd 운용에서는 유닛의 `RuntimeDirectory=can_relay` 가 `/run/can_relay` 를
    만들어 두므로 그것이 잡힌다. 어디로 떨어지든 `boot_id` 대조가 전원 사이클을
    걸러내므로 위치 자체가 안전을 결정하지는 않는다.
    """
    for cand in (os.environ.get("XDG_RUNTIME_DIR"), "/run"):
        if not cand:
            continue
        d = os.path.join(cand, "can_relay")
        if os.path.isdir(d) and os.access(d, os.W_OK):
            return d
        parent = os.path.dirname(d)
        if os.path.isdir(parent) and os.access(parent, os.W_OK):
            return d
    return os.path.join(tempfile.gettempdir(), "can_relay")


def proc_alive(name: str, proc_root: str = PROC_ROOT) -> Optional[bool]:
    """`/proc/*/comm` 에 그 이름이 있는가. 순회 자체가 실패하면 `None`(모름).

    `comm` 은 15자로 잘리므로 비교도 잘라서 한다 — 안 그러면 긴 실행파일명이 항상 미스가
    되어 좀비를 사망으로 오판한다.
    """
    key = name[:COMM_MAX]
    try:
        entries = os.listdir(proc_root)
    except OSError:
        return None
    for e in entries:
        if not e.isdigit():
            continue
        try:
            with open(os.path.join(proc_root, e, "comm"), "r") as f:
                if f.read().strip() == key:
                    return True
        except OSError:
            continue        # 순회 중 종료된 프로세스 — 정상
    return False


def _as_bool(text: str) -> bool:
    return str(text).strip().lower() in ("true", "1", "yes")


def as_level(level) -> int:
    """`DiagnosticStatus.level` → int.

    ⚠ **rclpy 에서 이 필드는 `bytes` 한 바이트다**(msg 정의가 `byte`). `int(b"\x01")` 은
    `ValueError` 를 던지므로 그대로 쓰면 첫 진단에서 감시자가 죽는다.
    변환 불가는 0 으로 두되, **판정은 level 이 아니라 key/value 로 한다** — level 은 기록용이다.
    """
    if isinstance(level, (bytes, bytearray)):
        return int.from_bytes(level, "big")
    try:
        return int(level)
    except (TypeError, ValueError):
        return 0


def _as_float(text: str) -> Optional[float]:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def parse_diag(values, level: int = 0, message: str = "") -> dict:
    """진단 KeyValue 목록 → 상태 dict.

    `values` 는 `.key`/`.value` 를 가진 객체들이거나 `(key, value)` 쌍이면 된다 —
    `diagnostic_msgs` 타입에 의존하지 않으려는 것이다.

    빠진 키는 넣지 않는다. 기본값으로 채우면 「관측하지 못한 것」과 「거짓으로 관측한
    것」이 구분되지 않고, 그 혼동이 곧 잘못된 복귀가 된다.
    """
    kv = {}
    for v in values or ():
        if hasattr(v, "key"):
            kv[str(v.key)] = str(v.value)
        else:
            k, val = v
            kv[str(k)] = str(val)
    out: dict = {"level": as_level(level), "message": str(message)}
    for key in ("engaged", "estop", "home_failed", "homed_effective",
                "hb_suppressed"):
        if key in kv:
            out[key] = _as_bool(kv[key])
    if "steer_target_deg" in kv:
        out["steer_target_deg"] = _as_float(kv["steer_target_deg"])
    if "drive_units" in kv:
        out["drive_units"] = kv["drive_units"]
    return out


def next_prev(prev: Optional[dict], cur: Optional[dict],
              verdict: str) -> Optional[dict]:
    """다음 판정에 쓸 「직전 상태」를 고른다.

    ⚠ **이것이 없으면 복귀가 영원히 안 된다.** 기록 파일은 기동 시 한 번 읽을 뿐이므로,
    감시자가 살아 있고 드라이버만 재기동되는 **설계가 의도한 바로 그 경로**에서
    `prev` 가 계속 비어 있게 된다.

    승격 조건은 「진단이 흐르는 동안의 관측」이다 — 두절 중 판정(`DEAD`·`ZOMBIE`·`WAIT`)은
    상태를 모르는 구간이므로 직전 상태를 덮지 않는다. 수동 해제(`IDLE`)는 덮는다:
    그래야 사람이 내려 둔 뒤 재기동해도 되살리지 않는다.
    """
    if cur is not None and verdict in (RUNNING, IDLE):
        return dict(cur)
    return prev


def is_outage(obs: Observation, cfg: SupervisorConfig) -> bool:
    """지금이 **진단 두절 구간**인가 — 판정 이름이 아니라 사실로 정한다.

    「한 번도 못 받음」과 「임계 안 공백」은 두절이 아니다.
    """
    return (obs.cur is None and obs.diag_age is not None
            and obs.diag_age > cfg.diag_timeout_s)


def next_was_down(was_down: bool, verdict: str, outage: bool) -> bool:
    """다음 판정에 쓸 「두절을 겪었는가」 표시.

    **세우는 근거는 판정 이름이 아니라 두절 사실이다.** 판정으로 세우면 빠른 재기동이
    좀비 유예(`WAIT`)로만 덮여 `DEAD` 를 거치지 않고, 그러면 되살아난 노드의
    `engaged=False` 가 「수동 해제」로 오독돼 **복귀가 조용히 건너뛰어진다.**

    **내리는 것은 `RUNNING` 관측뿐이다.** 복귀 서비스 성공만으로 내리면 진단이 아직
    따라오지 않은 한 틱이 같은 오독을 만든다(= 복귀가 한 번만 된다).
    """
    if outage:
        return True
    if verdict == RUNNING:
        return False
    return was_down


def decide(prev: Optional[dict], obs: Observation,
           cfg: SupervisorConfig) -> tuple[str, str]:
    """판정. 반환 `(판정, 사유)`. 사유는 로그·진단에 그대로 실린다.

    순서가 곧 우선순위다 — 진단 유무 → 제어권 보유 → 복귀 자격 → 차단 사유.
    """
    if obs.cur is None:
        if obs.diag_age is None:
            return WAIT, "진단을 아직 받지 못했다"
        if obs.diag_age <= cfg.diag_timeout_s:
            return WAIT, f"진단 {obs.diag_age:.1f}s 경과 (임계 {cfg.diag_timeout_s:.1f}s)"
        if obs.proc_alive is True and obs.diag_age >= cfg.zombie_after_s:
            return ZOMBIE, (
                f"진단 두절 {obs.diag_age:.1f}s 인데 프로세스는 살아 있다 "
                f"(임계 {cfg.zombie_after_s:.0f}s 초과) — 기동 지연이 아니라 정체로 본다. "
                f"정지는 백엔드 심박 억제가 처리한다")
        if obs.proc_alive is True:
            # 살아 있으나 아직 유예 안 — 재기동 직후일 수 있다. 사망으로 단정하지 않는다.
            return WAIT, (f"진단 두절 {obs.diag_age:.1f}s · 프로세스는 있다 — "
                          f"기동 중일 수 있다(좀비 판정까지 {cfg.zombie_after_s:.0f}s)")
        if obs.proc_alive is False:
            return DEAD, f"진단 두절 {obs.diag_age:.1f}s · 프로세스 없음"
        return DEAD, f"진단 두절 {obs.diag_age:.1f}s · 프로세스 확인 불가"

    if obs.cur.get("engaged"):
        return RUNNING, "제어권 보유"

    # 여기부터 engaged=false. 복귀 대상인지 가른다.
    if not obs.was_down:
        return IDLE, "제어권 미획득 (두절 없음 — 수동 해제로 본다)"
    if prev is None or not prev.get("engaged"):
        return IDLE, "제어권 미획득 (직전 기록도 미획득)"
    if not cfg.restore_enabled:
        return HOLD, "복귀 비활성(restore_enabled=false)"
    if obs.cur.get("estop"):
        return HOLD, "E-stop 인가 중 — 해제 후 복귀한다"
    if obs.cur.get("home_failed") or (prev or {}).get("home_failed"):
        # ⚠ **`prev` 를 함께 보는 것이 요점이다.** `_home_failed` 는 인스턴스 변수라
        # 재기동한 새 프로세스는 False 로 시작한다 — 즉 `cur` 만 보면 이 게이트가 막으려던
        # 바로 그 소실을 게이트가 따라간다. 살아남는 값은 두절 전 마지막 관측(`prev`)뿐이다.
        #
        # 왜 막아야 하나: 드라이브의 bit15 는 실패한 호밍 뒤에도 1 로 남아
        # `homed_effective()` 가 조향을 열어 준다. 거기에 제어권까지 자동으로 얹으면
        # 축이 어디 서 있는지 모르는 채 지령이 나간다(0° 지령 시 ≈136.7° 스윙).
        # 자동 해제 경로는 두지 않는다 — 해제는 `~/home` 재수행뿐이다.
        return HOLD, ("직전 호밍이 끝을 못 봤다(조향 잠금) — 재기동이 그 래치를 지우므로 "
                      "자동 복귀하지 않는다. `~/home` 재수행 후 복귀할 것")
    if obs.restarts_in_window >= cfg.restart_limit:
        return HOLD, (f"복귀 시도 {obs.restarts_in_window}회 / "
                      f"{cfg.restart_window_s:.0f}s — crash-loop 로 보고 멈춘다")
    return RESTORE, "직전 상태가 제어권 보유였다 — 복귀한다"
