#!/usr/bin/env bash
# Seer 파라미터를 **실기와 원본 하드 양쪽에서** 조회해 나란히 찍는다.
#
# 왜 필요한가 — Seer 의 동작 상수 다수(포트 동시연결 한도 포함)는 문서 판본이 정하는 값이 아니라
#   로봇의 **런타임 파라미터**다(변경 가능, `advanced` 표시). 따라서 매뉴얼·벤더 문의로는 확정할 수
#   없고, 두 원자료에서 직접 읽어야 한다: ① 실기 API 1400 ② amap-server 의 63G 원본 하드
#   `robot.param`(SQLite). 두 값이 어긋나면 그 자체가 신호다(하드 이미지 ≠ 현재 로봇 설정).
#
# 사용:
#   seer_param.sh                      # 포트 동시연결 한도 6종 (기본 세트)
#   seer_param.sh MaxAcc               # 이름 조각으로 검색 (원본 하드 전 플러그인 대상)
#   seer_param.sh MoveFactory MaxAcc   # 플러그인·파라미터 지정 → 실기 1400 정확 조회
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

live_query() {  # $1=plugin $2=param
  PYTHONPATH="$REPO/src/Comm/seer_tcp_ip:${PYTHONPATH:-}" \
  SEER_IP="$SEER_IP" PLUGIN="$1" PARAM="$2" python3 - <<'PY'
import os, sys
try:
    from seer_tcp_ip import SeerApi
except ImportError as e:
    print(f"(라이브러리 import 실패: {e})"); sys.exit(0)
plugin, param = os.environ["PLUGIN"], os.environ["PARAM"]
try:
    with SeerApi(os.environ["SEER_IP"], timeout=4.0) as c:
        r = c.get_param(plugin, param)
except Exception as e:
    print(f"(실기 조회 실패: {type(e).__name__}: {e})"); sys.exit(0)
d = r.get(plugin, {}).get(param)
if d is None:
    print("(응답에 항목 없음)")
else:
    print(f"value={d.get('value')} default={d.get('defaultValue')} "
          f"range={d.get('minValue')}~{d.get('maxValue')} type={d.get('type')}")
PY
}

drive_query() {  # $1=plugin(또는 --grep) $2=param(또는 조각)
  if [ ! -x "$AMAP" ]; then
    echo "(원본 하드 조회 생략 — $AMAP 없음. session/5466b21a 브랜치에 있다)"
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
  echo "=== Seer 포트 동시연결 한도 — 실기($SEER_IP) vs 원본 하드 ==="
  echo "⚠ 이 값은 문서 판본이 정하는 상수가 아니라 **런타임 파라미터**다(변경 가능)."
  for row in "${DEFAULT_PAIRS[@]}"; do
    read -r plugin param label <<<"$row"
    printf '\n[%s] %s\n' "$label" "$param"
    printf '  실기 1400 : %s\n' "$(live_query "$plugin" "$param")"
    printf '  원본 하드 : %s\n' "$(drive_query "$plugin" "$param" | sed 's/^ *//')"
  done
elif [ $# -eq 1 ]; then
  echo "=== 원본 하드 robot.param 에서 '$1' 검색 (전 플러그인) ==="
  drive_query --grep "$1"
  echo
  echo "정확한 플러그인·이름을 알면 실기도 조회한다:  $0 <플러그인> <파라미터>"
else
  printf '[%s.%s]\n' "$1" "$2"
  printf '  실기 1400 : %s\n' "$(live_query "$1" "$2")"
  printf '  원본 하드 : %s\n' "$(drive_query "$1" "$2" | sed 's/^ *//')"
fi
