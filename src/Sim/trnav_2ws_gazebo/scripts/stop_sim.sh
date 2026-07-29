#!/usr/bin/env bash
# stop_sim.sh — 시뮬레이션 관련 프로세스를 전부 정리한다.
#
# Gazebo 는 gzserver 가 죽어도 포트(11345)나 gzclient 가 남아 다음 기동이
#   "Unable to start server[bind: Address already in use]"
# 로 실패하는 경우가 잦다. 노드는 `python3 <절대경로>` 로 떠서 이름만으로는
# 안 잡히므로 경로 패턴으로 함께 죽인다.
set -u

echo "[stop_sim] 종료 중..."

# 1) launch 및 Gazebo
pkill -9 -f 'ros2 launch trnav_2ws_gazebo'  2>/dev/null
pkill -9 -f 'gzserver'                      2>/dev/null
pkill -9 -f 'gzclient'                      2>/dev/null

# 2) 시뮬 노드 (python3 절대경로로 실행됨)
pkill -9 -f 'trnav_2ws_gazebo/wheel_cmd_bridge.py' 2>/dev/null
pkill -9 -f 'trnav_2ws_gazebo/wheel_odometry.py'   2>/dev/null
pkill -9 -f 'gazebo_ros/spawn_entity.py'           2>/dev/null

# 3) 스포너·상태발행 (이전 실행분이 남아 새 controller_manager 를 가로채면
#    "already loaded" 경합이 난다)
pkill -9 -f 'controller_manager/spawner' 2>/dev/null
pkill -9 -f 'ros2 run controller_manager spawner' 2>/dev/null
pkill -9 -f 'robot_state_publisher'      2>/dev/null

# 4) ros2 CLI 데몬 (죽은 노드 캐시를 물고 있으면 topic list 가 오작동)
ros2 daemon stop >/dev/null 2>&1

sleep 2

left=$(pgrep -f 'gzserver|gzclient|trnav_2ws_gazebo/wheel_' | wc -l)
if [ "$left" -eq 0 ]; then
    echo "[stop_sim] 정리 완료 — 잔여 프로세스 없음"
else
    echo "[stop_sim] ⚠ 잔여 프로세스 $left 개:"
    pgrep -af 'gzserver|gzclient|trnav_2ws_gazebo/wheel_'
fi
