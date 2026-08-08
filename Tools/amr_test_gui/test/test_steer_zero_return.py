"""호밍 완료 후 **조향 0° 복귀** 회귀 (`gui.py`).

고정하는 계약(ADR `docs/adr/2026-08-08-steer-zero-return-after-homing.md`):

  ① 호밍 원점 신호(bit15 0→1) 뒤에 **0° 지령이 실제로 나간다** — `0x607A = STEER_HOME` + `0x6040=0x3F`.
     종전에는 이 경로가 0° 지령을 **한 번도 내지 않고** "조향 0° 복귀까지 확인하세요"라고
     육안에 위임했다. 그 문장이 사실이 아니었던 것이 이 작업의 출발점이다.
  ② **펌웨어 GOZERO 정착값(`7882020` / `7859062`)에 서 있는 것은 0° 도달이 아니다**
     — 0° 대비 +0.178° / +0.331°.
  ③ 0° 미도달이면 완료로 적지 않는다.
  ④ 판정 허용오차는 `STEER_ZERO_TOL_DEG` 이고, 사용자 정착 허용치(0.5~10°)가 **아니다.**

⚠ 실기 미검증 — `_sdo_write` 를 가로챈 하드웨어 없는 시험이다.
"""
from __future__ import annotations

import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
import gui  # noqa: E402

BIT15 = 1 << 15
STEER = (3, 4)
# 펌웨어 GOZERO 목표(`safety_seer_gate.h:212-213`) = 호밍 후 정착값. **0° 가 아니다.**
GOZERO = {3: 7882020, 4: 7859062}


@pytest.fixture(scope="module")
def app():
    yield QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def win(app):
    w = gui.MainWindow()
    w.HOMING_START_S = 1.0
    w.HOMING_TIMEOUT_S = 3.0
    w.STEER_ZERO_TIMEOUT_S = 1.0
    yield w
    w._seer_run = False
    w._run = False
    w._homing = False


@pytest.fixture
def sent(win, monkeypatch):
    log = []
    monkeypatch.setattr(win, "_sdo_write",
                        lambda node, idx, val, size, sub=0: log.append((node, idx, val, size, sub)))
    return log


def hold_at(win, counts: dict):
    """두 조향축이 `counts` 위치에 있다고 실측을 세운다(신선도 포함)."""
    for n in STEER:
        win._set_meas(n, (counts[n] - gui.STEER_HOME[n]) / gui.COUNTS_PER_DEG)


def run_homing(win, at: dict | None):
    """원점 신호를 흘려 주고 `_homing_run` 을 끝까지 돌린다.

    `at` 은 0° 복귀 지령이 나간 뒤 축이 서 있게 될 위치(counts)다. `None` 이면 실측 없음.
    """
    win._run = True
    win._homing = True

    def feed():
        time.sleep(0.05)
        win._status.update({n: 0 for n in STEER})       # 개시(bit15=0)
        # ⚠ 이 국면은 `_wait_homed` 의 폴 주기(0.1 s)보다 **길어야** 한다 — 짧으면
        #   개시를 관측하기 전에 완료로 덮여 「개시 신호를 못 봤습니다」로 떨어진다.
        time.sleep(0.4)
        win._status.update({n: BIT15 for n in STEER})   # 완료(bit15=1)
        if at is not None:
            for _ in range(40):                          # 정착 대기 동안 실측을 계속 공급
                hold_at(win, at)
                time.sleep(0.05)

    t = threading.Thread(target=feed, daemon=True)
    t.start()
    win._homing_run()
    t.join(timeout=3)


def targets(sent):
    """`0x607A` 쓰기에서 {node: counts}. 마지막 값이 최종 목표."""
    out = {}
    for node, idx, val, _size, _sub in sent:
        if idx == 0x607A:
            out[node] = val
    return out


# ── ① 0° 지령이 실제로 나간다 ────────────────────────────────────────────
def test_homing_issues_the_zero_command(win, sent):
    run_homing(win, at=dict(gui.STEER_HOME))
    assert targets(sent) == dict(gui.STEER_HOME), (
        "호밍 뒤 조향 목표가 0°(=STEER_HOME) 가 아니다 — 0° 복귀 지령이 없다")


def test_zero_command_is_applied_with_controlword(win, sent):
    """`0x607A` 만으로는 축이 움직이지 않는다 — `0x6040=0x3F` 가 따라야 한다."""
    run_homing(win, at=dict(gui.STEER_HOME))
    cw_after_target = [f for f in sent if f[1] == 0x6040 and f[2] == 0x3F]
    assert len(cw_after_target) >= len(STEER)


def test_zero_command_comes_after_the_homing_trigger(win, sent):
    """0° 지령이 호밍 트리거보다 **먼저** 나가면 호밍이 그것을 덮어쓴다."""
    run_homing(win, at=dict(gui.STEER_HOME))
    last_trigger = max(i for i, f in enumerate(sent) if f[1] == 0x60FB)
    first_zero = min(i for i, f in enumerate(sent) if f[1] == 0x607A)
    assert last_trigger < first_zero


# ── ② GOZERO 정착값은 0° 가 아니다 ───────────────────────────────────────
@pytest.mark.parametrize("node,expected", [(3, 0.178), (4, 0.331)])
def test_gozero_settle_value_is_not_zero(node, expected):
    """편차가 0 이면 이 작업 자체가 불필요하다 — 전제를 숫자로 고정한다."""
    off = (GOZERO[node] - gui.STEER_HOME[node]) / gui.COUNTS_PER_DEG
    assert off == pytest.approx(expected, abs=0.001)


def test_axis_left_at_gozero_is_not_reported_complete(win, sent):
    """정착값에 남아 있으면 0° 도달이 아니다 — 완료로 적지 않는다."""
    logs = []
    win.log_line.connect(logs.append)
    run_homing(win, at=GOZERO)
    assert any("호밍 미확인" in m and "0° 복귀 미확인" in m for m in logs), logs
    assert not any("호밍 완료" in m for m in logs), logs


def test_user_settle_tolerance_would_have_accepted_the_offset(win):
    """왜 사용자 정착 허용치를 쓰지 않는가 — 그 폭이면 위 편차가 통과한다.

    허용오차를 슬라이더 값(최소 0.5°)으로 되돌리면
    `test_axis_left_at_gozero_is_not_reported_complete` 가 깨진다. 그 이유가 이것이다.
    """
    worst = max(abs(GOZERO[n] - gui.STEER_HOME[n]) / gui.COUNTS_PER_DEG for n in STEER)
    assert worst < 0.5                        # 슬라이더 최소값 안 → 검출 불가
    assert worst > win.STEER_ZERO_TOL_DEG     # 전용 허용오차 밖 → 검출 가능


# ── ③ 미도달·실측 부재는 완료가 아니다 ──────────────────────────────────
def test_missing_measurement_is_not_completion(win, sent):
    logs = []
    win.log_line.connect(logs.append)
    run_homing(win, at=None)                  # 실측을 한 번도 공급하지 않는다
    assert any("0° 복귀 미확인" in m and "실측없음" in m for m in logs), logs


def test_homing_failure_skips_the_zero_command(win, sent):
    """원점 신호를 못 봤으면 0° 지령을 내지 않는다 — 기준이 없는 채로 축을 움직이지 않는다."""
    win._run = True
    win._homing = True
    win._status = {n: BIT15 for n in STEER}   # 시작 전부터 1 → 개시 미관측 → 실패
    win._homing_run()
    assert not [f for f in sent if f[1] == 0x607A]


# ── 0° 의 출처 ───────────────────────────────────────────────────────────
def test_zero_target_is_the_canonical_home_constant():
    """0° 는 `STEER_HOME`(정본 YAML)에서 나온다 — 이 경로가 자기 상수를 갖지 않는다."""
    for n in STEER:
        deg, counts = gui.steer_counts(n, 0.0)
        assert deg == 0.0
        assert counts == gui.STEER_HOME[n]
