#!/usr/bin/env bash
# 원본 libOdoCalculator.so 와 재구현본 seer_odom_core 를 **같은 입력**으로 돌려 대조한다.
#
# ⚠ 반드시 x86-64 에서 돌린다. aarch64 로봇 PC 에서 빌드한 재구현본은 계수행렬 한 원소가
#   1 ULP 갈려(0x…AAA vs 0x…AAB) 대조가 오염된다 — 실측 확인. 원본이 x86-64 이므로
#   대조도 그 아키텍처에서 해야 한다.
set +u
HOST="${AMAP_HOST:-amap-server}"
USER="${AMAP_USER:-amap}"
D=/media/amap/6ab6980d-f090-4387-8753-a2251e75651d
RBK=$D/usr/local/SeerRobotics/rbk
HERE="$(cd "$(dirname "$0")" && pwd)"
CORE="$HERE/../../../src/Navigation/seer_odom_core"

if ! timeout 30 ssh -o BatchMode=yes "$USER@$HOST" "test -f $RBK/plugins/libOdoCalculator.so"; then
  echo "원본에 닿지 못했다 — amap-server 상태를 확인하라" >&2; exit 2
fi

tar cf - -C "$CORE/.." seer_odom_core/include seer_odom_core/src \
  | ssh -o BatchMode=yes "$USER@$HOST" 'rm -rf /tmp/soc && mkdir -p /tmp/soc && tar xf - -C /tmp/soc'
scp -q -o BatchMode=yes "$HERE/odo_oracle.cpp" "$HERE/ours_run.cpp" "$USER@$HOST:/tmp/"

ssh -o BatchMode=yes "$USER@$HOST" "
  set -e
  g++ -std=c++17 -O1 -ffp-contract=off -o /tmp/odo_oracle /tmp/odo_oracle.cpp -ldl
  g++ -std=c++17 -O1 -ffp-contract=off -I /tmp/soc/seer_odom_core/include -I /usr/include/eigen3 \
      /tmp/ours_run.cpp /tmp/soc/seer_odom_core/src/multisteer_odometer.cpp -o /tmp/ours_x86
  LD_LIBRARY_PATH=$RBK/lib:$RBK/3rdlib:$RBK/core /tmp/odo_oracle 2>/dev/null | grep -E '^(SPEED|DPOSE|POSE)' > /tmp/o.txt
  /tmp/ours_x86 | grep -E '^(SPEED|DPOSE|POSE)' > /tmp/u.txt
  if diff -q /tmp/o.txt /tmp/u.txt >/dev/null; then
    echo \"비트 일치 — 대조 \$(wc -l < /tmp/o.txt) 줄 차이 0건\"
  else
    echo '불일치:'; diff /tmp/o.txt /tmp/u.txt; exit 1
  fi
"
