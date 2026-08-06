#!/usr/bin/env python3
"""Seer .smap → 평면도 이미지(PNG/JPG). 인쇄·공유용 정적 렌더.

usage: render_smap.py <map.smap> <출력경로(확장자 없이)> [pose_json]
"""
import hashlib
import io
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrow

KO = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
try:
    fm.fontManager.addfont(KO)
    plt.rcParams["font.family"] = fm.FontProperties(fname=KO).get_name()
except Exception:
    pass
plt.rcParams["axes.unicode_minus"] = False

smap_path, out_base = sys.argv[1], sys.argv[2]
pose = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None

raw = io.open(smap_path, "rb").read()
md5 = hashlib.md5(raw).hexdigest()
m = json.loads(raw.decode("utf-8"))
hdr = m.get("header", {})
mn, mx = hdr.get("minPos", {}), hdr.get("maxPos", {})
x0, x1 = float(mn.get("x", 0)), float(mx.get("x", 0))
y0, y1 = float(mn.get("y", 0)), float(mx.get("y", 0))

ox = [float(p.get("x", 0)) for p in m.get("normalPosList", [])]
oy = [float(p.get("y", 0)) for p in m.get("normalPosList", [])]
rx = [float(p.get("x", 0)) for p in m.get("rssiPosList", [])]
ry = [float(p.get("y", 0)) for p in m.get("rssiPosList", [])]
named = m.get("advancedPointList", [])
curves = m.get("advancedCurveList", [])

INK, OBST, RSSI, NAMED, ROBOT, GRID = "#14202C", "#20303F", "#C8811A", "#B12C61", "#2E7D32", "#DCE3EA"

pad = 1.5
w_m, h_m = (x1 - x0) + 2 * pad, (y1 - y0) + 2 * pad
scale = 22.0 / max(w_m, h_m)          # 긴 변을 22 inch 로
fig, ax = plt.subplots(figsize=(w_m * scale, h_m * scale + 1.6), dpi=140)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

for s in (1, 5):
    step, lw, c = (s, 0.4 if s == 1 else 0.8, GRID)
    xs = [x0 - pad + i * step for i in range(int(w_m / step) + 2)]
    ys = [y0 - pad + i * step for i in range(int(h_m / step) + 2)]
    ax.set_xticks([v for v in xs if v % 5 == 0] if s == 5 else [])
    for v in xs:
        ax.axvline(v, color=c, lw=lw, zorder=0)
    for v in ys:
        ax.axhline(v, color=c, lw=lw, zorder=0)

ax.scatter(ox, oy, s=0.8, c=OBST, marker="s", linewidths=0, zorder=3)
if rx:
    ax.scatter(rx, ry, s=26, facecolors="none", edgecolors=RSSI, linewidths=1.4, zorder=4)

for c in curves:
    st = (c.get("startPos") or {}).get("pos", {})
    en = (c.get("endPos") or {}).get("pos", {})
    if st and en:
        ax.plot([st.get("x", 0), en.get("x", 0)], [st.get("y", 0), en.get("y", 0)],
                ls="--", lw=1.2, color="#7A8794", zorder=5)

for p in named:
    pos = p.get("pos", {})
    px, py, d = float(pos.get("x", 0)), float(pos.get("y", 0)), float(p.get("dir", 0))
    ax.scatter([px], [py], s=90, facecolors="none", edgecolors=NAMED, linewidths=1.8, zorder=6)
    ax.add_patch(FancyArrow(px, py, 0.9 * __import__("math").cos(d), 0.9 * __import__("math").sin(d),
                            width=0.05, head_width=0.28, head_length=0.28, color=NAMED, zorder=6))
    ax.annotate("%s\n(%s)" % (p.get("instanceName", ""), p.get("className", "")),
                (px, py), textcoords="offset points", xytext=(10, 8),
                fontsize=9, color=NAMED, zorder=7)

if pose:
    import math
    px, py, a = float(pose["x"]), float(pose["y"]), float(pose["angle"])
    ax.scatter([px], [py], s=260, facecolors="none", edgecolors=ROBOT, linewidths=2.2, zorder=8)
    ax.add_patch(FancyArrow(px, py, 1.3 * math.cos(a), 1.3 * math.sin(a),
                            width=0.09, head_width=0.45, head_length=0.45, color=ROBOT, zorder=8))
    ax.annotate("로봇  (%.2f, %.2f)  %.1f°  신뢰도 %.3f" % (px, py, math.degrees(a), pose["confidence"]),
                (px, py), textcoords="offset points", xytext=(14, -20),
                fontsize=10, color=ROBOT, weight="bold", zorder=9)

# 축척 막대 5 m
bx, by = x0 - pad + 1.0, y0 - pad + 0.7
ax.plot([bx, bx + 5], [by, by], color=INK, lw=3, solid_capstyle="butt", zorder=9)
ax.annotate("5 m", ((bx + bx + 5) / 2, by), textcoords="offset points", xytext=(0, 7),
            ha="center", fontsize=10, color=INK, zorder=9)

ax.set_xlim(x0 - pad, x1 + pad)
ax.set_ylim(y0 - pad, y1 + pad)
ax.set_aspect("equal")
ax.tick_params(labelsize=9, colors="#5C6E80")
for sp in ax.spines.values():
    sp.set_color("#B9C4CE")
ax.set_xlabel("x [m]", fontsize=10, color="#5C6E80")
ax.set_ylabel("y [m]", fontsize=10, color="#5C6E80")

title = "%s  (v%s)" % (hdr.get("mapName", "?"), hdr.get("version", "?"))
sub = ("해상도 %s m/cell   범위 x[%.2f, %.2f] y[%.2f, %.2f]   크기 %.1f × %.1f m\n"
       "장애물 %s점 · 반사판 %d · 명명 위치 %d · 곡선 %d   |   md5 %s"
       % (hdr.get("resolution", "?"), x0, x1, y0, y1, x1 - x0, y1 - y0,
          format(len(ox), ","), len(rx), len(named), len(curves), md5))
fig.suptitle(title, fontsize=17, color=INK, y=0.985, weight="bold")
ax.set_title(sub, fontsize=10, color="#5C6E80", pad=14)

handles = [Line2D([], [], ls="", marker="s", ms=5, color=OBST, label="장애물 점군 (normalPosList)"),
           Line2D([], [], ls="", marker="o", ms=8, mfc="none", mec=RSSI, label="반사판 (rssiPosList)"),
           Line2D([], [], ls="", marker="o", ms=9, mfc="none", mec=NAMED, label="명명 위치 (advancedPointList)"),
           Line2D([], [], ls="--", color="#7A8794", label="곡선 경로 (advancedCurveList)")]
if pose:
    handles.append(Line2D([], [], ls="", marker="o", ms=11, mfc="none", mec=ROBOT, label="로봇 자세 (실시간 판독)"))
ax.legend(handles=handles, loc="upper right", fontsize=9, framealpha=0.95, edgecolor="#B9C4CE")

fig.tight_layout(rect=(0, 0, 1, 0.97))
png, jpg = out_base + ".png", out_base + ".jpg"
fig.savefig(png, facecolor="white")
fig.savefig(jpg, facecolor="white", pil_kwargs={"quality": 92})
print("저장: %s" % png)
print("저장: %s" % jpg)
