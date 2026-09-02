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
| `main` | `main() -> NoReturn` | ①DFU면 bootstub 복구 ②정상 재열거 시 통상 flash ③DFU 재진입 시 앱 DFU 직접 flash ④장치 서명(0xd3/0xd4)==파일 검증. exit 0=OK·2=부팅실패·3=불일치 | flash_new_board.py:51 |

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
