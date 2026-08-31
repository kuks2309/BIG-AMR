#!/usr/bin/env bash
# systemd 가 호출하는 래퍼 — ROS 환경을 갖춘 뒤 camera_manager 노드를 실행한다.
# (run_camera.sh 와 같은 이유: systemd 는 로그인 셸이 아니라 환경이 비어 있다.)
# -u(nounset) 금지 — ROS setup.bash 는 미정의 변수(AMENT_TRACE_SETUP_FILES 등)를
# 참조하는 nounset 비호환 스크립트라, -u 아래서 source 하면 즉사한다.
set -eo pipefail

REPO_ROOT="${REPO_ROOT:-/home/nvidia/Project/Ford-CATL-AMR/Big-AMR}"

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
# shellcheck disable=SC1091
source "${REPO_ROOT}/install/setup.bash"

export REPO_ROOT
export CAMERA_CONFIG="${CAMERA_CONFIG:-${REPO_ROOT}/config/camera/camera_common.yaml}"
exec ros2 run camera_manager manager_node
