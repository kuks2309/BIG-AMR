#!/bin/bash
# wall_localizer 시나리오 시뮬레이션 일괄 실행.
# 시나리오마다 측위 노드를 새로 띄워(추적 상태 초기화) sim_eval.py 로 평가한다.
# 시험 토픽에 다른 발행자가 이미 있으면 측정이 오염되므로 시작하지 않는다.
REPO=/home/nvidia/Project/Ford-CATL-AMR/Big-AMR
OUT="$REPO/Log/wall_localizer_sim"
cd "$REPO" || exit 1
source /opt/ros/humble/setup.bash
source install/setup.bash 2>/dev/null

# 노드 실행 파일 기준으로 잔류를 판정한다 — `ros2 run` 래퍼 PID 만 죽이면
# 실제 노드가 살아남아 /wall_pose 발행자가 누적되고 이후 측정이 전부 오염된다.
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
    local extra_node_args=("$@")
    ros2 run wall_localizer_ros2 wall_localizer_node --ros-args \
        --params-file src/Navigation/wall_localizer_ros2/config/wall_localizer.yaml \
        -p use_tf_extrinsic:=false -p laser_x_m:=0.3 \
        -r scan:=/wl_sim_scan "${extra_node_args[@]}" \
        > "$OUT/${name}_node.log" 2>&1 &
    sleep 2
    if [ "$(pgrep -cf "$NODE_PAT")" -ne 1 ]; then
        echo "중단: ${name} 측위 노드 프로세스 수가 1이 아님 ($(pgrep -cf "$NODE_PAT"))" >&2
        kill_nodes; exit 1
    fi
    python3 Tools/wall_localizer_sim/sim_eval.py --scenario "$name" \
        --out-dir "$OUT" "${SIM_ARGS[@]}" | tail -1
    kill_nodes
}

echo "=== S1 정지·무잡음 (기준선) ==="
SIM_ARGS=(--trajectory static --sigma 0.0 --duration 10); run_one S1

echo "=== S2 정지·σ=10mm ==="
SIM_ARGS=(--trajectory static --sigma 0.01 --duration 15); run_one S2

echo "=== S3 접근 주행·σ=10mm ==="
SIM_ARGS=(--trajectory approach --sigma 0.01 --duration 15); run_one S3

echo "=== S4 접근 주행·좌측 벽 가림·σ=10mm ==="
SIM_ARGS=(--trajectory approach --sigma 0.01 --duration 15 --occlude-wall 1); run_one S4

echo "=== S5 접근 주행·클러터·σ=10mm ==="
SIM_ARGS=(--trajectory approach --sigma 0.01 --duration 15 --clutter); run_one S5

echo "=== S6 초기 추정 오차 (0.15m·0.12m·4°)·σ=10mm ==="
SIM_ARGS=(--trajectory offset --sigma 0.01 --duration 10); run_one S6

echo "=== S7 정지·σ=20mm (기본 파라미터) ==="
SIM_ARGS=(--trajectory static --sigma 0.02 --duration 15); run_one S7

echo "=== S7T 정지·σ=20mm (임계를 잡음 3σ 로 조정) ==="
SIM_ARGS=(--trajectory static --sigma 0.02 --duration 15)
run_one S7T -p split_dist_m:=0.06 -p max_dist_residual_m:=0.05

echo "=== 종합 ==="
python3 - "$OUT" <<'EOF'
import glob, json, sys
rows = []
for p in sorted(glob.glob(sys.argv[1] + "/*_summary.json")):
    s = json.load(open(p))
    rows.append(s)
hdr = f"{'시나리오':8} {'스캔':>5} {'해':>5} {'해율%':>6} {'xyRMSE(mm)':>11} {'xyP95(mm)':>10} {'xyMax(mm)':>10} {'yawRMSE(°)':>11} {'OK':>5} {'DEG':>4} {'LOST':>5}"
print(hdr)
for s in rows:
    d = s.get("diag", {})
    print(f"{s['scenario']:8} {s['n_scans']:>5} {s['n_fix']:>5} {100*s['fix_rate']:>6.1f} "
          f"{1000*s.get('xy_rmse_m',0):>11.2f} {1000*s.get('xy_p95_m',0):>10.2f} "
          f"{1000*s.get('xy_max_m',0):>10.2f} {s.get('yaw_rmse_deg',0):>11.3f} "
          f"{d.get('OK',0):>5} {d.get('DEGRADED',0):>4} {d.get('LOST',0):>5}")
EOF
