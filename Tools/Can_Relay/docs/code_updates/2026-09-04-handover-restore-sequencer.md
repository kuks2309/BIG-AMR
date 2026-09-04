# 2026-09-04 — 펌웨어 핸드오버 복원 시퀀서 신설 (세션 67ed5a48)

- **무엇을**: `board/safety/safety_seer_gate.h` 에 `seer_handover_request/tick/active` 와 상태 전역 추가.
  `board/usb_comms.h` 0xe8=0·0xe9=0 은 pc_authority 중이면 시퀀서 요청으로, 0xdc SILENT 는 시퀀서 진행 중이면 보류로,
  0xec 상태 조회 신설. `board/main.c`(미추적) tick 에 `seer_handover_tick()` 추가, heartbeat fail-safe 는
  시퀀서에 위임(진행 중 power-save 진입 금지).
- **왜**: 반환이 조향 위치와 무관하게 그 자리에서 일어나 Seer 가 자기 목표로 되돌리는 동작·재init 위험이 있었다.
  사용자 결정(18:10)으로 펌웨어가 소유 — 호스트 사망 시에도 성립. ADR `docs/adr/2026-09-04-canrelay-handover-restore-sequencer.md`.
- **검증**: (a) 노드로 조향 +30° 뒤 `~/engage false` → RESTORE 2.0 s 도달 → SETTLE → safety 0, 조향 홈 +0.000°, Seer 알람 0.
  (b) heartbeat 중단(release 없음) → 1.2 s 뒤 fail-safe 가 시퀀서 요청(src=2) → 1.4 s 도달 → SILENT, 조향 홈, Seer 알람 0.
  (c) hold 10사이클 회귀 10/10 PASS(재init 0·EMCY 0·알람 0).
- **빌드**: 31,764 B, md5 `639b4654…`, 4e002c 플래시 서명 검증 OK. 롤백 이미지 `fw_backups/panda-8dcca835-harness-nc_2026-09-04.bin.signed`.
- **추가(18:3x)**: `0xe9=1` 재engage 가 시퀀서 진행 중이면 복원 중단·보류 SILENT 폐기(권한 유지). 최종 md5 `0eee6d66…` 31,784 B. 검증 (d) 반환 0.5 s 뒤 재engage 정상, (e) 회귀 3/3.
- **롤백 드릴(18:4x)**: 롤백 이미지 플래시→부팅·passthrough 확인→최종 이미지 재플래시→0xec·hold 1사이클 확인. 최종 이미지 백업 `fw_backups/panda-0eee6d66-handover-restore_2026-09-04.bin.signed`.
- **호스트 변경 없음(사용자 결정 18:41)**: 해제 명령 즉시 펌웨어가 복원·핸드오버를 수행하며 노드·GUI·Rig 는 그대로 둔다.
- **변경(21:2x, 최종 md5 `bdac6012…` 32,280 B)**: 재engage 중단 → **복원 완료 후 권한 유지**로 교체(`seer_ho_reengage`). 보드 이름 런타임 기록 기능 동반(ADR 2026-09-04-canrelay-board-name-runtime, 도구 `board_name.py`). 4e002c 이름 `trworks-t3-1` 기록·리셋 보존 확인. 최종 이미지 백업 `fw_backups/panda-bdac6012-handover-boardname_2026-09-04.bin.signed`.
