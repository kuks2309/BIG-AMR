#!/usr/bin/env python3
"""왕복 주행 실기 테스트 구동 UI — 탭① 패키지 구동(실행/중지), 탭② 왕복 실험.

비-ROS colcon 독립 도구(python3 즉시 실행). 실행:
    python3 Tools/drive_test_ui/drive_test_ui.py
E-STOP(하드웨어 비상정지)은 이 UI 가 대체하지 않는다 — 항상 손 닿는 곳에 둘 것.
"""
import json
import math
import os
import signal
import subprocess
import time

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (QApplication, QDoubleSpinBox, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                             QPlainTextEdit, QPushButton, QSpinBox, QTabWidget,
                             QVBoxLayout, QWidget)

# can_relay 상주(systemd, 도메인 125) 모델 — 실험 스택 전체를 같은 도메인에 태운다
os.environ.setdefault('ROS_DOMAIN_ID', '125')

REPO = '/home/nvidia/Project/Ford-CATL-AMR/Big-AMR'
SMAP = f'{REPO}/map/260709_test_2026-08-25_92e73074.smap'
LOGDIR = f'{REPO}/Log'
SRC = f'source /opt/ros/humble/setup.bash && source {REPO}/install/setup.bash 2>/dev/null'

# 탭① 상주 항목: (키, 표시명, 명령)
STACK_ITEMS = [
    ('bringup', '측위 브링업 (라이다×2·병합·ICP·mcl·맵서버·RViz2)',
     f'ros2 launch mcl2d_ros2 bringup.launch.py map_path:={SMAP} rviz:=true'),
    ('seer_map', 'smap 마커 발행 (노드·경로·장애물 → RViz)',
     f'python3 {REPO}/Tools/seer_viz/seer_map_viz.py --smap {SMAP} --no-tf'),
    ('bridge', '/robot_pose 브리지 (mcl→PoseStamped)',
     'ros2 run sil_pose_adapter sil_pose_adapter_node --ros-args '
     '-r /rtabmap/localization_pose:=/mcl_pose'),
    ('wall', '특징면 측위 (feature_localizer → /feature_pose)',
     'ros2 run feature_localizer_ros2 feature_localizer_node --ros-args '
     '-r /scan:=/scan_merged '
     f'--params-file {REPO}/Tools/feature_teach/features_lm1_live.yaml '
     '-p initial_x_m:=-6.40 -p initial_y_m:=13.95 -p initial_yaw_deg:=0.0'),
    ('imu', 'IMU (iahrs)', 'ros2 launch iahrs_driver iahrs_driver.py'),
    ('pgv', 'PGV 드라이버 (/dev/pgv, 보정 적용)',
     'ros2 run pgv_driver pgv_driver_node --ros-args -p serial_port:=/dev/pgv '
     '-p angle_offset_deg:=45.3 -p frame_rotation_deg:=-90.0'),
    ('mux', '모션 mux', 'ros2 launch trnav_motion_mux trnav_motion_mux.launch.py'),
    ('translator', '모터 지령 translator',
     'ros2 run amr_motor_cmd_translator amr_motor_cmd_translator_node --ros-args '
     f'--params-file {REPO}/install/amr_motor_cmd_translator/share/'
     'amr_motor_cmd_translator/config/amr_motor_cmd_translator_qd.yaml'),
    ('tf_srv', '전진 액션 서버', 'ros2 launch trnav_2ws_action_server translate_forward.launch.py'),
    ('tr_srv', '후진 액션 서버', 'ros2 launch trnav_2ws_action_server translate_reverse.launch.py'),
    ('dock_srv', '정밀 도킹 서버 (dock_approach, /feature_pose 기준)',
     'ros2 launch trnav_2ws_dock_ros dock_approach.launch.py'),
]

# 탭① 단발 항목: (키, 표시명, 명령, 확인 다이얼로그 문구 또는 None)
ONESHOT_ITEMS = [
    ('engage', '제어권 획득 (engage)',
     'ros2 service call /can_relay_node/engage std_srvs/srv/SetBool "{data: true}"', None),
    ('home', '조향 호밍',
     'ros2 service call /can_relay_node/home std_srvs/srv/Trigger "{}"',
     '조향 양축이 100° 이상 물리 스윙합니다.\n로봇 주변 1 m 를 비웠습니까?'),
    ('disengage', '제어권 반환 (disengage)',
     'ros2 service call /can_relay_node/engage std_srvs/srv/SetBool "{data: false}"', None),
]

# gate 는 도킹 PID(kp 0.8)가 진입 속도를 그대로 이어받는 거리 이상이어야
# 속도 저크가 없다: gate ≥ dock_speed/0.8 (dock_speed 0.6 이면 0.75 m 이상 필요)
DEFAULTS = {'speed': 1.0, 'accel': 0.3, 'dist': 6.0, 'laps': 10,
            'gate': 1.0, 'dock_speed': 0.6, 'pause': 1.0}
GOAL_TIMEOUT_S = 90.0
DOCK_TEACH_FILE = f'{REPO}/Log/dock_target_teach.json'
DOCK_TOL = (3.0, 3.0, 0.5)     # 종·횡 mm, 각 deg — 어제 33회 실기와 동일 공차

# 버튼 배색 — 실행/중지/특수 명령을 색으로 구분
STYLE_RUN = ('QPushButton{background:#1c7c39; color:white; font-weight:bold;'
             ' padding:4px 12px; border-radius:3px}'
             'QPushButton:pressed{background:#155d2b}'
             'QPushButton:disabled{background:#c9ced4; color:#eef0f2}')
STYLE_RUNNING = ('QPushButton{background:#1c5d99; color:white; font-weight:bold;'
                 ' padding:4px 12px; border-radius:3px}'
                 'QPushButton:disabled{background:#c9ced4; color:#eef0f2}')
STYLE_STOP = ('QPushButton{background:#b3372f; color:white; padding:4px 12px;'
              ' border-radius:3px}'
              'QPushButton:pressed{background:#8c2b25}'
              'QPushButton:disabled{background:#c9ced4; color:#eef0f2}')
STYLE_KILL = ('QPushButton{background:#7a1f1a; color:white; font-weight:bold;'
              ' padding:5px 12px; border-radius:3px}'
              'QPushButton:pressed{background:#5c1713}'
              'QPushButton:disabled{background:#c9ced4; color:#eef0f2}')
ONESHOT_STYLES = {
    'engage': 'QPushButton{background:#1c5d99; color:white; padding:5px 10px; border-radius:3px}'
        'QPushButton:disabled{background:#c9ced4; color:#eef0f2}',
    'home': 'QPushButton{background:#a35a00; color:white; padding:5px 10px; border-radius:3px}'
        'QPushButton:disabled{background:#c9ced4; color:#eef0f2}',
    'disengage': 'QPushButton{background:#5a6570; color:white; padding:5px 10px; border-radius:3px}'
        'QPushButton:disabled{background:#c9ced4; color:#eef0f2}',
}

# kill all 소탕 보강 — launch 부모가 비정상 종료로 고아를 남겨도 자식 노드까지 잡는다
EXTRA_KILL_MARKERS = [
    'sick_safetyscanners2_node', 'dual_laser_merger_node', 'icp_odometry',
    'mcl2d_localization_node', 'smap_map_server', 'rviz2',
    'amr_translate_forward_node', 'amr_translate_reverse_node',
    'trnav_motion_mux_node', 'iahrs_driver',
    'feature_localizer_node', 'dock_approach_action_server',
]


class ProcManager:
    """상주 프로세스 기동/정지 — 프로세스 그룹 단위, 로그는 Log/ui_<키>.log."""

    def __init__(self):
        self.procs = {}

    @staticmethod
    def marker(cmd):
        """중복 검사용 식별 토큰 — launch 파일명 > 실행 파일/스크립트명 순."""
        for tok in cmd.split():
            if tok.endswith('.launch.py') or tok.endswith('.py'):
                return os.path.basename(tok)
        parts = cmd.split()
        return parts[3] if parts[:2] == ['ros2', 'run'] and len(parts) > 3 else parts[-1]

    # launch 항목의 고아 '자식' 실행 파일까지 중복으로 판정하기 위한 부가 패턴
    CHILD_PATTERNS = {
        'bringup': ['sick_safetyscanners2_node', 'dual_laser_merger_node',
                    'icp_odometry', 'mcl2d_localization_node', 'smap_map_server'],
        'mux': ['trnav_motion_mux_node'],
        'tf_srv': ['amr_translate_forward_node'],
        'tr_srv': ['amr_translate_reverse_node'],
        'imu': ['iahrs_driver'],
        'wall': ['feature_localizer_node'],
        'dock_srv': ['dock_approach_action_server'],
    }

    def start(self, key, cmd):
        if self.alive(key):
            return True
        # 시스템 전역 중복 검사 — launch 부모 이름 + 고아 자식 실행 파일까지 본다
        for mk in [self.marker(cmd)] + self.CHILD_PATTERNS.get(key, []):
            if subprocess.run(['pgrep', '-f', mk], capture_output=True).returncode == 0:
                return False
        log = open(f'{LOGDIR}/ui_{key}.log', 'ab')
        env = dict(os.environ)
        env.setdefault('DISPLAY', ':0')   # RViz2 등 GUI 자식 프로세스용
        p = subprocess.Popen(['bash', '-c', f'{SRC}; exec {cmd}'],
                             stdout=log, stderr=log, preexec_fn=os.setsid, cwd=REPO,
                             env=env)
        self.procs[key] = p
        return True

    def stop(self, key):
        p = self.procs.get(key)
        if p is None or p.poll() is not None:
            return
        try:
            # SIGINT → SIGTERM → SIGKILL 3단 — launch 자식까지 그룹 단위로 확실 종료
            for sig, wait_s in ((signal.SIGINT, 3.0), (signal.SIGTERM, 2.0),
                                (signal.SIGKILL, 1.0)):
                os.killpg(p.pid, sig)
                t0 = time.time()
                while time.time() - t0 < wait_s:
                    if p.poll() is not None:
                        return
                    time.sleep(0.1)
        except ProcessLookupError:
            pass

    def alive(self, key):
        p = self.procs.get(key)
        return p is not None and p.poll() is None

    def stop_all(self):
        for key in list(self.procs):
            self.stop(key)
        # 잔존 소탕 — INT(정상 종료) 우선, 이후 TERM→KILL. can_relay 를 KILL 로
        # 잡았다면 판다 USB 인터페이스가 물릴 수 있어 자동 리셋한다.
        markers = {self.marker(cmd) for _, _, cmd in STACK_ITEMS} | set(EXTRA_KILL_MARKERS)
        for sig, wait_s in (('-INT', 3.0), ('-TERM', 2.0)):
            for mk in markers:
                subprocess.run(['pkill', sig, '-f', mk], capture_output=True)
            time.sleep(wait_s)
        for mk in markers:
            if subprocess.run(['pgrep', '-f', mk],
                              capture_output=True).returncode == 0:
                if 'can_relay' in mk:
                    # can_relay 는 KILL 금지 — USB 를 쥔 채 죽으면 판다가 버스에서
                    # 사라져 물리 재연결까지 필요해진다. 정상 종료 실패 시 사람이 처리.
                    continue
                subprocess.run(['pkill', '-9', '-f', mk], capture_output=True)


def panda_usb_reset():
    """판다 USB 소프트 리셋 — can_relay 를 강제 종료(-9)한 뒤 인터페이스 잠김 해제용."""
    try:
        out = subprocess.run(['lsusb'], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if 'panda' in line.lower():
                bus, dev = line.split()[1], line.split()[3].rstrip(':')
                import fcntl
                with open(f'/dev/bus/usb/{bus}/{dev}', 'w') as f:
                    fcntl.ioctl(f, 21780)  # USBDEVFS_RESET
                return True
    except OSError:
        pass
    return False


def smap_location_marks():
    """smap 의 LocationMark 2점을 x 오름차순으로 반환 — 탭② 고정 좌표계의 정본.

    RViz(seer_map)와 같은 지도 노드를 쓰므로 두 화면의 위치 표시가 일치한다.
    반환: (xa, ya, xb, yb, (nameA, nameB)) 또는 None(파일 없음·마크 2점 미만).
    """
    try:
        with open(SMAP) as f:
            d = json.load(f)
        lm = [p for p in d.get('advancedPointList', [])
              if p.get('className') == 'LocationMark']
        lm.sort(key=lambda p: p['pos']['x'])
        if len(lm) >= 2:
            a, b = lm[0], lm[-1]
            return (a['pos']['x'], a['pos']['y'], b['pos']['x'], b['pos']['y'],
                    (a.get('instanceName', 'A'), b.get('instanceName', 'B')))
    except Exception:
        pass
    return None


def run_oneshot(cmd, timeout_s=120):
    """단발 명령 동기 실행 — (성공여부, 마지막 출력 줄)."""
    try:
        r = subprocess.run(['bash', '-c', f'{SRC}; {cmd}'], capture_output=True,
                           text=True, timeout=timeout_s, cwd=REPO)
        out = (r.stdout + r.stderr).strip().splitlines()
        return r.returncode == 0, (out[-1] if out else '')
    except subprocess.TimeoutExpired:
        return False, '시간 초과'


class RosWorker(QThread):
    """rclpy 백그라운드 — 자세/PGV 구독 + 왕복 루프 실행."""

    sig_pose = pyqtSignal(float, float)
    sig_wheels = pyqtSignal(float, float)   # 전륜·후륜 조향각 (deg)
    sig_engaged = pyqtSignal(bool)          # can_relay 제어권 보유 여부
    sig_pgv = pyqtSignal(str)
    sig_lap = pyqtSignal(int, str, float, float, str)   # 회차, 구간, 소요s, 복귀오차mm, PGV
    sig_nodes = pyqtSignal(float, float, float, float)  # 노드 A(x,y)·B(x,y) (실험 시작 시)
    sig_arrival = pyqtSignal(int, float, float)         # 회차, 도착 PGV x/y (mm)
    sig_msg = pyqtSignal(str)
    sig_done = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.pose = None
        self.pgv = None
        self.wall = None           # 최신 /feature_pose (x, y, yaw_deg)
        self.trip_req = None
        self.teach_req = False
        self.cancel = False
        self._gh = None
        self.dock_target = None    # (x, y, yaw_deg) — 스테이션 프레임 도킹 목표
        self._lat_ref = None       # 주행 leg 횡편차 계측 기준 y (경로선)
        self._lat_max = 0.0
        try:
            with open(DOCK_TEACH_FILE) as f:
                d = json.load(f)
            self.dock_target = (d['x_m'], d['y_m'], d['yaw_deg'])
        except Exception:
            pass

    def run(self):
        import rclpy
        from geometry_msgs.msg import PoseStamped
        from pgv_interfaces.msg import PgvPosition
        from rclpy.action import ActionClient
        from trnav_2ws_interfaces.action import (AMRMotionDockApproach,
                                                 AMRMotionTranslateForward,
                                                 AMRMotionTranslateReverse)
        rclpy.init()
        node = rclpy.create_node('drive_test_ui')
        node.create_subscription(PoseStamped, '/robot_pose',
                                 lambda m: self._on_pose(m), 10)
        node.create_subscription(PoseStamped, '/feature_pose',
                                 lambda m: self._on_wall(m), 10)
        node.create_subscription(PgvPosition, '/pgv/position',
                                 lambda m: self._on_pgv(m), 10)
        from sensor_msgs.msg import JointState
        node.create_subscription(JointState, '/joint_states',
                                 lambda m: self._on_joints(m), 10)
        from diagnostic_msgs.msg import DiagnosticArray
        node.create_subscription(DiagnosticArray, '/diagnostics',
                                 lambda m: self._on_diag(m), 10)
        fwd = ActionClient(node, AMRMotionTranslateForward,
                           'amr_motion_translate_forward_abstract')
        rev = ActionClient(node, AMRMotionTranslateReverse,
                           'amr_motion_translate_reverse_abstract')
        dock = ActionClient(node, AMRMotionDockApproach,
                            'amr_motion_dock_approach')
        self._ctx = (rclpy, node, fwd, rev,
                     AMRMotionTranslateForward, AMRMotionTranslateReverse,
                     dock, AMRMotionDockApproach)
        while not self.isInterruptionRequested():
            rclpy.spin_once(node, timeout_sec=0.1)
            if self.teach_req:
                self.teach_req = False
                self._do_teach()
            if self.trip_req is not None:
                req = self.trip_req
                self.trip_req = None
                self._run_trips(*req)
        node.destroy_node()
        rclpy.shutdown()

    def _on_pose(self, m):
        self.pose = (m.pose.position.x, m.pose.position.y)
        self.sig_pose.emit(*self.pose)

    def _on_wall(self, m):
        q = m.pose.orientation
        yaw = math.degrees(math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                                      1.0 - 2.0 * (q.y * q.y + q.z * q.z)))
        self.wall = (m.pose.position.x, m.pose.position.y, yaw)

    def _do_teach(self):
        if self.wall is None:
            self.sig_msg.emit('티치 실패 — /feature_pose 없음 (feature_localizer·스테이션 시야 확인)')
            return
        self.dock_target = self.wall
        with open(DOCK_TEACH_FILE, 'w') as f:
            json.dump({'x_m': self.wall[0], 'y_m': self.wall[1],
                       'yaw_deg': self.wall[2], 'source': 'ui-teach'}, f)
        self.sig_msg.emit(f'도킹 목표 티치 완료: x {self.wall[0]:+.4f} m · '
                          f'y {self.wall[1]:+.4f} m · yaw {self.wall[2]:+.2f}°')

    def _on_diag(self, m):
        for st in m.status:
            if st.name.startswith('can_relay'):
                for kv in st.values:
                    if kv.key == 'engaged':
                        self.sig_engaged.emit(kv.value == 'True')
                        return

    def _on_joints(self, m):
        d = dict(zip(m.name, m.position))
        if 'steer_3' in d and 'steer_4' in d:
            self.sig_wheels.emit(math.degrees(d['steer_3']),
                                 math.degrees(d['steer_4']))

    def _on_pgv(self, m):
        self.pgv = m
        if m.tag_detected:
            self.sig_pgv.emit(f'x {m.x_position_mm:+.1f} · y {m.y_offset_mm:+.1f} mm '
                              f'· {m.angle_deg:+.1f}°')
        else:
            self.sig_pgv.emit('태그 없음' + (' (error %d)' % m.error_code if m.error else ''))

    def _goal(self, cli, act, dist, speed, accel, exit_speed=0.0, handoff_fut=None):
        rclpy = self._ctx[0]
        node = self._ctx[1]
        cur = self.pose
        g = act.Goal()
        g.start_x = cur[0] - (0.02 if dist > 0 else -0.02)
        g.start_y = cur[1]
        g.end_x, g.end_y = cur[0] + dist, cur[1]
        g.max_linear_speed, g.acceleration = speed, accel
        # 체이닝 leg(출구속도>0)는 조향 복귀(Phase 4)를 건너뛴다 — 그 루프가 속도 0
        # 지령을 반복 발행해 전환 단절(실측 0.22 s)을 만들고, 조향은 도킹이 이어받는다
        g.hold_steer = exit_speed > 0.0
        g.exit_steer_angle = g.entry_speed = 0.0
        g.exit_speed = exit_speed
        g.has_next = False
        g.control_mode = 0
        g.enable_localization_watchdog = True
        g.skip_initial_pose_check = False
        if not cli.wait_for_server(timeout_sec=5.0):
            self.sig_msg.emit('액션 서버 없음 — 탭①에서 서버를 실행하세요')
            return None
        fut = cli.send_goal_async(g)
        rclpy.spin_until_future_complete(node, fut, timeout_sec=10.0)
        gh = fut.result()
        if gh is None or not gh.accepted:
            self.sig_msg.emit('goal 거부')
            return None
        self._gh = gh
        rfut = gh.get_result_async()
        t0 = time.time()
        while not rfut.done():
            rclpy.spin_once(node, timeout_sec=0.1)
            if self._lat_ref is not None and self.pose is not None:
                self._lat_max = max(self._lat_max, abs(self.pose[1] - self._lat_ref))
            if handoff_fut is not None and handoff_fut.done():
                # 도킹(armed)이 게이트에서 인수해 먼저 종료 — 주행 goal 은 회수
                gh.cancel_goal_async()
                t1 = time.time()
                while not rfut.done() and time.time() - t1 < 5.0:
                    rclpy.spin_once(node, timeout_sec=0.1)
                self._gh = None
                return 'HANDOFF'
            if self.cancel:
                gh.cancel_goal_async()
            if time.time() - t0 > GOAL_TIMEOUT_S:
                gh.cancel_goal_async()
                self.sig_msg.emit('goal 대기 초과 — 취소')
                return None
        self._gh = None
        return rfut.result().result

    def _pgv_txt(self):
        m = self.pgv
        if m is None or not m.tag_detected:
            return '-'
        return f'{m.x_position_mm:+.1f}/{m.y_offset_mm:+.1f}'

    def _pgv_avg(self, n_target=10, timeout_s=2.5):
        """도착 정지 상태에서 PGV n샘플 평균 — 어제 실기 계측 방식과 동일."""
        rclpy, node = self._ctx[0], self._ctx[1]
        xs, ys, angs = [], [], []
        seen = None
        t0 = time.time()
        while len(xs) < n_target and time.time() - t0 < timeout_s:
            rclpy.spin_once(node, timeout_sec=0.1)
            m = self.pgv
            if m is not None and m.tag_detected and m is not seen:
                seen = m
                xs.append(m.x_position_mm)
                ys.append(m.y_offset_mm)
                angs.append(m.angle_deg)
        if not xs:
            return None
        return {'x_mm': sum(xs) / len(xs), 'y_mm': sum(ys) / len(ys),
                'ang': sum(angs) / len(angs), 'n': len(xs)}

    def _dock_send(self, max_speed):
        """정밀 도킹 goal 발행(armed 사전 대기) — 수락까지만 확인, 결과는 _dock_wait."""
        dock, act = self._ctx[6], self._ctx[7]
        g = act.Goal()
        g.target_x_m, g.target_y_m, g.target_yaw_deg = self.dock_target
        g.approach_axis_deg = 0.0
        g.max_speed_mps = max_speed
        g.tol_d_mm, g.tol_lat_mm, g.tol_yaw_deg = DOCK_TOL
        g.timeout_s = 60.0
        if not dock.wait_for_server(timeout_sec=5.0):
            self.sig_msg.emit('도킹 서버 없음 — 탭①에서 정밀 도킹 서버를 실행하세요')
            return None
        rclpy, node = self._ctx[0], self._ctx[1]
        fut = dock.send_goal_async(g)
        rclpy.spin_until_future_complete(node, fut, timeout_sec=10.0)
        gh = fut.result()
        if gh is None or not gh.accepted:
            self.sig_msg.emit('도킹 goal 거부')
            return None
        return gh, gh.get_result_async()

    def _dock_wait(self, gh, rfut):
        """armed 도킹의 결과 대기 — 공차(DOCK_TOL) 판정은 서버 소관."""
        rclpy, node = self._ctx[0], self._ctx[1]
        t0 = time.time()
        while not rfut.done():
            rclpy.spin_once(node, timeout_sec=0.1)
            if self.cancel:
                gh.cancel_goal_async()
            if time.time() - t0 > GOAL_TIMEOUT_S:
                gh.cancel_goal_async()
                self.sig_msg.emit('도킹 대기 초과 — 취소')
                return None
        return rfut.result().result

    def _run_trips(self, dist, speed, accel, laps, gate, dock_speed, pause):
        rclpy = self._ctx[0]
        fwd, rev = self._ctx[2], self._ctx[3]
        act_f, act_r = self._ctx[4], self._ctx[5]
        self.cancel = False
        if self.pose is None:
            self.sig_msg.emit('/robot_pose 없음 — 측위·브리지를 먼저 실행하세요')
            self.sig_done.emit(False)
            return
        if self.dock_target is None:
            self.sig_msg.emit('도킹 목표 없음 — 티치 버튼 또는 teach 파일 필요')
            self.sig_done.emit(False)
            return
        # armed 인수 거리 = 게이트 — 서버가 goal 수락 시점 값으로 재독한다
        run_oneshot(f'ros2 param set /dock_approach_server arm_engage_dist_m {gate}')
        out = time.strftime(f'{LOGDIR}/drive_trip_%Y%m%d_%H%M%S.jsonl')
        home = self.pose
        self.sig_nodes.emit(home[0] - dist, home[1], home[0], home[1])
        ok_all = True
        with open(out, 'w') as fp:
            for lap in range(1, laps + 1):
                # 사이클: 후진 이탈(정지) → 대기 → [도킹 armed 발행 → 전진 전 구간
                # → 게이트에서 서버가 mux 인수(무정지) → 도킹 완료] → PGV 평균 → 대기
                lap_row = {'lap': lap, 'speed': speed, 'accel': accel,
                           'dist': dist, 'gate': gate, 'dock_speed': dock_speed,
                           'pause': pause}
                if self.cancel:
                    self.sig_msg.emit('중지됨')
                    self.sig_done.emit(False)
                    return
                self._lat_ref, self._lat_max = home[1], 0.0
                t0 = time.time()
                res = self._goal(rev, act_r, -dist, speed, accel)
                dt = time.time() - t0
                self._lat_ref = None
                if res is None or res.status != 0:
                    self.sig_msg.emit(f'{lap}회차 후진 실패 — 중단')
                    self.sig_done.emit(False)
                    return
                lap_row['rev_s'] = round(dt, 2)
                lap_row['rev_lat_max_mm'] = round(1000 * self._lat_max, 1)
                self.sig_lap.emit(lap, '후진', dt, lap_row['rev_lat_max_mm'],
                                  self._pgv_txt())
                time.sleep(pause)   # 정지 후 재출발 대기 — 모터 부담 완화
                if self.cancel:
                    self.sig_msg.emit('중지됨')
                    self.sig_done.emit(False)
                    return
                sent = self._dock_send(dock_speed)
                if sent is None:
                    self.sig_done.emit(False)
                    return
                gh_d, rfut_d = sent
                self._lat_ref, self._lat_max = home[1], 0.0
                t0 = time.time()
                res = self._goal(fwd, act_f, dist, speed, accel,
                                 exit_speed=dock_speed, handoff_fut=rfut_d)
                dt = time.time() - t0
                self._lat_ref = None
                if res is None:
                    gh_d.cancel_goal_async()
                    self.sig_msg.emit(f'{lap}회차 전진 실패 — 중단')
                    self.sig_done.emit(False)
                    return
                lap_row['fwd_s'] = round(dt, 2)
                lap_row['fwd_lat_max_mm'] = round(1000 * self._lat_max, 1)
                self.sig_lap.emit(lap, '전진', dt, lap_row['fwd_lat_max_mm'],
                                  self._pgv_txt())
                self.sig_msg.emit(f'{lap}회차 도킹 접근…')
                t0 = time.time()
                dres = self._dock_wait(gh_d, rfut_d)
                ddt = time.time() - t0
                if dres is None or not dres.success:
                    reason = '' if dres is None else f' (stop_reason {dres.stop_reason})'
                    self.sig_msg.emit(f'{lap}회차 도킹 실패{reason} — 중단')
                    self.sig_done.emit(False)
                    return
                time.sleep(0.5)
                pv = self._pgv_avg()
                lap_row.update({
                    'success': True, 'stop_reason': int(dres.stop_reason),
                    'srv_d_mm': dres.final_e_d_mm, 'srv_lat_mm': dres.final_e_lat_mm,
                    'srv_yaw_deg': dres.final_e_yaw_deg, 'dock_s': round(ddt, 2),
                    'pgv': pv})
                ret_mm = abs(dres.final_e_d_mm)
                self.sig_lap.emit(lap, '도킹', ddt, ret_mm, self._pgv_txt())
                if pv is not None:
                    self.sig_arrival.emit(lap, pv['x_mm'], pv['y_mm'])
                lap_row['pose'] = self.pose
                fp.write(json.dumps(lap_row) + '\n')
                fp.flush()
                if lap < laps:
                    time.sleep(pause)   # 도킹 정지 후 다음 후진까지 대기
        self.sig_msg.emit(f'완료 — 기록 {out}')
        self.sig_done.emit(ok_all)


class StackTab(QWidget):
    """탭① — 패키지 실행/중지 버튼과 상태 램프, 단발 명령, 로그."""

    def __init__(self, pm, worker):
        super().__init__()
        self.pm = pm
        self.lamps = {}
        self.runbtns = {}
        self.cmds = {}
        self.oneshot_btns = {}
        root = QVBoxLayout(self)
        grp = QGroupBox('상주 패키지')
        grid = QGridLayout(grp)
        for i, (key, label, cmd) in enumerate(STACK_ITEMS):
            lamp = QLabel('●')
            lamp.setStyleSheet('color:#999; font-size:16px')
            self.lamps[key] = lamp
            self.cmds[key] = cmd
            b_run = QPushButton('실행')
            b_run.setStyleSheet(STYLE_RUN)
            self.runbtns[key] = b_run
            b_stop = QPushButton('중지')
            b_stop.setStyleSheet(STYLE_STOP)
            b_run.clicked.connect(lambda _, k=key, c=cmd: self._start(k, c))
            b_stop.clicked.connect(lambda _, k=key: self._stop(k))
            grid.addWidget(lamp, i, 0)
            grid.addWidget(QLabel(label), i, 1)
            grid.addWidget(b_run, i, 2)
            grid.addWidget(b_stop, i, 3)
        b_all = QPushButton('전체 순차 실행 (위에서 아래로)')
        b_all.setStyleSheet(STYLE_RUN)
        b_all.clicked.connect(self._start_all)
        grid.addWidget(b_all, len(STACK_ITEMS), 1, 1, 1)
        b_killall = QPushButton('전체 중지 (kill all)')
        b_killall.setStyleSheet(STYLE_KILL)
        b_killall.clicked.connect(self._kill_all)
        grid.addWidget(b_killall, len(STACK_ITEMS), 2, 1, 2)
        root.addWidget(grp)

        grp2 = QGroupBox('단발 명령 (드라이버 준비) — can_relay 는 systemd 상주(도메인 125)')
        h = QHBoxLayout(grp2)
        self.svc_lamp = QLabel('●')
        self.svc_lamp.setStyleSheet('color:#999; font-size:16px')
        h.addWidget(self.svc_lamp)
        h.addWidget(QLabel('can_relay 서비스'))
        for key, label, cmd, warn in ONESHOT_ITEMS:
            b = QPushButton(label)
            b.setStyleSheet(ONESHOT_STYLES.get(key, ''))
            b.clicked.connect(lambda _, l=label, c=cmd, w=warn: self._oneshot(l, c, w))
            self.oneshot_btns[key] = b
            h.addWidget(b)
        # 제어권 없으면 호밍·반환 비활성 (첫 진단 수신 전 기본 비활성)
        self.oneshot_btns['home'].setEnabled(False)
        self.oneshot_btns['disengage'].setEnabled(False)
        worker.sig_engaged.connect(self._on_engaged)
        root.addWidget(grp2)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(300)
        root.addWidget(self.log, 1)
        note = QLabel('⚠ E-STOP 은 하드웨어 버튼이 유일한 확실한 정지 수단입니다.')
        note.setStyleSheet('color:#a33')
        root.addWidget(note)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(1000)

    def _msg(self, s):
        self.log.appendPlainText(time.strftime('[%H:%M:%S] ') + s)

    def _start(self, key, cmd):
        if self.pm.start(key, cmd):
            self._msg(f'{key} 실행')
        else:
            self._msg(f'{key} 기동 거부 — 동일 프로세스가 이미 실행 중(외부/잔존). '
                      f'정리 후 다시 시도')

    def _stop(self, key):
        self.pm.stop(key)
        self._msg(f'{key} 중지')

    def _start_all(self):
        # HIL 실험 규칙: 실행 전 노드 정리 — 잔존·고아 전량 소탕 후 순차 기동
        if QMessageBox.question(self, '전체 순차 실행',
                                'HIL 규칙에 따라 기존 노드를 전부 정리한 뒤 순차 실행합니다.\n'
                                '진행할까요?',
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self._msg('실행 전 정리 — 잔존 노드 전량 소탕')
        self.pm.stop_all()
        time.sleep(1.0)
        for key, _, cmd in STACK_ITEMS:
            if not self.pm.alive(key):
                self._start(key, cmd)
                time.sleep(2.0)
        self._msg('전체 순차 실행 완료')

    def _on_engaged(self, engaged):
        self.oneshot_btns['home'].setEnabled(engaged)
        self.oneshot_btns['disengage'].setEnabled(engaged)
        self.oneshot_btns['engage'].setEnabled(not engaged)

    def _kill_all(self):
        if QMessageBox.question(self, '전체 중지',
                                '전체 노드를 내립니다 (외부/잔존 포함 확실 종료).\n진행할까요?',
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self._msg('전체 중지 시작 — 3단 종료 + 잔존 소탕')
        self.pm.stop_all()
        self._msg('전체 중지 완료')

    def _oneshot(self, label, cmd, warn):
        if warn and QMessageBox.warning(self, label, warn,
                                        QMessageBox.Ok | QMessageBox.Cancel) != QMessageBox.Ok:
            return
        ok, out = run_oneshot(cmd)
        self._msg(f'{label}: {"성공" if ok else "실패"} — {out[:120]}')

    def _refresh(self):
        svc = subprocess.run(['systemctl', 'is-active', 'amr-can-relay.service'],
                             capture_output=True, text=True).stdout.strip()
        self.svc_lamp.setStyleSheet('color:%s; font-size:16px'
                                    % ('#1c7c39' if svc == 'active' else '#b3372f'))
        # 외부(CLI 등)에서 기동한 동일 노드도 실행 중으로 표시 — 전역 중복 검사와 같은 눈
        try:
            pslist = subprocess.run(['ps', '-eo', 'args'], capture_output=True,
                                    text=True).stdout
        except Exception:
            pslist = ''
        for key, lamp in self.lamps.items():
            alive = self.pm.alive(key)
            if not alive and pslist:
                pats = [ProcManager.marker(self.cmds[key])] \
                    + ProcManager.CHILD_PATTERNS.get(key, [])
                alive = any(p in pslist for p in pats)
            lamp.setStyleSheet('color:%s; font-size:16px'
                               % ('#1c7c39' if alive else '#999'))
            b = self.runbtns.get(key)
            if b is not None:
                b.setText('실행 중' if alive else '실행')
                b.setStyleSheet(STYLE_RUNNING if alive else STYLE_RUN)


class TrackGraph(QWidget):
    """노드 A↔B 고정 좌표계 안에서 현재 위치를 원으로 표시.

    좌표계는 노드 설정 시 고정된다: 가로 = A~B 구간(+여백), 세로 = 경로 기준 ±Y_HALF.
    표시는 경로선·노드 A/B·현재 위치 원·횡편차 숫자뿐 — 궤적·자동 스케일 없음.
    """

    Y_HALF = 0.25   # 경로 기준 세로 표시 반폭 (m) — 고정

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(180)
        self.nodes = None          # ((xa, ya), (xb, yb)) — 설정 후 고정
        self.names = ('A', 'B')
        self.pose = None           # (x, y)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(200)

    def set_nodes(self, xa, ya, xb, yb, names=None):
        self.nodes = ((xa, ya), (xb, yb))
        if names:
            self.names = names
        self.update()

    def set_pose(self, x, y):
        self.pose = (x, y)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor('#fafbfc'))
        ml, mr, mt, mb = 64, 16, 14, 26
        gw, gh = w - ml - mr, h - mt - mb
        if gw <= 0 or gh <= 0:
            return
        if self.nodes is None:
            p.setPen(QPen(QColor('#888')))
            txt = '노드 미설정 — 실험 시작(또는 현재 위치 수신) 시 A·B 좌표계 고정'
            if self.pose:
                txt += f'\n현재 위치 ({self.pose[0]:+.3f}, {self.pose[1]:+.3f})'
            p.drawText(self.rect(), Qt.AlignCenter, txt)
            return
        (xa, ya), (xb, yb) = self.nodes
        xlo, xhi = min(xa, xb) - 0.3, max(xa, xb) + 0.3
        yc = 0.5 * (ya + yb)
        ylo, yhi = yc - self.Y_HALF, yc + self.Y_HALF

        def px(x):
            return ml + gw * (x - xlo) / (xhi - xlo)

        def py(y):
            return mt + gh * (1 - (y - ylo) / (yhi - ylo))

        # 고정 y 눈금 5 cm — 경로 중심선 0 기준 상대 표기
        gy = yc - self.Y_HALF
        while gy <= yhi + 1e-9:
            rel = gy - yc
            p.setPen(QPen(QColor('#c9d4d2' if abs(rel) < 1e-9 else '#e3e8ec')))
            p.drawLine(ml, int(py(gy)), w - mr, int(py(gy)))
            p.setPen(QPen(QColor('#999')))
            p.drawText(4, int(py(gy)) + 4, f'{100*rel:+.0f}cm')
            gy += 0.05
        # 경로선 + 노드 (고정)
        p.setPen(QPen(QColor('#8fa5a2'), 2))
        p.drawLine(int(px(xa)), int(py(ya)), int(px(xb)), int(py(yb)))
        for (nx, ny), name, col in (((xa, ya), self.names[0], '#0d6a66'),
                                    ((xb, yb), self.names[1], '#a35a00')):
            p.setBrush(QColor(col))
            p.setPen(Qt.NoPen)
            p.drawEllipse(int(px(nx)) - 9, int(py(ny)) - 9, 18, 18)
            p.setPen(QPen(QColor('white')))
            p.drawText(int(px(nx)) - 4 * len(name), int(py(ny)) + 5, name)
        # 현재 위치 — AMR 사각형(차체 상징, 고정 픽셀 크기) + 중심점 + 횡편차
        if self.pose:
            x, y = self.pose
            cx = min(max(px(x), ml), w - mr)
            cy = min(max(py(y), mt), h - mb)
            p.setBrush(QColor(211, 51, 51, 60))
            p.setPen(QPen(QColor('#d33'), 2))
            p.drawRect(int(cx) - 16, int(cy) - 9, 32, 18)
            p.setBrush(QColor('#d33'))
            p.setPen(Qt.NoPen)
            p.drawEllipse(int(cx) - 3, int(cy) - 3, 6, 6)
            p.setPen(QPen(QColor('#333')))
            p.drawText(int(min(cx + 20, w - 190)), int(max(cy - 14, 16)),
                       f'({x:+.3f}, {y:+.3f}) · 횡 {1000*(y-yc):+.0f} mm')
        p.setPen(QPen(QColor('#777')))
        p.drawText(ml, h - 8,
                   f'{self.names[0]}({xa:+.2f},{ya:+.2f}) ~ {self.names[1]}({xb:+.2f},{yb:+.2f})'
                   f' 고정 좌표계 · 세로 ±{self.Y_HALF:g} m')


class PgvScatter(QWidget):
    """도착 시 PGV 계산 위치의 2차원 산포도 — 공차 3 mm 원과 회차 점."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(260, 220)
        self.pts = []              # (lap, x_mm, y_mm)

    def add(self, lap, x_mm, y_mm):
        self.pts.append((lap, x_mm, y_mm))
        self.update()

    def clear(self):
        self.pts = []
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor('#fafbfc'))
        cx, cy = w / 2, h / 2
        rng = 5.0
        if self.pts:
            rng = max(rng, *(max(abs(x), abs(y)) for _, x, y in self.pts))
        rng *= 1.15
        scale = min(w, h) / 2 / rng * 0.9

        def sx(v):
            return cx + v * scale

        def sy(v):
            return cy - v * scale

        # 격자 원(1 mm 간격)·공차 3 mm 원·축
        step = 1.0 if rng <= 8 else 5.0
        g = step
        while g <= rng:
            col = QColor('#c33') if abs(g - 3.0) < 1e-9 else QColor('#dde3e8')
            p.setPen(QPen(col, 1))
            p.setBrush(Qt.NoBrush)
            r = g * scale
            p.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))
            g += step
        p.setPen(QPen(QColor('#b9c0c7'), 1))
        p.drawLine(int(cx), 0, int(cx), h)
        p.drawLine(0, int(cy), w, int(cy))
        p.setPen(QPen(QColor('#777')))
        p.drawText(int(cx) + 4, 12, '+x 전방 (mm)')
        p.drawText(4, int(cy) - 4, '+y 좌')
        p.drawText(w - 78, int(cy) + 14, f'공차 3 mm')
        # 점 — 공차 3 mm 원 기준 판정색(안=초록·밖=빨강), 마지막 점은 테두리 강조
        for i, (lap, x, y) in enumerate(self.pts):
            last = i == len(self.pts) - 1
            ok = math.hypot(x, y) <= 3.0
            p.setBrush(QColor('#1c7c39' if ok else '#b3372f'))
            p.setPen(QPen(QColor('#222'), 2) if last else Qt.NoPen)
            r = 5 if last else 3
            p.drawEllipse(int(sx(x)) - r, int(sy(y)) - r, 2 * r, 2 * r)
            p.setPen(QPen(QColor('#555')))
            p.drawText(int(sx(x)) + 6, int(sy(y)) + 4, str(lap))


class TripTab(QWidget):
    """탭② — 위: 노드 간 실시간 위치 그래프 / 아래 왼쪽: 도착 PGV 산포, 오른쪽: 실험 제어."""

    def __init__(self, worker):
        super().__init__()
        self.worker = worker
        root = QVBoxLayout(self)

        grp_top = QGroupBox('실시간 로봇 위치 — 노드 A ↔ 노드 B')
        vt = QVBoxLayout(grp_top)
        self.track = TrackGraph()
        vt.addWidget(self.track)
        self.lbl_pose = QLabel('pose: -    PGV: -')
        vt.addWidget(self.lbl_pose)
        root.addWidget(grp_top, 1)

        grp_bot = QGroupBox('도착 정밀도 (PGV 계산 위치)')
        hb = QHBoxLayout(grp_bot)
        self.scatter = PgvScatter()
        hb.addWidget(self.scatter, 2)

        right = QVBoxLayout()
        form = QGridLayout()

        def spin(row, label, val, lo, hi, step, deci=2):
            form.addWidget(QLabel(label), row, 0)
            s = QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setSingleStep(step)
            s.setDecimals(deci)
            s.setValue(val)
            form.addWidget(s, row, 1)
            return s

        self.sp_speed = spin(0, '최대속도 m/s', DEFAULTS['speed'], 0.05, 1.2, 0.05)
        self.sp_accel = spin(1, '가감속 m/s²', DEFAULTS['accel'], 0.05, 0.5, 0.05)
        self.sp_dist = spin(2, '편도거리 m', DEFAULTS['dist'], 0.5, 12.0, 0.5, 1)
        form.addWidget(QLabel('왕복수'), 3, 0)
        self.sp_laps = QSpinBox()
        self.sp_laps.setRange(1, 50)
        self.sp_laps.setValue(DEFAULTS['laps'])
        form.addWidget(self.sp_laps, 3, 1)
        self.sp_gate = spin(4, '도킹 게이트 m', DEFAULTS['gate'], 0.1, 2.0, 0.05)
        self.sp_dockv = spin(5, '도킹속도 m/s', DEFAULTS['dock_speed'], 0.05, 0.8, 0.05)
        self.sp_pause = spin(6, '정지 대기 s', DEFAULTS['pause'], 0.0, 5.0, 0.5, 1)
        right.addLayout(form)

        self.b_teach = QPushButton('도킹 목표 티치 (현재 /feature_pose)')
        self.b_teach.setStyleSheet(ONESHOT_STYLES['home'])
        self.b_teach.clicked.connect(self._teach)
        right.addWidget(self.b_teach)
        self.lbl_teach = QLabel('도킹 목표: -')
        self.lbl_teach.setWordWrap(True)
        right.addWidget(self.lbl_teach)
        self._teach_timer = QTimer(self)
        self._teach_timer.timeout.connect(self._refresh_teach)
        self._teach_timer.start(1000)

        hbb = QHBoxLayout()
        self.b_run = QPushButton('실행')
        self.b_stop = QPushButton('중지')
        self.b_run.setStyleSheet(STYLE_RUN)
        self.b_stop.setStyleSheet(STYLE_STOP)
        self.b_run.clicked.connect(self._run)
        self.b_stop.clicked.connect(self._stop)
        hbb.addWidget(self.b_run)
        hbb.addWidget(self.b_stop)
        right.addLayout(hbb)
        self.lbl_msg = QLabel('대기')
        self.lbl_msg.setWordWrap(True)
        right.addWidget(self.lbl_msg)
        self.lbl_last = QLabel('도착 기록 없음')
        self.lbl_last.setWordWrap(True)
        right.addWidget(self.lbl_last)
        right.addStretch(1)
        hb.addLayout(right, 1)
        root.addWidget(grp_bot, 1)

        worker.sig_pose.connect(self._on_pose)
        worker.sig_pgv.connect(lambda s: self._set_status(pgv=s))
        # 좌표계는 smap 의 LocationMark 2점으로 고정(RViz 와 동일 기준).
        # 실험 시작점(sig_nodes)은 좌표계를 옮기지 않는다.
        lm = smap_location_marks()
        if lm:
            self.track.set_nodes(lm[0], lm[1], lm[2], lm[3], names=lm[4])
        worker.sig_arrival.connect(self._on_arrival)
        worker.sig_msg.connect(self.lbl_msg.setText)
        worker.sig_done.connect(self._on_done)
        self._pose_txt = '-'
        self._pgv_txt = '-'

    def _on_done(self, ok):
        self.b_run.setEnabled(True)
        self.b_run.setText('실행')
        self.b_run.setStyleSheet(STYLE_RUN)

    def _set_status(self, pose=None, pgv=None):
        if pose is not None:
            self._pose_txt = pose
        if pgv is not None:
            self._pgv_txt = pgv
        self.lbl_pose.setText(f'pose: {self._pose_txt}    PGV: {self._pgv_txt}')

    def _on_pose(self, x, y):
        self.track.set_pose(x, y)
        if self.track.nodes is None:
            # smap 미가용 시 대체: 현재 위치 기준 임시 좌표계(수신마다 갱신하지 않고
            # 프레임을 크게 벗어날 때만 재고정 — mcl 초기 표류 박제 방지)
            self.track.set_nodes(x, y, x + self.sp_dist.value(), y)
        elif self.track.names == ('A', 'B'):
            (xa, ya), (xb, yb) = self.track.nodes
            yc = 0.5 * (ya + yb)
            if (abs(y - yc) > 0.5 or x < min(xa, xb) - 1.0 or x > max(xa, xb) + 1.0):
                self.track.set_nodes(x, y, x + self.sp_dist.value(), y)
        self._set_status(pose=f'({x:+.3f}, {y:+.3f})')

    def _on_arrival(self, lap, x_mm, y_mm):
        self.scatter.add(lap, x_mm, y_mm)
        self.lbl_last.setText(f'최근 도착 {lap}회차: PGV ({x_mm:+.1f}, {y_mm:+.1f}) mm')

    def _run(self):
        self.scatter.clear()
        self.b_run.setEnabled(False)
        self.b_run.setText('실행 중')
        self.b_run.setStyleSheet(STYLE_RUNNING)
        self.lbl_msg.setText('실험 시작')
        self.worker.trip_req = (self.sp_dist.value(), self.sp_speed.value(),
                                self.sp_accel.value(), self.sp_laps.value(),
                                self.sp_gate.value(), self.sp_dockv.value(),
                                self.sp_pause.value())

    def _teach(self):
        self.worker.teach_req = True

    def _refresh_teach(self):
        t = self.worker.dock_target
        self.lbl_teach.setText(
            '도킹 목표: -' if t is None else
            f'도킹 목표: x {t[0]:+.4f} · y {t[1]:+.4f} m · yaw {t[2]:+.2f}°')

    def _stop(self):
        self.worker.cancel = True
        self.lbl_msg.setText('중지 요청 — 현재 구간 취소 중')


class WheelTab(QWidget):
    """탭③ — 바퀴 조향 방향 시각화 (2WS 인라인: 전륜·후륜 각각의 조향각).

    상면도: 차체 사각형 위·아래에 전륜/후륜을 조향각만큼 회전시켜 그린다.
    |각| < 1° 는 초록(직진), 그 외 주황. 각도 숫자 병기.
    """

    def __init__(self, worker):
        super().__init__()
        self.front = None
        self.rear = None
        worker.sig_wheels.connect(self._on_wheels)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(200)

    def _on_wheels(self, f, r):
        self.front, self.rear = f, r

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor('#fafbfc'))
        if self.front is None:
            p.setPen(QPen(QColor('#888')))
            p.drawText(self.rect(), Qt.AlignCenter,
                       '/joint_states 대기 — can_relay 상주 서비스 확인')
            return
        cx = w // 2
        body_h = min(h - 120, 420)
        body_w = body_h * 9 // 16
        top = (h - body_h) // 2
        # 차체 (전방 = 위)
        p.setPen(QPen(QColor('#5a6570'), 2))
        p.setBrush(QColor('#eef1f4'))
        p.drawRoundedRect(cx - body_w // 2, top, body_w, body_h, 10, 10)
        p.setPen(QPen(QColor('#999')))
        p.drawText(cx - 14, top - 8, '전방 ↑')
        # 바퀴 2개 (인라인: 차체 중심선 위·아래)
        for angle, ny, name in ((self.front, top + body_h // 5, '전륜'),
                                (self.rear, top + body_h * 4 // 5, '후륜')):
            ok = abs(angle) < 1.0
            col = QColor('#1c7c39') if ok else QColor('#a35a00')
            p.save()
            p.translate(cx, ny)
            p.rotate(-angle)   # +각 = 좌조향 → 화면 반시계
            p.setPen(QPen(col, 2))
            p.setBrush(col)
            p.drawRoundedRect(-9, -34, 18, 68, 6, 6)
            p.setPen(QPen(QColor('white'), 2))
            p.drawLine(0, -26, 0, 26)
            p.restore()
            p.setPen(QPen(col))
            p.drawText(cx + body_w // 2 + 16, ny + 5,
                       f'{name} {angle:+.2f}°' + ('  (직진)' if ok else ''))
        p.setPen(QPen(QColor('#777')))
        p.drawText(12, h - 10, '데이터: /joint_states (조향 실측각) · |각|<1° = 직진 판정')


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('왕복 주행 실기 테스트')
        self.resize(860, 640)
        self.pm = ProcManager()
        self.worker = RosWorker()
        self.worker.start()
        tabs = QTabWidget()
        tabs.addTab(StackTab(self.pm, self.worker), '① 패키지 구동')
        tabs.addTab(TripTab(self.worker), '② 왕복 실험')
        tabs.addTab(WheelTab(self.worker), '③ 바퀴 방향')
        self.setCentralWidget(tabs)

    def closeEvent(self, ev):
        if QMessageBox.question(self, '종료', 'UI 로 실행한 패키지도 함께 중지할까요?\n'
                                '(아니오 = 패키지는 그대로 두고 UI 만 종료)',
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.pm.stop_all()
        self.worker.requestInterruption()
        self.worker.wait(2000)
        ev.accept()


def cleanup_previous_ui():
    """기동 시 자기정리 — 기존 UI 인스턴스가 있으면 그 UI 와 관련 패키지를 모두 내린다.

    상주 can_relay(systemd)는 건드리지 않는다. HIL 규칙(실행 전 잔존 정리)의 기동판.
    """
    me = os.getpid()
    out = subprocess.run(['pgrep', '-f', 'drive_test_ui.py'],
                         capture_output=True, text=True).stdout.split()
    others = [int(pid) for pid in out if int(pid) != me]
    if not others:
        return
    for pid in others:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    time.sleep(1.0)
    for pid in others:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    # 이전 UI 의 스택 전량 정리 — INT(정상 종료) 우선, can_relay 계열은 목록에 없음
    markers = ({ProcManager.marker(cmd) for _, _, cmd in STACK_ITEMS}
               | set(EXTRA_KILL_MARKERS))
    for sig_name, wait_s in (('-INT', 3.0), ('-TERM', 2.0)):
        for mk in markers:
            subprocess.run(['pkill', sig_name, '-f', mk], capture_output=True)
        time.sleep(wait_s)
    for mk in markers:
        if subprocess.run(['pgrep', '-f', mk], capture_output=True).returncode == 0:
            subprocess.run(['pkill', '-9', '-f', mk], capture_output=True)


def main():
    cleanup_previous_ui()
    app = QApplication([])
    w = MainWindow()
    w.show()
    app.exec_()


if __name__ == '__main__':
    main()
