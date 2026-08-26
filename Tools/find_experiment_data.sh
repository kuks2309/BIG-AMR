#!/bin/bash
# 실험 데이터 전수 검색기 — "그날 데이터 있나" 질문의 1순위 도구.
# 부재 보고는 본 스크립트의 0건 출력 첨부 시에만 허용한다.
# 깊이·경로를 제한한 검색의 0건은 부재의 근거가 될 수 없으므로 -maxdepth 를 쓰지 않는다.
#
# 사용: Tools/find_experiment_data.sh <YYMMDD 또는 YYYY-MM-DD>
# 검색 대상: rosbag(.db3/.mcap/metadata.yaml)·jsonl·csv·리포트(html/pdf)
# 범위: 저장소 전체 + /home/nvidia 전체, 깊이 제한 없음.

set -u
D="${1:?날짜 인자 필요 (예: 260825 또는 2026-08-25)}"
case "$D" in
    [0-9][0-9][0-9][0-9][0-9][0-9]) ISO="20${D:0:2}-${D:2:2}-${D:4:2}" ;;
    *) ISO="$D"; D="${ISO:2:2}${ISO:5:2}${ISO:8:2}" ;;
esac
NEXT=$(date -d "$ISO + 1 day" +%F)
REPO="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== ${ISO} 실험 데이터 전수 검색 (이름 매치 + 수정시각 ${ISO}~) ==="
echo "── 이름에 ${D} 포함:"
find "$REPO" /home/nvidia -xdev \( -path '*/node_modules' -o -path '*/.git' \) -prune \
     -o -name "*${D}*" -print 2>/dev/null | sort -u
echo "── ${ISO} 하루 동안 생성·수정된 bag/jsonl/csv/리포트:"
find "$REPO" /home/nvidia -xdev \( -path '*/node_modules' -o -path '*/.git' \) -prune \
     -o -type f \( -name '*.db3' -o -name '*.mcap' -o -name 'metadata.yaml' \
                   -o -name '*.jsonl' -o -name '*.csv' -o -name '*.html' -o -name '*.pdf' \) \
     -newermt "$ISO" ! -newermt "$NEXT" -print 2>/dev/null | sort -u
echo "=== 검색 끝 — 위 두 절이 모두 비어야만 '부재'를 보고할 수 있다 ==="
