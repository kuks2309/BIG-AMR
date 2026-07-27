# ADR 2026-07-27 — Tongyi 4축 AMR 구동 테스트 GUI (`Tool/amr_test_gui`)

Status: Accepted (사용자 지시 sess:56a709a5 2026-07-27: "Tongyi 4축 AMR 구동 테스트용 GUI 구축 … PC가 CAN relay(판다) 경유로 조향·구동·crab을 제어하고, 실시간 상태·IMU·Seer 알람을 표시. 저속·단계 램프·즉시 정지 우선")
선택지 승인: 제어기반=backend+PandaCanBus · 프레임워크=독립 PyQt5 · 배치=`Tool/amr_test_gui`(비-ROS 툴)

## Context (배경)

- 현장 구동 자산이 **두 갈래**로 존재한다.
  - **정본 드라이버** `src/Actuators/motor_control/` — 프로토콜([protocol.py](../../src/Actuators/motor_control/motor_control/protocol.py))·SDO 폴링 마스터([backend.py](../../src/Actuators/motor_control/motor_control/backend.py))·역기구학([kinematics.py](../../src/Actuators/motor_control/motor_control/kinematics.py))·안전게이트(콜드 홈 거부·조향 정착 게이트·cmd 워치독·E-stop 래치)를 모두 보유. 단 버스는 `socketcan can1` **직결** 전제라 relay 경유가 없다.
  - **필드 킷** `Tool/docking_field_kit/docking_drive.py` — 판다 relay 경유는 검증됐으나 프로토콜을 **재구현**했고 피드백 수신·안전게이트가 **전무**하다.
- GUI 요구("노드별 실위치/statusword/error 표시")의 유일한 공급원은 `TongyiSdoBackend.snapshot()` 이다. 필드 킷에는 RX 경로 자체가 없다.
- 지난 세션에 `PandaCanBus`(python-can 호환 어댑터)가 작성됐으나 **scratchpad에만 존재**해 리부팅 시 소실 위험이 있고, backend와의 **통합 실구동 이력이 없다**.
- 지난 세션 사고: node4를 전범위 급점프 지령해 137° 범위 밖 물리 갇힘 → 직결 호밍 복구 필요([docs/claude-mistake/2026-07-27-002](../claude-mistake/2026-07-27-002_node4-unverified-command-damage.md)). GUI는 이 사고 유형을 **구조적으로 불가능**하게 만들어야 한다.

## Decision (결정)

1. **배치·형태**: `Tool/amr_test_gui/` 비-ROS 독립 PyQt5 앱. colcon 빌드 불요, `python3 run_gui.py` 로 즉시 실행. 모터 제어 경로는 rclpy 무의존(정본 import 검증 완료 — `backend`/`kinematics`/`protocol` 은 순수 파이썬).
2. **제어 기반**: `TongyiSdoBackend` + `PandaCanBus`. 프로토콜 정본 1곳 유지(재구현 0). `PandaCanBus` 는 scratchpad에서 **git으로 승격**해 소실을 막는다.
3. **부호 투명 전송 (핵심 결정)** — backend 를 `drive_sign=+1`·`steer_sign=+1` 로 구성해 **항등 변환**으로 만든다. 그 결과:
   - 조향 counts `= steer_home + deg × 57344` — `pc_crab_steer.py` 실측 정본과 **바이트 동일**
   - 구동 raw `= velocity_mps / M_S_PER_UNIT` — 실측 raw 단위(0.1 rpm)와 **1:1**

   방향 의미(전진/crab 좌우)는 backend 파라미터가 아니라 **GUI 계층의 인용 상수**가 소유한다. 각 버튼은 자신의 raw 부호 근거를 문서·UI에 명시한다. 아래 §부호 모순 참조.
4. **단계 램프를 구조적 인터록으로** — `ramp.SteerRamp`(순수 로직, Qt·CAN 무의존):
   - 하드 클램프 **±90°** (구조적으로 137° 지령 불가)
   - 목표까지 **≤30° 단계**로만 전진, 각 단계는 실측 추종(|실측−지령| ≤ 정착허용) 확인 후 다음 단계
   - 단계 기한 내 미추종 → **FAULT 래치**: 지령 홈(0°) 강제 + 구동 금지. 해제는 운전자 명시 `reset()`
   - 정착 전 `drive_allowed=False` (backend 의 정착 게이트와 **이중 방어**)
5. **모드 = (조향각, raw 부호) 쌍의 인용 테이블**. 자유 twist 입력을 노출하지 않는다 — 요구된 위젯(전진/후진/crab 좌우/조향/홈)은 전부 **양 조향축 동일각**이라 램프 스칼라 1개로 충분하고, 검증되지 않은 스핀·복합 기동을 애초에 지령할 수 없다.
6. **dry-run 시뮬레이터 버스** 내장(`--dry-run`) — 하드웨어 없이 UI·램프·FAULT 경로를 검증하는 계단 1단.
7. **관측**: Seer 알람만 GUI 에 포함한다 — `seer_can_monitor` 정본 모듈을 import 해 1050 폴링(읽기 전용, status 포트 19204), **실패 시 graceful 비활성**(관측 부재가 제어를 막지 않는다). Seer 알람은 freeze 펌웨어 파손(55602 계열)을 감지할 수 있는 **유일한 외부 채널**이므로 남긴다.
   IMU 패널은 **채택하지 않는다**(사용자 결정 2026-07-27: "직접 보고 판단할것인데"). 방향 판정은 이미 실측으로 확정돼 있고(§부호 정합), 잔여 확인은 운전자 육안이 담당한다. 필요 시 기존 `imu_log.py`(field kit)를 별도 실행한다.
8. **의존성**: PyQt5(시스템 기설치 확인). License GPL v3/상용 듀얼 — 본 툴은 사내 비배포 테스트 도구라 GPL 충족. 취약점: 배포·네트워크 표면 없음(로컬 GUI). 대안 검토 — PySide2(LGPL, 동등 기능이나 프로젝트 내 사용례 없음), tkinter(의존 0이나 실시간 테이블·슬라이더 UX 열위), 웹(FastAPI: 신규 의존 + E-stop 네트워크 단절 리스크로 물리 구동에 부적합).

## 부호 정합 (초안의 '모순' 판단은 철회)

본 ADR 초안은 아래 두 실측을 "기하학적으로 동시에 참일 수 없다"고 적었으나, **그 판단은 틀렸다.**

| 근거 | 주장 |
| --- | --- |
| [tongyi_amr.yaml:14](../../src/Actuators/motor_control/config/tongyi_amr.yaml#L14) `drive_sign:-1` · [docking_drive.py:93](../../Tool/docking_field_kit/docking_drive.py#L93) `{1:-s,2:-s} # 전진=음(실측)` | 홈(조향 counts=home)에서 **raw 음수 = 전진** |
| 2026-07-27 crab 실측(IMU ay 출발+1.0/정지−1.6) | 조향 **+90° counts** + **raw 양수(+2445)** → **왼쪽(+y)** |

빠뜨린 자유도는 조향 counts↔물리 회전방향의 부호(`kin_steer_sign` — config 스스로 `⚠ 가정`으로 표시)다.
**조향 +counts 가 CW(−θ)** 이면 +90° counts 지령은 바퀴를 −y 로 향하게 하고, 모터 극성(홈에서 raw 음수가
전진 ⇒ raw 양수는 바퀴 지향의 반대)에 의해 이동은 +y(왼쪽)가 된다 — **두 실측이 정확히 정합한다.**

따라서 본 GUI 가 쓰는 모든 방향은 **이미 실측으로 확정된 상태**다. GUI 는 twist→모듈 변환을 쓰지 않고
실측과 동일한 언어(조향 counts · 구동 raw)로 직접 지령하므로 `kin_steer_sign` 의 영향을 받지 않는다.
남는 미확정은 `kin_steer_sign` 자체이며, 이는 `driver_node` 의 twist·오도메트리 경로 소관이다 → `debt-004`.

## Safety (안전 게이트 — 다층)

| 층 | 방어 |
| --- | --- |
| 지령 생성 | 조향 ±90° 하드 클램프 · 속도 상한 200 mm/s(=4889 units, `VEL_MAX`) · 기본 50 mm/s |
| 램프 | ≤30° 단계 · 단계별 실측 추종 확인 · 미추종 시 FAULT 래치 → 홈 강제·구동 금지 |
| backend | 콜드 브링업 거부(`allow_homing_motion=False` 기본) · 조향 정착 게이트(구동 0) · cmd 워치독 0.2 s · E-stop 래치(조향 신규 setpoint 억제) |
| relay | heartbeat 0.4 s 유지. 상실 시 펌웨어가 `SAFETY_SILENT` 로 복귀하고(2026-07-27 수정으로 `set_intercept_relay(false)`+`pc_authority=false` 동반), 하네스 릴레이가 물리 통과라 Seer↔모터 버스는 유지된다 |
| 운전자 | E-STOP 버튼 최상단 + Space 키 · 창 종료·예외 경로 전부 release 보장 |

**검증 계단(순서 고정)**: ① `--dry-run` UI·램프·FAULT 경로 → ② 잭업(바퀴 뜬 상태) 조향만 ±30 → ±60 → ±90 → ③ 저속(≤50 mm/s) 직진 → ④ 저속 crab. 각 단계 실측 확인 전 다음 단계 금지.

## Consequences (결과)

- (+) 프로토콜 정본 단일화 — GUI 가 판다 사일로 재구현을 늘리지 않는다.
- (+) 램프가 순수 로직이라 실차 없이 단위 테스트로 137° 사고 유형을 회귀 방지.
- (+) `PandaCanBus` 가 git 에 보존됨(소실 위험 제거).
- (−) **backend↔PandaCanBus 통합 relay 실구동은 미검증** — 검증 계단 ①②를 반드시 거쳐야 한다(`debt-005`).
- (−) guard RTR 은 판다가 송신 불가라 skip — intercept 중 Seer guard 가 gate 로 forward 되어 유지된다는 **가정에 의존**(`debt-006`).
- (−) 자유 twist·스핀 미지원(의도적 범위 축소). 필요 시 램프를 모듈별 벡터로 확장해야 한다.

## Rollback (롤백)

가역. `Tool/amr_test_gui/` 디렉터리 삭제로 완전 복귀한다 — **기존 파일 수정 0건**, 영속 상태·스키마·펌웨어 변경 0건, 정본 `motor_control` 은 읽기 전용 import 만 한다. 런타임 롤백은 GUI 의 `release`, 또는 프로세스 종료 시 heartbeat 소실 → 펌웨어가 `SAFETY_SILENT` 복귀 + `set_intercept_relay(false)`·`pc_authority=false`(2026-07-27 수정)로 Seer 주도권이 돌아온다.
