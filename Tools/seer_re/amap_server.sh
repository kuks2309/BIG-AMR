#!/usr/bin/env bash
# amap-server(Seer 리버스 엔지니어링 분석 장비) 접속 래퍼.
#
# 왜 스크립트인가 — 호스트명·계정·타임아웃·원본 하드 경로를 **여기 한 곳에만** 둔다.
#   2026-08-06 에 tailscale 이름이 amap-1 → amap-server 로 바뀌었는데, 기록(메모리·저장소 문서) 두 곳이
#   이미 정정돼 있었음에도 낡은 이름을 손으로 타이핑해 실패한 사건이 있었다:
#   docs/claude-mistake/2026-08-06-005. 값을 손으로 적을 수 있으면 손으로 적게 되므로, 적을 필요를 없앤다.
#   이름이 또 바뀌면 아래 HOST 한 줄만 고친다.
#
# 사용법:
#   amap_server.sh info                     # 접속 확인 + 원본 하드/바이너리 존재 확인
#   amap_server.sh ssh '<명령>'             # 원격 명령 실행
#   amap_server.sh nm '<패턴>'              # libMCLoc.so 심볼 검색(디맹글)
#   amap_server.sh disasm <start> <stop>    # libMCLoc.so 구간 디스어셈블 (16진 주소)
#   amap_server.sh push <파일...>           # /tmp/mcl_oracle/ 로 전송
#   amap_server.sh run <실행파일> [인자...]  # /tmp/mcl_oracle/ 에서 원본 라이브러리 경로를 걸고 실행
#
# 환경변수로 덮어쓰기: AMAP_HOST · AMAP_USER · AMAP_TIMEOUT
set -euo pipefail

HOST="${AMAP_HOST:-amap-server}"     # 구 이름 amap-1 (2026-08-06 개명)
HOST_IP="100.116.195.65"             # tailscale 이름이 안 잡힐 때 폴백
LOGIN_USER="${AMAP_USER:-amap}"      # 이 계정만 tailnet 정책 허용
TIMEOUT="${AMAP_TIMEOUT:-90}"        # 첫 접속이 느리다 — 15초면 Terminated(=거부 아님)

DRIVE="/media/amap/6ab6980d-f090-4387-8753-a2251e75651d"   # 63G 원본(/dev/sdb2), 읽기 전용으로만
RBK="$DRIVE/usr/local/SeerRobotics/rbk"
SO="$RBK/plugins/libMCLoc.so"
LIBPATH="$RBK/lib:$RBK/3rdlib:$RBK/core"
WORKDIR="/tmp/mcl_oracle"

target() {
  if timeout 10 getent hosts "$HOST" >/dev/null 2>&1 || timeout 10 ping -c1 -W2 "$HOST" >/dev/null 2>&1; then
    echo "$LOGIN_USER@$HOST"
  else
    echo "$LOGIN_USER@$HOST_IP"
  fi
}

remote() { timeout "$TIMEOUT" ssh -o BatchMode=yes -o ConnectTimeout=20 "$(target)" "$@"; }

cmd="${1:-info}"; shift || true
case "$cmd" in
  info)
    remote "hostname; echo '--- 원본 하드 ---'; ls -d '$DRIVE' && ls -la '$SO' | awk '{print \$5, \$NF}'"
    ;;
  ssh)   remote "$*" ;;
  nm)    remote "nm -C --defined-only '$SO' | grep -- '$*' | head -20" ;;
  disasm)
    [ $# -ge 2 ] || { echo "usage: disasm <start-hex> <stop-hex>" >&2; exit 2; }
    remote "objdump -d --start-address=$1 --stop-address=$2 '$SO'"
    ;;
  push)
    [ $# -ge 1 ] || { echo "usage: push <파일...>" >&2; exit 2; }
    remote "mkdir -p '$WORKDIR'"
    timeout "$TIMEOUT" rsync -a "$@" "$(target):$WORKDIR/"
    ;;
  run)
    [ $# -ge 1 ] || { echo "usage: run <실행파일> [인자...]" >&2; exit 2; }
    exe="$1"; shift
    remote "cd '$WORKDIR' && LD_LIBRARY_PATH='$LIBPATH' ./$exe $* "
    ;;
  so)    echo "$SO" ;;   # 오라클 인자로 쓸 원본 경로
  *)     sed -n '1,20p' "$0" >&2; exit 2 ;;
esac
