#!/usr/bin/env python3
"""카메라 1대의 퍼블리셔 노드를 실행한다(systemd 인스턴스용 진입점).

**장치가 없으면 비정상 종료한다.** 이것이 복구 설계의 핵심이다 — systemd 가
`Restart=always` 로 재시도하므로, 카메라를 뽑았다 꽂거나 부팅 직후 열거가 늦어도
그 카메라만 알아서 다시 붙는다. 다른 카메라 서비스에는 영향이 없다.

  python3 exec_camera_node.py cam0

종료 코드:
  0   노드가 정상 종료(수동 중지)
  2   로스터에 없는 카메라 이름 — 설정 오류이므로 재시도해도 소용없다
  3   장치 심링크 부재 — 재시도 대상
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from camera_params import (camera_params, default_config_path,  # noqa: E402
                           load_roster, ros_run_argv)

EXIT_BAD_CAMERA = 2
EXIT_NO_DEVICE = 3
DEFAULT_REPO_ROOT = os.path.dirname(os.path.dirname(HERE))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"사용법: {argv[0]} <카메라이름>", file=sys.stderr)
        return EXIT_BAD_CAMERA
    name = argv[1]
    repo_root = os.environ.get("REPO_ROOT", DEFAULT_REPO_ROOT)
    config_path = os.environ.get("CAMERA_CONFIG", default_config_path(repo_root))

    try:
        config = load_roster(config_path)
        params = camera_params(config, name)
    except (OSError, ValueError, KeyError) as exc:
        print(f"[{name}] 설정 오류: {exc}", file=sys.stderr)
        return EXIT_BAD_CAMERA

    device = params["video_device"]
    if not os.path.exists(device):
        # 존재하지 않는 장치로 노드를 띄우면 노드는 살아있는 채 프레임 0 이 된다
        # (usb_cam_publisher_node.cpp 캡처 루프에 재오픈 경로가 없다). 그 상태를
        # 만들지 않고 즉시 죽어서 systemd 재시도에 맡긴다.
        print(f"[{name}] 장치 없음: {device} — 재시도 대기", file=sys.stderr)
        return EXIT_NO_DEVICE

    argv_run = ros_run_argv(name, params)
    print(f"[{name}] exec: {' '.join(argv_run)}", flush=True)
    os.execvp(argv_run[0], argv_run)        # 성공 시 반환하지 않는다
    return 1                                 # execvp 실패 시에만 도달


if __name__ == "__main__":
    sys.exit(main(sys.argv))
