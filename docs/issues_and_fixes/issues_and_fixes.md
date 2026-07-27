# 이슈 및 수정 기록 (Issues and Fixes)

---

## 2026-07-27

### [Fix] 로봇 단독 전원 인가 시 Seer CAN/모터 알람 지속 — 판다 부팅 기본 비트레이트 500 kbps

- **문제**: 호스트 소프트웨어를 **하나도 실행하지 않은 채** 전원만 인가하면 Seer 가 `52106 odo data lost` + `52111 motor driver connection error` + `54022 CAN1 Bit Recessive error`(10 초마다 타임스탬프 갱신 = 진행 중) + `54301 Motor is calibrating` 을 지속 발생. 판다 health 는 `safety_mode=0`·`power_save=1`·`car_harness_status=1`·`faults=0`.
- **원인**: 세 가지가 겹침 — ① `Tool/Can_Relay/panda-firmware/board/drivers/harness.h:91` `set_intercept_relay(false)`("keep busses connected by default")로 **릴레이가 버스를 물리 연결**(Seer↔모터 직결, 펌웨어 포워딩 무관) ② `board/main.c:405-406` `can_silent = ALL_CAN_LIVE` + 루프마다 `enable_can_transceivers(true)` 로 **판다가 그 버스에 live 로 부착** ③ `board/drivers/can_common.h:164-166` `.can_speed = 5000U` = **500 kbps**(버스는 250 kbps). 단위 근거: `usb_comms.h:322` 가 `wIndex` 를 그대로 저장, `panda/python/__init__.py:550` 이 `speed*10` 송신. ⇒ 250k 버스에 500k 로 붙은 live 노드가 전 프레임을 오독해 에러 프레임을 방출, 버스 파괴. **호스트 도구가 take() 에서 `set_can_speed_kbps(b,250)` 을 부르기 때문에 지금까지 가려져 있었다**(= PC 가 붙어야만 버스가 성립하는 구조).
- **해결**: `bus_config[]` 의 bus0/1/2 `can_speed` `5000U`→`2500U`(250 kbps). 함께 ① heartbeat 상실 블록(`main.c`)에 `set_intercept_relay(false)` + `pc_authority = false` 추가 — 이상 상태에서 릴레이가 intercept 로 남지 않도록(fail-open, 사용자 요구) ② `safety/safety_seer_gate.h` freeze 집합에 `0x6041` 추가(Seer SDO 폴 12초 실측으로 확정: `0x6064` 2718~2920회·`0x6041` 66~312회·`0x6078` 66회, **`0x606C` 0회 = 미폴**). 총 3 파일 소수 라인.
- **파일**: `Tool/Can_Relay/panda-firmware/board/drivers/can_common.h`, `.../board/main.c`, `.../board/safety/safety_seer_gate.h`, `docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md`(신규)
- **상태**: 완료 — 빌드 `-Werror` 0 error → 플래시 → **비트레이트 미설정 상태로** 8초 29,625 프레임 수신(부팅 기본 250 kbps 확정) · Seer `errors=[]` 21초+ 유지 · `rx_errs=0 faults=0` · 현장 육안 확인("오류 안남"). ⚠ 펌웨어 version 문자열은 상위 레포 HEAD 에서 오므로(`panda-firmware` 자체 .git 없음) 커밋 전 빌드는 신구 구분 불가 — 현재 플래시본은 `DEV-d98bc1a5-DEBUG` 표기이나 내용은 본 수정 반영본이다.

### [Fix] vision_guard 6대 표시가 16fps로 저하 — 프레임 변환의 BGR→RGB 복사(9.2ms/대)가 렌더 병목

- **문제**: 퍼블리셔 캡처는 29.7fps인데 뷰어 표시는 16~20fps. 6대 동시 표시 시에만 발현.
- **원인**: [실측] 구간 분리 측정 결과 병목 2개. **(주)** `main_window.bgr_to_qimage` 가 `np.ascontiguousarray(frame[:, :, ::-1])`(비연속 스트라이드 복사) + `QImage.copy()` 로 2.76MB 프레임을 **두 번 복사** → 오프스크린 실측 **9.2ms/대**(변환 12.0ms/대 중 76%). 6대×30Hz면 한 틱 72ms 로 30Hz 예산(33ms) 초과 → **렌더 상한 13.9fps**. 실측 CPU도 일치: 프로세스 145%, GUI 메인 스레드 단독 83%. **(부)** raw bgr8 전송 자체 손실 — 아무 것도 안 하는 카운트 전용 구독자(CPU 55%)도 24Hz만 수신(6대 합계 166MB/s, best-effort/depth=1).
- **해결**: Qt 가 BGR 을 직접 읽는 `QImage.Format_BGR888` 로 채널 스왑 복사를 제거하고, numpy 버퍼 수명이 살아있는 함수 내부에서 `QPixmap.fromImage` 로 소유권을 옮기도록 `bgr_to_qimage` → `bgr_to_pixmap` 교체(호출부 `_pump`·`CameraCell.update_frame` 포함 3곳). 대안 비교 실측: 현재 14.3ms → **BGR888 무복사 1.1ms**(12.6배) / cv2 선축소 0.9~2.2ms.
- **파일**: `src/Tools/USB_CCTV/vision_guard/vision_guard/main_window.py`, `.../test/test_frame_convert.py`(신규 — 채널 순서·크기·원본 해제 후 생존·비연속 입력 7 케이스)
- **상태**: 완료. 테스트 **14 passed**(기존 7 + 신규 7), 빌드 클린. 실측: 표시 **20.7~24.1 fps**(6/6), 뷰어 CPU **145% → 85%**. 남은 상한은 (부)의 전송 손실(~24Hz)이며 compressed transport 도입은 미적용(별건).

### [Diag] 뷰어를 kill -9 로 강제 종료하면 퍼블리셔 쓰기가 막혀 일부 카메라가 영구 "No Signal"

- **문제**: 진단 중 뷰어를 `kill -9` 로 수차례 종료한 뒤, 재기동한 뷰어에서 cam0·cam1·cam2·cam5 가 **콜백 0회**("No Signal", 에러 로그 없음). 동시에 해당 4대의 퍼블리셔 캡처 FPS 가 29.7 → 18(순간 0.8까지) 로 동반 저하. cam3·cam4 만 정상.
- **원인**: [증거] 독립 구독자(`rate_probe.py`)는 같은 시각 6토픽 모두 정상 수신 → 발행 자체는 살아있음. 즉 SIGKILL 로 정리 없이 사라진 리더의 FastDDS 공유메모리(`/dev/shm/fastrtps_*`, 40→50개로 증가) 상태가 남아 해당 라이터의 전달·쓰기가 지연된 것. 퍼블리셔는 캡처 스레드에서 `grab → convert → publish` 를 직렬 수행(`usb_cam_publisher_node.cpp:168,192`)하므로 **쓰기 지연이 곧 캡처 FPS 저하**로 나타남.
- **해결**: 퍼블리셔 재기동으로 즉시 정상화(6/6 표시, 캡처 전 카메라 29.7 복귀). 운용 규칙: 뷰어는 **Ctrl+C / SIGTERM 으로 종료**(SIGKILL 금지), 부득이 SIGKILL 한 경우 퍼블리셔도 함께 재기동.
- **파일**: (코드 변경 없음) 관련: `src/Tools/USB_CCTV/usb_cam_publisher/src/usb_cam_publisher_node.cpp`
- **상태**: 원인·회복 절차 확인 완료. ⚠ 미해결: 퍼블리셔의 publish 블로킹이 캡처 루프를 멈추는 구조(캡처·발행 스레드 미분리)는 그대로 — 재발 시 같은 증상 가능.

### [Fix] vision_guard 기동 즉시 abort — opencv-python 이 Qt 플랫폼 플러그인 경로를 오염

- **문제**: `ros2 launch vision_guard vision_guard.launch.py` 실행 시 `qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in ".../cv2/qt/plugins" even though it was found` 후 프로세스 abort(exit -6). 6대 카메라 퍼블리셔는 정상(29.7fps)인데 뷰어만 뜨지 않음.
- **원인**: pip 설치본 `opencv-python 4.10.0`(`~/.local/lib/python3.10/site-packages/cv2`)이 **import 시점에 `QT_QPA_PLATFORM_PLUGIN_PATH` 를 자기 번들 경로로 덮어씀**(실측: import 전 `None` → import 후 `.../cv2/qt/plugins`). 그 번들 `libqxcb.so` 는 cv2 자체 Qt 에 링크돼 시스템 PyQt5(`/usr/lib/aarch64-linux-gnu/qt5/plugins/platforms`)와 호환되지 않아 플랫폼 플러그인 초기화 실패. 발현 경로: `app.py:17` 의 `from .ros_worker import ...` → `ros_worker.py:21` `import cv2` 가 `app.py:23` `QApplication()` 보다 먼저 실행. **외부 환경변수 지정으로는 못 고침** — cv2 가 import 시 다시 덮어쓰는 것을 실측 확인.
- **해결**: `app.py` import 직후·`QApplication` 생성 전에 `os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)` 추가(주석 5줄 + `import os` + pop 1줄). 재현 스크립트로 `platform = xcb` 정상 기동 선검증 후 적용.
- **파일**: `src/Tools/USB_CCTV/vision_guard/vision_guard/app.py`
- **상태**: 완료 (colcon build 성공, 6대 뷰어 `6/6 cameras shown` 실측 확인)

### [Change] USB CCTV 카메라 로스터 6대로 확장 (cam5 = AY4EC5401BT)

- **문제**: 6대 장착 상태인데 roster 에 5대만 등록돼 뷰어에 5분할만 표시.
- **원인**: `config/camera/camera_common.yaml` 로스터 미갱신 — 6번째 시리얼 `AY4EC5401BT`(/dev/video2, usb 1-3.3) 누락.
- **해결**: cam5 항목 추가 + 버스 공유 주석(cam4·cam5 는 둘 다 Bus 001). 6대 동시 구동 실측: 전 카메라 **29.7fps, grab_failures=0** — 기존 문서의 "RGB 최대 4대" 제약(tr-orin-22 단일 USB2.0 컨트롤러 기준)은 이 Tegra 호스트에 미적용임을 재확인.
- **파일**: `config/camera/camera_common.yaml`
- **상태**: 완료

### [Fix] vision_guard(USB_CCTV 뷰어) 메모리 누수 → OOM kill (프레임별 queued signal 무한 적재)

- **문제**: CCTV 5-카메라 내구 테스트 중 GUI `vision_guard` 가 시작 ~1시간 만에 강제 종료(exit code -9=SIGKILL). 동시에 20:32~20:49 5대 publisher FPS 가 0.5~28 로 요동. `journalctl -k`: `20:49:59 Out of memory: Killed process 1195045 (vision_guard) total-vm:24.9GB anon-rss:11.2GB` — vision_guard 가 11.2GB 까지 성장해 OOM killer 가 kill, 그 메모리·스왑 압박 여파로 publisher 캡처 FPS 동반 하락(카메라/USB 결함 아님 — grab_failures=0·stall=0, GUI 사망 후 9시간+ 29.7 FPS 안정).
- **원인**: [실측·증거] `main_window.py:37` `frame_ready = pyqtSignal(str, object)` 를 ROS 스핀 스레드에서 프레임마다 emit(`ros_worker.py:102·125`), GUI 스레드 `_on_frame`(`main_window.py:189`)에 **cross-thread queued connection**(`main_window.py:154`)으로 연결. GUI 렌더(bgr_to_qimage copy+scale+setPixmap)가 유입률(5대×30=150fps, 각 ~2.7MB)을 못 따라가면 **Qt 이벤트 큐에 프레임이 무한 적재**(드롭·백프레셔 없음) → 11GB/1h → OOM. ROS 구독 QoS 는 KEEP_LAST depth=1 로 정상(ROS 큐 누수 아님). 원본 tr-orin-22 는 2대라 누수가 느려 미노출, 5대에서 발현.
- **해결**: 유입률과 렌더율 **분리**. `FrameSignals`(queued signal) → `LatestFrameStore`(스레드 안전 dict, `put`=카메라별 최신 프레임 덮어쓰기·`drain`=GUI가 당겨 비움)로 교체. ros_worker 는 `_store.put(topic, frame)`, GUI 는 `QTimer(30Hz)`로 `_pump` 드레인 렌더. 메모리 상한 = 카메라수×1프레임(구버전 무한 큐 제거). (main_window.py: 클래스 교체+QTimer+_pump, ros_worker.py: emit→put 2곳+docstring, app.py: wiring)
- **파일**: `src/Tools/USB_CCTV/vision_guard/vision_guard/{main_window.py, ros_worker.py, app.py}` (원본 병기: `tr-orin-22:~/Project/Ford_CATL_AMR/src/Tools/USB_CCTV/vision_guard/` 동일 3파일)
- **상태**: 양쪽 완료·검증. **tegra**: 빌드 클린·테스트 7 passed(flake8·pep257 포함)·GUI RSS **268.6MB 80초 완전 평탄(Δ=0)** 실측(구 11GB→OOM 대비 상한 고정)·5대 렌더·소크 무영향. **tr-orin-22(원본)**: 수정 3파일 rsync 전파·빌드 클린·테스트 7 passed(코드 tegra와 동일). ⚠ tr-orin-22 런타임 RSS 미실측(동일 코드라 동작 동일 판단). launch 의 카메라 하드코딩은 누수 무관이라 이번 범위 외.

---

## 2026-07-26

### [Fix] motor_control 리뷰 지적 4건 수정 (E-stop 안전 2 · 브링업 누수 1 · 테스트 레이스 1)

- **문제**: 이식된 `src/Actuators/motor_control/` 코드 리뷰([docs/code_review/motor_control/2026-07-26.md](../code_review/motor_control/2026-07-26.md), Verdict REQUEST CHANGES) High 1·Medium 3. ① `test_cold_bringup_allowed_with_permission` 이 이 Jetson(ARM)에서 8/8 결정적 실패(x86 원격은 통과). ② E-stop 중 조향축이 계속 지령받아 정지 상태에서 물리 스윙 가능. ③ 브링업 예외 시 CAN 버스·rclpy 컨텍스트 누수. ④ E-stop 중 도착한 cmd_vel 이 해제 직후 급발진.
- **원인**: ① `_tx_loop`(backend.py:258)이 생성하는 조향 write 를 tx 데몬 스레드 기동 전에 테스트가 단언 — 스케줄링 레이스(`test_backend.py:126`). ② `_tx_loop`(backend.py:257-259)가 조향 setpoint 를 `_estop` 무관하게 무조건 송신. ③ `main`(driver_node.py:206)의 `node = MotorControlNode()` 가 try/finally 밖 + `__init__` 이 버스 개방(72) 후 `start()`(83) 예외 시 정리 없음. ④ `set_command`(backend.py:131)이 `_estop` 미확인.
- **해결**: ① 테스트를 tx 첫 write 폴링 대기(≤1s)로 견고화(+회귀 테스트 2건 추가). ② `_tx_loop` 에 `estopped` 캡처 후 E-stop 시 조향 setpoint 송신 `continue`(현 위치 hold, 설계문서 §5-4 step-cut 정렬). ③ `__init__` start() 를 try 로 감싸 실패 시 `backend.shutdown()`(버스 close) 재-raise + `main()` 노드 생성 실패 시 `rclpy.shutdown()`. ④ `set_command` 진입부 `if self._estop: return`. (backend.py +5줄, driver_node.py +8줄, test_backend.py +42줄)
- **파일**: `src/Actuators/motor_control/motor_control/backend.py`, `.../motor_control/driver_node.py`, `.../test/test_backend.py` (병기: `src/Actuators/motor_control/docs/code_review/motor_control/2026-07-26.md` findings 상태 [해결])
- **상태**: 로컬 완료 · 원본 반영 **부분(검증 보류)** — 로컬 **31 passed**(원본 29 + 신규 2), 레이스 테스트 8/8 PASS(Jetson), AST 정상. ⚠ 원본과 바이트 동일했던 코드에 **의도적 divergence**. 원본 `amap@amap-2:.../T-Driver-Analysis/src/Motor_Control/` 에 3파일 **rsync 전송 성공**(backend.py·driver_node.py·test_backend.py)했으나, 직후 amap-2 **SSH 도달 불가(오프라인)** 로 원격 pytest 검증·원격 doc 기록·git commit **미완**. 재개 시: (1) 원격 `python3 -m pytest test -q` 31 passed 확인, (2) 원격 docs/issues_and_fixes 동일 기록, (3) 협업 모드 확인 후 commit.

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
- **원인**: **CAN 버스 종단이 모터(Tongyi) 끝 120Ω 하나뿐 = under-termination.** Seer 끝(DB9 2·7번=CAN_L/H) 종단 **없음**(실측 51.6kΩ 개방). 개방단 신호반사 → Bit/Ack/Stuff 에러. 판다는 온보드 종단이 없음(CAN0 pin4·5 / CAN2 pin23·24 실측 개방) — 문서 `Tool/docking_field_kit/PINMAP.md:50`의 "CAN2 온보드 120Ω 내장"은 오기였음(초기 혼선 원인).
- **해결**: **Seer 끝(DB9 2–7번)에 120Ω 종단저항 1개 추가** → 전체 60Ω(양단 120Ω) 정상화. PINMAP.md 종단 문구를 실측대로 정정(판다 종단 없음·Seer끝 120 필수·도킹시 스위칭종단 필요 명시).
- **파일**: `Tool/docking_field_kit/PINMAP.md`(정정), (하드웨어) Seer DB9 종단 120Ω 추가
- **상태**: 완료(판다측 검증) — 종단 60Ω 확인 후 라이브 트래픽 12s(33,278프레임·2,773fps)에서 판다 CAN 에러 전부 0(can_rx/send/fwd_errs Δ0, faults 0). **잔여 확증**: Seer 자체 로그 지속 무에러(수시간~밤샘 관찰) + per-bus 에러카운터(can_health) 위한 펌웨어 보강 예정.
- **[2026-07-27 종결 append]** 위 "잔여 확증" 항목을 닫는다. 그 후로도 간헐 재발하던 Seer CAN 알람의 원인은 **종단이 아니라 판다 부팅 기본 비트레이트 500 kbps** 였다(같은 날짜 상단 entry 참조). 250 kbps 정합만으로 `52106`·`52111`·`54022` 전량 소멸이 실증됐고 펌웨어 기본값을 정정했다. ⇒ **종단 문제는 종결. 이후 CAN 계열 알람에서 종단을 원인 후보로 재제기하지 않는다**(사용자 지시 2026-07-27). 먼저 판다 비트레이트·펌웨어 버전을 확인할 것.

---

## 2026-07-04

### [Fix] python 훅 전체가 한국어 Windows(cp949) 콘솔에서 UnicodeEncodeError 로 조용히 실패

- **문제**: `.claude/settings.json` 에 등록된 python reminder 훅들이 실제 런타임에서 출력 없이 실패 — 게이트 컨텍스트(user_instruction·debt·git_workflow 등)가 세션에 주입되지 않음. kuks_claude_agent_setup 업데이트(git_workflow v1.4.0) 설치 스모크 테스트 중 발견.
- **원인**: Windows 에서 stdout 이 파이프일 때 python 기본 인코딩이 cp949 — 훅 출력의 em-dash(U+2014) 등 cp949 비수록 문자가 `UnicodeEncodeError` 유발. 예: `docs/claude_guideline/git_workflow/hooks/git_workflow-reminder.py:128` 의 `print(DIRECTIVE ...)` (`[GIT-WORKFLOW SOP — 강제 게이트]` 헤더 18번째 문자). 구버전 훅에도 동일 문자 존재 → 신버전 회귀가 아닌 기존 잠재 버그. 검증: 기본 환경에서 user_instruction(exit=1)·debt(exit=1)·git_workflow(crash) 재현.
- **해결**: `.claude/settings.json` 최상위에 `"env": {"PYTHONUTF8": "1"}` 추가 (4줄 추가). 훅 파일은 저장소 원본과 동일하게 유지(diff 0) — 프로젝트 환경 레벨에서 UTF-8 모드 일괄 적용. 세션 재시작 후 발효.
- **파일**: `.claude/settings.json`
- **상태**: 완료 — 등록 훅 10종 전부 `PYTHONUTF8=1` 환경에서 exit=0 확인 (reminder 8종 + git_workflow track·stage-gate). 업스트림(kuks_claude_agent_setup) 훅에 `sys.stdout.reconfigure(encoding="utf-8")` 추가 또는 install.sh 의 settings env 등록 권고.
