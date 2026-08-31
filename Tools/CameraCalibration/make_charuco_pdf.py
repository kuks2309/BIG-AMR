"""ChArUco 캘리브레이션 보드를 정확한 물리 치수 PDF 로 생성한다.

핵심: 페이지 = 보드 실치수가 되도록 DPI 를 설정해 저장하므로, 100% 배율로
인쇄하면 사각형 한 변이 지정한 mm 와 정확히 일치한다(스케일바로 재확인).
OpenCV 4.7+ 신규 aruco API 사용(cv2.aruco.CharucoBoard).
"""
from __future__ import annotations

import argparse
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

MM_PER_INCH = 25.4


def mm_to_px(mm, dpi):
    return int(round(mm / MM_PER_INCH * dpi))


def make_board(squares_x, squares_y, square_mm, dict_name, dpi, marker_ratio=0.72):
    """ChArUco 보드 비트맵(numpy, 흑백)을 생성한다. 각 사각형이 정확히 square_mm."""
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dict_name))
    marker_mm = square_mm * marker_ratio
    board = cv2.aruco.CharucoBoard(
        (squares_x, squares_y), square_mm, marker_mm, dictionary
    )
    square_px = mm_to_px(square_mm, dpi)
    out_size = (squares_x * square_px, squares_y * square_px)
    img = board.generateImage(out_size, marginSize=0, borderBits=1)
    return img, marker_mm


def render_pdf(
    path, board_img, square_mm, squares_x, squares_y, dpi, margin_mm=12
):
    """보드 비트맵을 여백·라벨·100mm 스케일바와 함께 실치수 PDF 로 저장한다."""
    margin_px = mm_to_px(margin_mm, dpi)
    label_px = mm_to_px(18, dpi)  # 하단 라벨/스케일바 영역 높이

    board_h, board_w = board_img.shape[:2]
    page_w = board_w + 2 * margin_px
    page_h = board_h + 2 * margin_px + label_px

    page = Image.new("L", (page_w, page_h), 255)
    board_pil = Image.fromarray(board_img)
    page.paste(board_pil, (margin_px, margin_px))

    draw = ImageDraw.Draw(page)
    outer_w_mm = squares_x * square_mm
    outer_h_mm = squares_y * square_mm
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", mm_to_px(4, dpi))
    except OSError:
        font = ImageFont.load_default()

    text = (
        "ChArUco  %dx%d squares  |  square=%.2f mm  |  board=%.0fx%.0f mm  "
        "|  PRINT AT 100%% (no scaling)"
        % (squares_x, squares_y, square_mm, outer_w_mm, outer_h_mm)
    )
    text_y = margin_px + board_h + mm_to_px(3, dpi)
    draw.text((margin_px, text_y), text, fill=0, font=font)

    # 100mm 스케일바 — 인쇄 배율 검증용(인쇄물에서 자로 재서 100mm 여야 함).
    bar_len = mm_to_px(100, dpi)
    bar_y = text_y + mm_to_px(7, dpi)
    bar_x = margin_px
    draw.rectangle([bar_x, bar_y, bar_x + bar_len, bar_y + mm_to_px(2, dpi)], fill=0)
    draw.text(
        (bar_x + bar_len + mm_to_px(2, dpi), bar_y - mm_to_px(1, dpi)),
        "100 mm",
        fill=0,
        font=font,
    )

    page.save(path, "PDF", resolution=float(dpi))
    return outer_w_mm, outer_h_mm


def generate_set(sizes_cm, square_mm, dict_name, dpi, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for size_cm in sizes_cm:
        target_mm = size_cm * 10.0
        squares = max(3, int(round(target_mm / square_mm)))
        board_img, marker_mm = make_board(squares, squares, square_mm, dict_name, dpi)
        path = os.path.join(
            out_dir, "charuco_%02dcm_%dx%d_sq%dmm.pdf" % (size_cm, squares, squares, square_mm)
        )
        outer_w, outer_h = render_pdf(path, board_img, square_mm, squares, squares, dpi)
        rows.append((size_cm, squares, square_mm, marker_mm, outer_w, path))
    return rows


def main():
    ap = argparse.ArgumentParser(description="ChArUco 보드 PDF 생성기")
    ap.add_argument(
        "--sizes-cm", type=float, nargs="+", default=[15, 20, 25, 30, 35, 40],
        help="목표 보드 외곽 크기(cm) 목록",
    )
    ap.add_argument("--square-mm", type=float, default=30.0, help="사각형 한 변(mm)")
    ap.add_argument("--dict", default="DICT_5X5_1000", help="ArUco 사전")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument(
        "--out-dir",
        default=os.path.join(os.path.dirname(__file__), "charuco_boards"),
    )
    args = ap.parse_args()

    rows = generate_set(args.sizes_cm, args.square_mm, args.dict, args.dpi, args.out_dir)
    print("생성 완료 (%d개) → %s" % (len(rows), args.out_dir))
    print("%-8s %-8s %-10s %-10s %-12s %s" % ("목표cm", "격자", "square", "marker", "실외곽mm", "파일"))
    for size_cm, squares, square_mm, marker_mm, outer_w, path in rows:
        print(
            "%-8.0f %-8s %-10.2f %-10.2f %-12.0f %s"
            % (size_cm, "%dx%d" % (squares, squares), square_mm, marker_mm, outer_w, os.path.basename(path))
        )


if __name__ == "__main__":
    main()
