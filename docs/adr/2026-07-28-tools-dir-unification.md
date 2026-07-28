# ADR 2026-07-28 — 루트 도구 폴더 `Tools/` 단일화 종결

Status: Accepted (사용자 지시 sess:9826be4b 2026-07-28: "Tool  Tools폴더 통일 앞으로 Tools로 하도록가이드 문서 수정 부탁 그리고 폴더도 병합부탁" → "Tools로 가이드 문서 [싹] 찾아서 고치세요" → "내가 바꾸는 것이 중요하지 깃은 나중에 해결하면 되는 것이잖아 / 바꾼다고 해결 못해?")

## Context (배경)

루트 도구 폴더의 이름이 세 갈래(`tools/` · `Tools/` · `Tool/`)로 흔들려 왔다.

- 2026-07-27 — 사용자의 `tools/` + `Tools/` 병합 지시에 대해 지목된 두 디렉토리만 보고
  전수 조사를 건너뛰어 대상 2건을 놓쳤다([2026-07-27-004](../claude-mistake/2026-07-27-004_repo-wide-dir-survey-skipped.md)).
  같은 세션에 정본을 `Tools/`(복수)로 재확정했으나 **정리가 끝나지 않은 채 남았다**.
- 2026-07-28 세션 시작 시점의 잔존 상태:
  - `Tool/`(단수) 디렉토리가 살아 있었다. 내용물은 타 세션 OMC 런타임 상태 5파일뿐
    (`Tool/Can_Relay/panda-firmware/.omc/…`, `Tool/docking_field_kit/.omc/…`, 68 KiB),
    소스·git 추적 파일 **0건**(`git ls-files Tool` → 0).
  - 루트 `.gitignore` 의 판다 펌웨어 산출물 규칙 4줄이 `Tool/…` 경로여서 **매칭 0건인 죽은 규칙**이었다.
    유출은 없었다 — 실제 무시는 상류 저장소 자체 파일(`Tools/Can_Relay/panda-firmware/.gitignore:4,14`)이 하고 있었다.
  - 소문자 `tools/` 로 **현재 저장소를 가리키는 깨진 경로**가 문서·스크립트 다수에 남아 있었다.
    `tools/` 디렉토리는 저장소에 존재하지 않으므로 전부 실행·도달 불가 경로였다.
  - 벤더 소스 `src/Sensors/Camera/RGBD/OrbbecSDK_ROS2/orbbec_camera/tools/` 가 소문자로 남아 있었다.

## Decision (결정)

1. **정본은 `Tools/`(대문자 T·복수) 하나.** 루트에 `Tool/`·`tools/` 를 신설하지 않는다.
   새 도구는 예외 없이 `Tools/<도구명>/` 아래.
2. **`Tool/`(단수) 삭제로 병합 종결.** 삭제 전 내용물을 확인해 소스 0건임을 확정한 뒤 제거했다.
3. **`.gitignore` 죽은 규칙 정정** — `Tool/Can_Relay/panda-firmware/…` 4줄 → `Tools/…`.
   격리 임시 저장소에서 4줄 단독으로 `.o`·`.elf` IGNORED / `.c` TRACKED 를 검증했다.
4. **소문자 `tools/` 현재 경로 오기 전면 정정** — 아래 §변경 목록.
5. **벤더 소스도 예외로 두지 않는다.** `orbbec_camera/tools/` → `Tools/` 개명 + `CMakeLists.txt` 6줄 수정.
   근거: 이 저장소에는 **서브모듈·상류 원격이 없다**(`git submodule status` 0건, `.gitmodules` 부재,
   `OrbbecSDK_ROS2/.git` 부재, remote 는 `origin` 하나). 구 이름이 merge 로 되돌아올 경로가 없으므로
   "upstream merge 가 깨진다" 는 이 저장소에서 성립하지 않는다. 상류 신버전을 들여올 때 재적용한다.
6. **적용 범위는 이 저장소 경로뿐.** 타 PC(Personal Computer)·타 저장소 경로(amap-2 호스트,
   GitHub `kuks2309/CAN-Relay`, 이식 원본 T-Robotics AMR-Motion)는 우리 규약이 미치지 않으므로
   **고치지도, 주석을 달지도 않는다.**
7. **과거 문서의 `Tool/` 표기 중 특정 커밋 시점 경로 인용은 고치지 않는다.**
   (예: "커밋 `fdc1c51` 의 `Tool/amr_test_gui/`" — 그 커밋에서는 실제로 `Tool/` 이 맞다.)

## 변경 목록

**디렉토리**

| 대상 | 조치 |
| --- | --- |
| `Tool/` (루트) | 삭제 (내용물 = 타 세션 `.omc/` 상태 5파일, git 추적 0건) |
| `src/…/orbbec_camera/tools/` | → `Tools/` 개명 |

**소문자 `tools/` → `Tools/` 경로 정정 (현재 저장소를 가리키던 깨진 경로)**

| 파일 | 내용 |
| --- | --- |
| `Tools/firmware/README.md:6-7` | 이중화 위치·배포본 경로 |
| `Tools/panda_bench/seer_gate_bench.py:19` | 실행 예시 명령 |
| `Tools/panda_bench/docking_scenario_bench.py:20` | 실행 예시 명령 |
| `docs/usb_cctv/README.md:80,85,113` | 벤치 스크립트 경로 → `Tools/usb_cam_bench/…` (실제 위치) |
| `Tools/docking_field_kit/NEXT-SESSION-PROMPT.md` | 프롬프트·핵심파일 목록 6곳 |
| `Tools/docking_field_kit/MIGRATION-orin-nx.md` | 본 저장소 지칭 3곳 |
| `Tools/Can_Relay/FIELD-RECORD-2026-07-25.md:113` | 번들 이중화 위치 |
| `docs/can_relay/field-record-orin-nx-2026-07-25.md:97` | 번들 이중화 위치 |
| `docs/claude_guideline/code_review/review.md:210` | `<패키지루트>` 예시를 본 저장소 규약으로 |

**규약 문서**

| 파일 | 내용 |
| --- | --- |
| `README.md` | §디렉토리 배치 규약 — 정본·금지·적용 범위·벤더 소스·신규 도구 절차 표 + 병합 이력 |
| `CLAUDE.md` | §저장소 디렉토리 배치 — 매 세션 주입되는 진입점에 동일 규칙 (`kuks_agent_setup` 관리 블록 **바깥**에 배치해 setup 스크립트에 덮이지 않게 함) |
| `.gitignore` | 판다 펌웨어 산출물 규칙 4줄 경로 정정 |

## Verification (검증)

| 항목 | 결과 |
| --- | --- |
| 루트 도구 폴더 단일성 | `find . -maxdepth 1 -type d -iname 'tool*'` → `./Tools` 1건 |
| 소문자 `tools` 디렉토리 | 저장소 전역 **0건** |
| orbbec 빌드 | `colcon build --packages-select orbbec_camera` → **exit 0**, 1min 43s |
| orbbec 산출물 | `Tools/` 소스에서 나오는 타깃 6개 전부 설치 확인 — `list_devices_node`, `list_depth_work_mode_node`, `list_camera_profile_mode_node`, `topic_statistics_node`, `frame_latency_node`, `libframe_latency.so` |
| 빌드 에러 | 0건 (로그의 error 매칭 2건은 Orbbec SDK 의 `Error.hpp`·`Error.h` **파일명**) |
| 파이썬 docstring 수정분 | `python3 -m py_compile Tools/panda_bench/*.py` PASS |
| 정정 경로 실재 | 새로 써 넣은 경로 14개 전부 `-e` 확인 |
| `.gitignore` 패턴 | 격리 임시 저장소에서 `.o`·`.elf` IGNORED / `.c` TRACKED |

## Consequences (결과)

**긍정**
- 저장소 내 도구 경로 표기가 `Tools/` 하나로 수렴. 문서의 실행 예시 명령이 실제로 동작한다
  (이전에는 `python3 tools/panda_bench/…` 가 존재하지 않는 경로였다).
- `.gitignore` 의 의도가 실제로 작동한다.

**부정·잔여 부채**
- `orbbec_camera` 는 벤더 SDK 다. 상류 신버전을 다시 들여오면 `tools/` 가 되살아나므로
  **그 시점에 개명을 재적용**해야 한다. 자동 감지 장치는 없다.
- 본 커밋에 포함된 `src/Sensors/Camera/RGBD/OrbbecSDK_ROS2/orbbec_camera/CMakeLists.txt` 는
  **고아 파일**이다 — 해당 패키지 나머지가 저장소에 추적되지 않은 상태라 이 파일 혼자로는
  빌드되지 않는다. 변경 이력 보존 목적으로만 커밋한다.
- 규약에 **강제 장치가 없다**(`⟦권고⟧`). 루트 `checks/`·pre-commit·CI 가 모두 미설치라
  (CLAUDE.md 상단 "강제 장치 미설치 고지" 참조) 소문자 `tools/` 재발을 기계적으로 막지 못한다.
  향후 `find . -maxdepth 1 -type d -iname 'tool*'` 단일성 검사를 pre-commit 에 거는 것이 후보.

## 관련 기록

- 실수: [2026-07-28-010](../claude-mistake/2026-07-28-010_upstream-merge-blocker-unverified.md) — 검증 없는 "upstream merge 가 깨진다" 부정형 단정
- 실수: [2026-07-28-011](../claude-mistake/2026-07-28-011_out-of-scope-annotation-creep.md) — 범위 외 경로에 불필요한 주석 추가
- 선행 실수: [2026-07-27-004](../claude-mistake/2026-07-27-004_repo-wide-dir-survey-skipped.md) — 전수 조사 누락
