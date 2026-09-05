# Can_Relay — 함수표 (모듈 권위본)

> 대상: `Tools/Can_Relay/` — 판다(comma.ai) 기반 CAN relay 보드 현장 킷·플래시 도구.
> 정본 라이브러리/펌웨어는 `Tools/Can_Relay/panda-firmware/`(별도 상류 트리, 여기서 등재하지 않음).
> ROS2 런타임(`can_relay` 노드·backend·ui)은 `src/Comm/CAN/can_relay/` 소관이라 별개.

## 함수표 — flash_new_board.py (신규 공장/DFU 보드 플래시 + 서명검증)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `pick_fw` | `pick_fw(argv) -> str` | `--fw <경로>` 우선, 없으면 저장소 현재 빌드(`board/obj/panda.bin.signed`) | flash_new_board.py:24 |
| `read_sidecar_version` | `read_sidecar_version(fw) -> str \| None` | 이미지 옆 `version` 사이드카(빌드마다 갱신) 판독 — 검증 기대값 | flash_new_board.py:33 |
| `normals` | `normals() -> list[str]` | 정상 판다(bbaa:ddcc/ddee) 시리얼 열거(예외 흡수) | flash_new_board.py:41 |
| `dfus` | `dfus() -> list[str]` | DFU(0483:df11) 장치 시리얼 열거(예외 흡수) | flash_new_board.py:46 |
| `read_board_name` | `read_board_name(p) -> str` | 펌웨어 0xed 보드 이름(섹터 4) 판독. 미기록·예외면 `''` | flash_new_board.py:51 |
| `read_ho_status` | `read_ho_status(p) -> tuple[int,int] \| None` | 펌웨어 0xec → (state, pc_authority). 빈 응답·예외면 None = 현행 펌웨어(시퀀서 탑재) 아님 | flash_new_board.py:60 |
| `main` | `main() -> NoReturn` | ①DFU면 bootstub 복구 ②정상 재열거 시 통상 flash ③DFU 재진입 시 앱 DFU 직접 flash ④장치 서명(0xd3/0xd4)==파일 ∧ 사이드카 version 대조(0xd6 의 `#<보드이름>` 접미 제거 후) ∧ 0xec 응답 있음 + 보드 이름 출력(섹터 4 보존 확인용). exit 0=OK·2=부팅실패·3=불일치 | flash_new_board.py:69 |

> ⚠ version 문자열은 빌드 시점 git HEAD 에서 나오므로(`DEV-<HEAD 8자>-DEBUG`) **미커밋 소스로 여러 번 빌드하면 전부 같은 값**이다
> (2026-09-04·05 이미지 7종이 모두 `DEV-8dcca835-DEBUG`, `fw_backups/README-2026-09-05.md`). 어느 빌드가 올라갔는지는 **서명(0xd3/0xd4) 대조**만이 가른다.

## 전역변수표 — flash_new_board.py

| 이름 | 값/형 | 용도 | 위치 |
| --- | --- | --- | --- |
| `PF` | str(절대경로) | `panda-firmware/` 루트 — 라이브러리 import 경로·기본 이미지 기준 | flash_new_board.py:17 |
| `APP_ADDRESS_FX` | `0x8004000` (import) | F4 앱 시작 주소 — DFU 직접 플래시 대상 | flash_new_board.py:21 |
| `BLOCK_SIZE_FX` | `0x800` (import) | F4 DFU 프로그램 블록 크기 | flash_new_board.py:22 |

> 구조 배경: `docking_field_kit/flash_panda.py` 는 정상 판다 선존을 전제해 공장 DFU 상태에서
> `Panda()` 가 assert 로 죽는다(2026-09-01 실측). 이 도구는 bootstub 부터 굽는 경로로 그 공백을 메운다.
> BOOT0 스트랩으로 bootstub 후 DFU 재진입하는 보드가 있어(2026-08-23·2026-09-01 실측 2보드) ③ 폴백이 상시 필요.

## 함수표 — ui/flash_gui.py (펌웨어 플래시 GUI · 뷰 계층, PyQt5)

> UI 분리 원칙: 위젯·상호작용만. 감지·경로·argv 로직은 `ui/flash_backend.py`. 플래시 로직은
> 검증된 `flash_new_board.py`(DFU·앱)·`flash_panda.py --recover` 를 QProcess 로 호출(재구현 금지).
> 어느 폴더에서든 실행: `python3 <repo>/Tools/Can_Relay/ui/flash_gui.py`.

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `FlashGui.__init__` | `__init__(self)` | 위젯 생성 + 최초 감지 | ui/flash_gui.py:25 |
| `FlashGui._build` | `_build(self)` | 상태줄·펌웨어 선택·버튼·진행막대·로그 레이아웃 구성 | ui/flash_gui.py:34 |
| `FlashGui.refresh` | `refresh(self)` | 재감지 → 상태 표시·버튼 활성/잠금(실행 중·모호면 플래시 비활성) | ui/flash_gui.py:86 |
| `FlashGui._browse` | `_browse(self)` | 펌웨어 파일 선택 대화상자 | ui/flash_gui.py:97 |
| `FlashGui._flash` | `_flash(self)` | 확인 후 `fb.flash_argv(fw)` 실행(앱 재플래시 경고 동반) | ui/flash_gui.py:105 |
| `FlashGui._recover` | `_recover(self)` | 확인 후 `fb.recover_argv()` 실행(부트스텁→DFU) | ui/flash_gui.py:121 |
| `FlashGui._run` | `_run(self, argv)` | QProcess 실행·스트리밍 + 진행막대 busy 시작(중복 실행 방지·버튼 잠금) | ui/flash_gui.py:128 |
| `FlashGui._on_output` | `_on_output(self)` | 표준출력 → 로그 창 append | ui/flash_gui.py:141 |
| `FlashGui._on_done` | `_on_done(self, code, status)` | 종료 코드·진행막대 정지(완료 100%/유휴 0%)·재감지 | ui/flash_gui.py:147 |
| `main` | `main() -> NoReturn` | QApplication 기동 | ui/flash_gui.py:156 |

## 함수표 — ui/flash_backend.py (플래시 GUI 로직 · Qt 미의존)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `detect` | `detect() -> tuple[str,str]` | 판다 상태 감지 → (mode, detail). mode∈{dfu,app,none,both,multi,error}. 2대↑는 모호로 플래시 차단 | ui/flash_backend.py:30 |
| `flash_argv` | `flash_argv(fw) -> list[str]` | DFU·앱 겸용 플래시 실행 argv(`flash_new_board.py --fw`) | ui/flash_backend.py:56 |
| `recover_argv` | `recover_argv() -> list[str]` | 부트스텁→DFU 복구 argv(`flash_panda.py --recover`) | ui/flash_backend.py:61 |

## 전역변수표 — ui/flash_backend.py

| 이름 | 값/형 | 용도 | 위치 |
| --- | --- | --- | --- |
| `HERE` | str(절대경로) | `Tools/Can_Relay/ui` | ui/flash_backend.py:11 |
| `ROOT` | str(절대경로) | `Tools/Can_Relay/` — 스크립트·기본 이미지 기준 | ui/flash_backend.py:12 |
| `FLASH_NEW` | str(경로) | DFU·앱 겸용 플래셔(`flash_new_board.py`) | ui/flash_backend.py:13 |
| `FLASH_PANDA` | str(경로) | `docking_field_kit/flash_panda.py`(`--recover`) | ui/flash_backend.py:14 |
| `DEFAULT_FW` | str(경로) | 기본 이미지 `board/obj/panda.bin.signed` | ui/flash_backend.py:15 |
| `MODE_TEXT` | dict | mode→(표시문구·색) 매핑 | ui/flash_backend.py:20 |

## 함수표 — flash_dfu_direct.py (4e002c 앱모드 보드 DFU 직접 재플래시)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| (없음 — 스크립트 본문) | `python3 flash_dfu_direct.py` | 앱 판다 → `reset(enter_bootloader)` → DFU erase(0x8004000/8000/C000 = 섹터 1~3)+program+reset → 재열거 후 장치 서명==파일 ∧ 0xec 응답(현행 펌웨어) 검증 + 보드 이름(0xed, 섹터 4) 출력. exit 0=OK·2=재열거 실패·3=불일치 | flash_dfu_direct.py:1 |

## 전역변수표 — flash_dfu_direct.py

| 이름 | 값/형 | 용도 | 위치 |
| --- | --- | --- | --- |
| `PF` | str(절대경로) | `panda-firmware/` 루트 | flash_dfu_direct.py:7 |
| `APP` | str | 플래시 이미지 `board/obj/panda.bin.signed` | flash_dfu_direct.py:13 |
| `app` | bytes | 이미지 바이트(49,152 B 앱영역 초과 시 abort) | flash_dfu_direct.py:14 |

## 함수표 — panda-firmware/board/safety/safety_seer_gate.h (우리 추가분: 핸드오버 복원 시퀀서, 2026-09-04)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `seer_handover_active` | `bool seer_handover_active(void)` | 시퀀서가 RESTORE/SETTLE 중인지 | safety_seer_gate.h (시퀀서 절) |
| `seer_handover_request` | `void seer_handover_request(uint8_t source)` | 반환 요청 수락(pc_authority 필요). 호밍 취소·구동 0·조향 목표(`seer_last_target`) 송신 후 RESTORE 진입. 진행 중 재요청은 `seer_ho_reengage` 삭제(최신 요청 우선)·failsafe 로 source 승격만 | 〃 |
| `seer_handover_tick` | `void seer_handover_tick(void)` | 8 Hz. 1 s 마다 목표 재송신(재engage 대기 중이면 중지), 캐시 0x6064 로 도달(≤5,734 counts)·8 s 타임아웃 판정 → SETTLE 0.5 s → `seer_handover_finish` | 〃 |
| `seer_handover_finish` | `static void seer_handover_finish(void)` | 재engage 대기면 권한·emulate 유지한 채 종료. 아니면 pc_authority 해제·frozen 해제·cover arm·`set_intercept_relay(false)`, (보류 SILENT ∨ failsafe ∨ heartbeat 상실)이면 SILENT 전환 | 〃 |
| `seer_ho_send_targets` / `seer_ho_reached` / `seer_ho_have_target` | static | 목표 송신·잔차 판정·목표 보유 여부 | 〃 |

## 전역변수표 — 핸드오버 시퀀서

| 이름 | 값/형 | 용도 | 위치 |
| --- | --- | --- | --- |
| `seer_ho_state` | uint8 (0 IDLE·1 RESTORE·2 SETTLE) | 시퀀서 상태 | safety_seer_gate.h |
| `seer_ho_source` | uint8 (1 host·2 failsafe) | 요청 출처 — failsafe 면 완료 시 SILENT (재engage 차단 래치 `relay_off_latched` 는 현행 펌웨어에 없다) | 〃 |
| `seer_ho_result` | uint8 (0 none·1 reached·2 timeout·3 no-target) | 마지막 복원 결과(0xec 로 조회) | 〃 |
| `seer_ho_ticks` / `seer_ho_settle` | uint8 | 경과 tick / 정착 tick | 〃 |
| `seer_ho_pending_silent` | bool | 진행 중 받은 0xdc SILENT 보류 플래그 | 〃 |
| `seer_ho_reengage` | bool | 복원 진행 중 받은 0xe9=1 — 완료 시 권한 유지(출처 무관). 뒤이은 반환 요청이 지운다(최신 요청 우선), 대기 중엔 목표 재송신 중지 | 〃 |

## 함수표 — board_name.py (보드 이름 USB 읽기/쓰기)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `get_name` | `get_name(p: Panda) -> str` | 0xed 로 32 B 읽어 NUL 앞까지 반환 | board_name.py:20 |
| `ho_status` | `ho_status(p: Panda) -> tuple[int,int] \| None` | 0xec 6 B → (state, pc_authority). 빈 응답(0xec 없음)이면 None = 현행 펌웨어 아님 | board_name.py:25 |
| `set_name` | `set_name(p: Panda, name: str) -> bool` | 형식 검사 후 0xee 로 2바이트씩 스테이징, 0xef(0x5AA5) 커밋 결과 반환 | board_name.py:31 |
| `main` | `main()` | 인자 없으면 읽기(이름 + 0xec state·pc_authority), `set <name>` 이면 safety_mode 0 + 0xec 응답 있음 + 시퀀서 IDLE·pc_authority 0 (펌웨어 커밋 가드와 동일 조건) 확인 후 기록·재확인. 0xec 없으면 거부(현행 펌웨어 아님) | board_name.py:41 |

## 전역변수표 — board_name.py

| 이름 | 값/형 | 용도 | 위치 |
| --- | --- | --- | --- |
| `REQ_GET` / `REQ_STAGE` / `REQ_COMMIT` | 0xED / 0xEE / 0xEF | 보드 이름 읽기·스테이징·커밋 USB 요청 | board_name.py:16 |
| `COMMIT_KEY` / `NAME_LEN` | 0x5AA5 / 32 | 커밋 키·레코드 길이 | board_name.py:16 |
| `REQ_HO_STATUS` | 0xEC | 핸드오버 시퀀서 상태 조회 | board_name.py:17 |

## 함수표 — tests/test_board_name_flash_tools.py (하드웨어 없는 USB 계약 회귀)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `FakeHandle` | class | usb_comms.h 의 0xec/0xed/0xee/0xef 핸들러를 파이썬으로 옮긴 모의 장치(형식 검사·커밋 가드 포함) | tests/test_board_name_flash_tools.py |
| `main` | `main() -> int` | `board_name`·`flash_new_board` 의 공개 함수 17 항목 검사, 실패 수 반환. 실행에 `panda-firmware/python`(git 미추적)이 필요 — 없으면 `PYTHONPATH` 로 공유 트리 것을 지정 | 〃 |

## 함수표 — panda-firmware/board/usb_comms.h (우리 추가분: 보드 이름)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `board_name_read` | `static uint8_t board_name_read(uint8_t *out)` | 섹터 4 레코드(magic 'CRNM') 읽기, 길이 반환 | usb_comms.h |
| `board_name_stage_valid` | `static bool board_name_stage_valid(void)` | 스테이징 형식 검사 `[A-Za-z0-9_-]{1,31}` + 첫 NUL 뒤 전부 NUL. 위반이면 커밋 거부 | usb_comms.h |
| `board_name_commit` | `static bool board_name_commit(void)` | 형식 OK ∧ SILENT ∧ 시퀀서 IDLE ∧ pc_authority 0 일 때만 섹터 4 erase+program 후 검증(F413 전용) | usb_comms.h |

## USB 제어 요청표 — usb_comms.h 우리 추가·변경분 (호스트 도구가 의존하는 계약)

| 요청 | 방향·인자 | 동작 | 사용처 |
| --- | --- | --- | --- |
| `0xd6` | IN | 버전 문자열. 보드 이름이 있으면 `#<name>` 접미(총 64 B 이내) | `Panda.get_version()` 전부 — 사이드카 대조는 접미 제거 후 |
| `0xdc` | OUT wValue=mode | SILENT 요청: 시퀀서 진행 중이면 보류, pc_authority 중이면 시퀀서 요청 후 보류, 그 외 즉시. 라이브 모드 요청은 보류 SILENT 폐기 | can_relay 노드 `_rollback`/`acquire` |
| `0xe8` | OUT wValue=0/1 | 1: intercept+cover arm. 0: pc_authority 중이면 시퀀서 요청(host), 아니면 즉시 passthrough+cover | 노드·Rig |
| `0xe9` | OUT wValue=0/1 | 1: 시퀀서 진행 중이면 재engage 예약(보류 SILENT 폐기), 아니면 pc_authority=1. 0: pc_authority 중이면 시퀀서 요청, 아니면 0 | 노드·Rig |
| `0xea` / `0xeb` | OUT / IN 8 B | 조향 호밍 개시·중단 / 상태 | 노드 호밍 서비스 |
| `0xec` | IN 6 B | `[state, source, result, pending_silent, ticks, pc_authority]`. 응답 유무가 "현행 펌웨어(c04e7b07 계열)" 판별 기준 | `board_name.py ho_status`(없으면 set 거부), 플래시 도구 verify(없으면 MISMATCH), 실기 시험 스크립트 |
| `0xed` / `0xee` / `0xef` | IN 32 B / OUT idx,2 B / IN 1 B (wValue=0x5AA5) | 보드 이름 읽기 / 스테이징 / 커밋 | `board_name.py`, 플래시 도구 verify |
