# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""AMR VisionGuard entry point: wires the ROS2 subscriber to the PyQt5 GUI.

rclpy spins on a background thread; the Qt event loop owns the main thread.
Frames cross the boundary through a bounded latest-frame store drained by a GUI
timer (see main_window.LatestFrameStore).
"""

import os
import signal
import sys

import rclpy
from PyQt5.QtWidgets import QApplication

from .main_window import LatestFrameStore, MainWindow
from .ros_worker import RosImageWorker, RosSpinThread

# pip 설치본 opencv-python 은 import 시 QT_QPA_PLATFORM_PLUGIN_PATH 를 자기 번들
# 경로로 덮어쓴다. 그 libqxcb.so 는 cv2 자체 Qt 에 링크돼 시스템 PyQt5 와 호환되지
# 않아 플랫폼 플러그인 초기화가 실패한다(프로세스 abort). ros_worker 가 cv2 를
# import 하므로 여기서 제거해 PyQt5 기본 플러그인 경로(xcb)로 되돌린다.
# 외부 환경변수 지정으로는 못 고친다 — cv2 가 import 시점에 다시 덮어쓴다.
os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)


def main(args=None):
    rclpy.init(args=args)

    app = QApplication(sys.argv)
    # Let Ctrl+C in the terminal terminate the Qt loop.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    frame_store = LatestFrameStore()
    worker = RosImageWorker(frame_store)

    initial_layout = worker.layout or ""
    # 노드 로거를 넘겨 표시 FPS 를 주기적으로 남긴다(장시간 내구 시 정지 구간 식별).
    window = MainWindow(
        worker.camera_topics, initial_layout, frame_store, logger=worker.get_logger()
    )
    window.show()

    spin_thread = RosSpinThread(worker)
    spin_thread.start()

    try:
        exit_code = app.exec_()
    finally:
        spin_thread.stop()
        spin_thread.join(timeout=2.0)
        # Only tear the node down once the executor has actually stopped, else
        # destroy_node() can race a live spin() into a use-after-free in rclpy.
        if not spin_thread.is_alive():
            worker.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
