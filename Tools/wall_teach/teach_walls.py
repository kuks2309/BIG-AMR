#!/usr/bin/env python3
"""벽 티치 도구 — Seer .smap 맵 위 사각 ROI(Region of Interest)에서 직선을 검출해
wall_localizer 기준 벽 YAML 을 생성한다.

기준 벽을 도면 좌표가 아니라 **라이다 실측 맵**에서 뽑는다(.smap 은 Seer 가 라이다로
만든 맵). 좌표는 맵 프레임이므로 출력 YAML 은 station_frame: "map" 이고, /wall_pose 도
맵 프레임 자세가 된다. 초기 추정(initial_*)은 스테이션 진입 지점에 맞춰 별도 설정할 것.

사용:
  비대화형: python3 teach_walls.py --smap map/260709_test.smap \
              --roi front:1.0,2.0,1.4,5.0 --roi left:2.0,5.0,5.0,5.4 --out walls.yaml
  대화형:   python3 teach_walls.py --smap map/260709_test.smap --interactive
            (사각형 드래그 → 콘솔에 벽 이름 입력, 빈 입력=버림. 창 닫으면 YAML 기록)
  미리보기: python3 teach_walls.py --smap ... --preview-only   (맵 PNG 만 출력)

ROI 형식: name:x1,y1,x2,y2 — 맵 프레임 m, 사각형 마주보는 두 모서리(순서 무관).

⚠ ROI 는 스테이션 규모(2~4 m 구간)로 지정할 것 — 홀 전장(10 m 급) 벽을 한 ROI 로 잡으면
SLAM 맵의 전역 굴곡이 rms 로 드러난다(260709_test 실측: 17 m 벽 rms 52 mm ↔ 같은 벽
3 m 구간 rms 28 mm). 측위가 실제로 쓰는 것도 스테이션 앞 구간이다.
"""
import argparse
import json
import math
import os
import sys

import numpy as np


def load_smap_points(path):
    """Seer .smap 의 normalPosList → (N,2) 배열. 생략 좌표=0 규칙(mcl2d_map 로더와 동일)."""
    with open(path) as f:
        d = json.load(f)
    pts = d.get("normalPosList", [])
    return np.array([[p.get("x", 0.0), p.get("y", 0.0)] for p in pts], dtype=float), \
        d.get("header", {}).get("mapName", os.path.basename(path))


class WallFit:
    def __init__(self, name, roi):
        self.name = name
        self.roi = roi          # [xmin, ymin, xmax, ymax]
        self.p1 = self.p2 = None  # 선분 끝점 (맵 프레임 m)
        self.rms_m = 0.0
        self.n_points = 0
        self.length_m = 0.0
        self.warnings = []


def fit_line_in_roi(points, name, roi, trim_sigma=3.0, min_points=30, max_iters=5,
                    max_rms_m=0.03, min_length_m=0.4):
    """ROI 내 점들의 총최소자승 직선 + 3σ 트림 반복. 끝점은 인라이어 접선 사영 극값."""
    x1, y1, x2, y2 = roi
    lo = np.array([min(x1, x2), min(y1, y2)])
    hi = np.array([max(x1, x2), max(y1, y2)])
    fit = WallFit(name, [lo[0], lo[1], hi[0], hi[1]])
    sel = points[np.all((points >= lo) & (points <= hi), axis=1)]
    if len(sel) < min_points:
        fit.warnings.append(f"ROI 내 점 부족: {len(sel)} < {min_points}")
        fit.n_points = len(sel)
        return fit

    inliers = sel
    for _ in range(max_iters):
        c = inliers.mean(axis=0)
        dxy = inliers - c
        sxx, syy = (dxy[:, 0] ** 2).sum(), (dxy[:, 1] ** 2).sum()
        sxy = (dxy[:, 0] * dxy[:, 1]).sum()
        direction = 0.5 * math.atan2(2.0 * sxy, sxx - syy)  # 주성분 방향각
        n = np.array([-math.sin(direction), math.cos(direction)])
        d = float(n @ c)
        res = inliers @ n - d
        rms = float(np.sqrt((res ** 2).mean()))
        # 트림 척도는 rms 가 아니라 MAD(중앙절대편차) — 벽 기둥·잡물이 ROI 점의 수십 %를
        # 차지하면 rms 가 그만큼 부풀어 3σ 트림이 잡물을 통과시킨다. MAD 는 과반이 벽이면
        # 잡물 비율과 무관하게 벽 잡음 수준을 잰다.
        scale = max(1.4826 * float(np.median(np.abs(res - np.median(res)))), 2e-3)
        keep = np.abs(res) <= trim_sigma * scale
        if keep.sum() < min_points or keep.all():
            break
        inliers = inliers[keep]

    u = np.array([math.cos(direction), math.sin(direction)])  # 접선
    t = inliers @ u
    lo_p, hi_p = inliers[t.argmin()], inliers[t.argmax()]
    project = lambda q: q - (float(n @ q) - d) * n
    fit.p1, fit.p2 = project(lo_p), project(hi_p)
    fit.rms_m = rms
    fit.n_points = int(len(inliers))
    fit.length_m = float(np.linalg.norm(fit.p2 - fit.p1))
    if rms > max_rms_m:
        fit.warnings.append(f"rms {1000*rms:.1f}mm > {1000*max_rms_m:.0f}mm — 직선이 아니거나 ROI 에 잡물")
    if fit.length_m < min_length_m:
        fit.warnings.append(f"길이 {fit.length_m:.2f}m < {min_length_m}m — 기준 벽으로 부적합(ANT 최소 세그먼트 준용)")
    return fit


def write_walls_yaml(fits, out_path, smap_name):
    ok = [f for f in fits if f.p1 is not None]
    lines = [
        "# wall_localizer 기준 벽 — teach_walls.py 가 라이다 실측 맵에서 생성",
        f"# 소스 맵: {smap_name} (맵 프레임 좌표, station_frame=map)",
        "# 초기 추정(initial_x_m 등)은 스테이션 진입 지점의 맵 좌표로 별도 설정할 것.",
        "wall_localizer:",
        "  ros__parameters:",
        '    station_frame: "map"',
        f"    wall_names: [{', '.join(repr(f.name) for f in ok)}]",
    ]
    for f in ok:
        lines.append(f"    # {f.name}: 점 {f.n_points}개, rms {1000*f.rms_m:.1f}mm, 길이 {f.length_m:.2f}m")
        lines.append(f"    walls.{f.name}: [{f.p1[0]:.4f}, {f.p1[1]:.4f}, {f.p2[0]:.4f}, {f.p2[1]:.4f}]")
    with open(out_path, "w") as fo:
        fo.write("\n".join(lines) + "\n")
    return out_path


def render_preview(points, fits, out_png, roi_zoom=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.scatter(points[:, 0], points[:, 1], s=0.3, c="0.55", linewidths=0)
    for f in fits:
        x1, y1, x2, y2 = f.roi
        ax.add_patch(Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, ec="tab:blue", lw=1))
        if f.p1 is not None:
            ax.plot([f.p1[0], f.p2[0]], [f.p1[1], f.p2[1]], c="tab:red", lw=2)
            ax.annotate(f"{f.name} rms={1000*f.rms_m:.0f}mm n={f.n_points}",
                        xy=((f.p1[0] + f.p2[0]) / 2, (f.p1[1] + f.p2[1]) / 2),
                        color="tab:red", fontsize=9)
    if roi_zoom is not None:
        m = 1.0
        ax.set_xlim(roi_zoom[0] - m, roi_zoom[2] + m)
        ax.set_ylim(roi_zoom[1] - m, roi_zoom[3] + m)
    ax.set_aspect("equal")
    ax.grid(True, lw=0.3)
    ax.set_xlabel("x [m] (map)")
    ax.set_ylabel("y [m] (map)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)
    return out_png


def run_interactive(points, smap_name, out_yaml, out_png):
    """사각형 드래그 → 즉시 적합·표시 → 콘솔에 벽 이름 입력(빈 입력=버림) → 창 닫으면 기록."""
    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib.widgets import RectangleSelector
    fits = []
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.scatter(points[:, 0], points[:, 1], s=0.3, c="0.55", linewidths=0)
    ax.set_aspect("equal")
    ax.grid(True, lw=0.3)
    ax.set_title("드래그로 벽 ROI 지정 → 콘솔에 이름 입력 (빈 입력=버림) → 창 닫으면 YAML 기록")

    def on_select(eclick, erelease):
        roi = [eclick.xdata, eclick.ydata, erelease.xdata, erelease.ydata]
        tmp = fit_line_in_roi(points, f"wall{len(fits)}", roi)
        if tmp.p1 is None:
            print(f"적합 실패: {tmp.warnings}")
            return
        print(f"적합: 점 {tmp.n_points}개, rms {1000*tmp.rms_m:.1f}mm, 길이 {tmp.length_m:.2f}m "
              f"{'⚠ ' + '; '.join(tmp.warnings) if tmp.warnings else ''}")
        name = input("벽 이름 (빈 입력=버림): ").strip()
        if not name:
            return
        tmp.name = name
        fits.append(tmp)
        ax.plot([tmp.p1[0], tmp.p2[0]], [tmp.p1[1], tmp.p2[1]], c="tab:red", lw=2)
        fig.canvas.draw_idle()

    selector = RectangleSelector(ax, on_select, useblit=True, button=[1], interactive=True)
    plt.show()
    del selector
    if fits:
        write_walls_yaml(fits, out_yaml, smap_name)
        render_preview(points, fits, out_png)
        print(f"기록: {out_yaml} · {out_png}")
    else:
        print("지정된 벽 없음 — 기록 생략")
    return fits


def parse_roi(spec):
    name, rest = spec.split(":", 1)
    vals = [float(v) for v in rest.split(",")]
    if len(vals) != 4:
        raise argparse.ArgumentTypeError(f"ROI 는 name:x1,y1,x2,y2 형식: {spec}")
    return name.strip(), vals


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smap", required=True)
    ap.add_argument("--roi", action="append", type=parse_roi, default=[],
                    help="name:x1,y1,x2,y2 (반복 지정)")
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--preview-only", action="store_true", help="맵 PNG 만 생성")
    ap.add_argument("--out", default="walls_taught.yaml")
    ap.add_argument("--png", default="walls_taught.png")
    ap.add_argument("--min-points", type=int, default=30)
    ap.add_argument("--max-rms-mm", type=float, default=30.0)
    args = ap.parse_args()

    points, smap_name = load_smap_points(args.smap)
    print(f"맵 {smap_name}: 점 {len(points)}개")

    if args.preview_only:
        render_preview(points, [], args.png)
        print(f"미리보기: {args.png}")
        return 0
    if args.interactive:
        run_interactive(points, smap_name, args.out, args.png)
        return 0
    if not args.roi:
        print("ROI 미지정 — --roi 또는 --interactive 를 쓰십시오", file=sys.stderr)
        return 2

    fits = []
    for name, roi in args.roi:
        f = fit_line_in_roi(points, name, roi, min_points=args.min_points,
                            max_rms_m=args.max_rms_mm / 1000.0)
        state = "실패" if f.p1 is None else \
            f"점 {f.n_points}개, rms {1000*f.rms_m:.1f}mm, 길이 {f.length_m:.2f}m"
        warn = (" ⚠ " + "; ".join(f.warnings)) if f.warnings else ""
        print(f"{name}: {state}{warn}")
        fits.append(f)
    ok = [f for f in fits if f.p1 is not None]
    if not ok:
        print("적합된 벽 없음 — 기록 생략", file=sys.stderr)
        return 1
    write_walls_yaml(fits, args.out, smap_name)
    render_preview(points, fits, args.png)
    print(f"기록: {args.out} · {args.png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
