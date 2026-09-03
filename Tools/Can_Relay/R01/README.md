# CAN RELAY R01 — 초판 하드웨어 (보드 리비전별 분리)

R01 보드 전용 자산 폴더. 신규 보드는 [`../R02/`](../R02/), 빌드 시스템은 공유 `../panda-firmware/`.

## 이 폴더 내용
- `CAN RELAY R01.pdf` — R01 회로도(2026-07-27, STM32F413RGT).

## R01 요지 (근본 결함 — R02 재설계 사유)
- Seer·모터 커넥터가 정본(comma black-panda)의 **STM32 CAN2 뮤텍스 쌍**(PB12/13·PB5/6)에 동거 +
  bus2 트랜시버 미실장 → **동시 MITM 물리 불가**(2026-08-23 engage 실측 실패, bus2 ACK 0/TEC=128).
  passthrough(Seer 단독 주행)만 동작. 상세:
  [../fw_backups/README-2026-08-23.md](../fw_backups/README-2026-08-23.md):42-74 ·
  [docs/can_relay/clone-board-U3P-pinmap-findings.md](../../../docs/can_relay/clone-board-U3P-pinmap-findings.md).
- 초기 현장 기록: [../FIELD-RECORD-2026-07-25.md](../FIELD-RECORD-2026-07-25.md)(공유 위치 유지 — 다수 문서가 참조).
