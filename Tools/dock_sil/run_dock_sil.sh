#!/bin/bash
# 도킹 폐루프 SIL — 플랜트 → wall_localizer → dock 서버 전 체인.
# 전 토픽·서비스를 /dock_sil/* 로 리맵해 실기 체인과 격리한다.
# 사용: run_dock_sil.sh [시나리오]   (기본: D1 D2 순차)
REPO=/home/nvidia/Project/Ford-CATL-AMR/Big-AMR
OUT="$REPO/Log/dock_sil"
cd "$REPO" || exit 1
source /opt/ros/humble/setup.bash
source install/setup.bash 2>/dev/null
mkdir -p "$OUT"

PATS='dock_sil_plant.py|wall_localizer_ros2/wall_localizer_node|dock_approach_action_server'
cleanup() { pkill -f 'dock_sil_plant.py' 2>/dev/null; pkill -f 'wall_localizer_ros2/wall_localizer_node' 2>/dev/null; pkill -f 'dock_approach_action_server' 2>/dev/null; sleep 1; }
count_procs() { ps aux | grep -E "$PATS" | grep -v grep | wc -l; }

run_case() {
    local name="$1" x0="$2" y0="$3" yaw0="$4" gx="$5" gy="$6" gyaw="$7"
    cleanup
    if [ "$(count_procs)" -ne 0 ]; then echo "중단: 잔류 프로세스"; exit 1; fi

    python3 Tools/dock_sil/dock_sil_plant.py --x0 "$x0" --y0 "$y0" --yaw0-deg "$yaw0" \
        --truth-log "$OUT/${name}_truth.jsonl" > "$OUT/${name}_plant.log" 2>&1 &
    # 초기 추정 = 시나리오 시작 자세(실운용에선 mcl2d/접근 설정이 공급 — 게이트 0.3 m 안)
    ros2 run wall_localizer_ros2 wall_localizer_node --ros-args \
        --params-file Tools/dock_sil/walls_sil.yaml \
        -p initial_x_m:="$x0" -p initial_y_m:="$y0" -p initial_yaw_deg:="$yaw0" \
        -r scan:=/dock_sil/scan -r wall_pose:=/dock_sil/wall_pose \
        -r wall_localizer/diagnostics:=/dock_sil/diag > "$OUT/${name}_wall.log" 2>&1 &
    ros2 run trnav_2ws_dock_ros dock_approach_action_server --ros-args \
        --params-file src/Control/Motion_Control/2WS/trnav_2ws_dock_ros/config/dock_approach_params.yaml \
        -r /wall_pose:=/dock_sil/wall_pose \
        -r /motion/wheel_cmd/dock:=/dock_sil/wheel_cmd \
        -r /select_motion_source:=/dock_sil/select_motion_source \
        > "$OUT/${name}_server.log" 2>&1 &
    sleep 4
    # ros2 run 래퍼도 패턴에 걸리므로 수가 아니라 **구성요소별 존재**로 판정한다
    for pat in 'dock_sil_plant.py' 'wall_localizer_node' 'dock_approach_action_server'; do
        if ! ps aux | grep "$pat" | grep -v grep > /dev/null; then
            echo "중단: ${name} 기동 실패 — $pat 없음"; cleanup; exit 1
        fi
    done

    echo "── ${name}: 시작 ($x0, $y0, $yaw0°) → 목표 ($gx, $gy, $gyaw°)"
    timeout 90 ros2 action send_goal /amr_motion_dock_approach \
        trnav_2ws_interfaces/action/AMRMotionDockApproach \
        "{target_x_m: $gx, target_y_m: $gy, target_yaw_deg: $gyaw, approach_axis_deg: 0.0, \
          max_speed_mps: 0.15, tol_d_mm: 3.0, tol_lat_mm: 3.0, tol_yaw_deg: 0.5, timeout_s: 80.0}" \
        > "$OUT/${name}_goal.log" 2>&1
    grep -E 'success|stop_reason|final_' "$OUT/${name}_goal.log" | head -6
    cleanup
    python3 - "$OUT/${name}_truth.jsonl" "$gx" "$gy" "$gyaw" <<'EOF'
import json, math, sys
lines = [json.loads(l) for l in open(sys.argv[1])]
gx, gy, gyaw = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
f = lines[-1]
dy = f["yaw_deg"] - gyaw
dy = (dy + 180.0) % 360.0 - 180.0
print(f"   참값 최종: ({f['x']:.4f}, {f['y']:.4f}, {f['yaw_deg']:.2f}°) → "
      f"참오차 d={1000*(f['x']-gx):+.1f}mm lat={1000*(f['y']-gy):+.1f}mm yaw={dy:+.2f}°")
EOF
}

case "${1:-all}" in
  D1) run_case D1 0.4 0.10 2.0 1.5 0.0 0.0 ;;
  D2) run_case D2 0.4 0.35 0.0 1.5 0.0 0.0 ;;
  all) run_case D1 0.4 0.10 2.0 1.5 0.0 0.0
       run_case D2 0.4 0.35 0.0 1.5 0.0 0.0 ;;
esac
cleanup
