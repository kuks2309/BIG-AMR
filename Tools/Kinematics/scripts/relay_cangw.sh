#!/usr/bin/env bash
# 커널 게이트웨이(can-gw) 양방향 릴레이: can0(Seer 측) <-> can1(모터 측)
# 사용: sudo ./02_relay_cangw.sh start|stop|status
# 근거: docs/can_relay/2026-07-07-design-inputs.md §8 구현 옵션 1
# 루프 방지: can-gw 는 자신이 송신한 프레임을 재포워딩하지 않음 (커널 skb 플래그) — 양방향 룰 2개로 무한루프 없음
set -euo pipefail

SRC0=can0   # Seer 측
SRC1=can1   # 모터 측

case "${1:-}" in
  start)
    [[ $EUID -eq 0 ]] || { echo "root 필요: sudo $0 start" >&2; exit 1; }
    modprobe can_gw
    cangw -F || true                          # 중복 방지 초기화
    cangw -A -s "$SRC0" -d "$SRC1"            # Seer -> 모터 (지령·읽기요청·node guard RTR)
    # 모터 -> Seer: 0x600~0x67F(요청 에코 — PC 게이트/직접조종 TX 포함) 는 역방향 비전달 (inverse filter)
    cangw -A -s "$SRC1" -d "$SRC0" -f 600~780
    echo "relay ON: $SRC0 <-> $SRC1"
    cangw -L || true   # cangw -L 은 성공해도 비0 종료코드 반환 — 실패 오인 방지
    ;;
  gate_on)
    # 주도권 PC: Seer->모터 커널 통과만 제거 (유저스페이스 게이트가 대신). 모터->Seer 커널 유지(저지연)
    [[ $EUID -eq 0 ]] || { echo "root 필요" >&2; exit 1; }
    cangw -D -s "$SRC0" -d "$SRC1"
    echo "gate ON"
    ;;
  gate_off)
    # 주도권 반환: Seer->모터 커널 통과 복원
    [[ $EUID -eq 0 ]] || { echo "root 필요" >&2; exit 1; }
    cangw -A -s "$SRC0" -d "$SRC1"
    echo "gate OFF"
    ;;
  stop)
    [[ $EUID -eq 0 ]] || { echo "root 필요: sudo $0 stop" >&2; exit 1; }
    cangw -F   # 전체 룰 삭제
    echo "relay OFF (전 룰 삭제)"
    ;;
  status)
    cangw -L || true   # 룰 목록 + handled/dropped 카운터 (비0 종료코드 무시)
    ;;
  *)
    echo "사용법: $0 start|gate_on|gate_off|stop|status" >&2; exit 1
    ;;
esac
