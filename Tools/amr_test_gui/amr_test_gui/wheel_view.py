"""WheelView — AMR 차체 top-view 바퀴축 시각화.

노드 숫자 대신 **실제 바퀴가 어느 방향을 향하고 얼마나 도는지**를 그린다.
조향 지령(점선)과 실측(실선)을 겹쳐 그리므로 램프 추종 지연·한쪽 축 뒤처짐이 눈에 바로 보인다.

좌표계: 차체 +x = 전방(화면 위), +y = 좌(화면 왼쪽) — 우수좌표계 top view.
기하 근거: constants.WHEEL_X / WHEEL_Y (References/Tongyi-Motor-Controller §1 EasyDRIVE canID config).
차체 외형(BODY_LENGTH/WIDTH)은 시각화용 근사치이며 실측이 아니다 — 바퀴 위치만 실측이다.

⚠ 화면 Front/Rear 라벨이 의존하는 노드↔전/후 배정은 미확정 모순 — docs/debt/registry.md:44, Tools/Kinematics/chassis_kinematics.py:29-31.

그리는 것과 그리지 않는 것:
  - 그린다: 바퀴 지향(조향 지령·실측), 구동 지령 raw/mm/s, 구동 실측 mm/s(엔코더 변위 도출)
  - 그리지 않는다: 실제 이동 궤적·차체 자세. 이 위젯은 **관측값의 표시**이지 시뮬레이션이 아니다.
"""
from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import QWidget

from .constants import BODY_LENGTH, BODY_WIDTH, WHEEL_RADIUS

C_BODY_FILL = QColor("#eaeef2")
C_BODY_EDGE = QColor("#8c9aa8")
C_MEAS = QColor("#1e8449")      # 실측 — 실선
C_CMD = QColor("#b9770e")       # 지령 — 점선
C_FAULT = QColor("#c0392b")
C_TEXT = QColor("#22303c")
C_MUTED = QColor("#7b8794")
C_ARROW = QColor("#1f6feb")


class WheelView(QWidget):
    """상태 dict(controller.tick() 반환)를 받아 그리는 순수 표시 위젯."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(360, 340)
        self._st: dict | None = None

    def set_state(self, st: dict):
        self._st = st
        self.update()

    # ── 좌표 변환: 차체(m) → 화면(px) ───────────────────────────────────────
    def _transform(self):
        """(m→px 스케일, 화면중앙) 반환. +x=위, +y=왼쪽 이 되도록 부호를 뒤집는다."""
        margin = 40.0
        span_x = BODY_LENGTH * 1.15
        span_y = BODY_WIDTH * 1.15
        sx = (self.height() - 2 * margin) / span_x if span_x else 1.0
        sy = (self.width() - 2 * margin) / span_y if span_y else 1.0
        s = max(20.0, min(sx, sy))
        return s, QPointF(self.width() / 2.0, self.height() / 2.0)

    def _pt(self, x_m: float, y_m: float) -> QPointF:
        s, c = self._transform()
        return QPointF(c.x() - y_m * s, c.y() - x_m * s)   # +y→왼쪽, +x→위

    # ── 그리기 ──────────────────────────────────────────────────────────────
    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#ffffff"))
        self._draw_body(p)
        st = self._st
        if not st or not st.get("wheels"):
            self._hint_text(p, "연결하면 바퀴 상태가 표시됩니다")
            p.end()
            return
        fault = bool(st.get("fault"))
        for w in st["wheels"]:
            self._draw_wheel(p, w, fault)
        self._draw_expected_motion(p, st)
        self._draw_legend(p)
        p.end()

    def _draw_body(self, p: QPainter):
        s, _ = self._transform()
        half_l, half_w = BODY_LENGTH / 2.0, BODY_WIDTH / 2.0
        tl = self._pt(half_l, half_w)
        br = self._pt(-half_l, -half_w)
        rect = QRectF(tl, br).normalized()
        p.setPen(QPen(C_BODY_EDGE, 2))
        p.setBrush(QBrush(C_BODY_FILL))
        p.drawRoundedRect(rect, 10, 10)
        # 전방 표식
        p.setPen(QPen(C_MUTED, 1))
        f = QFont()
        f.setPointSize(8)
        p.setFont(f)
        p.drawText(QRectF(rect.left(), rect.top() - 20, rect.width(), 18),
                   Qt.AlignHCenter | Qt.AlignVCenter, "▲ 전방 (+x)")
        p.drawText(QRectF(rect.left() - 62, rect.center().y() - 9, 58, 18),
                   Qt.AlignRight | Qt.AlignVCenter, "좌 (+y)")
        # 센터라인
        pen = QPen(C_MUTED, 1, Qt.DotLine)
        p.setPen(pen)
        p.drawLine(self._pt(half_l, 0.0), self._pt(-half_l, 0.0))

    def _draw_wheel(self, p: QPainter, w: dict, fault: bool):
        s, _ = self._transform()
        ctr = self._pt(w["x"], w["y"])
        cmd = w.get("steer_cmd_deg")
        meas = w.get("steer_meas_deg")

        # 지령 지향(점선 실루엣)
        if cmd is not None:
            self._wheel_shape(p, ctr, cmd, s, QPen(C_CMD, 2, Qt.DashLine), None)
        # 실측 지향(실선 채움)
        col = C_FAULT if fault else C_MEAS
        if meas is not None:
            self._wheel_shape(p, ctr, meas, s, QPen(col, 2.4), QBrush(QColor(col.red(), col.green(), col.blue(), 60)))
            self._drive_arrow(p, ctr, meas, w, s)
        p.setPen(QPen(C_TEXT, 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(ctr, 3.0, 3.0)
        self._wheel_labels(p, ctr, w, s)

    def _wheel_shape(self, p: QPainter, ctr: QPointF, deg: float, s: float, pen: QPen, brush):
        """조향각 deg(홈 기준 counts 각)에서의 바퀴 사각형.

        바퀴 지향 = (cos θ, −sin θ) — modes.py 도출 모델(+counts = CW)과 동일 규약.
        """
        th = math.radians(deg)
        ux, uy = math.cos(th), -math.sin(th)          # 차체좌표 지향
        L = WHEEL_RADIUS * 2.0 * s                     # 바퀴 지름(휠 길이)
        W = max(7.0, WHEEL_RADIUS * 0.62 * s)          # 폭
        # 차체좌표 → 화면좌표 (x:위, y:왼쪽)
        dx, dy = -uy * s, -ux * s                      # 지향 단위벡터의 화면 성분(스케일 포함)
        n = math.hypot(dx, dy) or 1.0
        ax, ay = dx / n, dy / n                        # 길이방향
        bx, by = -ay, ax                               # 폭방향
        pts = [QPointF(ctr.x() + ax * L / 2 + bx * W / 2, ctr.y() + ay * L / 2 + by * W / 2),
               QPointF(ctr.x() + ax * L / 2 - bx * W / 2, ctr.y() + ay * L / 2 - by * W / 2),
               QPointF(ctr.x() - ax * L / 2 - bx * W / 2, ctr.y() - ay * L / 2 - by * W / 2),
               QPointF(ctr.x() - ax * L / 2 + bx * W / 2, ctr.y() - ay * L / 2 + by * W / 2)]
        p.setPen(pen)
        p.setBrush(brush if brush is not None else Qt.NoBrush)
        p.drawPolygon(QPolygonF(pts))

    def _drive_arrow(self, p: QPainter, ctr: QPointF, deg: float, w: dict, s: float):
        """구동 지령 raw 부호·크기를 바퀴 축선 위 화살표로. 길이 ∝ |mm/s|."""
        mmps = w.get("cmd_mmps") or 0.0
        if abs(mmps) < 0.05:
            return
        th = math.radians(deg)
        ux, uy = math.cos(th), -math.sin(th)
        dx, dy = -uy, -ux                              # 화면 성분(지향)
        # 이동 방향 = −sign(raw) × 지향  (modes.py 모델)
        sgn = -1.0 if (w.get("raw_units") or 0) > 0 else 1.0
        dx, dy = dx * sgn, dy * sgn
        ln = min(58.0, 16.0 + abs(mmps) * 0.22)
        tip = QPointF(ctr.x() + dx * ln, ctr.y() + dy * ln)
        p.setPen(QPen(C_ARROW, 2.6))
        p.setBrush(QBrush(C_ARROW))
        p.drawLine(ctr, tip)
        # 화살촉
        a = math.atan2(dy, dx)
        for off in (2.6, -2.6):
            p.drawLine(tip, QPointF(tip.x() + 9 * math.cos(a + off), tip.y() + 9 * math.sin(a + off)))

    def _wheel_labels(self, p: QPainter, ctr: QPointF, w: dict, s: float):
        """바퀴 **옆**에 속도·조향각을 붙인다 (사용자 요청)."""
        f = QFont("monospace")
        f.setPointSize(7)
        f.setBold(True)
        p.setFont(f)
        meas = w.get("steer_meas_deg")
        lines = [f"{w['label']}  N{w['drive_node']}/N{w['steer_node']}",
                 f"지령 {w['cmd_mmps']:+.1f} mm/s ({w['raw_units']:+d}u)",
                 f"실측 {w['meas_mmps']:+.1f} mm/s (enc)",
                 f"조향 지령 {w['steer_cmd_deg']:+.1f}°",
                 f"     실측 {'--' if meas is None else f'{meas:+.1f}'}°"]
        # 바퀴 오른쪽에 배치, 화면 밖이면 왼쪽으로 접기
        bw, bh = 150.0, 13.5 * len(lines) + 5
        x = ctr.x() + 46
        if x + bw > self.width() - 4:
            x = ctr.x() - 46 - bw
        y = ctr.y() - bh / 2
        y = max(2.0, min(y, self.height() - bh - 2))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 232)))
        p.drawRoundedRect(QRectF(x, y, bw, bh), 5, 5)
        p.setPen(QPen(QColor("#c8d0d8"), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(x, y, bw, bh), 5, 5)
        for i, ln in enumerate(lines):
            p.setPen(QPen(C_TEXT if i < 3 else C_MUTED, 1))
            p.drawText(QRectF(x + 5, y + 3 + i * 13.5, bw - 10, 13.5),
                       Qt.AlignLeft | Qt.AlignVCenter, ln)

    def _draw_expected_motion(self, p: QPainter, st: dict):
        """모드의 **예상** 차체 이동 방향(모델 예측)을 중앙에 크게. 실측 아님을 명시."""
        mode = st.get("mode")
        if mode is None or getattr(mode, "raw_sign", 0) == 0 or not st.get("drive_allowed"):
            return
        from .modes import motion_unit_vector
        mx, my = motion_unit_vector(mode)
        if mx == 0.0 and my == 0.0:
            return
        s, c = self._transform()
        dx, dy = -my, -mx
        ln = 66.0
        tip = QPointF(c.x() + dx * ln, c.y() + dy * ln)
        col = QColor(C_ARROW)
        col.setAlpha(150 if mode.verified else 90)
        p.setPen(QPen(col, 5, Qt.SolidLine if mode.verified else Qt.DashLine))
        p.drawLine(c, tip)
        a = math.atan2(dy, dx)
        for off in (2.6, -2.6):
            p.drawLine(tip, QPointF(tip.x() + 15 * math.cos(a + off), tip.y() + 15 * math.sin(a + off)))
        f = QFont()
        f.setPointSize(8)
        p.setFont(f)
        p.setPen(QPen(C_MUTED, 1))
        p.drawText(QRectF(c.x() - 90, c.y() + 76, 180, 16), Qt.AlignHCenter,
                   "예상 이동(모델)" + ("" if mode.verified else " ⚠ 도출·미검증"))

    def _draw_legend(self, p: QPainter):
        f = QFont()
        f.setPointSize(8)
        p.setFont(f)
        items = [(C_MEAS, "실측 조향(실선)"), (C_CMD, "지령 조향(점선)"), (C_ARROW, "구동 지령")]
        x, y = 8, self.height() - 18
        for col, txt in items:
            p.setPen(QPen(col, 3))
            p.drawLine(QPointF(x, y + 6), QPointF(x + 16, y + 6))
            p.setPen(QPen(C_MUTED, 1))
            p.drawText(QRectF(x + 20, y, 110, 14), Qt.AlignLeft | Qt.AlignVCenter, txt)
            x += 132

    def _hint_text(self, p: QPainter, txt: str):
        """차체 밖(하단)에 안내문 — 축 라벨과 겹치지 않게."""
        p.setPen(QPen(C_MUTED, 1))
        f = QFont()
        f.setPointSize(9)
        p.setFont(f)
        p.drawText(QRectF(0, self.height() - 26, self.width(), 20), Qt.AlignCenter, txt)
