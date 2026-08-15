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
                              Observation, SupervisorConfig, boot_id, decide,
                              default_state_dir, parse_diag, proc_alive)

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
    """두절을 겪은 뒤 제어권이 없고 직전 기록이 보유였다면 복귀한다."""
    v, _ = decide(ENGAGED, Observation(cur=IDLE_STATE, diag_age=0.1,
                                       was_down=True), CFG)
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


def test_home_failed_holds_restore():
    """실패한 호밍 뒤에는 자동 복귀하지 않는다 — **재기동이 잠금을 지우기 때문**.

    `RelayBackend._home_failed` 는 인스턴스 변수라 새 프로세스에서 False 로 시작하고,
    드라이브의 `0x6041` bit15 는 실패한 호밍 뒤에도 1 로 남아 `homed_effective()` 가
    조향을 열어 준다. 그 위에 제어권까지 자동으로 얹으면 축이 어디 서 있는지 모르는 채
    지령이 나간다(0° 지령 시 ≈136.7° 스윙 — 상류 `54ceea4` 가 막은 그 사고).
    자동 재기동을 도입한 쪽이 그 래치를 이어받아야 한다.
    """
    v, why = decide(ENGAGED, Observation(cur={"engaged": False, "home_failed": True},
                                         diag_age=0.1, was_down=True), CFG)
    assert v == HOLD
    assert "호밍" in why


def test_home_failed_false_does_not_block():
    """정상 호밍 뒤에는 막지 않는다 — 게이트가 항상 걸리면 복귀 기능이 죽는다."""
    v, _ = decide(ENGAGED, Observation(cur={"engaged": False, "home_failed": False},
                                       diag_age=0.1, was_down=True), CFG)
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


# ── decide: 진단이 없는 경우 ───────────────────────────────────────────────
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
    """살아 있는데 조용하다 = ROS 계층 정체. 정지는 백엔드 심박 억제가 처리한다."""
    v, why = decide(ENGAGED, Observation(cur=None, diag_age=5.0,
                                         proc_alive=True), CFG)
    assert v == ZOMBIE
    assert "정체" in why


def test_unknown_process_state_is_not_called_zombie():
    """프로세스 확인 실패를 「살아 있다」로 읽지 않는다 — 모름은 모름이다."""
    v, why = decide(ENGAGED, Observation(cur=None, diag_age=5.0,
                                         proc_alive=None), CFG)
    assert v == DEAD
    assert "확인 불가" in why


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
