#!/usr/bin/env bash
# Seer 파라미터를 **실기와 원본 하드 양쪽에서** 조회해 나란히 찍는다.
#
# 왜 필요한가 — Seer 의 동작 상수 다수(포트 동시연결 한도 포함)는 문서 판본이 정하는 값이 아니라
#   로봇의 **런타임 파라미터**다(변경 가능, `advanced` 표시). 따라서 매뉴얼·벤더 문의로는 확정할 수
#   없고, 두 원자료에서 직접 읽어야 한다: ① 실기 API 1400 ② amap-server 의 63G 원본 하드
#   `robot.param`(SQLite). 두 값이 어긋나면 그 자체가 신호다(하드 이미지 ≠ 현재 로봇 설정).
#
# 실기 조회는 `seer_tcp_ip` 의 C++ 실행파일이 한다 — 저장소에서 Seer 와 TCP 로 말하는 유일한 지점.
#
# 사용:
#   seer_param.sh                      # 포트 동시연결 한도 6종 (기본 세트)
#   seer_param.sh MaxAcc               # 이름 조각으로 검색 (원본 하드 전 플러그인 대상)
#   seer_param.sh MoveFactory MaxAcc   # 플러그인·파라미터 지정 → 실기·하드 동시 조회
#
# 환경변수: SEER_IP(기본 192.168.44.82) · AMAP_* 는 amap_server.sh 가 해석
# 인벤토리·경위: docs/code_review/seer_re/ 의 최신 항목
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
SEER_IP="${SEER_IP:-192.168.44.82}"
AMAP="$HERE/amap_server.sh"
DRIVE_PARAMS="/media/amap/6ab6980d-f090-4387-8753-a2251e75651d/usr/local/etc/.SeerRobotics/rbk/resources/params"

# 기본 세트 — 포트별 동시연결 한도(NetProtocol 플러그인)
DEFAULT_PAIRS=(
  "NetProtocol RobotStatusAPITCPServerMaxConnections 19204_Status"
  "NetProtocol RobotControlAPITCPServerMaxConnections 19205_Control"
  "NetProtocol RobotTaskAPITCPServerMaxConnections 19206_Task"
  "NetProtocol RobotConfigAPITCPServerMaxConnections 19207_Config"
  "NetProtocol RobotOtherAPITCPServerMaxConnections 19210_Other"
  "NetProtocol RobotPushTCPServerMaxConnections 19301_Push"
)

# seer_tcp_ip 의 seer_param 실행파일을 찾는다 — 설치본 우선, 없으면 빌드 트리.
find_cli() {
  if command -v ros2 >/dev/null 2>&1 && ros2 pkg prefix seer_tcp_ip >/dev/null 2>&1; then
    local p; p="$(ros2 pkg prefix seer_tcp_ip)/lib/seer_tcp_ip/seer_param"
    [ -x "$p" ] && { echo "$p"; return 0; }
  fi
  local b="$REPO/install/seer_tcp_ip/lib/seer_tcp_ip/seer_param"
  [ -x "$b" ] && { echo "$b"; return 0; }
  b="$REPO/build/seer_tcp_ip/seer_param"
  [ -x "$b" ] && { echo "$b"; return 0; }
  return 1
}

live_query() {  # $1=plugin $2=param  (인자 없으면 기본 세트)
  local cli
  if ! cli="$(find_cli)"; then
    echo "(실기 조회 생략 — seer_tcp_ip 미빌드. colcon build --packages-select seer_tcp_ip)"
    return 0
  fi
  SEER_IP="$SEER_IP" "$cli" "$@" 2>&1 || true
}

drive_query() {  # $1=plugin(또는 --grep) $2=param(또는 조각)
  if [ ! -x "$AMAP" ]; then
    echo "(원본 하드 조회 생략 — $AMAP 없음)"
    return 0
  fi
  AMAP_TIMEOUT="${AMAP_TIMEOUT:-240}" "$AMAP" ssh "
    mkdir -p /tmp/pcopy && cp '$DRIVE_PARAMS/robot.param' /tmp/pcopy/ 2>/dev/null || exit 0
    PLUGIN='$1' PARAM='$2' python3 - <<'PY'
import os, sqlite3
plugin, param = os.environ['PLUGIN'], os.environ['PARAM']
con = sqlite3.connect('file:/tmp/pcopy/robot.param?mode=ro', uri=True)
tabs = [r[0] for r in con.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")]
if plugin == '--grep':
    for t in tabs:
        for k, ty, v, m in con.execute('SELECT Key,Type,Value,Mutable FROM %s' % t):
            if param.lower() in k.lower():
                print('  %s.%s = %s  (type=%s mutable=%s)' % (t, k, v, ty, m))
elif plugin not in tabs:
    print('  (플러그인 %s 테이블 없음)' % plugin)
else:
    rows = [r for r in con.execute('SELECT Key,Value,Mutable FROM %s' % plugin) if r[0] == param]
    print('  value=%s mutable=%s' % (rows[0][1], rows[0][2]) if rows else '  (항목 없음)')
con.close()
PY
  "
}

if [ $# -eq 0 ]; then
  echo "=== 실기 ==="
  live_query
  echo
  echo "=== 원본 하드 ==="
  for row in "${DEFAULT_PAIRS[@]}"; do
    read -r plugin param label <<<"$row"
    printf '  %-14s %-46s %s\n' "$label" "$param" "$(drive_query "$plugin" "$param" | sed 's/^ *//')"
  done
elif [ $# -eq 1 ]; then
  echo "=== 원본 하드 robot.param 에서 '$1' 검색 (전 플러그인) ==="
  drive_query --grep "$1"
  echo
  echo "정확한 플러그인·이름을 알면 실기도 조회한다:  $0 <플러그인> <파라미터>"
else
  printf '[%s.%s]\n' "$1" "$2"
  printf '  실기      : %s\n' "$(live_query "$1" "$2" | sed 's/^ *//')"
  printf '  원본 하드 : %s\n' "$(drive_query "$1" "$2" | sed 's/^ *//')"
fi
