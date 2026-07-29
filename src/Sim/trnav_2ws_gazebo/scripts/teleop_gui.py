#!/usr/bin/env python3
"""
teleop_gui - PyQt5 control panel for the Foil_A082 2WS AMR.

Publishes /cmd_vel (geometry_msgs/Twist) and /estop (std_msgs/Bool), so it drives
the Gazebo simulation and the real robot identically - motor_control subscribes
to exactly these two topics.

Layout - a 9-button pad matching the platform's 3 degrees of freedom:

    FWD-LEFT     FORWARD      FWD-RIGHT      (vx>0 with vy, pure vx, vx>0 with vy)
    CRAB-LEFT     STOP        CRAB-RIGHT     (pure vy - both wheels near 90 deg)
    ROTATE-CCW   REVERSE      ROTATE-CW      (pure wz / pure -vx)

Buttons are press-and-hold: motion continues while held and stops on release.
Arrow keys and A/D/Q/E work the same way. Space is an immediate stop.

The wheel view on the right draws the two steering modules from /joint_states,
so you can see what the steering is actually doing versus what you commanded -
the thing that matters most on a slow-servo dual-steer platform.
"""

import math
import signal
import sys

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool

from PyQt5 import QtCore, QtGui, QtWidgets

# Geometry (robot_geometry_2ws.yaml) - used only for drawing the wheel view
W1_X, W1_Y = 0.6039, -0.0014
W2_X, W2_Y = -0.5961, -0.0014
WHEEL_RADIUS = 0.125
BODY_L, BODY_W = 1.600, 0.900

PUBLISH_HZ = 20.0


class RosLink(Node):
    """ROS side. Kept deliberately thin - Qt owns the main loop."""

    def __init__(self):
        super().__init__('teleop_gui')
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.pub_estop = self.create_publisher(Bool, '/estop', 10)

        self.create_subscription(JointState, '/joint_states', self._on_joints, 10)
        self.create_subscription(Odometry, '/odom', self._on_odom, 10)

        # Latest feedback, read by the GUI
        self.steer = [0.0, 0.0]      # w1, w2 steering angle [rad]
        self.wheel_vel = [0.0, 0.0]  # w1, w2 drive angular velocity [rad/s]
        self.odom = (0.0, 0.0, 0.0)  # x, y, yaw
        self.have_joints = False
        self.have_odom = False

    def _on_joints(self, msg):
        idx = {n: i for i, n in enumerate(msg.name)}
        need = ('w1_steer_joint', 'w2_steer_joint', 'w1_wheel_joint', 'w2_wheel_joint')
        if not all(n in idx for n in need):
            return
        if len(msg.position) < len(msg.name) or len(msg.velocity) < len(msg.name):
            return
        self.steer = [msg.position[idx['w1_steer_joint']],
                      msg.position[idx['w2_steer_joint']]]
        self.wheel_vel = [msg.velocity[idx['w1_wheel_joint']],
                          msg.velocity[idx['w2_wheel_joint']]]
        self.have_joints = True

    def _on_odom(self, msg):
        q = msg.pose.pose.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                         1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        self.odom = (msg.pose.pose.position.x, msg.pose.pose.position.y, yaw)
        self.have_odom = True

    def send(self, vx, vy, wz):
        t = Twist()
        t.linear.x, t.linear.y, t.angular.z = float(vx), float(vy), float(wz)
        self.pub_cmd.publish(t)

    def send_estop(self, engaged):
        self.pub_estop.publish(Bool(data=bool(engaged)))


class WheelView(QtWidgets.QWidget):
    """Top-down view of the chassis and the two steering modules.

    Each module is drawn rotated by its measured steering angle, with an arrow
    whose length and sign follow the drive velocity. Because the two wheels sit
    on the centreline, this view makes the difference between crab (both wheels
    parallel at ~90 deg) and spin (wheels opposed) immediately obvious.
    """

    def __init__(self, ros):
        super().__init__()
        self.ros = ros
        self.setMinimumSize(260, 340)

    def paintEvent(self, _event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QtGui.QColor('#1e2128'))

        # metres -> pixels, with the robot's +x (forward) pointing up the screen
        margin = 30
        scale = min((h - 2 * margin) / (BODY_L * 1.25),
                    (w - 2 * margin) / (BODY_W * 1.6))
        cx, cy = w / 2.0, h / 2.0

        def to_px(rx, ry):
            return cx - ry * scale, cy - rx * scale

        # chassis outline
        bl, bw = BODY_L * scale, BODY_W * scale
        p.setPen(QtGui.QPen(QtGui.QColor('#5a6270'), 2))
        p.setBrush(QtGui.QColor('#2a2f3a'))
        p.drawRoundedRect(QtCore.QRectF(cx - bw / 2, cy - bl / 2, bw, bl), 8, 8)

        # front marker
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor('#f2cc0d'))
        p.drawRect(QtCore.QRectF(cx - bw * 0.4, cy - bl / 2 - 7, bw * 0.8, 6))

        p.setPen(QtGui.QPen(QtGui.QColor('#8b94a3'), 1))
        p.drawText(QtCore.QRectF(0, 4, w, 18), QtCore.Qt.AlignCenter, 'FRONT')

        for i, (wx, wy, label) in enumerate(
                [(W1_X, W1_Y, 'W1'), (W2_X, W2_Y, 'W2')]):
            px, py = to_px(wx, wy)
            steer = self.ros.steer[i]
            speed = self.ros.wheel_vel[i] * WHEEL_RADIUS  # m/s at the contact patch

            p.save()
            p.translate(px, py)
            # Screen y is inverted relative to the robot frame, so a +CCW steering
            # angle becomes a clockwise screen rotation.
            p.rotate(-math.degrees(steer))

            wheel_l, wheel_w = WHEEL_RADIUS * 2 * scale, 0.08 * scale
            p.setPen(QtGui.QPen(QtGui.QColor('#0d0d0d'), 1))
            p.setBrush(QtGui.QColor('#4a90d9') if abs(speed) < 1e-3
                       else QtGui.QColor('#3fb950'))
            p.drawRoundedRect(
                QtCore.QRectF(-wheel_w / 2, -wheel_l / 2, wheel_w, wheel_l), 3, 3)

            # drive arrow, clamped so a fast wheel does not draw off the widget
            if abs(speed) > 1e-3:
                arrow = max(-60.0, min(60.0, -speed * 45.0))
                p.setPen(QtGui.QPen(QtGui.QColor('#3fb950'), 3))
                p.drawLine(QtCore.QPointF(0, 0), QtCore.QPointF(0, arrow))
                tip = 6 if arrow > 0 else -6
                p.drawLine(QtCore.QPointF(0, arrow),
                           QtCore.QPointF(-4, arrow - tip))
                p.drawLine(QtCore.QPointF(0, arrow),
                           QtCore.QPointF(4, arrow - tip))
            p.restore()

            p.setPen(QtGui.QPen(QtGui.QColor('#c9d1d9')))
            p.drawText(QtCore.QRectF(px + 18, py - 22, 90, 16),
                       QtCore.Qt.AlignLeft, label)
            p.drawText(QtCore.QRectF(px + 18, py - 6, 90, 16),
                       QtCore.Qt.AlignLeft, f'{math.degrees(steer):+.1f}deg')
            p.drawText(QtCore.QRectF(px + 18, py + 10, 90, 16),
                       QtCore.Qt.AlignLeft, f'{speed:+.2f} m/s')

        if not self.ros.have_joints:
            p.setPen(QtGui.QPen(QtGui.QColor('#f85149')))
            p.drawText(QtCore.QRectF(0, h - 22, w, 18), QtCore.Qt.AlignCenter,
                       'no /joint_states')
        p.end()


class TeleopWindow(QtWidgets.QWidget):

    # label, tooltip, (vx sign, vy sign, wz sign), grid row/col, keyboard key
    BUTTONS = [
        ('↖\nFWD+LEFT',  'Forward while crabbing left',  (1, 1, 0),  0, 0, QtCore.Qt.Key_7),
        ('↑\nFORWARD',   'Drive forward (vx > 0)',       (1, 0, 0),  0, 1, QtCore.Qt.Key_Up),
        ('↗\nFWD+RIGHT', 'Forward while crabbing right', (1, -1, 0), 0, 2, QtCore.Qt.Key_9),
        ('←\nCRAB LEFT', 'Pure sideways left (vy > 0)',  (0, 1, 0),  1, 0, QtCore.Qt.Key_Left),
        ('■\nSTOP',      'Stop immediately',             (0, 0, 0),  1, 1, QtCore.Qt.Key_Space),
        ('→\nCRAB RIGHT', 'Pure sideways right (vy < 0)', (0, -1, 0), 1, 2, QtCore.Qt.Key_Right),
        ('↺\nROTATE CCW', 'Spin in place, counter-clockwise', (0, 0, 1), 2, 0, QtCore.Qt.Key_Q),
        ('↓\nREVERSE',   'Drive backward (vx < 0)',      (-1, 0, 0), 2, 1, QtCore.Qt.Key_Down),
        ('↻\nROTATE CW', 'Spin in place, clockwise',     (0, 0, -1), 2, 2, QtCore.Qt.Key_E),
    ]

    def __init__(self, ros):
        super().__init__()
        self.ros = ros
        self.active = (0.0, 0.0, 0.0)   # currently held direction signs
        self.estop = False
        self.key_map = {}

        self.setWindowTitle('Foil_A082 - 2WS AMR Control')
        self.setStyleSheet(
            "QWidget { background: #14171d; color: #c9d1d9;"
            "          font-family: 'DejaVu Sans'; font-size: 12px; }"
            "QPushButton { background: #262c36; border: 1px solid #3a424e; }")

        root = QtWidgets.QHBoxLayout(self)
        left = QtWidgets.QVBoxLayout()
        root.addLayout(left, 3)

        # ---------------- direction pad ----------------
        pad_box = QtWidgets.QGroupBox('Motion  (hold button, or use keys)')
        pad_box.setStyleSheet('QGroupBox { border: 1px solid #30363d; margin-top: 8px;'
                              ' padding-top: 10px; font-weight: bold; }'
                              'QGroupBox::title { left: 10px; }')
        pad = QtWidgets.QGridLayout(pad_box)
        pad.setSpacing(6)

        for label, tip, signs, row, col, key in self.BUTTONS:
            btn = QtWidgets.QPushButton(label)
            btn.setToolTip(tip)
            btn.setMinimumSize(104, 74)
            is_stop = signs == (0, 0, 0)
            btn.setStyleSheet(
                'QPushButton { background: %s; border: 1px solid #3a424e;'
                ' border-radius: 6px; font-size: 12px; font-weight: bold; }'
                'QPushButton:hover { background: %s; }'
                'QPushButton:pressed { background: #3fb950; color: #08130a; }'
                % (('#5c1f24', '#7a2a30') if is_stop else ('#262c36', '#323a47')))

            if is_stop:
                btn.clicked.connect(self.stop_now)
            else:
                btn.pressed.connect(lambda s=signs: self.set_active(s))
                btn.released.connect(self.clear_active)
                self.key_map[key] = signs
            pad.addWidget(btn, row, col)

        left.addWidget(pad_box)

        # ---------------- speed sliders ----------------
        speed_box = QtWidgets.QGroupBox('Speed')
        speed_box.setStyleSheet(pad_box.styleSheet())
        sl = QtWidgets.QGridLayout(speed_box)

        self.lin_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.lin_slider.setRange(5, 150)      # 0.05 .. 1.50 m/s
        self.lin_slider.setValue(50)
        self.lin_label = QtWidgets.QLabel('0.50 m/s')
        sl.addWidget(QtWidgets.QLabel('Linear'), 0, 0)
        sl.addWidget(self.lin_slider, 0, 1)
        sl.addWidget(self.lin_label, 0, 2)

        self.ang_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.ang_slider.setRange(5, 150)      # 0.05 .. 1.50 rad/s
        self.ang_slider.setValue(50)
        self.ang_label = QtWidgets.QLabel('0.50 rad/s')
        sl.addWidget(QtWidgets.QLabel('Angular'), 1, 0)
        sl.addWidget(self.ang_slider, 1, 1)
        sl.addWidget(self.ang_label, 1, 2)

        self.lin_slider.valueChanged.connect(
            lambda v: self.lin_label.setText(f'{v / 100.0:.2f} m/s'))
        self.ang_slider.valueChanged.connect(
            lambda v: self.ang_label.setText(f'{v / 100.0:.2f} rad/s'))
        left.addWidget(speed_box)

        # ---------------- estop + status ----------------
        self.estop_btn = QtWidgets.QPushButton('E-STOP   (disengaged)')
        self.estop_btn.setCheckable(True)
        self.estop_btn.setMinimumHeight(44)
        self.estop_btn.setStyleSheet(
            'QPushButton { background: #262c36; border: 2px solid #f85149;'
            ' border-radius: 6px; font-weight: bold; font-size: 13px; }'
            'QPushButton:checked { background: #f85149; color: #14171d; }')
        self.estop_btn.toggled.connect(self.on_estop)
        left.addWidget(self.estop_btn)

        self.status = QtWidgets.QLabel()
        self.status.setStyleSheet(
            'background: #0d1117; border: 1px solid #30363d; border-radius: 6px;'
            ' padding: 8px; font-family: monospace; font-size: 12px;')
        self.status.setMinimumHeight(96)
        self.status.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        left.addWidget(self.status)
        left.addStretch(1)

        # ---------------- wheel view ----------------
        right = QtWidgets.QVBoxLayout()
        wheel_title = QtWidgets.QLabel('Steering modules')
        wheel_title.setStyleSheet('font-weight: bold; padding: 4px;')
        right.addWidget(wheel_title)
        self.wheel_view = WheelView(ros)
        right.addWidget(self.wheel_view, 1)
        root.addLayout(right, 2)

        # ---------------- timers ----------------
        # One timer drives ROS callbacks, command publishing and the repaint,
        # so there is no second thread to synchronise with.
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(int(1000.0 / PUBLISH_HZ))

        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    # ------------------------------------------------------------ interaction

    def set_active(self, signs):
        self.active = signs

    def clear_active(self):
        self.active = (0.0, 0.0, 0.0)

    def stop_now(self):
        self.active = (0.0, 0.0, 0.0)
        self.ros.send(0.0, 0.0, 0.0)

    def on_estop(self, checked):
        self.estop = checked
        self.estop_btn.setText(
            'E-STOP   (ENGAGED)' if checked else 'E-STOP   (disengaged)')
        self.ros.send_estop(checked)
        if checked:
            self.stop_now()

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        key = event.key()
        if key == QtCore.Qt.Key_Space:
            self.stop_now()
        elif key in self.key_map:
            self.set_active(self.key_map[key])
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        if event.key() in self.key_map:
            self.clear_active()
        else:
            super().keyReleaseEvent(event)

    # ------------------------------------------------------------------- loop

    def tick(self):
        rclpy.spin_once(self.ros, timeout_sec=0.0)

        lin = self.lin_slider.value() / 100.0
        ang = self.ang_slider.value() / 100.0
        sx, sy, sw = self.active

        if self.estop:
            vx = vy = wz = 0.0
        else:
            # Diagonal presses set both vx and vy; scale so the resulting speed
            # matches the slider rather than exceeding it by sqrt(2).
            norm = math.hypot(sx, sy)
            k = (1.0 / norm) if norm > 1.0 else 1.0
            vx, vy, wz = sx * lin * k, sy * lin * k, sw * ang

        self.ros.send(vx, vy, wz)

        x, y, yaw = self.ros.odom
        odom_line = (f'{x:+.3f}  {y:+.3f}  {math.degrees(yaw):+.1f}deg'
                     if self.ros.have_odom else 'waiting...')
        self.status.setText(
            f'cmd_vel   vx {vx:+.3f} m/s   vy {vy:+.3f} m/s   wz {wz:+.3f} rad/s\n'
            f'odom      x {odom_line}\n'
            f'steering  W1 {math.degrees(self.ros.steer[0]):+7.2f}deg   '
            f'W2 {math.degrees(self.ros.steer[1]):+7.2f}deg\n'
            f'estop     {"ENGAGED" if self.estop else "clear"}')
        self.wheel_view.update()

    def closeEvent(self, event):
        self.ros.send(0.0, 0.0, 0.0)
        super().closeEvent(event)


def main():
    rclpy.init()
    ros = RosLink()

    app = QtWidgets.QApplication(sys.argv)
    # Let Ctrl+C in the launching terminal close the window.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    win = TeleopWindow(ros)
    win.resize(720, 560)
    win.show()

    try:
        rc = app.exec_()
    finally:
        ros.send(0.0, 0.0, 0.0)
        ros.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(rc)


if __name__ == '__main__':
    main()
