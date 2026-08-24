#!/bin/bash
# 노드 간 주행 SIL — 공유 플랜트 스택(sil_crab_linear.launch.py) + spin 서버 + 경로 실행기.
# 무모터: 지령은 플랜트(translate_sim_odom)가 소비한다. 실기 지령 경로 접촉 없음.
REPO=/home/nvidia/Project/Ford-CATL-AMR/Big-AMR
OUT="$REPO/Log/waypoint_sil"
cd "$REPO" || exit 1
source /opt/ros/humble/setup.bash
source install/setup.bash 2>/dev/null
mkdir -p "$OUT"

cleanup() {
    pkill -f 'sil_crab_linear.launch.py' 2>/dev/null
    pkill -f 'translate_sim_odom_node' 2>/dev/null
    pkill -f 'sil_pose_adapter_node' 2>/dev/null
    pkill -f 'trnav_motion_mux_node' 2>/dev/null
    pkill -f 'trnav_motion_supervisor_node' 2>/dev/null
    pkill -f 'amr_safety_watchdog' 2>/dev/null
    pkill -f 'amr_crab_linear_node' 2>/dev/null
    pkill -f 'amr_spin_node' 2>/dev/null
    pkill -f 'topic pub /safety' 2>/dev/null
    sleep 1
}
trap cleanup EXIT

cleanup
ros2 launch trnav_2ws_action_server sil_crab_linear.launch.py > "$OUT/stack.log" 2>&1 &
sleep 6
ros2 run trnav_2ws_action_server amr_spin_node --ros-args \
    --params-file src/Control/Motion_Control/2WS/trnav_2ws_action_server/config/spin_params.yaml \
    > "$OUT/spin.log" 2>&1 &
sleep 4

for pat in translate_sim_odom_node sil_pose_adapter_node amr_crab_linear_node amr_spin_node; do
    if ! ps aux | grep "$pat" | grep -v grep > /dev/null; then
        echo "중단: $pat 없음 — $OUT/stack.log 확인"; exit 1
    fi
done

echo "── 경로 실행 (route_sil.yaml: 전방 4 m → 측방 2 m → 전진 2 m)"
timeout 300 python3 Tools/waypoint_nav/run_route.py \
    --route Tools/waypoint_nav/route_sil.yaml 2>&1 | tee "$OUT/route.log" | grep -E '\[.\/.\]|성공|실패|거부|없음'

# 플랜트 참값(= /rtabmap/localization_pose)으로 최종 도착 오차 확인
timeout 5 ros2 topic echo /rtabmap/localization_pose --once 2>/dev/null \
    | grep -A3 'position:' | head -4
