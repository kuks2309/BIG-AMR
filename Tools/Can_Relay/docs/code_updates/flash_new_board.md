# flash_new_board.py Code Updates

`Tools/Can_Relay/flash_new_board.py` 의 수정 이력. coding.md §수정 이력 기록에 따라
**이력은 여기와 git commit message 가 담당**하고, 소스 주석은 현재 사실만 담는다.

## 2026-09-01 — `flash_new_board.py` 신설

- **무엇을**: 신규 공장(DFU) CAN relay 보드에 검증본 펌웨어를 굽는 자립 도구. 흐름 —
  ① DFU 상태면 `PandaDFU.recover()` 로 bootstub 프로그램 → ② 정상 판다로 재열거되면 통상
  `Panda().flash()` → ③ **DFU 로 재진입하면 앱을 DFU 로 직접 프로그램**(섹터
  0x8004000/0x8008000/0x800C000 소거 + `APP_ADDRESS_FX` 기록) → ④ 부팅 후 장치 서명
  (0xd3/0xd4) 을 파일과 대조 검증. 기본 이미지 `board/obj/panda.bin.signed`, `--fw` 로 교체.
- **왜**: 정본 킷 도구 `docking_field_kit/flash_panda.py` 는 정상 판다(bbaa:ddcc) 선존을
  전제해 **공장 DFU 상태에선 `Panda()` 가 `assert self._handle is not None` 로 죽는다**
  (2026-09-01 실측). 2026-08-23 신규 보드 설치 때도 같은 이유로 통상 경로가 막혀
  세션 스크래치패드 1회용 스크립트로 우회했는데, 교체가 반복되므로 정본 도구로 승격.
- **설계 판단**: ③ DFU 직접 경로를 상시 폴백으로 둔다 — 이 보드군은 **BOOT0/DFU-모드 강제 핀**이
  SET 이면 bootstub 후 DFU 로 재진입해 통상 재열거가 막히기 때문(2026-08-23·2026-09-01 실측 2보드).
- **검증**: 교체 보드(DFU `356534903232`)에 실행 → ③ 경로로 앱 기록, 1차엔 앱 부팅
  (`0xddcc`)·`get_signature()`==파일·version `DEV-cc5e0491-DEBUG`·safety_mode 0·hw_type 0x03 실증,
  재설치 후 **DFU read-back** 로 장치 앱 영역 == 파일(md5 `91fe4282…`) 재확인.
- **인벤토리**: 함수표 `Tools/Can_Relay/docs/function_table.md`(코드 작성 전 작성 — 게이트 강제).
- **함정(기록)**: ② 통상 경로는 **DFU 강제핀이 SET 인 보드를 bootstub(`0xddee`)에 가둔다**
  (flash 시작의 `reset(enter_bootstub=True)` 후 리셋이 앱 점프를 못 함). 복구는
  `reset(enter_bootloader=True)` 로 DFU 로 밀어넣고 ③ 재플래시. → 핀 SET 동안엔 항상 ③ 으로 굽고,
  이미 앱 부팅 중인 보드엔 재플래시 금지. 상세 `R02/README-2026-09-01.md`(보드 리비전별 분리).
