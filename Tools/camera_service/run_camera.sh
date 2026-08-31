#!/usr/bin/env bash
# systemd 인스턴스가 호출하는 래퍼 — ROS 환경을 갖춘 뒤 카메라 1대를 실행한다.
#
#   run_camera.sh cam0
#
# systemd 는 로그인 셸이 아니라 환경이 비어 있으므로 여기서 명시적으로 source 한다.
# -u(nounset) 금지 — ROS setup.bash 는 미정의 변수(AMENT_TRACE_SETUP_FILES 등)를
# 참조하는 nounset 비호환 스크립트라, -u 아래서 source 하면 즉사한다.
set -eo pipefail

CAMERA="${1:?사용법: run_camera.sh <카메라이름>}"
REPO_ROOT="${REPO_ROOT:-/home/nvidia/Project/Ford-CATL-AMR/Big-AMR}"

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
# shellcheck disable=SC1091
source "${REPO_ROOT}/install/setup.bash"

export REPO_ROOT
exec python3 "${REPO_ROOT}/Tools/camera_service/exec_camera_node.py" "${CAMERA}"
