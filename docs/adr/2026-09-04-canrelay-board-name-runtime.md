# ADR 2026-09-04 — CAN relay 보드 이름을 런타임 USB 로 기록 (플래시 섹터 4)

- **Status**: Accepted · 구현·플래시·검증 완료 (사용자 결정 2026-09-04 21:1x "런타임에 USB 로 써 넣기")
- **대상**: `Tools/Can_Relay/panda-firmware/board/usb_comms.h`(추적), `Tools/Can_Relay/board_name.py`(신규)

## Context
보드가 3장(4e002c·4f0040·51003b)이라 호스트명(trworks-t3-1)처럼 사람이 읽는 이름이 필요하다. USB 시리얼은 MCU 고유 ID 라 바꾸지 않는다(플래시 가드·식별 기록이 의존).

## Decision
- 레코드 `[magic 'CRNM'][name 32 B]` 를 **플래시 섹터 4(0x08010000, 64 KB)** 에 둔다. 앱은 섹터 1~3(≤49,152 B)만 쓰고 `flash_dfu_direct.py` 도 그 세 섹터만 지우므로 **펌웨어 재플래시에도 이름이 보존**된다.
- USB: `0xed` 읽기(32 B, 미기록이면 길이 0) · `0xee` 스테이징(wValue=바이트 인덱스, wIndex=2바이트) · `0xef` 커밋(wValue=0x5AA5). 커밋은 **SILENT idle·비권한·시퀀서 비활성**에서만 허용 — 섹터 erase 동안 코어가 멈춰 CAN 수신을 놓치므로 intercept 중엔 금지.
- `get_version()`(0xd6)이 `"<gitversion>#<name>"` 으로 이름을 덧붙인다(64 B 이내).
- 도구 `Tools/Can_Relay/board_name.py [set <name>]` — 영문·숫자·하이픈·밑줄 1~31자.

## Rollback
- 코드: `usb_comms.h` 의 보드 이름 절과 0xd6 접미·0xed/0xee/0xef case 를 revert. 이름 레코드는 섹터 4 에 남지만 읽는 코드가 없으면 무해(다음 커밋으로 덮어씀).
- 실기: 직전 이미지 `fw_backups/panda-0eee6d66-handover-restore_2026-09-04.bin.signed` 재플래시.

## Verification (2026-09-04 21:2x)
- 미기록 상태 읽기 → '' · `set trworks-t3-1` → commit OK, readback 일치, version `DEV-8dcca835-DEBUG#trworks-t3-1`.
- 판다 리셋 후 readback 'trworks-t3-1' 유지. 이후 핸드오버 회귀(조향 +30° 반환 복원 1.1 s)·hold 3/3 PASS.
