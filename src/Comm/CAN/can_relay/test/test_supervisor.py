"""감시 노드 회귀 — 판정과 파싱을 ROS·하드웨어 없이 고정한다.

`decide()` 는 이 노드의 **모든 판단이 모이는 한 곳**이다. 순수 함수로 둔 이유가
여기서 전 분기를 고정하기 위해서이므로, 분기가 늘면 이 파일도 같이 는다.

특히 고정하는 것:
  · 수동 해제(진단 두절 없음)를 복귀시키지 않는다 — 감시자가 운용자와 싸우면 안 된다
  · E-stop·crash-loop 이면 복귀하지 않는다
  · 「모름」(프로세스 확인 실패)을 사망으로 단정하지 않는다
"""
import json
import os

from can_relay.health import (DEAD, HOLD, IDLE, RESTORE, RUNNING, WAIT, ZOMBIE,
                              Observation, SupervisorConfig, as_level, boot_id,
                              decide, default_state_dir, is_outage, next_prev,
                              next_was_down, parse_diag, proc_alive, prune_stamps,
                              restore_call_expired)

CFG = SupervisorConfig(diag_timeout_s=3.0, restart_limit=3, restart_window_s=120.0)
ENGAGED = {"engaged": True}
IDLE_STATE = {"engaged": False}


# ── parse_diag ────────────────────────────────────────────────────────────
def test_parse_diag_reads_key_values():
    st = parse_diag([("engaged", "True"), ("estop", "False"),
                     ("steer_target_deg", "45.0"), ("hb_suppressed", "False")],
                    level=0, message="정상")
    assert st["engaged"] is True
    assert st["estop"] is False
    assert st["steer_target_deg"] == 45.0
    assert st["message"] == "정상"


def test_level_accepts_bytes_from_rclpy():
    """`DiagnosticStatus.level` 은 rclpy 에서 **bytes 한 바이트**다.

    ⚠ 이 시험이 없어서 `int(b"\\x01")` 이 그대로 나갔고, SIL 에서 감시자가 **첫 진단에
    죽었다**. 단위 시험이 `level=0` 을 정수로만 넘겨 실물 타입을 한 번도 안 봤기 때문이다.
    """
    assert as_level(b"\x00") == 0
    assert as_level(b"\x01") == 1
    assert as_level(b"\x02") == 2
    assert as_level(2) == 2              # 정수도 그대로 받는다
    assert as_level(None) == 0           # 알 수 없으면 0 — 판정은 key/value 가 한다
    st = parse_diag([("engaged", "True")], level=b"\x02", message="CAN 버스 이상")
    assert st["level"] == 2 and st["engaged"] is True


def test_parse_diag_omits_missing_keys():
    """빠진 키를 기본값으로 채우지 않는다 — 「관측 못 함」과 「거짓 관측」은 다르다."""
    st = parse_diag([("engaged", "True")])
    assert "estop" not in st
    assert "homed_effective" not in st


def test_parse_diag_accepts_objects_with_key_attr():
    """실제 `KeyValue` 처럼 `.key`/`.value` 를 가진 객체도 받는다."""
    class KV:
        def __init__(self, k, v):
            self.key, self.value = k, v

    st = parse_diag([KV("engaged", "true"), KV("drive_units", "0")])
    assert st["engaged"] is True
    assert st["drive_units"] == "0"


def test_parse_diag_bad_float_becomes_none():
    st = parse_diag([("steer_target_deg", "None")])
    assert st["steer_target_deg"] is None


# ── decide: 진단이 있는 경우 ───────────────────────────────────────────────
def test_running_when_engaged():
    v, _ = decide(None, Observation(cur=ENGAGED, diag_age=0.1), CFG)
    assert v == RUNNING


def test_manual_disengage_is_not_restored():
    """진단이 끊긴 적 없이 제어권만 내려갔다 = 사람이 내렸다. 되돌리지 않는다."""
    v, why = decide(ENGAGED, Observation(cur=IDLE_STATE, diag_age=0.1,
                                         was_down=False), CFG)
    assert v == IDLE
    assert "수동" in why


def test_restore_after_downtime():
    """두절을 겪은 뒤 제어권이 없고 직전 기록이 보유였다면 복귀한다(안정화 충족 시)."""
    v, _ = decide(ENGAGED, Observation(cur=IDLE_STATE, diag_age=0.1,
                                       was_down=True, cur_settle_s=10.0), CFG)
    assert v == RESTORE


def test_no_restore_when_previous_state_was_idle():
    """직전에도 제어권이 없었으면 되돌릴 것이 없다."""
    v, _ = decide(IDLE_STATE, Observation(cur=IDLE_STATE, diag_age=0.1,
                                          was_down=True), CFG)
    assert v == IDLE


def test_no_restore_without_record():
    v, _ = decide(None, Observation(cur=IDLE_STATE, diag_age=0.1,
                                    was_down=True), CFG)
    assert v == IDLE


def test_estop_holds_restore():
    """E-stop 인가 중에는 제어권을 다시 잡지 않는다."""
    v, why = decide(ENGAGED, Observation(cur={"engaged": False, "estop": True},
                                         diag_age=0.1, was_down=True), CFG)
    assert v == HOLD
    assert "E-stop" in why


def test_home_failed_in_prev_holds_restore():
    """**재기동 뒤에는 `prev` 만이 래치를 기억한다** — 이것이 이 게이트의 본체다.

    `_home_failed` 는 인스턴스 변수라 새 프로세스는 False 로 시작한다. 즉 재기동 직후의
    `cur` 에는 래치가 없다 — 게이트가 `cur` 만 보면 **막으려던 그 소실을 그대로 따라간다.**
    처음 이 시험을 `cur` 기준으로 써서 게이트가 무동작인 채 통과했고, SIL 실험 3 이 잡았다.
    """
    v, why = decide({"engaged": True, "home_failed": True},
                    Observation(cur={"engaged": False, "home_failed": False},
                                diag_age=0.1, was_down=True), CFG)
    assert v == HOLD, "재기동으로 래치가 지워진 경우를 막지 못한다"
    assert "호밍" in why


def test_home_failed_in_cur_also_holds_restore():
    """같은 프로세스가 아직 래치를 들고 있는 경우도 막는다(양쪽 다 본다)."""
    v, _ = decide(ENGAGED, Observation(cur={"engaged": False, "home_failed": True},
                                       diag_age=0.1, was_down=True), CFG)
    assert v == HOLD


def test_home_failed_false_does_not_block():
    """정상 호밍 뒤에는 막지 않는다 — 게이트가 항상 걸리면 복귀 기능이 죽는다.

    `prev`·`cur` **양쪽 모두** 래치가 없어야 복귀가 성립한다.
    """
    v, _ = decide({"engaged": True, "home_failed": False},
                  Observation(cur={"engaged": False, "home_failed": False},
                              diag_age=0.1, was_down=True, cur_settle_s=10.0), CFG)
    assert v == RESTORE


def test_parse_diag_reads_home_failed():
    """진단에서 실제로 읽어야 게이트가 동작한다 — 상류가 KeyValue 로 낸다."""
    st = parse_diag([("engaged", "False"), ("home_failed", "True")])
    assert st["home_failed"] is True


def test_crash_loop_holds_restore():
    """반복 복귀는 Seer 에게서 버스를 뺏었다 놓기를 반복한다 — 멈춘다."""
    v, why = decide(ENGAGED, Observation(cur=IDLE_STATE, diag_age=0.1,
                                         was_down=True, restarts_in_window=3), CFG)
    assert v == HOLD
    assert "crash-loop" in why


def test_restore_disabled_holds():
    cfg = SupervisorConfig(restore_enabled=False)
    v, _ = decide(ENGAGED, Observation(cur=IDLE_STATE, diag_age=0.1,
                                       was_down=True), cfg)
    assert v == HOLD


# ── next_prev: 「직전 상태」 승격 ──────────────────────────────────────────
def test_prev_is_promoted_while_diagnostics_flow():
    """감시자가 살아 있는 동안 관측이 직전 상태가 된다.

    ⚠ 이것이 없으면 **복귀가 영원히 안 된다** — 기록 파일은 기동 시 한 번 읽을 뿐이라
    「감시자는 살고 드라이버만 재기동」이라는 설계 의도 경로에서 prev 가 계속 비어 있다.
    SIL 실험 1 이 잡은 결함이며, 단위 시험은 `decide()` 만 봐서 못 잡았다.
    """
    assert next_prev(None, ENGAGED, RUNNING) == ENGAGED
    assert next_prev(None, IDLE_STATE, IDLE) == IDLE_STATE


def test_prev_is_not_overwritten_while_blind():
    """두절 구간(DEAD·ZOMBIE·WAIT)은 상태를 모르므로 직전 상태를 덮지 않는다."""
    for v in (DEAD, ZOMBIE, WAIT):
        assert next_prev(ENGAGED, None, v) == ENGAGED


def test_prev_promotion_survives_restore_cycle():
    """복귀 1회전이 실제로 성립하는지 — 승격·판정을 이어 붙여 확인한다."""
    prev = None
    prev = next_prev(prev, ENGAGED, RUNNING)              # 정상 운전 중
    v, _ = decide(prev, Observation(cur=None, diag_age=9.0, proc_alive=False), CFG)
    assert v == DEAD
    prev = next_prev(prev, None, v)                        # 두절 — 덮지 않는다
    v, _ = decide(prev, Observation(cur=IDLE_STATE, diag_age=0.1, was_down=True,
                                    cur_settle_s=10.0), CFG)
    assert v == RESTORE, "재기동 후 복귀가 성립하지 않는다"


def test_manual_disengage_is_promoted_so_later_restart_does_not_restore():
    """사람이 내린 상태도 승격된다 — 그래야 나중 재기동이 되살리지 않는다."""
    prev = next_prev(next_prev(None, ENGAGED, RUNNING), IDLE_STATE, IDLE)
    v, _ = decide(prev, Observation(cur=IDLE_STATE, diag_age=0.1, was_down=True), CFG)
    assert v == IDLE


def test_outage_is_a_fact_not_a_verdict():
    """두절 판정은 경과 시간으로 한다 — 「첫 진단 전」·「임계 안 공백」은 두절이 아니다."""
    assert is_outage(Observation(cur=None, diag_age=None), CFG) is False
    assert is_outage(Observation(cur=None, diag_age=CFG.diag_timeout_s - 0.1), CFG) is False
    assert is_outage(Observation(cur=None, diag_age=CFG.diag_timeout_s + 0.1), CFG) is True
    assert is_outage(Observation(cur=ENGAGED, diag_age=99.0), CFG) is False


def test_was_down_set_by_outage_not_by_verdict():
    """빠른 재기동은 `DEAD` 를 거치지 않고 유예 `WAIT` 로만 덮인다.

    표시를 판정 이름으로 세우면 그 경로에서 표시가 서지 않아, 되살아난 노드의
    `engaged=False` 가 「수동 해제」로 오독되고 **복귀가 조용히 건너뛰어진다.**
    """
    assert next_was_down(False, WAIT, outage=True) is True    # 유예 WAIT 도 세운다
    assert next_was_down(False, DEAD, outage=True) is True
    assert next_was_down(False, WAIT, outage=False) is False   # 임계 안 공백은 아니다


def test_was_down_clears_only_on_observed_running():
    """복귀 서비스 성공만으로는 내리지 않는다 — 내리면 복귀가 한 번만 되고 끝난다."""
    assert next_was_down(True, RESTORE, outage=False) is True
    assert next_was_down(True, IDLE, outage=False) is True
    assert next_was_down(True, RUNNING, outage=False) is False


def test_fast_restart_still_restores():
    """유예 WAIT 만 거친 빠른 재기동에서도 복귀가 성립한다(실험 4 실패 형태)."""
    prev = next_prev(None, ENGAGED, RUNNING)
    was_down = False
    # 두절이지만 프로세스가 살아 있어 유예 WAIT — DEAD 를 거치지 않는다
    obs = Observation(cur=None, diag_age=CFG.diag_timeout_s + 0.5, proc_alive=True)
    v, _ = decide(prev, obs, CFG)
    assert v == WAIT
    was_down = next_was_down(was_down, v, is_outage(obs, CFG))
    assert was_down is True
    v, _ = decide(prev, Observation(cur=IDLE_STATE, diag_age=0.1,
                                    was_down=was_down, cur_settle_s=10.0), CFG)
    assert v == RESTORE, "빠른 재기동에서 복귀가 건너뛰어진다"


def test_restore_survives_repeated_cycles():
    """복귀 → 관측 → 재사망 을 두 바퀴 돌려 두 번째 복귀도 성립하는지 본다."""
    prev, was_down = None, False
    for _ in range(2):
        prev = next_prev(prev, ENGAGED, RUNNING)
        was_down = next_was_down(was_down, RUNNING, outage=False)
        down = Observation(cur=None, diag_age=9.0, proc_alive=False)
        v, _ = decide(prev, down, CFG)
        assert v == DEAD
        was_down = next_was_down(was_down, v, is_outage(down, CFG))
        v, _ = decide(prev, Observation(cur=IDLE_STATE, diag_age=0.1,
                                        was_down=was_down, cur_settle_s=10.0), CFG)
        assert v == RESTORE, "두 번째 주기에서 복귀가 성립하지 않는다"


def test_restore_call_expires_so_restore_is_never_permanently_blocked():
    """무응답 복귀 호출은 시한 뒤 포기한다.

    `rclpy` 의 `call_async` future 는 응답이 와야만 완료되고 자체 시한이 없다. 호출 직후
    대상이 죽으면 future 가 영원히 미완료로 남고, 중복 방지 가드가 그것을 보고 있으면
    **이후 모든 복귀가 영구 차단된다** — 감시자의 존재 이유가 사라진다.
    """
    assert restore_call_expired(None, 100.0, CFG) is False        # 진행 중 호출 없음
    t0 = 100.0
    assert restore_call_expired(t0, t0 + CFG.restore_call_timeout_s - 0.1, CFG) is False
    assert restore_call_expired(t0, t0 + CFG.restore_call_timeout_s + 0.1, CFG) is True


def test_restore_waits_for_settle_window():
    """재기동 직후의 첫 진단만으로는 복귀하지 않는다.

    latched 토픽(estop 등)은 DDS 재전달이 첫 진단보다 늦을 수 있다 — 그 진단 하나로
    복귀하면 **E-stop 인가 중에 제어권을 되찾는다**(SIL 실험 5 가 이 형태로 실패했다).
    """
    v, why = decide(ENGAGED, Observation(cur=IDLE_STATE, diag_age=0.1,
                                         was_down=True, cur_settle_s=0.5), CFG)
    assert v == WAIT
    assert "안정화" in why
    # 모름(None)은 「안정됐다」로 치지 않는다
    v, _ = decide(ENGAGED, Observation(cur=IDLE_STATE, diag_age=0.1,
                                       was_down=True, cur_settle_s=None), CFG)
    assert v == WAIT
    # 경계: 충족 직후에는 복귀
    v, _ = decide(ENGAGED, Observation(cur=IDLE_STATE, diag_age=0.1, was_down=True,
                                       cur_settle_s=CFG.restore_settle_s + 0.1), CFG)
    assert v == RESTORE


def test_hold_gates_do_not_wait_for_settle():
    """차단 게이트는 안정화 전에도 동작한다 — 막는 쪽은 항상 안전하다."""
    v, _ = decide(ENGAGED, Observation(cur={"engaged": False, "estop": True},
                                       diag_age=0.1, was_down=True, cur_settle_s=0.1), CFG)
    assert v == HOLD
    v, _ = decide({"engaged": True, "home_failed": True},
                  Observation(cur={"engaged": False}, diag_age=0.1,
                              was_down=True, cur_settle_s=0.1), CFG)
    assert v == HOLD


# ── decide: 진단이 없는 경우 ───────────────────────────────────────────────
def test_restarting_process_is_not_called_zombie():
    """재기동 직후(프로세스 있음·진단 아직 없음)를 좀비로 부르지 않는다.

    정상 재기동마다 ERROR 를 내면 경보가 무의미해진다. 진짜 좀비는 무기한 조용하므로
    유예를 둬도 놓치지 않는다.
    """
    # 두절 임계는 넘고 좀비 유예는 안 넘는 구간 — 재기동 직후가 여기 있다.
    # ⚠ 경계값을 상수로 박지 않는다. 실기 기동이 30 s 걸린다는 실측으로 유예가 6 → 45 s
    #   로 바뀐 적이 있고, 그때 이 시험이 상수 때문에 깨졌다.
    age = (CFG.diag_timeout_s + CFG.zombie_after_s) / 2
    v, why = decide(ENGAGED, Observation(cur=None, diag_age=age, proc_alive=True), CFG)
    assert v == WAIT
    # 문구가 아니라 의미를 본다 — 임계값이 사유에 실려 운용자가 얼마나 더 기다리는지 안다.
    assert f"{CFG.zombie_after_s:.0f}" in why


def test_long_silence_with_live_process_is_zombie():
    v, _ = decide(ENGAGED, Observation(cur=None, diag_age=CFG.zombie_after_s + 0.1,
                                       proc_alive=True), CFG)
    assert v == ZOMBIE



def test_wait_before_first_diagnostic():
    v, _ = decide(None, Observation(cur=None, diag_age=None), CFG)
    assert v == WAIT


def test_wait_within_timeout():
    """임계 안의 공백은 두절이 아니다 — 한 주기 놓쳤다고 사망 선언하지 않는다."""
    v, _ = decide(None, Observation(cur=None, diag_age=1.0), CFG)
    assert v == WAIT


def test_dead_when_process_gone():
    v, why = decide(ENGAGED, Observation(cur=None, diag_age=5.0,
                                         proc_alive=False), CFG)
    assert v == DEAD
    assert "프로세스 없음" in why


def test_zombie_when_process_alive_but_silent():
    """살아 있는데 조용하다 = ROS 계층 정체. 정지는 백엔드 심박 억제가 처리한다.

    ⚠ `zombie_after_s`(유예) 도입으로 기대가 바뀌었다 — 종전 5.0 s 는 이제 유예 안이라
    `WAIT` 다. 유예를 넘긴 침묵만 좀비로 본다(재기동 직후 오탐을 막기 위한 것).
    """
    v, why = decide(ENGAGED, Observation(cur=None, diag_age=CFG.zombie_after_s + 1.0,
                                         proc_alive=True), CFG)
    assert v == ZOMBIE
    assert "정체" in why


def test_unknown_process_state_is_not_called_zombie():
    """프로세스 확인 실패를 「살아 있다」로 읽지 않는다 — 모름은 모름이다."""
    v, why = decide(ENGAGED, Observation(cur=None, diag_age=5.0,
                                         proc_alive=None), CFG)
    assert v == DEAD
    assert "확인 불가" in why


def test_prune_stamps_is_pure_and_windowed():
    """잘라내기는 새 목록을 돌려주고 원본을 바꾸지 않는다(조회·갱신 분리)."""
    stamps = [100.0, 150.0, 190.0]
    out = prune_stamps(stamps, now=200.0, window_s=60.0)
    assert out == [150.0, 190.0]
    assert stamps == [100.0, 150.0, 190.0]      # 원본 불변
    assert prune_stamps([], 200.0, 60.0) == []


# ── 보조 함수 ─────────────────────────────────────────────────────────────
def test_boot_id_reads_file(tmp_path):
    p = tmp_path / "boot_id"
    p.write_text("abc-123\n")
    assert boot_id(str(p)) == "abc-123"


def test_boot_id_missing_file_returns_empty():
    """읽지 못해도 예외를 던지지 않는다 — 대조를 포기하되 기록은 계속한다."""
    assert boot_id("/nonexistent/boot_id") == ""


def test_proc_alive_finds_and_misses(tmp_path):
    """`/proc` 순회를 가짜 트리로 시험한다 — 실제 프로세스에 의존하지 않는다."""
    (tmp_path / "100").mkdir()
    (tmp_path / "100" / "comm").write_text("can_relay_node\n")
    (tmp_path / "self").mkdir()          # 숫자가 아닌 항목은 건너뛴다
    assert proc_alive("can_relay_node", str(tmp_path)) is True
    assert proc_alive("nothing_here", str(tmp_path)) is False


def test_proc_alive_truncates_to_comm_limit(tmp_path):
    """`comm` 은 15자로 잘린다 — 비교도 잘라서 해야 긴 이름이 항상 미스가 되지 않는다."""
    (tmp_path / "101").mkdir()
    (tmp_path / "101" / "comm").write_text("a" * 15 + "\n")
    assert proc_alive("a" * 20, str(tmp_path)) is True


def test_proc_alive_unreadable_root_is_unknown():
    assert proc_alive("x", "/nonexistent/proc") is None


def test_default_state_dir_is_under_runtime():
    d = default_state_dir()
    assert d.endswith("can_relay")
    assert os.path.isabs(d)


def test_state_record_roundtrips_as_json():
    """기록은 JSON 직렬화 가능해야 한다 — 원자적 저장이 이 형식을 전제한다."""
    rec = dict(parse_diag([("engaged", "True"), ("steer_target_deg", "12.5")]))
    rec.update(boot_id="b", saved_at=1.0, restore_stamps=[1.0, 2.0])
    assert json.loads(json.dumps(rec, ensure_ascii=False))["engaged"] is True


# ── 배선 — 판정이 보는 「직전 기록」이 관측을 따라가는가 ────────────────
#
# 아래 시험들은 `decide()` 를 직접 부르지 않는다. `decide` 에 무엇이 **전달되는지**가
# 대상이기 때문이다. 순수 함수 시험은 인자를 시험자가 넣으므로 이 구간을 지나가지 않는다.
import time as _time

import pytest

# `conftest.py` 는 「설치·소싱 없이도 돈다」를 계약으로 선언한다. 모듈 스코프에서 rclpy 를
# 그냥 import 하면 미소싱 환경에서 **이 파일 전체가 수집 단계에서 터지고**, 수집 에러는
# 실행 전체를 중단시킨다 — 같은 파일의 순수 시험까지 못 돌게 된다.
rclpy = pytest.importorskip("rclpy", reason="rclpy 미소싱 — 배선 시험만 건너뛴다")
from can_relay.supervisor import RelaySupervisor  # noqa: E402


@pytest.fixture
def sup(tmp_path):
    rclpy.init(args=["--ros-args", "-p", f"state_dir:={tmp_path}"])
    node = RelaySupervisor()
    yield node
    node.destroy_node()
    rclpy.shutdown()


def _observe(node, engaged: bool):
    """진단 1장을 받은 것으로 만들고 틱을 한 번 돌린다."""
    node._cur = {"level": 0, "message": "정상", "engaged": engaged, "estop": False}
    node._last_diag = _time.monotonic()
    node._on_tick()


def test_engaging_reaches_the_decision_input(sup):
    """제어권을 잡은 사실이 다음 틱의 판정 입력에 도달해야 한다."""
    assert (sup._prev or {}).get("engaged") in (None, False)
    _observe(sup, engaged=True)
    assert (sup._prev or {}).get("engaged") is True, (
        "제어권 획득이 판정 입력에 도달하지 않는다 — 복귀가 영영 걸리지 않는다")


def test_releasing_also_reaches_the_decision_input(sup):
    """반환도 같은 경로로 도달해야 한다 — 안 그러면 요청하지 않은 재획득이 난다."""
    _observe(sup, engaged=True)
    _observe(sup, engaged=False)
    assert (sup._prev or {}).get("engaged") is False, (
        "제어권 반환이 판정 입력에 도달하지 않는다 — 굳은 값으로 재획득이 일어난다")


# ── 두절 → 복귀 경로 (기존 배선 시험은 RUNNING→IDLE 만 밟는다) ────────────
def _down(node):
    """진단이 끊긴 것으로 만들고 틱을 돌린다."""
    node._cur = None
    node._last_diag = _time.monotonic() - (node.cfg.diag_timeout_s + 5.0)
    node._on_tick()


def test_transition_logging_survives_severity_change(sup):
    """상태 전이 로그가 severity 를 바꿔도 틱이 예외로 죽지 않아야 한다.

    rclpy 는 로그 컨텍스트를 호출 지점으로 캐시하고 severity 변경을 거부한다.
    한 줄에서 warn/info 를 번갈아 부르면 두 번째 호출이 `ValueError` 를 낸다.
    """
    _observe(sup, engaged=True)      # → RUNNING (info)
    _down(sup)                       # → DEAD    (warn) — 같은 자리에서 severity 변경
    assert sup._verdict != "RUNNING", "전이가 기록되지 않았다"
    assert sup._was_down is True, "두절 사실이 기록되지 않았다"


def test_restore_eligibility_survives_a_failed_attempt(sup, monkeypatch):
    """복귀 시도가 실패해도 다음 틱에 다시 시도할 수 있어야 한다.

    판정 입력을 복귀 틱에 덮으면 기회가 1회로 끝난다 — 재기동 직후 서비스
    디스커버리가 늦으면 그 한 번을 날리고 영구히 시도하지 않는다.
    안정화 창(`restore_settle_s`) 안에서는 복귀가 의도적으로 보류되므로,
    창 안에는 0회 · 창을 지난 뒤에는 틱마다 재시도를 요구한다.
    """
    tried = []
    monkeypatch.setattr(sup, "_restore", lambda: tried.append(1))   # 전송 실패 모사
    _observe(sup, engaged=True)
    _down(sup)
    _observe(sup, engaged=False)     # 재기동 — 안정화 창 안이라 보류
    assert not tried, "안정화 창 안에서 복귀가 나갔다 — latched E-stop 도착 전일 수 있다"
    sup._cur_seen_since -= sup.cfg.restore_settle_s + 0.1   # 창 경과 모사
    _observe(sup, engaged=False)     # 창 밖 첫 틱
    _observe(sup, engaged=False)     # 다음 틱
    assert len(tried) >= 2, f"복귀 시도가 {len(tried)}회뿐 — 실패하면 영구 포기한다"
