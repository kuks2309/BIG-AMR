# 2026-09-04 — `board_name.py` 신설: 보드 이름 USB 읽기/쓰기 (세션 67ed5a48)

- **무엇을**: `Tools/Can_Relay/board_name.py` — 펌웨어 0xed(읽기)/0xee(2바이트 스테이징)/0xef(0x5AA5 커밋)으로
  플래시 섹터 4 의 보드 이름 레코드를 읽고 쓴다. 인자 없으면 읽기, `set <name>` 은 SILENT idle(safety_mode 0)에서만
  기록 후 재확인. 이름 형식 `[A-Za-z0-9_-]{1,31}`.
- **왜**: 보드 3장을 호스트명(trworks-t3-1)처럼 구분하되 USB 시리얼(MCU 고유 ID, 플래시 가드 의존)은 바꾸지 않기 위해.
  사용자 결정(21:1x) "런타임에 USB 로 써 넣기". ADR `docs/adr/2026-09-04-canrelay-board-name-runtime.md`.
- **검증**: 미기록 '' → `set trworks-t3-1` commit OK·readback 일치 → 판다 리셋 후 유지 → `get_version()` 에 `#trworks-t3-1` 접미.
- **함수표**: `Tools/Can_Relay/docs/function_table.md` "board_name.py" 절.
- **2026-09-05 (펌웨어 md5 `c04e7b07…`)**: 0xef 커밋 전 `board_name_stage_valid()` 로 `[A-Za-z0-9_-]` 1~31자·NUL 패딩만 허용(검토 #19). 실기: 비ASCII·공백·빈 값·NUL 뒤 문자 4종 거부·기존 이름 보존, 유효 이름 수락, hold 1/1. 백업 `fw_backups/panda-c04e7b07-boardname-validate_2026-09-05.bin.signed`.
