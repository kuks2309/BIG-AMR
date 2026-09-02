# flash_gui — 코드 갱신 이력

대상: `Tools/Can_Relay/ui/flash_gui.py`(뷰) + `Tools/Can_Relay/ui/flash_backend.py`(로직).
함수표: `Tools/Can_Relay/docs/function_table.md`.

## 2026-09-02 — 신설 + UI 분리 정정

- **요청**: "펌웨어 다운로드를 위한 간단한 GUI — DFU 모드랑 non-DFU 모드", 이어서 "어느 폴더에서든
  실행" + "UI 분리 원칙 준수".
- **설계**: 플래시 로직 재구현 없이 검증된 스크립트를 `QProcess` 로 호출·스트리밍.
  - DFU·앱 모두 → `flash_new_board.py --fw <이미지>`(DFU면 bootstub 복구+DFU 직접 플래시, 앱이면 통상
    flash, 서명 검증). 부트스텁 갇힘 복구 → `flash_panda.py --recover`.
  - 상태 자동 감지(`Panda.list()`/`PandaDFU.list()`) mode 표시, 2대↑는 모호로 플래시 차단.
  - 플래시 전 확인 대화상자, 앱 재플래시 시 force-pin 경고([[biguamr-canrelay-flash-new-board]] 함정).
  - 경로는 `__file__` 기준 절대 → **cwd 무관**(다른 폴더에서 실증). 프레임워크 PyQt5 5.15.3.
  - **진행 막대**(`QProgressBar`, 불확정 busy) — 플래시/복구 실행 중 이동, 유휴 0% / 완료 100%.
    (출력 형식이 경로마다 달라 정확 %는 불안정 → busy 채택.)
- **UI 분리**: `ui/flash_gui.py`(뷰: 위젯·상호작용) ↔ `ui/flash_backend.py`(로직: 감지·경로·argv, Qt
  미의존) 로 분리. 저장소 관례(`src/Comm/CAN/can_relay/can_relay/ui/` 의 app↔backend, 레이아웃 규약
  "UI 는 …/ui/ 에 종속")를 따른다.
- **검증**: `py_compile` OK(2파일). `/tmp` 에서 헤드리스(`QT_QPA_PLATFORM=offscreen`) 구성 —
  `detect()`=('app','4e002c…')·버튼 상태·경로 해석·GUI 구성 실증(cwd 무관 확인).
- **미검증**: 실제 클릭 → 플래시 완주 E2E 는 표시 장치에서 1회 대기(호출 스크립트는 검증본).
- ⚠ **정정 경위**: 최초 구현은 `Tools/Can_Relay/flash_gui.py` **단일 파일(뷰+로직 혼재, 루트 배치)**
  로 UI 분리 원칙을 어겼다. 사용자 지적으로 위 2파일 구조로 재배치. 실수 기록 `docs/claude-mistake/2026-09-02-001`.
