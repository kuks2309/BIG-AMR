# ADR 2026-07-27 — Tongyi 4축 AMR 구동 테스트 GUI (`Tools/amr_test_gui`)

Status: Accepted (사용자 지시 sess:56a709a5 2026-07-27: "Tongyi 4축 AMR 구동 테스트용 GUI 구축 … PC가 CAN relay(판다) 경유로 조향·구동·crab을 제어하고, 실시간 상태·IMU·Seer 알람을 표시. 저속·단계 램프·즉시 정지 우선")
선택지 승인: 제어기반=backend+PandaCanBus · 프레임워크=독립 PyQt5 · 배치=`Tools/amr_test_gui`(비-ROS 툴)

## Context (배경)

- 현장 구동 자산이 **두 갈래**로 존재한다.
  - **정본 드라이버** `src/Actuators/motor_control/` — 프로토콜([protocol.py](../../src/Actuators/motor_control/motor_control/protocol.py))·SDO 폴링 마스터([backend.py](../../src/Actuators/motor_control/motor_control/backend.py))·역기구학([kinematics.py](../../src/Actuators/motor_control/motor_control/kinematics.py))·안전게이트(콜드 홈 거부·조향 정착 게이트·cmd 워치독·E-stop 래치)를 모두 보유. 단 버스는 `socketcan can1` **직결** 전제라 relay 경유가 없다.
  - **필드 킷** `Tools/docking_field_kit/docking_drive.py` — 판다 relay 경유는 검증됐으나 프로토콜을 **재구현**했고 피드백 수신·안전게이트가 **전무**하다.
- GUI 요구("노드별 실위치/statusword/error 표시")의 유일한 공급원은 `TongyiSdoBackend.snapshot()` 이다. 필드 킷에는 RX 경로 자체가 없다.
- 지난 세션에 `PandaCanBus`(python-can 호환 어댑터)가 작성됐으나 **scratchpad에만 존재**해 리부팅 시 소실 위험이 있고, backend와의 **통합 실구동 이력이 없다**.
- 지난 세션 사고: node4를 전범위 급점프 지령해 137° 범위 밖 물리 갇힘 → 직결 호밍 복구 필요([docs/claude-mistake/2026-07-27-002](../claude-mistake/2026-07-27-002_node4-unverified-command-damage.md)). GUI는 이 사고 유형을 **구조적으로 불가능**하게 만들어야 한다.

## Decision (결정)

1. **배치·형태**: `Tools/amr_test_gui/` 비-ROS 독립 PyQt5 앱. colcon 빌드 불요, `python3 run_gui.py` 로 즉시 실행. 모터 제어 경로는 rclpy 무의존(정본 import 검증 완료 — `backend`/`kinematics`/`protocol` 은 순수 파이썬).
2. **제어 기반**: `TongyiSdoBackend` + `PandaCanBus`. 프로토콜 정본 1곳 유지(재구현 0). `PandaCanBus` 는 scratchpad에서 **git으로 승격**해 소실을 막는다.
3. **부호 투명 전송 (핵심 결정)** — backend 를 `drive_sign=+1`·`steer_sign=+1` 로 구성해 **항등 변환**으로 만든다. 그 결과:
   - 조향 counts `= steer_home + deg × 57344` — ~~`pc_crab_steer.py` 실측 정본과 **바이트 동일**~~
     > ⚠ **2026-07-27 정정(원문 이력 보존)**: 이 대조는 **불능**이다.
     > `pc_crab_steer.py` 는 저장소·파일시스템·git 이력 어디에도 **존재하지 않는다**
     > (`find /home/nvidia -name 'pc_crab_steer*'` → 0 건, `git log --all -- '*pc_crab_steer*'` → 0 건,
     > 2026-07-27 재확인). 저장소 내 문자열 언급은 본 줄과
     > `Tools/amr_test_gui/amr_test_gui/ramp.py:10-19` 뿐이며, 그 파일도 이미 같은 사유로
     > 「⚠ 2026-07-27 정정 — 위 취소선 인용은 **확인 불가**」라고 자기 정정을 달아 두었다.
     > ⇒ 「실측 정본과 바이트 동일」 주장은 **인용 불능**으로 철회한다.
     > 스케일 상수 `57344` 자체도 본 세션 미재검증이다 — `docs/verified_facts/2026-07-27.md` §C
     > 「`COUNTS_PER_DEG=57344` · `VEL_PER_MMPS=24.447` · `M_S_PER_UNIT` 등 스케일 상수」(= 이 세션에서
     > 검증하지 않은 것). **수식·상수는 바꾸지 않았다** — 근거 상태만 정정한다.
     > **판정에 필요한 측정**: 잭업 상태에서 단계 램프로 알려진 각도(예 +30°)를 지령하고 0x6064 counts
     > 변화량 / 각도 = 57344 인지 실측 대조.
   - 구동 raw `= velocity_mps / M_S_PER_UNIT` — 실측 raw 단위(0.1 rpm)와 **1:1**
     (⚠ `M_S_PER_UNIT` 도 verified_facts §C 의 미재검증 스케일 상수 목록에 포함)

   방향 의미(전진/crab 좌우)는 backend 파라미터가 아니라 **GUI 계층의 인용 상수**가 소유한다. 각 버튼은 자신의 raw 부호 근거를 문서·UI에 명시한다. 아래 §부호 모순 참조.
4. **단계 램프를 구조적 인터록으로** — `ramp.SteerRamp`(순수 로직, Qt·CAN 무의존):
   - 하드 클램프 **±90°** (~~구조적으로 137° 지령 불가~~)
     > ⚠ **2026-07-27 정정 — 조건 명시(원문 이력 보존)**: 클램프는 **각도**에 걸리고, 그 각도는
     > `steer_home_counts` 를 기준으로 counts 에서 환산된다 —
     > `Tools/amr_test_gui/amr_test_gui/constants.py:97-99`
     > `return (counts - STEER_HOME_COUNTS[node]) / COUNTS_PER_DEG`.
     > 그런데 **그 홈 기준 자체가 미판정이다** —
     > `src/Actuators/motor_control/config/tongyi_amr.yaml` 「⚠ debt-007 판정 전까지 무비판 신뢰 금지」
     > 및 같은 파일 상단 「미판정 상태이므로 어느 쪽으로도 값을 고치지 않는다」,
     > `docs/verified_facts/2026-07-27.md` §B-1 「조향 홈 기준(`steer_home_counts`) ⚠ 안전 직결 —
     > 서로 어긋나는 관측」(판다 read 는 node3 ≈ −1,517 / node4 ≈ +1,161 counts 인데 config 상수는
     > 7,871,815 / 7,840,086, `design-inputs.md:56,81` 은 부팅 시 0x6064≈0 이 정상이고 홈 상수는
     > 절대 목표(steerOffset 137.3°)라고 한다).
     > `constants.py:16-19` 도 같은 경고를 이미 달고 있다.
     > ⇒ **성립 조건**: 「±90° 클램프가 137° 지령을 막는다」는 **`steer_home_counts` 가 그 시점에
     > 유효할 때만** 참이다. 홈 기준이 137° 어긋난 상태라면 "0°~±90°" 지령이 물리적으로 137° 대역을
     > 가리킬 수 있으므로 **"구조적으로 137° 지령 불가" 는 무조건 성립하지 않는다.**
     > ⇒ ~~**실제 방어선은 backend 의 콜드 브링업 거부 게이트**(`allow_homing_motion=False` — 홈에서 5°
     > 이상 이탈 시 브링업 거부)다.~~ `tongyi_amr.yaml` 「사용 규칙(판정 전까지): allow_homing_motion
     > 게이트를 **끄지 말 것**. 그 게이트가 이 불일치를 잡아내는 방어선이다. 끄고 진행하면 137° 지령이
     > 나갈 수 있다」. **이 게이트를 끄지 말 것.**
     >
     > **⚠ 2026-07-27 재정정 — 이 게이트를 「실제 방어선」으로 부르지 말 것 (원문 이력 보존. 코드 무변경)**
     > - 게이트는 `_write_init_sequence()` **이전에 1 회만** 판정하는 사전 검사다
     >   (`src/Actuators/motor_control/motor_control/backend.py:185-187` —
     >   `_preflight_read() → _gate_homing_motion() → _write_init_sequence()`).
     > - 그 init 시퀀스가 조향 노드에 `0x6099=2500`(Homing Speeds)·`0x60FB.4=1` 을
     >   **게이트 통과 여부와 무관하게 무조건** 쓴다(`backend.py:362`, `:368`; `:367` 주석
     >   「⚠ allow_homing_motion 게이트는 홈 이탈만 보므로 웜 상태에서도 이 줄은 실행된다」).
     >   `0x60FB.4` = **RstStart(호밍 개시)**, "0-Reset off, 1-Reset on" [Handbook V7.0 §6.9, page 171].
     > - 실기에서 이 두 write 는 곧바로 물리 호밍을 개시한다 — `0x60FB.4=1`(t=17.925) → `0x6064` 가 0 으로
     >   약 31 s 고정 → 음의 리밋 물림(`0x6000:01` bit3, t≈47.02) → `0x6041` bit15 0→1(t≈49.0) →
     >   `0x607A`=조향 0° 목표(t≈49.14) → 약 3 s 복귀 이동(`Log/homing_capture_220350.jsonl`).
     >
     > ⇒ **게이트가 켜져 있어도(웜 판정으로 통과해도) 호밍·복귀 스윙 경로는 열려 있다.**
     > (i) 게이트는 계속 **끄지 말 것**, (ii) 다만 이를 「실제 방어선」으로 부르지 말 것,
     > (iii) 호밍 완료(`0x6041` bit15 0→1 복귀 + `0x6000:01` bit3 해제)까지 `0x607A` 송신을 보류하는
     > 게이트를 **별도로 추가**할 것.
     >
     > **부수 정정(위 인용문 중)**: `design-inputs.md:56,81` 의 「부팅 시 `0x6064`≈0 이 정상」은 **오류**다 —
     > `0x6064`=0 은 **호밍 진행 중 카운터 리셋** 상태이며(같은 캡처 t≈18.0~49.2), 캡처 시작 시점 실판독은
     > node3 7,882,014(137.4513°) / node4 7,859,058(137.0511°) 였다. 또한 콜드부팅 137° 스윙은 이상거동이
     > 아니라 **호밍 완료 후 음의 리밋(원점)에서 조향 0° 로 복귀하는 설계된 이동**이다(복귀 목표
     > node3 7,882,020 / node4 7,859,062 counts ↔ EasyDRIVE `steerOffset` 138.000/137.250, 57344 counts/°).
     > 조향축에 **리밋 스위치는 실재**하고 방식은 **Home 1(음의 리밋 트리거)** — 전 노드 `0x6098 = 1`
     > 실기 판독으로 확정(2026-07-27; Handbook V7.0 §4.6 printed page 116). **`steer_home_counts` 상수
     > 불일치(debt-007) 자체는 여전히 미판정**이므로 위 클램프 성립조건 논지는 그대로 유효하다.
   - 목표까지 **≤30° 단계**로만 전진, 각 단계는 실측 추종(|실측−지령| ≤ 정착허용) 확인 후 다음 단계
   - 단계 기한 내 미추종 → **FAULT 래치**: 지령 홈(0°) 강제 + 구동 금지. 해제는 운전자 명시 `reset()`
   - 정착 전 `drive_allowed=False` (backend 의 정착 게이트와 **이중 방어**)
5. **모드 = (조향각, raw 부호) 쌍의 인용 테이블**. 자유 twist 입력을 노출하지 않는다 — 요구된 위젯(전진/후진/crab 좌우/조향/홈)은 전부 **양 조향축 동일각**이라 램프 스칼라 1개로 충분하고, 검증되지 않은 스핀·복합 기동을 애초에 지령할 수 없다.
6. **dry-run 시뮬레이터 버스** 내장(`--dry-run`) — 하드웨어 없이 UI·램프·FAULT 경로를 검증하는 계단 1단.
7. **관측**: Seer 알람만 GUI 에 포함한다 — `seer_can_monitor` 정본 모듈을 import 해 1050 폴링(읽기 전용, status 포트 19204), **실패 시 graceful 비활성**(관측 부재가 제어를 막지 않는다). Seer 알람은 freeze 펌웨어 파손(55602 계열)을 감지할 수 있는 **유일한 외부 채널**이므로 남긴다.
   IMU 패널은 **채택하지 않는다**(사용자 결정 2026-07-27: "직접 보고 판단할것인데"). ~~방향 판정은 이미 실측으로 확정돼 있고(§부호 정합)~~ (⚠ 2026-07-27 정정: 실측된 방향은 **전진·crab 좌측
2 건뿐**이고 후진·crab 우측은 미측정 추론이다 — §부호 정합 정정 블록 참조), 잔여 확인은 운전자 육안이 담당한다. 필요 시 기존 `imu_log.py`(field kit)를 별도 실행한다.
8. **의존성**: PyQt5(시스템 기설치 확인). License GPL v3/상용 듀얼 — 본 툴은 사내 비배포 테스트 도구라 GPL 충족. 취약점: 배포·네트워크 표면 없음(로컬 GUI). 대안 검토 — PySide2(LGPL, 동등 기능이나 프로젝트 내 사용례 없음), tkinter(의존 0이나 실시간 테이블·슬라이더 UX 열위), 웹(FastAPI: 신규 의존 + E-stop 네트워크 단절 리스크로 물리 구동에 부적합).

## 부호 정합 (초안의 '모순' 판단은 철회)

본 ADR 초안은 아래 두 실측을 "기하학적으로 동시에 참일 수 없다"고 적었으나, **그 판단은 틀렸다.**

| 근거 | 주장 |
| --- | --- |
| [tongyi_amr.yaml:14](../../src/Actuators/motor_control/config/tongyi_amr.yaml#L14) `drive_sign:-1` · [docking_drive.py:93](../../Tools/docking_field_kit/docking_drive.py#L93) `{1:-s,2:-s} # 전진=음(실측)` | 홈(조향 counts=home)에서 **raw 음수 = 전진** |
| 2026-07-27 crab 실측(IMU ay 출발+1.0/정지−1.6) | 조향 **+90° counts** + **raw 양수(+2445)** → **왼쪽(+y)** |

빠뜨린 자유도는 조향 counts↔물리 회전방향의 부호(`kin_steer_sign` — config 스스로 `⚠ 가정`으로 표시)다.
**조향 +counts 가 CW(−θ)** 이면 +90° counts 지령은 바퀴를 −y 로 향하게 하고, 모터 극성(홈에서 raw 음수가
전진 ⇒ raw 양수는 바퀴 지향의 반대)에 의해 이동은 +y(왼쪽)가 된다 — **두 실측이 정확히 정합한다.**

~~따라서 본 GUI 가 쓰는 모든 방향은 **이미 실측으로 확정된 상태**다.~~ GUI 는 twist→모듈 변환을 쓰지 않고
실측과 동일한 언어(조향 counts · 구동 raw)로 직접 지령하므로 `kin_steer_sign` 의 영향을 받지 않는다.
남는 미확정은 `kin_steer_sign` 자체이며, 이는 `driver_node` 의 twist·오도메트리 경로 소관이다 → `debt-004`.

> ### ⚠ 2026-07-27 정정 — "모든 방향이 실측 확정" 은 과장 (원문 이력 보존)
>
> **실제로 측정된 방향은 2 건뿐이다** (위 표 그대로):
> 1. 홈(조향 counts = home)에서 **raw 음수 = 전진**
> 2. 2026-07-27 crab 실측(IMU ay): 조향 **+90° counts + raw 양수(+2445) → 왼쪽(+y)**
>
> **측정되지 않은 것**: **후진**(1의 부호반전 추론), **crab 우측**(2의 부호반전 추론).
> 부호반전은 물리적으로 그럴듯하지만 **측정이 아니다** — 이 프로젝트에서 "그럴듯한 추론"을 확정으로
> 적었다가 실장비가 손상됐다(`docs/claude-mistake/2026-07-27-002`).
>
> **정합 논증(위 문단)이 의존하는 가정**: 「조향 **+counts 가 CW(−θ)**」. 이 가정은 저장소 정본과
> **반대 방향**이다 —
> `src/Actuators/motor_control/config/tongyi_amr.yaml` `kin_steer_sign: 1  # +counts = +θ(CCW) ⚠ 가정`,
> `Tools/Kinematics/chassis_kinematics.py:33` `KIN_STEER_SIGN = +1  # +counts = +θ(CCW) 가정 — 실차 검증 필요`.
> (`driver_node.py` 의 `kin_steer_sign` 주석은 「실측은 -1 을 시사(직접 관측 미완)」라고 적어 또 갈린다.)
> ⇒ 두 실측이 "정확히 정합한다"는 결론은 **CW 가정이 참일 때만** 성립하며, 그 가정은 **미판정**이다.
> (두 실측이 서로 모순이 아니라는 것 — 즉 초안의 '모순' 판단 철회 — 은 유효하다. 정합의 *메커니즘*이
> 미판정이라는 뜻이다.)
>
> **인용 규칙 위반 주의**: `docs/verified_facts/2026-07-27.md` §C 는 「구동 raw 부호(전진=음수)·crab
> 좌우 방향 — 이전 세션 실측, **본 세션 미재현**」으로 분류하고, 같은 문서 §사용규칙 2 는 「§B 항목은
> "확정"으로 인용하지 않는다」고 정한다.
>
> ⇒ **정정된 서술**: 「GUI 가 쓰는 방향 중 실측된 것은 (홈, raw 음수)=전진 과 (+90° counts, raw 양수)=왼쪽
> **두 건**이다. 후진·crab 우측은 부호반전 **추론**이며 미측정이다.」
> **판정에 필요한 측정**: 잭업 → 저속(≤50 mm/s) 상태에서 ① raw 양수 직진이 실제 후진인지 육안 확인,
> ② 조향 −90° counts + raw 양수가 오른쪽(−y)인지 IMU ay 부호로 확인.
> **미측정 방향(후진·crab 우측)은 §검증 계단 ③④ 에서 처음 사용할 때 반드시 실측 확인 후 진행할 것.**
> (그 결과가 나오면 `verified_facts` §A 에 추가하고 이 절도 갱신한다.)

## Safety (안전 게이트 — 다층)

| 층 | 방어 |
| --- | --- |
| 지령 생성 | 조향 ±90° 하드 클램프(⚠ **조건부** — 아래 주 참조) · 속도 상한 200 mm/s(=4889 units, `VEL_MAX`) · 기본 50 mm/s |
| 램프 | ≤30° 단계 · 단계별 실측 추종 확인 · 미추종 시 FAULT 래치 → 홈 강제·구동 금지 |
| backend | 콜드 브링업 거부(`allow_homing_motion=False` 기본 — ⚠ **호밍·복귀 스윙은 막지 못함**, 아래 주 참조) · 조향 정착 게이트(구동 0) · cmd 워치독 0.2 s · E-stop 래치(조향 신규 setpoint 억제) |
| relay | heartbeat 0.4 s 유지. 상실 시 펌웨어가 `SAFETY_SILENT` 로 복귀하고(2026-07-27 수정으로 `set_intercept_relay(false)`+`pc_authority=false` 동반), 하네스 릴레이가 물리 통과라 Seer↔모터 버스는 유지된다 |
| 운전자 | E-STOP 버튼 최상단 + Space 키 · 창 종료·예외 경로 전부 release 보장 |

> ⚠ **2026-07-27 주 — ±90° 클램프의 성립 조건**: 이 클램프는 각도 기준이며, 각도는
> `steer_home_counts` 로 counts↔deg 환산된다(`constants.py:97-99`). 그 홈 기준은 **debt-007 미판정**
> 이다(`docs/verified_facts/2026-07-27.md` §B-1, `tongyi_amr.yaml` 「debt-007 판정 전까지 무비판 신뢰
> 금지」). 홈 기준이 어긋난 상태에서는 클램프가 137° 지령을 막는다는 보장이 없다.
> ~~**판정 전까지의 실제 방어선은 backend 의 콜드 브링업 거부 게이트(`allow_homing_motion=False`)이며,
> 이 게이트를 끄지 말 것.**~~ ±90° 클램프는 그 게이트 위에 얹은 2차 방어로만 취급한다.
>
> ⚠ **2026-07-27 재정정(원문 이력 보존)**: 게이트는 계속 **끄지 말 것**이나 **「실제 방어선」이 아니다.**
> 게이트는 `_write_init_sequence()` 이전 1 회 사전 검사이고(`src/Actuators/motor_control/motor_control/backend.py:185-187`),
> 그 init 시퀀스가 조향 노드에 `0x6099=2500`·`0x60FB.4=1`(**RstStart = 호밍 개시**,
> "0-Reset off, 1-Reset on" [Handbook V7.0 §6.9, page 171])을 **게이트 통과 여부와 무관하게 무조건**
> 보내 드라이브 호밍과 그에 이은 조향 0° 복귀 이동(리밋 원점 기준 약 137°)을 트리거한다
> (`backend.py:362`, `:368`; 실측 `Log/homing_capture_220350.jsonl` t=17.925 개시 → t≈49.14 복귀 지령).
> ⇒ 필요한 방어는 **호밍 완료 대기 게이트**(`0x6041` bit15 0→1 복귀 + `0x6000:01` bit3 해제 확인 전
> `0x607A` 송신 금지)다. 상세 근거는 §Decision 4 의 재정정 블록 참조.

**검증 계단(순서 고정)**: ① `--dry-run` UI·램프·FAULT 경로 → ② 잭업(바퀴 뜬 상태) 조향만 ±30 → ±60 → ±90 → ③ 저속(≤50 mm/s) 직진 → ④ 저속 crab. 각 단계 실측 확인 전 다음 단계 금지.
(⚠ ③④ 는 **미측정 방향**(후진·crab 우측)을 처음 쓰는 지점이다 — §부호 정합 정정 참조. 방향 확인을 육안·IMU 로 먼저 할 것.)

## Consequences (결과)

- (+) 프로토콜 정본 단일화 — GUI 가 판다 사일로 재구현을 늘리지 않는다.
- (+) 램프가 순수 로직이라 실차 없이 단위 테스트로 137° 사고 유형을 회귀 방지.
- (+) `PandaCanBus` 가 git 에 보존됨(소실 위험 제거).
- (−) **backend↔PandaCanBus 통합 relay 실구동은 미검증** — 검증 계단 ①②를 반드시 거쳐야 한다(`debt-005`).
- (−) guard RTR 은 판다가 송신 불가라 skip — intercept 중 Seer guard 가 gate 로 forward 되어 유지된다는 **가정에 의존**(`debt-006`).
- (−) 자유 twist·스핀 미지원(의도적 범위 축소). 필요 시 램프를 모듈별 벡터로 확장해야 한다.

## Rollback (롤백)

가역. `Tools/amr_test_gui/` 디렉터리 삭제로 완전 복귀한다 — **기존 파일 수정 0건**, 영속 상태·스키마·펌웨어 변경 0건, 정본 `motor_control` 은 읽기 전용 import 만 한다. 런타임 롤백은 GUI 의 `release`, 또는 프로세스 종료 시 heartbeat 소실 → 펌웨어가 `SAFETY_SILENT` 복귀 + `set_intercept_relay(false)`·`pc_authority=false`(2026-07-27 수정)로 Seer 주도권이 돌아온다.
