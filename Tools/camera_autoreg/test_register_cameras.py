# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""register_cameras 순수 로직 단위 테스트 — 카메라·ROS 무의존."""
from collections import Counter

import cv2
import pytest

from generate_boards import BOARD_MAP, make_board, mm_to_px
from register_cameras import (
    build_mapping,
    decide_board,
    decide_flip,
    detect_board_votes,
    detect_flip_votes,
    render_udev_rules,
    rewrite_roster_flips,
    rewrite_roster_serials,
)


@pytest.mark.parametrize("board_no", sorted(BOARD_MAP))
def test_detect_board_votes_on_synthetic_board(board_no):
    square_px = mm_to_px(30.0, 150)
    img = make_board(board_no).generateImage(
        (6 * square_px, 6 * square_px), marginSize=square_px, borderBits=1)
    votes = detect_board_votes(img)
    assert set(votes) == {board_no}
    assert votes[board_no] == 18


def test_detect_board_votes_ignores_calibration_ids():
    # 캘리브레이션 보드(ID 0 시작) 합성 — 전 마커가 무소속(0)이라 득표 0 이어야 한다.
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_1000)
    board = cv2.aruco.CharucoBoard((6, 6), 30.0, 21.6, dictionary)  # ids 기본 = 0..17
    square_px = mm_to_px(30.0, 150)
    img = board.generateImage((6 * square_px, 6 * square_px),
                              marginSize=square_px, borderBits=1)
    assert not detect_board_votes(img)


def test_detect_flip_votes_upright_and_rotated():
    square_px = mm_to_px(30.0, 150)
    img = make_board(1).generateImage(
        (6 * square_px, 6 * square_px), marginSize=square_px, borderBits=1)
    upright = detect_flip_votes(img)
    assert upright.get(False, 0) == 18 and upright.get(True, 0) == 0
    rotated = detect_flip_votes(cv2.rotate(img, cv2.ROTATE_180))
    assert rotated.get(True, 0) == 18 and rotated.get(False, 0) == 0


def test_decide_flip_threshold_tie_and_majority():
    assert decide_flip(Counter(), 3) is None
    assert decide_flip(Counter({True: 2}), 3) is None            # 임계 미달
    assert decide_flip(Counter({True: 5}), 3) is True
    assert decide_flip(Counter({False: 5}), 3) is False
    assert decide_flip(Counter({True: 4, False: 4}), 3) is None  # 동률
    assert decide_flip(Counter({True: 9, False: 2}), 3) is True


def test_rewrite_roster_flips_insert_remove_and_preserve():
    yaml_text = (
        "cameras:\n"
        "  - name: \"cam_f\"           # 전면\n"
        "    serial: \"S_F\"\n"
        "  - name: \"cam_r\"\n"
        "    serial: \"S_R\"\n"
        "    flip: true\n"
        "  - name: \"cam_lf\"\n"
        "    serial: \"S_LF\"\n")
    out = rewrite_roster_flips(yaml_text, {"cam_f": True, "cam_r": False})
    lines = out.split("\n")
    assert "    flip: true" in lines[lines.index('    serial: "S_F"') + 1]  # 삽입
    assert out.count("flip: true") == 1                                     # cam_r 의 줄 제거
    assert "# 전면" in out                                                   # 주석 보존
    assert 'serial: "S_LF"' in out and "cam_lf" in out                       # 비대상 불변


def test_rewrite_roster_flips_idempotent_when_already_set():
    yaml_text = (
        "cameras:\n"
        "  - name: \"cam_f\"\n"
        "    serial: \"S_F\"\n"
        "    flip: true\n")
    assert rewrite_roster_flips(yaml_text, {"cam_f": True}) == yaml_text


def test_decide_board_threshold_tie_and_majority():
    assert decide_board(Counter(), 3) is None
    assert decide_board(Counter({1: 2}), 3) is None            # 임계 미달
    assert decide_board(Counter({1: 5}), 3) == 1
    assert decide_board(Counter({1: 5, 2: 5}), 3) is None      # 동률
    assert decide_board(Counter({1: 9, 2: 3}), 3) == 1         # 최다 우선


def test_build_mapping_happy_path():
    observed = {f"S{n}": n for n in range(1, 7)}
    mapping, errors = build_mapping(observed)
    assert errors == []
    assert mapping == {BOARD_MAP[n][0]: f"S{n}" for n in range(1, 7)}


def test_build_mapping_reports_all_error_kinds():
    observed = {"S1": 1, "S2": 1, "S3": None, "S4": 4, "S5": 5, "S6": 6}
    _mapping, errors = build_mapping(observed)
    text = "\n".join(errors)
    assert "동시 검출" in text        # 보드 1 중복
    assert "미검출" in text           # S3
    assert "배정된 카메라 없음" in text  # cam_lf(2)·cam_lr(3) 누락


def test_render_udev_rules_contains_serial_and_symlink():
    rules = render_udev_rules({"cam_f": "AY001", "cam_r": "AY002"})
    assert 'ATTRS{serial}=="AY001"' in rules
    assert 'SYMLINK+="camera/cam_f"' in rules
    assert 'ATTR{index}=="0"' in rules
    assert "cam_lf" not in rules  # 매핑에 없는 위치는 규칙도 없다


def test_rewrite_roster_serials_targets_only_serials():
    yaml_text = (
        "# 머리 주석 유지\n"
        "by_id_prefix: \"P\"\n"
        "cameras:\n"
        "  - name: \"cam_f\"           # 전면\n"
        "    serial: \"OLD_F\"\n"
        "  - name: \"cam_r\"\n"
        "    # 중간 주석 유지\n"
        "    serial: \"OLD_R\"   # 꼬리 주석 유지\n")
    out = rewrite_roster_serials(yaml_text, {"cam_f": "NEW_F", "cam_r": "NEW_R"})
    assert '"NEW_F"' in out and '"NEW_R"' in out
    assert "OLD_F" not in out and "OLD_R" not in out
    assert "# 머리 주석 유지" in out and "# 중간 주석 유지" in out
    assert "# 꼬리 주석 유지" in out and "# 전면" in out


def test_rewrite_roster_serials_leaves_unmapped_alone():
    yaml_text = "cameras:\n  - name: \"cam_f\"\n    serial: \"KEEP\"\n"
    assert rewrite_roster_serials(yaml_text, {"cam_r": "X"}) == yaml_text
