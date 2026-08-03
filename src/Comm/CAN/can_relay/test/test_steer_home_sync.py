"""조향 홈 정본 ↔ 사본 동기화 시험.

## 왜 있는가

2026-08-03 적대적 검증(변이 시험)에서 드러난 것: **정본 YAML 의 `steer_home_counts` 를
쓰레기 값으로 바꿔도 저장소 회귀 319건이 전부 통과했다.** 어떤 테스트도 정본 YAML 을
로드하지 않고, 픽스처가 값을 하드코딩해 자기 자신과 비교하기 때문이다(동어반복).

실제로 2026-08-02~08-03 사이 저장소는 **정본(구값)과 사본 6곳·픽스처(신값)가 서로 모순인
상태로 319/319 green** 이었고 아무 게이트도 울리지 않았다.

⇒ 본 시험이 그 공백을 메운다. **값이 무엇인지는 판정하지 않는다**(그것은 실측의 몫이다).
   판정하는 것은 **정본과 사본이 같은가** 하나뿐이다.

## 정본
`src/Comm/CAN/can_relay/config/machine/foil_a082.yaml` 의 `steer_home_counts`.
값의 근거는 `docs/homing/2026-08-03-can-relay-homing-assets.md` §10 및 그 §11(적대적 검증 정정).

⚠ 범위: 이 값은 **Seer 좌표계의 0°** 이며 물리적 직진은 미확정이다(같은 문서 §11).
   본 시험은 그 유보와 무관하게 **일관성만** 강제한다.
"""
from __future__ import annotations

import os
import re

import pytest


def _repo_root() -> str:
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        if os.path.isdir(os.path.join(d, ".git")) or os.path.isdir(os.path.join(d, "Tools")):
            return d
        d = os.path.dirname(d)
    raise RuntimeError("저장소 루트를 찾지 못했다")


REPO = _repo_root()
CANONICAL = os.path.join(REPO, "src/Comm/CAN/can_relay/config/machine/foil_a082.yaml")

# 사본 — (경로, 정규식). 정규식은 캡처그룹 2개(node3, node4)를 내야 한다.
# 주석 안의 이력 인용은 잡지 않도록 **선언문만** 매칭한다.
COPIES = [
    ("src/Actuators/motor_control/config/tongyi_amr.yaml",
     r"^\s*steer_home_counts:\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]"),
    ("src/Actuators/motor_control/motor_control/driver_node.py",
     r'^\s*\("steer_home_counts",\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]\)'),
    ("Tools/amr_test_gui/gui.py",
     r"^STEER_HOME\s*=\s*\{\s*3:\s*(\d+)\s*,\s*4:\s*(\d+)\s*\}"),
    ("Tools/Kinematics/chassis_kinematics.py",
     r"^STEER_HOME\s*=\s*\{\s*3:\s*(\d+)\s*,\s*4:\s*(\d+)\s*\}"),
    ("Tools/docking_field_kit/docking_drive.py",
     r"^STEER_HOME\s*=\s*\{\s*3:\s*(\d+)\s*,\s*4:\s*(\d+)\s*\}"),
    ("Tools/docking_field_kit/amap2_monitor.py",
     r"^STEER_HOME\s*=\s*\{\s*3:\s*(\d+)\s*,\s*4:\s*(\d+)\s*\}"),
    ("Tools/docking_field_kit/orin_home_experiment.py",
     r"^HOME_0DEG\s*=\s*\{\s*3:\s*(\d+)\s*,\s*4:\s*(\d+)\s*\}"),
]

# 픽스처 — 정본과 같아야 하는 테스트 상수.
FIXTURES = [
    ("src/Comm/CAN/can_relay/test/test_safety.py",
     r"^HOME\s*=\s*\{\s*3:\s*(\d+)\s*,\s*4:\s*(\d+)\s*\}"),
    ("src/Actuators/motor_control/test/test_backend.py",
     r"^HOME\s*=\s*\{\s*3:\s*(\d+)\s*,\s*4:\s*(\d+)\s*\}"),
]


def _read_canonical() -> tuple[int, int]:
    """정본 YAML 에서 `steer_home_counts` 선언을 읽는다.

    yaml 모듈에 의존하지 않는다 — 이 파일은 ROS2 파라미터 형식이라
    일반 파서로도 최상위 구조가 단순하지 않고, 우리가 볼 것은 한 줄뿐이다.
    """
    assert os.path.exists(CANONICAL), f"정본 부재: {CANONICAL}"
    pat = re.compile(r"^\s*steer_home_counts:\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]", re.M)
    hits = pat.findall(open(CANONICAL, encoding="utf-8").read())
    assert len(hits) == 1, f"정본에 steer_home_counts 선언이 {len(hits)}개 (1개여야 한다)"
    return int(hits[0][0]), int(hits[0][1])


def _extract(rel: str, pattern: str):
    path = os.path.join(REPO, rel)
    if not os.path.exists(path):
        pytest.skip(f"대상 부재(저장소 부분 체크아웃?): {rel}")
    hits = re.compile(pattern, re.M).findall(open(path, encoding="utf-8").read())
    assert hits, (
        f"{rel} 에서 조향 홈 선언을 찾지 못했다.\n"
        f"  패턴: {pattern}\n"
        f"  → 상수를 옮기거나 이름을 바꿨다면 본 시험의 COPIES/FIXTURES 도 함께 갱신할 것."
    )
    assert len(hits) == 1, f"{rel} 에 선언이 {len(hits)}개 (1개여야 한다): {hits}"
    return int(hits[0][0]), int(hits[0][1])


def test_canonical_is_readable():
    n3, n4 = _read_canonical()
    assert n3 > 0 and n4 > 0, "정본 값이 양수여야 한다"


@pytest.mark.parametrize("rel,pattern", COPIES, ids=[c[0] for c in COPIES])
def test_copy_matches_canonical(rel, pattern):
    """사본이 정본과 다르면 실패한다 — 이것이 본 파일의 존재 이유다."""
    assert _extract(rel, pattern) == _read_canonical(), (
        f"조향 홈 사본이 정본과 다르다.\n"
        f"  정본 {CANONICAL} = {_read_canonical()}\n"
        f"  사본 {rel} = {_extract(rel, pattern)}\n"
        f"  → 정본이 유일 근원이다. 사본을 정본에 맞춰라."
    )


@pytest.mark.parametrize("rel,pattern", FIXTURES, ids=[f[0] for f in FIXTURES])
def test_fixture_matches_canonical(rel, pattern):
    """픽스처가 정본과 어긋나면 다른 회귀가 전부 동어반복이 된다."""
    assert _extract(rel, pattern) == _read_canonical(), (
        f"테스트 픽스처가 정본과 다르다 — 다른 회귀의 통과가 무의미해진다.\n"
        f"  정본 = {_read_canonical()}  픽스처 {rel} = {_extract(rel, pattern)}"
    )


def test_firmware_gozero_is_not_the_home_constant():
    """펌웨어 GOZERO 상수가 조향 홈으로 오인돼 복제되지 않았는지 지킨다.

    `SEER_HOME_ZERO_N3/N4`(7882020 / 7859062)는 **호밍 후 정착 목표**이며 0° 가 아니다
    (0° 에서 +0.178° / +0.331°). 이름에 ZERO 가 들어가 반복적으로 혼동돼 왔다 — debt-034.
    값을 고치는 것은 실기 검증이 선행돼야 하므로, 여기서는 **홈으로 새어 들어오는 것만** 막는다.
    """
    fw = os.path.join(REPO, "Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h")
    if not os.path.exists(fw):
        pytest.skip("펌웨어 소스 부재")
    src = open(fw, encoding="utf-8", errors="replace").read()
    gozero = {int(v) for v in re.findall(r"#define\s+SEER_HOME_ZERO_N[34]\s+(\d+)", src)}
    assert gozero, "펌웨어에서 SEER_HOME_ZERO_N3/N4 를 찾지 못했다"
    assert gozero.isdisjoint(set(_read_canonical())), (
        f"펌웨어 GOZERO 상수 {sorted(gozero)} 가 조향 홈 정본 {_read_canonical()} 과 겹친다.\n"
        f"  둘은 서로 다른 물리량이다 — 같아졌다면 어느 한쪽이 잘못 복제된 것이다."
    )
