#!/usr/bin/env bash
# stop_sim.sh — 시뮬레이션 관련 프로세스를 전부 정리한다.
#
# Gazebo 는 gzserver 가 죽어도 포트(11345)나 gzclient 가 남아 다음 기동이
#   "Unable to start server[bind: Address already in use]"
# 로 실패하는 경우가 잦다. 노드는 `python3 <절대경로>` 로 떠서 이름만으로는
# 안 잡히므로 경로 패턴으로 함께 죽인다.
set -u

echo "[stop_sim] 종료 중..."

# 0) Close the terminal windows start_sim.sh opened. Each window wrote its own
#    shell PID here, so only those windows are closed — never the user's own.
PIDFILE="/tmp/trnav_2ws_sim_windows.pids"
if [ -f "$PIDFILE" ]; then
    while read -r pid; do
        [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null
    done < "$PIDFILE"
    rm -f "$PIDFILE"
fi

# 1) launch 및 Gazebo
pkill -9 -f 'ros2 launch trnav_2ws_gazebo'  2>/dev/null
pkill -9 -f 'gzserver'                      2>/dev/null
pkill -9 -f 'gzclient'                      2>/dev/null

# 2) 시뮬 노드 (python3 절대경로로 실행됨)
#
# Match the package's SCRIPT DIRECTORY, not individual filenames. Listing names
# one by one is what failed: fleet_wheel_bridge.py was added and never added
# here, so every launch left its bridge behind. Measured 2026-08-07 — six
# bridges alive at once, four of them publishing to /amr1's steer and drive
# command topics simultaneously at 100 Hz. The robot was driven 9 m out of its
# parking bay before the MES had even started, then thrashed between +0.9 and
# -0.9 rad/s because four nodes were commanding different wheel angles. It
# looked exactly like a navigation bug and was not one.
#
# This is the same trap fleet.launch.py already documents: "ten leftover
# wheel_cmd_bridge nodes per robot were publishing wheel commands the whole
# time". A directory match cannot go stale when a new script is added.
#
# --older 1 excludes this script itself. The directory pattern matches THIS
# file's own path whenever the script is invoked by a path that contains it
# (`bash src/Sim/trnav_2ws_gazebo/scripts/stop_sim.sh`), so it killed itself
# here and steps 3 and 4 below never ran — leaving robot_state_publisher alive
# and the ros2 daemon holding a stale cache. Measured 2026-08-18: five
# publishers from earlier runs, the oldest 1h35m, survived every teardown.
# `--older 1` only matches processes at least a second old; this script reaches
# this line immediately, so it can never match itself.
pkill -9 --older 1 -f 'trnav_2ws_gazebo/(lib|scripts)/'  2>/dev/null
pkill -9 -f 'gazebo_ros/spawn_entity.py'           2>/dev/null

# The MES. fleet.launch.py starts it, so a teardown that leaves it running
# means the next launch has two — and csm/README.md is emphatic about what
# that looks like: both publish /amrN/cmd_vel and the robot judders on the
# spot without going anywhere, exactly like a navigation bug. Match the
# installed executable path, because it runs as `python3 <abs path>`.
pkill -9 --older 1 -f 'lib/csm/sim_node'           2>/dev/null

# 3) 스포너·상태발행 (이전 실행분이 남아 새 controller_manager 를 가로채면
#    "already loaded" 경합이 난다)
pkill -9 -f 'controller_manager/spawner' 2>/dev/null
pkill -9 -f 'ros2 run controller_manager spawner' 2>/dev/null
pkill -9 -f 'robot_state_publisher'      2>/dev/null

# 4) ros2 CLI 데몬 (죽은 노드 캐시를 물고 있으면 topic list 가 오작동)
ros2 daemon stop >/dev/null 2>&1

sleep 2

left=$(pgrep --older 1 -f 'gzserver|gzclient|trnav_2ws_gazebo/wheel_|lib/csm/sim_node' | wc -l)
if [ "$left" -eq 0 ]; then
    echo "[stop_sim] 정리 완료 — 잔여 프로세스 없음"
else
    echo "[stop_sim] ⚠ 잔여 프로세스 $left 개:"
    pgrep -af --older 1 'gzserver|gzclient|trnav_2ws_gazebo/wheel_|lib/csm/sim_node'
fi
