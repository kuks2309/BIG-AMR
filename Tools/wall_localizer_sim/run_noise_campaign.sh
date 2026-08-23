#!/bin/bash
# wall_localizer 잡음 정밀도 캠페인 — 지정한 라이다 거리 잡음 σ[mm]에서
# 기본 파라미터 1종(V1) + 3σ 스케일 파라미터 3종(V2 정지·V3 접근 주행·V4 벽 가림)을 잰다.
# 사용: run_noise_campaign.sh <sigma_mm>   (예: 30)
# 시험 토픽에 다른 발행자가 이미 있으면 측정이 오염되므로 시작하지 않는다.
SIGMA_MM=${1:?사용법: run_noise_campaign.sh <sigma_mm>}
REPO=/home/nvidia/Project/Ford-CATL-AMR/Big-AMR
OUT="$REPO/Log/wall_localizer_sim/sigma${SIGMA_MM}"
SIGMA=$(python3 -c "print(${SIGMA_MM}/1000.0)")
T3=$(python3 -c "print(3*${SIGMA_MM}/1000.0)")   # 거리 임계 3σ 스케일
cd "$REPO" || exit 1
source /opt/ros/humble/setup.bash
source install/setup.bash 2>/dev/null

NODE_PAT='wall_localizer_ros2/wall_localizer_node'
kill_nodes() {
    pkill -f "$NODE_PAT" 2>/dev/null
    for _ in 1 2 3 4 5; do
        [ "$(pgrep -cf "$NODE_PAT")" -eq 0 ] && return 0
        sleep 0.5
    done
    echo "중단: 측위 노드 잔류를 정리하지 못함" >&2
    exit 1
}

kill_nodes
if [ "$(ros2 topic info /wl_sim_scan -v 2>/dev/null | grep -c 'Node name')" -gt 0 ]; then
    echo "중단: /wl_sim_scan 에 기존 노드가 있음" >&2
    exit 1
fi
mkdir -p "$OUT"

run_one() {
    local name="$1"; shift
    ros2 run wall_localizer_ros2 wall_localizer_node --ros-args \
        --params-file src/Navigation/wall_localizer_ros2/config/wall_localizer.yaml \
        -p use_tf_extrinsic:=false -p laser_x_m:=0.3 \
        -r scan:=/wl_sim_scan "$@" \
        > "$OUT/${name}_node.log" 2>&1 &
    sleep 2
    if [ "$(pgrep -cf "$NODE_PAT")" -ne 1 ]; then
        echo "중단: ${name} 측위 노드 프로세스 수가 1이 아님" >&2
        kill_nodes; exit 1
    fi
    python3 Tools/wall_localizer_sim/sim_eval.py --scenario "$name" \
        --out-dir "$OUT" "${SIM_ARGS[@]}" | tail -1
    kill_nodes
}

TUNED=(-p split_dist_m:="$T3" -p merge_dist_m:="$T3" -p max_dist_residual_m:="$T3" -p refit_corridor_m:="$T3")

echo "=== V1 정지·σ=${SIGMA_MM}mm·기본 파라미터 ==="
SIM_ARGS=(--trajectory static --sigma "$SIGMA" --duration 15); run_one V1

echo "=== V2 정지·σ=${SIGMA_MM}mm·3σ 파라미터(임계 ${T3}m) ==="
SIM_ARGS=(--trajectory static --sigma "$SIGMA" --duration 30); run_one V2 "${TUNED[@]}"

echo "=== V3 접근 주행·σ=${SIGMA_MM}mm·3σ 파라미터 ==="
SIM_ARGS=(--trajectory approach --sigma "$SIGMA" --duration 15); run_one V3 "${TUNED[@]}"

echo "=== V4 정지·좌측 벽 가림·σ=${SIGMA_MM}mm·3σ 파라미터 ==="
SIM_ARGS=(--trajectory static --sigma "$SIGMA" --duration 15 --occlude-wall 1); run_one V4 "${TUNED[@]}"

echo "=== 종합 (σ=${SIGMA_MM}mm) ==="
python3 - "$OUT" <<'EOF'
import glob, json, sys
print(f"{'케이스':6} {'스캔':>5} {'해':>5} {'해율%':>6} {'xyRMSE(mm)':>11} {'xyP95(mm)':>10} {'xyMax(mm)':>10} {'yawRMSE(°)':>11} {'yawMax(°)':>10} {'OK':>5} {'DEG':>4} {'LOST':>5}")
for p in sorted(glob.glob(sys.argv[1] + "/*_summary.json")):
    s = json.load(open(p)); d = s.get("diag", {})
    print(f"{s['scenario']:6} {s['n_scans']:>5} {s['n_fix']:>5} {100*s['fix_rate']:>6.1f} "
          f"{1000*s.get('xy_rmse_m',0):>11.2f} {1000*s.get('xy_p95_m',0):>10.2f} "
          f"{1000*s.get('xy_max_m',0):>10.2f} {s.get('yaw_rmse_deg',0):>11.3f} "
          f"{s.get('yaw_max_deg',0):>10.3f} {d.get('OK',0):>5} {d.get('DEGRADED',0):>4} {d.get('LOST',0):>5}")
EOF
