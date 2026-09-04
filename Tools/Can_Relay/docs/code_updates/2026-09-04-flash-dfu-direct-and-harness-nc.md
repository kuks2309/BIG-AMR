# 2026-09-04 — `flash_dfu_direct.py` 저장소 편입 + `black.h` 하네스 판정 NC 고정 (세션 67ed5a48)

- **flash_dfu_direct.py**: 이전 세션(44fa6711) scratchpad 에만 있던 4e002c 전용 DFU 직접 플래시 도구를
  `Tools/Can_Relay/` 로 옮겼다(내용 동일). 통상 `Panda().flash` 경로가 이 보드를 bootstub 에 가두는 함정을
  회피한다(2026-09-01 검증 경로). 왜: 사용자가 플래시를 직접 실행해야 해 안정된 경로가 필요했다.
- **panda-firmware/board/boards/black.h** (git 미추적, 원문은 ADR·분석 §7 보존):
  `harness_init()` 제거 → `car_harness_status = HARNESS_STATUS_NC` 고정, FLIPPED 전용 `can_flip_buses(0,2)`
  삭제, `has_harness = false`. 왜: 하네스 없는 보드에서 방향 판정이 부팅마다 흔들려 FLIPPED 시
  bus0/bus2 교체·PC10 반전으로 릴레이 제어가 깨졌다(debt-130, E1 실측).
  ADR `docs/adr/2026-09-04-canrelay-harness-orientation-neutralize.md`.
- **검증**: 빌드 PASS(31,172 B, md5 1f9fe50b…). 실기 플래시·검증은 사용자 실행 대기.
