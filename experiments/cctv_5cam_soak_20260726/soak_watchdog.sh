#!/bin/bash
# CCTV 5-camera 12h endurance watchdog (log-based, zero-interference).
#
# 실행 중인 usb_cam_publisher 5대(cam0..cam4)를 재시작 없이 감시한다.
# publisher 는 카메라당 5초마다 "[camN] capture FPS: X (grab_failures=Y)" 를
# 로그에 남긴다. 이 로그만 파싱하므로 추가 구독자(부하)나 ros2 호출이 없다.
#
# 감지 항목:
#   (1) 스톨/크래시 — INTERVAL 동안 해당 카메라의 새 capture 로그가 0줄
#   (2) grab_failures 증가 — V4L2 grab 실패(순간 끊김)
#   (3) capture FPS 급락 — FPS_MIN 미만
#
# 사용: nohup soak_watchdog.sh <SOAK_DIR> <PUBLISHER_LOG> [DURATION_S] [INTERVAL] &
set -u

SOAK_DIR="${1:?SOAK_DIR required}"
PUBLOG="${2:?PUBLISHER_LOG required}"
DURATION_S="${3:-43200}"      # 기본 12h
INTERVAL="${4:-60}"           # 샘플 주기(초)
FPS_MIN=20.0                  # capture FPS 이 미만이면 알림(정상 ~29.7)
CAMS=(cam0 cam1 cam2 cam3 cam4)

TL="$SOAK_DIR/soak_timeline.csv"
AL="$SOAK_DIR/soak_alerts.log"
SUM="$SOAK_DIR/soak_summary.txt"

last_fps() { grep "\[$1\] capture FPS" "$PUBLOG" 2>/dev/null | tail -1 \
  | grep -oE 'FPS: [0-9.]+' | grep -oE '[0-9.]+'; }
last_gf()  { grep "\[$1\] capture FPS" "$PUBLOG" 2>/dev/null | tail -1 \
  | grep -oE 'grab_failures=[0-9]+' | grep -oE '[0-9]+'; }
line_count() { grep -c "\[$1\] capture FPS" "$PUBLOG" 2>/dev/null || echo 0; }

START=$(date +%s)
echo "timestamp,elapsed_s,cam0_fps,cam1_fps,cam2_fps,cam3_fps,cam4_fps,cam0_gf,cam1_gf,cam2_gf,cam3_gf,cam4_gf,new_alerts" > "$TL"
: > "$AL"
echo "[$(date '+%F %T')] SOAK START — 5-cam CCTV endurance, duration=${DURATION_S}s interval=${INTERVAL}s publog=$PUBLOG" | tee -a "$AL"

declare -A PREV_GF PREV_CNT MAXGF MINFPS STALL_CNT LOWFPS_CNT GFINC_CNT
for c in "${CAMS[@]}"; do
  PREV_GF[$c]=$(last_gf "$c"); [ -z "${PREV_GF[$c]}" ] && PREV_GF[$c]=0
  PREV_CNT[$c]=$(line_count "$c")
  MAXGF[$c]=${PREV_GF[$c]}; MINFPS[$c]=999; STALL_CNT[$c]=0; LOWFPS_CNT[$c]=0; GFINC_CNT[$c]=0
done
TOTAL_ALERTS=0; SAMPLES=0
sleep "$INTERVAL"

while :; do
  NOW=$(date +%s); ELAPSED=$((NOW-START))
  [ "$ELAPSED" -ge "$DURATION_S" ] && break
  SAMPLES=$((SAMPLES+1))
  ROW="$(date '+%F %T'),$ELAPSED"; GFROW=""; ATHIS=0

  for c in "${CAMS[@]}"; do
    fps=$(last_fps "$c"); gf=$(last_gf "$c"); cnt=$(line_count "$c")
    [ -z "$gf" ] && gf=${PREV_GF[$c]}
    ROW="$ROW,${fps:-NA}"; GFROW="$GFROW,$gf"

    # (1) 스톨: 새 capture 로그가 없음
    if [ "$cnt" -le "${PREV_CNT[$c]}" ]; then
      echo "[$(date '+%F %T')] ALERT $c: STALL — no new capture log in ${INTERVAL}s (crash/disconnect?) elapsed=${ELAPSED}s" | tee -a "$AL"
      STALL_CNT[$c]=$(( ${STALL_CNT[$c]} + 1 )); ATHIS=$((ATHIS+1))
    else
      # (3) 저FPS
      if [ -n "$fps" ]; then
        low=$(awk -v v="$fps" -v m="$FPS_MIN" 'BEGIN{print (v+0<m+0)?1:0}')
        if [ "$low" = "1" ]; then
          echo "[$(date '+%F %T')] ALERT $c: LOW capture FPS ${fps} (<${FPS_MIN}) elapsed=${ELAPSED}s" | tee -a "$AL"
          LOWFPS_CNT[$c]=$(( ${LOWFPS_CNT[$c]} + 1 )); ATHIS=$((ATHIS+1))
        fi
        awk -v v="$fps" -v m="${MINFPS[$c]}" 'BEGIN{exit !(v+0<m+0)}' && MINFPS[$c]=$fps
      fi
    fi
    # (2) grab_failures 증가
    if [ "${gf:-0}" -gt "${PREV_GF[$c]}" ] 2>/dev/null; then
      echo "[$(date '+%F %T')] ALERT $c: grab_failures ${PREV_GF[$c]} -> ${gf} elapsed=${ELAPSED}s" | tee -a "$AL"
      GFINC_CNT[$c]=$(( ${GFINC_CNT[$c]} + 1 )); ATHIS=$((ATHIS+1))
    fi
    [ "${gf:-0}" -gt "${MAXGF[$c]}" ] 2>/dev/null && MAXGF[$c]=$gf
    PREV_GF[$c]=$gf; PREV_CNT[$c]=$cnt
  done

  TOTAL_ALERTS=$((TOTAL_ALERTS+ATHIS))
  echo "${ROW}${GFROW},${ATHIS}" >> "$TL"

  {
    echo "CCTV 5-cam soak — 진행중"
    echo "start=$(date -d @$START '+%F %T')  now=$(date '+%F %T')  elapsed=${ELAPSED}s / ${DURATION_S}s"
    echo "samples=$SAMPLES  total_alerts=$TOTAL_ALERTS"
    for c in "${CAMS[@]}"; do
      printf "  %s: min_fps=%s max_grab_failures=%s stall=%s lowfps=%s gf_inc=%s\n" \
        "$c" "${MINFPS[$c]}" "${MAXGF[$c]}" "${STALL_CNT[$c]}" "${LOWFPS_CNT[$c]}" "${GFINC_CNT[$c]}"
    done
  } > "$SUM"

  SPENT=$(( $(date +%s) - NOW )); SLEEP=$(( INTERVAL - SPENT )); [ "$SLEEP" -lt 5 ] && SLEEP=5
  sleep "$SLEEP"
done

echo "[$(date '+%F %T')] SOAK END — elapsed=$(( $(date +%s)-START ))s samples=$SAMPLES total_alerts=$TOTAL_ALERTS" | tee -a "$AL"
{
  echo "==== CCTV 5-cam 12h SOAK 최종 요약 ===="
  echo "start=$(date -d @$START '+%F %T')  end=$(date '+%F %T')"
  echo "duration=$(( $(date +%s)-START ))s  samples=$SAMPLES  total_alerts=$TOTAL_ALERTS"
  echo ""
  for c in "${CAMS[@]}"; do
    printf "  %s: min_fps=%s max_grab_failures=%s stall_events=%s lowfps_events=%s gf_inc_events=%s\n" \
      "$c" "${MINFPS[$c]}" "${MAXGF[$c]}" "${STALL_CNT[$c]}" "${LOWFPS_CNT[$c]}" "${GFINC_CNT[$c]}"
  done
  echo ""
  if [ "$TOTAL_ALERTS" -eq 0 ]; then
    echo "판정: PASS — 12시간 동안 카메라 중단/드랍/실패 증가 없음"
  else
    echo "판정: 검토필요 — 알림 ${TOTAL_ALERTS}건 (soak_alerts.log 확인)"
  fi
} | tee "$SUM"
