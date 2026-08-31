#!/usr/bin/env python3
"""카메라 자동 등록용 ChArUco 보드 1~6 생성 (+ 자가 검증).

번호 규약: ROS2 좌표계처럼 전방=1, 반시계 —
1=cam_f(전방) 2=cam_lf(좌전방) 3=cam_lr(좌후방) 4=cam_r(후방) 5=cam_rr(우후방) 6=cam_rf(우전방).

`Tools/CameraCalibration/make_charuco_pdf.py` 의 실치수 렌더 방식을 재사용한다.
그 도구의 기존 보드 6종은 전부 마커 ID 0 시작이라 서로 구분되지 않으므로,
여기서는 보드마다 고유 ID 대역을 부여한다: 보드 n = ID 500+(n-1)*20 .. +17
(500 미만은 캘리브레이션 보드 몫 — 겹치면 시야의 캘리브레이션 보드가 위치로 오인된다).
역산은 `board_number_from_marker_id` — 2단계 인식 스크립트도 이 함수를 쓴다.
"""
from __future__ import annotations

import argparse
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "CameraCalibration"))
from make_charuco_pdf import mm_to_px  # noqa: E402

# 보드 번호 → (카메라 논리명, 한글 위치). 번호 규약의 단일 근원.
BOARD_MAP = {
    1: ("cam_f", "전방"),
    2: ("cam_lf", "좌전방"),
    3: ("cam_lr", "좌후방"),
    4: ("cam_r", "후방"),
    5: ("cam_rr", "우후방"),
    6: ("cam_rf", "우전방"),
}

# make_charuco_pdf.py 기본값과 동일 사전이어야 한다 — 갈리면 캘리브레이션 보드와
# 혼용할 때 검출기 설정이 두 벌이 된다.
ARUCO_DICT_NAME = "DICT_5X5_1000"
SQUARES = 6          # 6x6 칸 → 마커 18개, 외곽 180mm(A4 세로에 여유)
SQUARE_MM = 30.0
MARKER_RATIO = 0.72  # 마커 21.6mm — 720p 기준 약 1m 이내 검출 전제
IDS_PER_BOARD = 20   # 대역 폭(18 사용 + 여유 2)
# 캘리브레이션 보드(make_charuco_pdf.py 산출물)는 전부 ID 0 시작·최대 ~84 를 쓴다.
# 등록 보드가 그 대역과 겹치면 시야에 남은 캘리브레이션 보드가 위치로 오인되므로
# 500 부터 시작해 완전히 분리한다(DICT_5X5_1000 이라 500+120 < 1000).
BOARD_ID_OFFSET = 500


def board_marker_ids(board_no: int) -> np.ndarray:
    """보드 n 의 마커 ID 대역 — 500+(n-1)*20 부터 18개."""
    n_markers = (SQUARES * SQUARES) // 2
    start = BOARD_ID_OFFSET + (board_no - 1) * IDS_PER_BOARD
    return np.arange(start, start + n_markers, dtype=np.int32)


def board_number_from_marker_id(marker_id: int) -> int:
    """검출된 마커 ID → 보드 번호. 대역 밖(캘리브레이션 보드·여유분 ID)은 0."""
    board_no = (marker_id - BOARD_ID_OFFSET) // IDS_PER_BOARD + 1
    if board_no in BOARD_MAP and marker_id in board_marker_ids(board_no):
        return board_no
    return 0


def make_board(board_no: int) -> "cv2.aruco.CharucoBoard":
    """고유 ID 대역이 부여된 6x6 ChArUco 보드 객체."""
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, ARUCO_DICT_NAME))
    return cv2.aruco.CharucoBoard(
        (SQUARES, SQUARES), SQUARE_MM, SQUARE_MM * MARKER_RATIO, dictionary,
        ids=board_marker_ids(board_no))


def render_board_pdf(board_no: int, out_dir: str, dpi: int) -> str:
    """보드 1장을 실치수 PDF 로 저장 — 100% 배율 인쇄 시 칸 한 변이 정확히 30mm.

    페이지 구성은 make_charuco_pdf.render_pdf 와 같은 원리(여백·라벨·100mm
    스케일바)이되, 등록용 큰 번호·카메라명 라벨을 추가한다.
    """
    cam_name, _position = BOARD_MAP[board_no]
    board = make_board(board_no)
    square_px = mm_to_px(SQUARE_MM, dpi)
    board_img = board.generateImage(
        (SQUARES * square_px, SQUARES * square_px), marginSize=0, borderBits=1)

    margin_px = mm_to_px(12, dpi)
    label_px = mm_to_px(30, dpi)
    board_h, board_w = board_img.shape[:2]
    page = Image.new("L", (board_w + 2 * margin_px, board_h + 2 * margin_px + label_px), 255)
    page.paste(Image.fromarray(board_img), (margin_px, margin_px))

    draw = ImageDraw.Draw(page)
    try:
        font_big = ImageFont.truetype("DejaVuSans-Bold.ttf", mm_to_px(12, dpi))
        font_small = ImageFont.truetype("DejaVuSans.ttf", mm_to_px(3.5, dpi))
    except OSError:
        font_big = font_small = ImageFont.load_default()

    text_y = margin_px + board_h + mm_to_px(3, dpi)
    ids = board_marker_ids(board_no)
    draw.text((margin_px, text_y), f"{board_no}  {cam_name}", fill=0, font=font_big)
    draw.text(
        (margin_px, text_y + mm_to_px(14, dpi)),
        f"ChArUco {SQUARES}x{SQUARES} sq={SQUARE_MM:.0f}mm ids={ids[0]}..{ids[-1]} "
        f"{ARUCO_DICT_NAME} | PRINT AT 100%",
        fill=0, font=font_small)

    bar_len = mm_to_px(100, dpi)
    bar_y = text_y + mm_to_px(20, dpi)
    bar_x = page.width - margin_px - bar_len
    draw.rectangle([bar_x, bar_y, bar_x + bar_len, bar_y + mm_to_px(2, dpi)], fill=0)
    draw.text((bar_x, bar_y + mm_to_px(3, dpi)), "100 mm", fill=0, font=font_small)

    path = os.path.join(out_dir, f"board_{board_no}_{cam_name}.pdf")
    page.save(path, "PDF", resolution=float(dpi))
    return path


def self_test(board_no: int) -> list[str]:
    """생성 비트맵을 재검출해 ID 대역·역산 보드 번호·전수 검출을 확인한다."""
    board = make_board(board_no)
    square_px = mm_to_px(SQUARE_MM, 300)
    img = board.generateImage(
        (SQUARES * square_px, SQUARES * square_px), marginSize=square_px, borderBits=1)
    detector = cv2.aruco.CharucoDetector(board)
    _corners, _ids, _marker_corners, marker_ids = detector.detectBoard(img)
    if marker_ids is None or len(marker_ids) == 0:
        return [f"보드 {board_no}: 마커 검출 0개"]
    problems = []
    expected = set(board_marker_ids(board_no).tolist())
    detected = set(int(i) for i in marker_ids.flatten())
    if not detected <= expected:
        problems.append(f"보드 {board_no}: 대역 밖 ID {sorted(detected - expected)}")
    wrong = [i for i in detected if board_number_from_marker_id(i) != board_no]
    if wrong:
        problems.append(f"보드 {board_no}: 역산 불일치 ID {sorted(wrong)}")
    if len(detected) < len(expected):
        problems.append(
            f"보드 {board_no}: 검출 {len(detected)}/{len(expected)}개(비트맵 기준 전수 기대)")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="카메라 자동 등록용 ChArUco 보드 1~6 생성")
    parser.add_argument(
        "--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "boards"))
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    problems = []
    print(f"{'보드':<4} {'카메라':<8} {'위치':<6} {'ID대역':<10} 파일")
    for board_no, (cam_name, position) in BOARD_MAP.items():
        path = render_board_pdf(board_no, args.out, args.dpi)
        problems += self_test(board_no)
        ids = board_marker_ids(board_no)
        band = f"{ids[0]}..{ids[-1]}"
        print(f"{board_no:<4} {cam_name:<8} {position:<6} {band:<10} {os.path.basename(path)}")
    if problems:
        print("자가 검증 실패:\n  " + "\n  ".join(problems))
        return 1
    print(f"자가 검증 PASS (6보드 × 마커 18개 재검출·역산 일치) → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
