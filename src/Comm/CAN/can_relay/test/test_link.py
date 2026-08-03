"""판다 링크 계층 회귀 — 하드웨어 없이 바이트 계약을 고정한다.

이 파일이 메우는 공백: `docs/adr/2026-07-31-can-relay-cpp-motor-layer.md:184` 가
「`link.py` 의 `PandaLink` 경로(커버리지 45%)는 여전히 회귀 그물 밖」이라고 지적했다.
여기서는 **순수 디코더**와 **MockLink 상태기계**를 고정한다(USB 왕복은 여전히 실기 몫).

바이트 배치의 근거는 펌웨어 원문이다:
  0xc3 → `board/health.h:29-37` `can_health_t`
  0xeb → `board/usb_comms.h:417-426`
  상태 enum → `board/safety/safety_seer_gate.h:222-233`
"""
import struct

import pytest

from can_relay import link as L


# ── 0xc3 can_health 디코더 ────────────────────────────────────────────────
def build_health(bus_off=0, passive=0, warn=0, lec=0, rec=0, tec=0, esr=0):
    return struct.pack("<BBBBBBI", bus_off, passive, warn, lec, rec, tec, esr)


def test_can_health_decodes_firmware_layout():
    d = L.decode_can_health(build_health(bus_off=1, passive=1, warn=1, lec=3,
                                         rec=200, tec=128, esr=0xDEADBEEF))
    assert d["bus_off"] == 1 and d["error_passive"] == 1 and d["error_warning"] == 1
    assert d["last_error_code"] == 3
    assert d["rec"] == 200 and d["tec"] == 128
    assert d["esr_reg"] == 0xDEADBEEF


def test_can_health_counters_are_uint8_and_saturate():
    """REC/TEC 는 bxCAN 에서 8비트다 — 255 위를 구분할 수 없다."""
    d = L.decode_can_health(build_health(rec=255, tec=255))
    assert d["rec"] == 255 and d["tec"] == 255


def test_can_health_packet_is_ten_bytes():
    """`can_health_t` = uint8×6 + uint32 packed = 10B.

    0xeb 호밍 상태(8B)와 길이가 다르다 — 섞으면 언팩이 어긋난다.
    펌웨어 `board/usb_comms.h:43` `get_can_health_pkt` 이 구조체를 그대로 쓴다.
    """
    assert L.CAN_HEALTH_STRUCT.size == 10
    assert len(build_status()) == 8


def test_can_health_rejects_short_response():
    with pytest.raises(L.LinkError):
        L.decode_can_health(b"\x00" * 7)


# ── 0xeb 호밍 상태 디코더 ─────────────────────────────────────────────────
def build_status(state=0, done=0, seen=0, elapsed=0, di3=0, di4=0, reached=0):
    return bytes([state, done, seen, elapsed & 0xFF, (elapsed >> 8) & 0xFF,
                  di3, di4, reached])


def test_homing_status_decodes_firmware_layout():
    d = L.decode_homing_status(build_status(state=4, done=0b01, seen=0b11,
                                            elapsed=300, di3=1, di4=9, reached=0b10))
    assert (d["state"], d["state_name"]) == (4, "WAIT")
    assert d["elapsed_s"] == 300            # LE u16 이 바이트 3·4 에 걸쳐 있다
    assert d["done_mask"] == 0b01 and d["reached_mask"] == 0b10
    assert d["digital_in"] == {3: 1, 4: 9}


@pytest.mark.parametrize("state,name,terminal", [
    (0, "IDLE", True), (1, "ENABLE", False), (2, "SET_SPEED", False),
    (3, "START", False), (4, "WAIT", False), (5, "DONE", True),
    (6, "ERR_TIMEOUT", True), (7, "ERR_ABORT", True), (8, "RESTORE", False),
    (9, "GOZERO", False), (10, "ERR_GOZERO", True), (11, "GOZERO_W", False),
])
def test_homing_state_table_matches_firmware(state, name, terminal):
    d = L.decode_homing_status(build_status(state=state))
    assert d["state_name"] == name
    assert d["terminal"] is terminal


def test_only_done_counts_as_success():
    """ERR_ABORT·ERR_TIMEOUT 도 terminal 이지만 성공이 아니다."""
    assert L.HOMING_OK == frozenset({5})
    for bad in (6, 7, 10):
        assert bad in L.HOMING_TERMINAL and bad not in L.HOMING_OK


def test_homing_status_rejects_short_response():
    with pytest.raises(L.LinkError):
        L.decode_homing_status(b"\x00" * 7)


# ── 라이브러리 사본 해석 (①) ─────────────────────────────────────────────
def test_panda_sources_prefer_superset_copy():
    """`can_health()` 를 가진 docking_field_kit 사본이 우선이어야 한다."""
    first, second = L._PANDA_SOURCES
    assert first[0].endswith("docking_field_kit") and first[1] == "panda"
    assert second[0].endswith("panda-firmware") and second[1] == "python"


def test_panda_source_paths_are_repo_relative():
    """저장소 밖 절대경로 하드코딩이 아니어야 이식·재현이 된다."""
    for root, _ in L._PANDA_SOURCES:
        assert L._REPO in root


def test_repo_root_actually_contains_the_tools_dir():
    """**경로가 실재하는지**까지 본다 — 이게 없어서 실기에서 처음 터졌다.

    2026-08-01: `_REPO` 가 `dirname` 을 고정 5회 호출해 `.../Big-AMR/src` 를 루트로
    잡았고, 회귀 155건이 전부 `MockLink` 라 아무도 못 잡았다. 실기 연결 순간
    `LinkError: panda 라이브러리를 찾지 못했다` 로 드러났다.
    문자열 비교만 하면 같은 버그를 또 놓친다 — 디렉터리 존재를 확인한다.
    """
    import os
    # ⚠ 단언 대상은 **git 추적 자산**이어야 한다. 판다 라이브러리(`Tools/docking_field_kit/panda`,
    #   `Tools/Can_Relay/panda-firmware/python`)는 벤더 사본이라 **추적되지 않는다**
    #   (`git ls-files` → 0건). 그것의 존재를 단언하면 새 clone·worktree·CI 어디서도
    #   실패한다 — 실제로 2026-08-02 세션 worktree 에서 이 시험만 깨졌다.
    #   그래서 루트 판정은 추적 자산으로 하고, 판다 사본은 있을 때만 본다.
    assert os.path.isdir(os.path.join(L._REPO, "Tools", "docking_field_kit")), \
        f"_REPO 가 저장소 루트가 아니다: {L._REPO}"
    assert os.path.isfile(os.path.join(L._REPO, "README.md")), \
        f"_REPO 가 저장소 루트가 아니다(README.md 없음): {L._REPO}"


def test_panda_source_candidates_exist_when_vendored():
    """판다 사본이 배치된 환경에서는 후보 중 최소 하나가 실재해야 한다.

    사본은 미추적이라 없을 수 있다(새 clone·worktree). 그때는 건너뛴다 —
    **없는 것이 정상**인 환경에서 실패하면 시험이 거짓말을 하는 것이다.
    실기 배포 환경에서는 사본이 있으므로 이 시험이 실제로 돈다.
    """
    import os
    import pytest
    existing = [os.path.join(r, m) for r, m in L._PANDA_SOURCES
                if os.path.isdir(os.path.join(r, m))]
    if not existing:
        pytest.skip("판다 사본 미배치 환경(미추적 자산) — 실기 환경에서만 검사")
    # 배치돼 있으면 **실제로 import 되는지**까지 본다. 디렉터리 존재만 보면
    # 경로는 맞는데 import 가 깨진 경우를 놓친다(실기에서 그게 곧 기동 실패다).
    mod = L._panda_module()
    assert hasattr(mod, "list"), f"판다 모듈에 list() 가 없다: {mod!r}"


def test_repo_root_finder_is_depth_independent():
    """깊이를 세지 않고 마커로 찾으므로, 더 깊은 경로에서도 같은 루트가 나온다."""
    import os
    deep = os.path.join(L._REPO, "src", "Comm", "CAN", "can_relay",
                        "can_relay", "a", "b", "link.py")
    assert L._find_repo_root(deep) == L._REPO


# ── 펌웨어 계약 상수 ──────────────────────────────────────────────────────
def test_firmware_contract_constants():
    assert L.SAFETY_SEER_GATE == 30          # safety.h
    assert (L.REQ_INTERCEPT, L.REQ_AUTHORITY, L.REQ_HEARTBEAT) == (0xE8, 0xE9, 0xF3)
    assert (L.REQ_CAN_HEALTH, L.REQ_HOMING_CMD, L.REQ_HOMING_STATUS) == (0xC3, 0xEA, 0xEB)
    assert (L.HOMING_SPEED_MIN, L.HOMING_SPEED_MAX) == (100, 3000)
    assert L.HOMING_NODES == (3, 4)          # SEER_HOME_NODE_LO/HI


# ── MockLink 호밍 상태기계 ────────────────────────────────────────────────
def engaged_mock():
    m = L.MockLink()
    m.open()
    m.acquire()
    return m


def test_homing_requires_authority():
    m = L.MockLink()
    m.open()
    with pytest.raises(L.LinkError):
        m.homing_start()


def test_homing_start_then_cancel_marks_abort():
    m = engaged_mock()
    assert m.homing_start() is True
    assert m.homing_status()["terminal"] is False
    assert m.homing_cancel() is True
    st = m.homing_status()
    assert st["state_name"] == "ERR_ABORT" and st["terminal"] is True


def test_cancel_is_always_accepted_even_when_idle():
    """펌웨어와 같은 성질 — 취소에는 전제조건이 없다."""
    m = engaged_mock()
    assert m.homing_cancel() is True
    assert m.homing_status()["state_name"] == "IDLE"


def test_restart_refused_while_running():
    m = engaged_mock()
    m.homing_start()
    assert m.homing_start() is False        # terminal 아니면 거부


@pytest.mark.parametrize("speed", [99, 3001, 5000])
def test_mock_rejects_out_of_range_speed(speed):
    m = engaged_mock()
    assert m.homing_start(speed) is False


@pytest.mark.parametrize("speed", [0, 100, 2500, 3000])
def test_mock_accepts_allowed_speed(speed):
    m = engaged_mock()
    assert m.homing_start(speed) is True


def test_can_health_fixture_roundtrip():
    m = engaged_mock()
    with pytest.raises(L.LinkError):
        m.can_health(2)                     # 픽스처 미설정이면 조용히 0 을 주지 않는다
    m.health_fixture = {2: L.decode_can_health(build_health(rec=7, tec=9))}
    assert m.can_health(2)["rec"] == 7
