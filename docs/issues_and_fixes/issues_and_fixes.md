# 이슈 및 수정 기록 (Issues and Fixes)

---

## 2026-07-29

### [Fix] 패키지 안에 중첩 colcon 워크스페이스 생성 + 테스트가 환경 소싱 없이는 미실행

- **문제**: ① `src/Comm/CAN/can_relay/` 안에 `build/`·`install/`·`log/` 가 생겨 **중첩
  워크스페이스**가 됐다(412 KB). ② 테스트가 `PYTHONPATH=.` 또는 `source install/setup.bash`
  없이는 `ModuleNotFoundError: No module named 'can_relay'` 로 수집 단계에서 죽었다.
- **원인**: ① Bash 작업 디렉터리가 호출 간 유지되는데, 패키지 디렉터리로 `cd` 한 상태에서
  `colcon build` 를 실행했다(`src/Comm/CAN/can_relay/log/build_2026-07-29_14-02-35/…/command.log`
  가 그 경로에서 invoke 됐음을 기록). ② `test/` 에 경로 부트스트랩이 없었다 — 저장소 선례
  `src/Actuators/motor_control/test/test_protocol.py:5-8` 은 각 파일에서 `sys.path.insert` 를
  한다.
- **해결**: ① 세 디렉터리 삭제(git 추적 0건, 루트 워크스페이스에 정본 산출물 별도 존재 확인 후).
  ② `test/conftest.py` 신설(11줄) — 파일마다 3줄을 반복하는 대신 한 곳에 모았다.
- **파일**: `src/Comm/CAN/can_relay/test/conftest.py`(신설) · 산출물 디렉터리 3개 삭제
- **상태**: 완료 — 세 실행 방식 전부 확인: 저장소 루트·환경 미소싱 **84 passed** / 패키지
  디렉터리 **84 passed** / 설치 환경 소싱 **84 passed**. 재빌드 후 중첩 산출물 재발 **0건**.

### [Fix] 「호밍은 소프트웨어가 멈출 수 없다」 과장 서술 3곳 — S6 게이트가 검출

- **문제**: 오늘 신설한 `can_relay` 의 docstring 3곳이 "호밍은 시작하면 소프트웨어가 멈출 수
  없다(드라이브 내부 루틴)" 고 단정했다. 운전자가 **중단 수단이 원리적으로 없다**고 읽게 되는
  서술이다.
- **원인**: 원문 대조 없이 `Tools/amr_test_gui/gui.py:921-922` 의 확인 대화상자 문구
  ("이 **프로그램이** 중간에 멈출 수 없습니다")를 **범위를 넓혀** 옮겼다. 실제로는
  `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:307-309`
  `seer_home_cancel_frames()` 가 `0x60FB:04 = 0`(호밍 중단)을 송신하는 경로가 **실재**하며,
  USB `0xea` wValue=0 으로 기동된다. 즉 "불가능"이 아니라 **본 구현이 그 경로를 안 쓰는 것**이다.
- **해결**: 3곳을 "불가능" → "본 구현에 취소 경로가 없다(미구현)" 으로 정정하고 펌웨어 경로를
  `파일:줄` 로 병기(각 3~6줄). 주장 범위를 구현 단위로 좁힌 것이 핵심이다.
- **파일**: `src/Comm/CAN/can_relay/can_relay/backend.py`(모듈 docstring · `home()`) ·
  `src/Comm/CAN/can_relay/can_relay/driver_node.py`
- **상태**: 완료 — 검출 경로가 자동이었다는 점이 중요하다. 같은 날 추가한 S6 게이트
  (`review-claim-lint.py`)가 **도입 직후 전수 검사에서 이 3곳을 잡았다**. 사람이 다시 읽어서
  찾은 것이 아니다. 재검사 `TOTAL FAIL 0건 — PASS`, 회귀 `84 passed`.

### [Fix] review-claim-lint 에 S6 추가 + 검사 대상을 소스 주석까지 확대

- **문제**: 검증 명령 없는 절대형 부정 단정이 반복 재발하는데 기계 검사가 없었다
  (`docs/claude-mistake/2026-07-28-005`, `2026-07-29-003`). 기존 lint 는 S1~S5 뿐이고 검사
  대상도 `docs/code_review/*.md` 로 한정돼 **소스 주석·docstring 이 사각지대**였다.
- **원인**: `docs/claude_guideline/code_review/checks/review-claim-lint.py` 의 검사 항목 부재.
- **해결**: S6(절대형 부정 ↔ 근거 병기) 추가, `.md` 는 S1~S6 / 그 외는 S6 만 적용.
  설계 조정 3건은 **전부 실측으로 확정**했다 — ① 근거 인정 범위를 리뷰 SOP 룰 8 과 동일하게
  (도구 호출·결과 **또는** `파일:줄` 인용): 전자만 인정했더니 기존 통과 산출물
  `docs/code_review/can_relay_firmware/2026-07-28.md` 에 신규 FAIL 3건이 생겼고 원문 대조 결과
  **3건 전부 오탐**이었다. ② 일반형 "할 수 없다"·"알 수 없다" 제외 — 인용된 사실에서 끌어낸
  결과 서술이라 오탐이 된다(`docs/code_review/trnav-icp-odometry/2026-07-28.md:256` 실측).
  ③ 따옴표 쌍 매칭 수정 — `"된다" 만 … "안 된다·불가능하다"` 에서 짝이 어긋나 인용 안의
  부정을 놓쳤다(`docs/claude-mistake/INDEX.md:64` 오탐). 인용 **밖** 부정은 계속 잡는다.
  게이트 자체 회귀 `--selftest` 10건을 인라인 픽스처로 내장했다(S4 가 금지하는 절대경로 없이
  저장소에서 재현 가능).
- **파일**: `docs/claude_guideline/code_review/checks/review-claim-lint.py` ·
  `docs/claude_guideline/code_review/review.md`(VERSION 1.3.0 → 1.4.0, 자체 점검 8-1 추가)
- **상태**: 완료 — `--selftest` **10/10 PASS**, 저장소 리뷰 산출물 6종 + 오늘 산출물 + 소스
  전수 `TOTAL FAIL 0건 — PASS`. 사용자 승인 2026-07-29(SSOT 번들 §변경 절차).

### [Fix] can_relay 신설 중 자체 결함 3건 + 검증 명령 없는 부정형 단정 2곳

> 대상은 **오늘 신설한** `src/Comm/CAN/can_relay` 다. 기존 코드에서 발견한 결함
> (조향 클램프 부재·NaN·단발 송신·피드백 신선도)은 **이번에 고치지 않았고** 부채로 등록했다
> (debt-025~019) — 소유 세션이 다르거나 실기 검증이 선행돼야 하기 때문이다.

- **문제**:
  - ① 신설 테스트 2건 FAIL — `test_write_controlword_exact`,
    `test_write_fault_reset_enable` 이 `AssertionError: '2b4060003f000000' == '2b40603f00000000'`.
  - ② `ros2 launch` 시 파라미터 미로드 위험 — config YAML 첫 줄이 `_#` 로 시작해 주석이 아닌
    스칼라로 파싱된다.
  - ③ 제어권 반환 후 종료 시 오류 로그 2줄
    (`LinkError: 제어권 없이 프레임을 보내려 했다`)이 매번 출력. 기능은 정상이나 정지 실패로
    오독될 수 있는 노이즈.
  - ④ 부정형 단정에 확인 명령 미병기 — "gui.py 에는 이 시퀀스가 없다"를 근거 명령 없이 서술.
    이 저장소가 반복해 당한 실패 유형이다(`docs/claude-mistake/2026-07-28-005`).
- **원인**:
  - ① 기대 hex 를 원본 대조 없이 작성 — SDO(Service Data Object) 프레임 배치는
    `[cmd, idx_lo, idx_hi, **sub**, payload…]` 인데 **sub 바이트를 빠뜨린** 기대값을 썼다.
    코드가 맞고 테스트가 틀린 경우다 — 근거 `Tools/amr_test_gui/gui.py:833`.
  - ② 파일 작성 시 오타 — `config/can_relay.yaml:1`.
  - ③ `backend.stop()`·`shutdown()` 이 링크 제어권 상태를 보지 않고 무조건 송신을 시도 —
    `src/Comm/CAN/can_relay/can_relay/backend.py` `stop()`. 노드 종료 경로가
    `~/engage false` 와 겹쳐 이미 반환된 링크에 다시 쐈다.
  - ④ `protocol.py` `drive_init_frames` docstring · `config/can_relay.yaml` 주석.
- **해결**:
  - ① 기대값을 실제 배치로 정정(2줄). **코드는 바꾸지 않았다** — 인코더 28종이 실측 캡처
    `Log/homing_capture_220350.jsonl` 과 바이트 동일함을 별도 대조로 확인했다(12,958건 일치).
  - ② `_#` → `#` (1줄).
  - ③ `stop()`·`shutdown()` 에 `if self.link.engaged:` 가드 + `shutdown()` 멱등화(9줄 추가).
    지령 자체(속도 0)는 제어권과 무관하게 **항상 확정**되도록 유지 — 정지가 거부되면 안 된다.
    회귀 2건 추가(`test_stop_target_is_zero_even_without_authority`,
    `test_shutdown_is_idempotent`).
  - ④ 실행한 grep 과 결과(0건)를 인라인 병기하고 **주장의 범위 한계**까지 명시
    ("gui.py 가 controlword 를 아예 안 쓰는 것은 아니다 — `gui.py:942` 는 조향축 호밍 전용")(10줄).
- **파일**: `src/Comm/CAN/can_relay/test/test_protocol.py` ·
  `src/Comm/CAN/can_relay/config/can_relay.yaml` ·
  `src/Comm/CAN/can_relay/can_relay/backend.py` ·
  `src/Comm/CAN/can_relay/can_relay/protocol.py` ·
  `src/Comm/CAN/can_relay/test/test_backend.py`
- **상태**: 완료 — `PYTHONPATH=. python3 -m pytest test -q` → **84 passed in 1.64s**,
  `colcon build --packages-select can_relay` → **1 package finished [3.08s]**,
  YAML 파싱 확인 → 파라미터 20개 로드. ④ 는 `docs/claude-mistake/2026-07-29-003` 에 별도 기록
  (강제 메커니즘 S6 적용으로 `status: closed`. 미채택 항목은 debt-030 으로 이관).


## 2026-07-28

### [Fix] 호밍 기록의 잘못된 서술 정정 + 정오표 수립 (2회 적대적 검증)

- **문제**: 2026-07-27 호밍 조사에서 생성된 기록 다수가 (a) `0x6041` bit15 **전이 시각**을 폴 상한값으로
  확정형 서술 (b) `Tool/`(단수) 경로 인용 (c) `0x6040` 반복률 「~50 Hz」 (d) 호밍 중 write 정지 범위를
  조향축으로 과소 서술 — 로 부정확했다. 더해 **정정하려고 만든 정오표(v1) 자체가 신규 오류 7건을 심었다**
  (정확한 Handbook 인용을 「오진」으로 규정 등).
- **원인**: ① 폴링 관측값을 이벤트 시각으로 취급(직전 폴 간격 미확인) — `Log/homing_capture_220350.jsonl`
  node3 `0x6041` 최대 폴 간격 12.818 s ② 한 노드 결과를 전 노드로 일반화 ③ v1 작성 시 원문 재대조 없이
  기억·요약에 의존해 **정확한 인용을 틀렸다고 판정**(자기 표와 모순).
- **해결**: 원문(`pdftotext -f N -l N`) 재대조로 쪽 사실을 확정하고 v2 정오표로 전면 개정.
  저장소 잔여 서술 11건 정정(전이 시각 → 「0 최초 관측」 + 확정 구간 병기, `Tool/`→`Tools/`),
  `docs/debt/registry.md:146` 의 `0x6040=0x86` 「enable」 오라벨을 「fault reset(+enable voltage)」로 정정
  (Bit7 rising edge = Fault Reset, `Enable Operation`(0x0F) 아님).
  미해결 항목은 **debt-008**(Handbook 1차 source 내부 DI 번호 충돌)·**debt-009**(캡처 출처·12.62 s
  무응답 구간 미확정)로 등록.
- **검증**: 40 에이전트 적대적 재검증(wf_83c55976-efe) → v1 작성 → **10 에이전트가 v1 을 공격**
  (wf_ea102b6e-a7c, 비-CONFIRMED 51건·신규오류 7건 검출) → v2. 각 레인이 캡처를 직접 재파싱하고
  PDF 를 각자 재추출. 이전 실패 레인(`cap-digital-in`) 재수행 완료.
- **파일**: `docs/verified_facts/2026-07-28-errata.md`(신규 v2), `docs/debt/registry.md`,
  `docs/verified_facts/2026-07-27.md`, `docs/ros2_driver/2026-07-09-design-inputs.md`,
  `References/Tongyi-Motor-Controller/docs/tongyi-motor-protocol-tables.md`,
  `References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md`,
  `Tools/docking_field_kit/amap2_monitor.py`, `Tools/docking_field_kit/HANDOFF-amap2.md`
- **상태**: 완료 (미해결분은 debt-008·debt-009 로 이관)

---


## 2026-07-27

### [Fix] vision_guard 6대 표시가 16fps로 저하 — 프레임 변환의 BGR→RGB 복사(9.2ms/대)가 렌더 병목

- **문제**: 퍼블리셔 캡처는 29.7fps인데 뷰어 표시는 16~20fps. 6대 동시 표시 시에만 발현.
- **원인**: [실측] 구간 분리 측정 결과 병목 2개. **(주)** `main_window.bgr_to_qimage` 가 `np.ascontiguousarray(frame[:, :, ::-1])`(비연속 스트라이드 복사) + `QImage.copy()` 로 2.76MB 프레임을 **두 번 복사** → 오프스크린 실측 **9.2ms/대**(변환 12.0ms/대 중 76%). 6대×30Hz면 한 틱 72ms 로 30Hz 예산(33ms) 초과 → **렌더 상한 13.9fps**. 실측 CPU도 일치: 프로세스 145%, GUI 메인 스레드 단독 83%. **(부)** raw bgr8 전송 자체 손실 — 아무 것도 안 하는 카운트 전용 구독자(CPU 55%)도 24Hz만 수신(6대 합계 166MB/s, best-effort/depth=1).
- **해결**: Qt 가 BGR 을 직접 읽는 `QImage.Format_BGR888` 로 채널 스왑 복사를 제거하고, numpy 버퍼 수명이 살아있는 함수 내부에서 `QPixmap.fromImage` 로 소유권을 옮기도록 `bgr_to_qimage` → `bgr_to_pixmap` 교체(호출부 `_pump`·`CameraCell.update_frame` 포함 3곳). 대안 비교 실측: 현재 14.3ms → **BGR888 무복사 1.1ms**(12.6배) / cv2 선축소 0.9~2.2ms.
- **파일**: `src/Sensors/Camera/USB/ui/vision_guard/vision_guard/main_window.py`, `.../test/test_frame_convert.py`(신규 — 채널 순서·크기·원본 해제 후 생존·비연속 입력 7 케이스)
- **상태**: 완료. 테스트 **14 passed**(기존 7 + 신규 7), 빌드 클린. 실측: 표시 **20.7~24.1 fps**(6/6), 뷰어 CPU **145% → 85%**. 남은 상한은 (부)의 전송 손실(~24Hz)이며 compressed transport 도입은 미적용(별건).

### [Diag] 뷰어를 kill -9 로 강제 종료하면 퍼블리셔 쓰기가 막혀 일부 카메라가 영구 "No Signal"

- **문제**: 진단 중 뷰어를 `kill -9` 로 수차례 종료한 뒤, 재기동한 뷰어에서 cam0·cam1·cam2·cam5 가 **콜백 0회**("No Signal", 에러 로그 없음). 동시에 해당 4대의 퍼블리셔 캡처 FPS 가 29.7 → 18(순간 0.8까지) 로 동반 저하. cam3·cam4 만 정상.
- **원인**: [증거] 독립 구독자(`rate_probe.py`)는 같은 시각 6토픽 모두 정상 수신 → 발행 자체는 살아있음. 즉 SIGKILL 로 정리 없이 사라진 리더의 FastDDS 공유메모리(`/dev/shm/fastrtps_*`, 40→50개로 증가) 상태가 남아 해당 라이터의 전달·쓰기가 지연된 것. 퍼블리셔는 캡처 스레드에서 `grab → convert → publish` 를 직렬 수행(`usb_cam_publisher_node.cpp:168,192`)하므로 **쓰기 지연이 곧 캡처 FPS 저하**로 나타남.
- **해결**: 퍼블리셔 재기동으로 즉시 정상화(6/6 표시, 캡처 전 카메라 29.7 복귀). 운용 규칙: 뷰어는 **Ctrl+C / SIGTERM 으로 종료**(SIGKILL 금지), 부득이 SIGKILL 한 경우 퍼블리셔도 함께 재기동.
- **파일**: (코드 변경 없음) 관련: `src/Sensors/Camera/USB/usb_cam_publisher/src/usb_cam_publisher_node.cpp`
- **상태**: 원인·회복 절차 확인 완료. ⚠ 미해결: 퍼블리셔의 publish 블로킹이 캡처 루프를 멈추는 구조(캡처·발행 스레드 미분리)는 그대로 — 재발 시 같은 증상 가능.

> ⚠ **[2026-07-27 감사 부기 — 기전은 미검증 가설]** (원문 무변경)
> 위 "원인" 절의 "SIGKILL 로 사라진 리더의 FastDDS 공유메모리 상태가 남아 해당 라이터의 전달·쓰기가 지연된 것" 은 **"…지연됐을 가능성이 크다(미검증 가설)"** 로 읽어야 한다. 제시된 근거는 (a) 독립 구독자 정상 수신 (b) `/dev/shm/fastrtps_*` 40→50 개 증가 두 정황뿐이고, 인과를 확인한 재현 시험이 없다. 실제 해결도 원인 제거가 아닌 **퍼블리셔 재기동**이었고(위 "해결" 절), 같은 entry 의 "상태" 절도 구조적 원인이 남아 있음을 스스로 적고 있다.
> 따라서 "해결" 절의 **SIGKILL 금지 운용 규칙은 "기전 미확정 — 예방적 규칙"** 으로 병기한다(규칙 자체는 유지: 비용이 낮고 회복 절차가 확인돼 있음).
> **판정에 필요한 측정**: ① SIGTERM 종료 N회 vs SIGKILL 종료 N회 후 뷰어 콜백 수신 여부 대조 ② SIGKILL 후 잔존 `/dev/shm/fastrtps_*` **정리만으로** 회복하는지(퍼블리셔 재기동 없이) 확인.

### [Fix] vision_guard 기동 즉시 abort — opencv-python 이 Qt 플랫폼 플러그인 경로를 오염

- **문제**: `ros2 launch vision_guard vision_guard.launch.py` 실행 시 `qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in ".../cv2/qt/plugins" even though it was found` 후 프로세스 abort(exit -6). 6대 카메라 퍼블리셔는 정상(29.7fps)인데 뷰어만 뜨지 않음.
- **원인**: pip 설치본 `opencv-python 4.10.0`(`~/.local/lib/python3.10/site-packages/cv2`)이 **import 시점에 `QT_QPA_PLATFORM_PLUGIN_PATH` 를 자기 번들 경로로 덮어씀**(실측: import 전 `None` → import 후 `.../cv2/qt/plugins`). 그 번들 `libqxcb.so` 는 cv2 자체 Qt 에 링크돼 시스템 PyQt5(`/usr/lib/aarch64-linux-gnu/qt5/plugins/platforms`)와 호환되지 않아 플랫폼 플러그인 초기화 실패. 발현 경로: `app.py:17` 의 `from .ros_worker import ...` → `ros_worker.py:21` `import cv2` 가 `app.py:23` `QApplication()` 보다 먼저 실행. **외부 환경변수 지정으로는 못 고침** — cv2 가 import 시 다시 덮어쓰는 것을 실측 확인.
- **해결**: `app.py` import 직후·`QApplication` 생성 전에 `os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)` 추가(주석 5줄 + `import os` + pop 1줄). 재현 스크립트로 `platform = xcb` 정상 기동 선검증 후 적용.
- **파일**: `src/Sensors/Camera/USB/ui/vision_guard/vision_guard/app.py`
- **상태**: 완료 (colcon build 성공, 6대 뷰어 `6/6 cameras shown` 실측 확인)

### [Change] USB CCTV 카메라 로스터 6대로 확장 (cam5 = AY4EC5401BT)

- **문제**: 6대 장착 상태인데 roster 에 5대만 등록돼 뷰어에 5분할만 표시.
- **원인**: `config/camera/camera_common.yaml` 로스터 미갱신 — 6번째 시리얼 `AY4EC5401BT`(/dev/video2, usb 1-3.3) 누락.
- **해결**: cam5 항목 추가 + 버스 공유 주석(cam4·cam5 는 둘 다 Bus 001). 6대 동시 구동 실측: 전 카메라 **29.7fps, grab_failures=0** — 기존 문서의 "RGB 최대 4대" 제약(tr-orin-22 단일 USB2.0 컨트롤러 기준)은 이 Tegra 호스트에 미적용임을 재확인.
- **파일**: `config/camera/camera_common.yaml`
- **상태**: 완료

> ⚠ **[2026-07-27 감사 부기 — 6대 무손실 주장은 조건부]** (원문 무변경 · 로스터 값 무변경)
> 위 "해결" 절의 "6대 동시 구동 실측 29.7fps · grab_failures=0 ⇒ 'RGB 최대 4대' 제약 미적용 재확인" 은 다음 두 이유로 **조건부**로 읽어야 한다.
> - 이 entry 가 수정한 바로 그 파일이 상반된 문구를 **미정정 상태로 유지**한다: `config/camera/camera_common.yaml:22` "HARDWARE LIMIT: 단일 USB 2.0 컨트롤러라 RGB 최대 4대", `:23` "이 호스트에 실제 연결된 Gemini E **4대**" — 실제 로스터는 `:26-38` 의 cam0~cam5 **6대**. (어느 쪽이 옳은지는 여기서 판정하지 않는다. 값·주석은 해당 파일 담당 범위.)
> - 같은 파일 `:39-40` 은 "**5대** 실측 검증", `:41-42` 는 "cam4·cam5 는 둘 다 Bus 001 공유이므로 **6대 동시 구동 시 이 두 대의 FPS/grab 실패를 우선 관찰할 것**" 이라 적어 6대 조건을 **열린 관찰 대상**으로 남겨둔다.
> - 또 본 entry 의 6대 측정에는 **조건이 기재돼 있지 않다**(해상도·픽셀포맷·측정 지속시간·동시 뷰어 유무).
> **판정에 필요한 측정**: 6대 동시 구동을 해상도·픽셀포맷(`camera_common.yaml:14-17` 기준)·지속시간을 명기해 재측정하고, cam4/cam5(Bus 001 공유)의 FPS·`grab_failures` 를 별도로 기록.

---

## 2026-07-26

### [Diag] emulate 내구 중 Seer 52954(zeroing/재호밍 timeout) 1회 — zeroDI 하드웨어 아님, 기동 전환 트랜지언트로 추정

- **문제**: `emulate_endurance.py` 내구(2026-07-26 09:05~13:00, emulate firmware, engage180s/diseng5s) 중 Seer API 1050 알람에 **52954 "Motor calibration/zeroing timeout"(ERROR) 1회**(desc 09:29:19). 재호밍(원점복귀) 타임아웃.
- **원인**: [실측·증거] appendix 002 매뉴얼의 일반원인(zeroDI 원점스위치 손상/오설치)은 **이 런 증거로 미지지**. 실제 인과사슬 = **첫 engage 전환(09:08) 순간 emulate 인수 전 수초 모터 통신 순단** → Seer가 모터침묵 감지(동시각 52111 motor timeout·52106 odo lost·54022 stuff, `seermon_endur.log` 09:08:42~43) → 자동 재호밍(54301 calibrating) 시작 → **emulate 경로가 실 원점센서(zeroDI) 피드백 미제공** → 시작+약20분 뒤 zeroing 카운트다운 만료로 52954(09:29). 09:29 시점 판다측 모터응답 정상(endur cyc7/8 급감0)=신규 통신갭 아님=09:08 zeroing의 종착점. 이후 59사이클 급감0·무재발. 근거모델: `docs/can_relay/field-record-orin-nx-2026-07-25.md:47,137`(모터응답/guard 상실=재호밍 방아쇠).
- **해결**: [미확정·검증대기] 코드 변경 없음. zeroDI 하드웨어 고장 가설 배제 위해 **실로봇 전원사이클 재현**(emulate 없이 실 Seer 재기동 → zeroing 정상완료=52954 미발생 확인) 예정. 정상완료 시 "emulate 기동 전환 트랜지언트"로 확정, 재발 시 실 zeroDI 점검. ⚠안전: Seer 전원복구=조향 물리 재호밍 동반(field-record §5-4), 가동범위 주변 클리어 후 수행.
- **파일**: (분석) `~/docking_reliability/seermon_endur.log`, `~/docking_reliability/endur_out.log`, `T-Robot_seer_gui/references/seer/robokit-api/appendix/002-alarm-code.md:183`; (재현도구) `~/Project/CAN-Relay/docking_field_kit/seer_powercycle_repro.py`(신규 작성·검증)
- **상태**: 진단 완료 · **재현검증 미실시(다음 세션 재개 필요)**. 내구는 76사이클 완주 PASS(모터급감 0, `endur_out.log` 13:00:12 종료요약). 전원사이클 재현 모니터 2회 기동(13:01·14:52, 각 10분 창)했으나 **양 창 모두 실 전원 OFF→ON 미수행**으로 zeroDI 하드웨어 가설 확정/배제 못함. **재개 절차**: (안전-조향 재호밍 물리이동 주변 클리어) → `python3 ~/Project/CAN-Relay/docking_field_kit/seer_powercycle_repro.py 192.168.44.82 600` 실행 후 Seer 전원 OFF→수초→ON → 판정(zeroing 완료=배제 / 52954 재발=하드웨어).

---

## 2026-07-24

### [Fix] amap-2 현장 CAN 버스 단절오류 다발 — Seer 끝 종단저항(120Ω) 누락

- **문제**: 실 로봇 Foil_A082에서 CAN1(모터) 버스에러 다발(2026-07-23 23:13~24 01:05, 1h52m). Seer 알람 54022(Ack 250·Bit Recessive 183·Bit Dominant 104·Stuff 7 = 544회), 52111 모터 응답타임아웃(4개 동시 302회), 52106 odo lost 408회, 54301 재캘리 347회. 로봇 정지 중 발생, 수 초 내 자동복구 반복. Seer는 "check CAN router"만 지목, 원인 특정 못함. 판다측 모니터도 트래픽만 봐서 못 잡음.
- **원인**: **CAN 버스 종단이 모터(Tongyi) 끝 120Ω 하나뿐 = under-termination.** Seer 끝(DB9 2·7번=CAN_L/H) 종단 **없음**(실측 51.6kΩ 개방). 개방단 신호반사 → Bit/Ack/Stuff 에러. 판다는 온보드 종단이 없음(CAN0 pin4·5 / CAN2 pin23·24 실측 개방) — 문서 `tools/docking_field_kit/PINMAP.md:50`의 "CAN2 온보드 120Ω 내장"은 오기였음(초기 혼선 원인).
- **해결**: **Seer 끝(DB9 2–7번)에 120Ω 종단저항 1개 추가** → 전체 60Ω(양단 120Ω) 정상화. PINMAP.md 종단 문구를 실측대로 정정(판다 종단 없음·Seer끝 120 필수·도킹시 스위칭종단 필요 명시).
- **파일**: `tools/docking_field_kit/PINMAP.md`(정정), (하드웨어) Seer DB9 종단 120Ω 추가
- **상태**: 완료(판다측 검증) — 종단 60Ω 확인 후 라이브 트래픽 12s(33,278프레임·2,773fps)에서 판다 CAN 에러 전부 0(can_rx/send/fwd_errs Δ0, faults 0). **잔여 확증**: Seer 자체 로그 지속 무에러(수시간~밤샘 관찰) + per-bus 에러카운터(can_health) 위한 펌웨어 보강 예정.

---

## 2026-07-04

### [Fix] python 훅 전체가 한국어 Windows(cp949) 콘솔에서 UnicodeEncodeError 로 조용히 실패

- **문제**: `.claude/settings.json` 에 등록된 python reminder 훅들이 실제 런타임에서 출력 없이 실패 — 게이트 컨텍스트(user_instruction·debt·git_workflow 등)가 세션에 주입되지 않음. kuks_claude_agent_setup 업데이트(git_workflow v1.4.0) 설치 스모크 테스트 중 발견.
- **원인**: Windows 에서 stdout 이 파이프일 때 python 기본 인코딩이 cp949 — 훅 출력의 em-dash(U+2014) 등 cp949 비수록 문자가 `UnicodeEncodeError` 유발. 예: `docs/claude_guideline/git_workflow/hooks/git_workflow-reminder.py:128` 의 `print(DIRECTIVE ...)` (`[GIT-WORKFLOW SOP — 강제 게이트]` 헤더 18번째 문자). 구버전 훅에도 동일 문자 존재 → 신버전 회귀가 아닌 기존 잠재 버그. 검증: 기본 환경에서 user_instruction(exit=1)·debt(exit=1)·git_workflow(crash) 재현.
- **해결**: `.claude/settings.json` 최상위에 `"env": {"PYTHONUTF8": "1"}` 추가 (4줄 추가). 훅 파일은 저장소 원본과 동일하게 유지(diff 0) — 프로젝트 환경 레벨에서 UTF-8 모드 일괄 적용. 세션 재시작 후 발효.
- **파일**: `.claude/settings.json`
- **상태**: 완료 — 등록 훅 10종 전부 `PYTHONUTF8=1` 환경에서 exit=0 확인 (reminder 8종 + git_workflow track·stage-gate). 업스트림(kuks_claude_agent_setup) 훅에 `sys.stdout.reconfigure(encoding="utf-8")` 추가 또는 install.sh 의 settings env 등록 권고.
