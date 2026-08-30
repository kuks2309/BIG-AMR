# ADR 2026-07-26 — motor_control 구동축 freewheel(servo-off) 지령 신설

Status: Accepted (사용자 지시 sess:01d0eb18 2026-07-26: "구동바퀴 freewheel 명령 … 구현해주세요")

## Context (배경)

- 현 드라이버는 정지 계열(shutdown·estop·워치독·정착게이트)이 전부 **속도지령 0**이다. 서보가 켜진 채 0 rpm을 붙잡으므로 바퀴에 **홀딩토크(제동)**가 걸린다 → 사람이 밀어 굴리는 **견인/정비(tow)** 불가.
- ~~실측 정본~~([tongyi-canopen-protocol-reference.md](../../References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md) §4, [tongyi-motor-protocol-tables.md](../../References/Tongyi-Motor-Controller/docs/tongyi-motor-protocol-tables.md) §7 지령값 사전 p194)에 **0x6040=0x05 = servo enable 해제(모터 전원 차단 ~~= free spin~~)**가 정의됨. 코드에도 `CW_DISABLE=0x05` 상수만 정의되고 **송신처가 0건**이었다([protocol.py:40](../../src/Actuators/motor_control/motor_control/protocol.py#L40)).

  > ### ⚠ 2026-07-27 정정 — 근거 등급 하향 (원문 이력 보존. 값·로직 변경 0건)
  >
  > **(a) "실측 정본" 라벨은 틀렸다 — 출처는 벤더 매뉴얼이다.**
  > - 인용된 `tongyi-canopen-protocol-reference.md` §4(런타임 오브젝트 전수)의 `0x6040` 행에는
  >   **0x05 가 없다**: 「**0x86**=fault reset/enable(구동축, 기동시 1회), **0x3F**=운전(조향축,
  >   신규setpoint+즉시)」 두 값뿐이다.
  > - 실제 출처는 `tongyi-motor-protocol-tables.md` 의 「**지령값 사전** ([Handbook V7.0,
  >   **Appendix I 0x6040, page 194**])」 표이며, 그 행은 `0x0005 | servo enable 해제(모터 전원 차단)` 이다.
  >   이는 **벤더 문서 정의**이지 이 장비에서 관측한 실측이 아니다.
  > - 코드도 둘을 구분해 적어 두었다 — `src/Actuators/motor_control/motor_control/protocol.py:37`
  >   「Controlword 값 — Seer **실측 관례**」 vs :40 `CW_DISABLE = 0x05  # servo enable 해제
  >   (**Handbook** 0x6040 지령값 사전 p194)`.
  > - 본 ADR 스스로 「송신처가 **0건**」이라 적었다 ⇒ 이 프로젝트에서 0x05 를 실제로 보낸 적이 없으므로
  >   **실측 캡처가 존재할 수 없다.**
  > ⇒ 정정된 서술: 「**벤더 Handbook V7.0 Appendix I p194 정의**(실측 캡처 없음, 0x05 송신 이력 0 건)」.
  >
  > **(b) "모터 전원 차단 = free spin" 등가는 매뉴얼에 없는 추론이다.**
  > 매뉴얼 행의 문구는 "servo enable 해제(모터 전원 차단)" 까지이고 **자유회전 여부는 언급이 없다.**
  > 본 구동계는 감속비 **32**(`src/Control/Motion_Control/2WS/trnav_2ws_core/config/robot_geometry_2ws.yaml`
  > `gear_walk: 32.0`, `chassis_kinematics.py:38` `M_S_PER_UNIT` 주석 「r=0.125 m, reduction=32」)이며,
  > **감속기의 역구동성(back-drivability)은 확인된 바 없다.** 통전이 끊겨도 감속기가 역구동을 막으면
  > 사람이 밀어 굴릴 수 없다(= 본 ADR 의 목적 자체가 달성되지 않는다).
  > ⇒ 정정된 서술: 「전원 차단 시 **자유회전 여부는 미검증**(감속기 역구동성 미확인)」.
  >
  > **(c) statusword 기반 상태 판정을 신뢰하지 말 것** — 같은 매뉴얼 문서가
  > 「⚠ 실측 편차: 운전 중에도 bit6(Switch on disabled)=1 관측(실측 정지값 0x8050/0x9450) — 비표준
  > Controlword 사용의 결과로 추정. **상태 판정표를 그대로 신뢰하지 말 것**」이라고 경고한다
  > (`tongyi-canopen-protocol-reference.md` §9 도 동일 취지). 0x05 송신 후 상태를 statusword 로만
  > 확인하려 하면 오판할 수 있다.
  >
  > **판정에 필요한 측정**: **첫 사용 전 잭업(바퀴 뜬 상태)에서** ① 0x05 송신 → ② 손으로 바퀴를 돌려
  > **실제로 자유회전하는지 육안·촉감 확인** → ③ 0x6064 위치 변화로 회전 여부 교차확인.
  > 결과를 `docs/verified_facts/` 에 §A 로 기록할 것.
- 스레드 불변식: **TX 루프 = 유일 버스 writer**([backend.py:10](../../src/Actuators/motor_control/motor_control/backend.py#L10)). `estop()`이 그렇듯 공개 메서드는 플래그만 세우고 실제 CAN 송신은 TX가 수행해야 한다.

## Decision (결정)

1. **공개 API 신설** `TongyiSdoBackend.freewheel(engage: bool)` — `_freewheel` 플래그(`_lock` 보호)만 토글. 실 송신 없음. engage 시 `_vel_units`를 0으로 리셋(해제 후 잔류지령 급발진 방지).
2. **TX 루프 상태 전이 처리**(유일 writer 유지):
   - `False→True`: **구동 노드에만** `0x6040=CW_DISABLE(0x05)` 1회 송신 → servo-off. 이후 구동 `Target_velocity` write **정지**. Node Guarding RTR·위치 폴링은 유지(노드 생존·오도메트리 추종).
   - `True→False`: 구동 노드 `0x6040=0x86`(fault reset+enable) + `0x6060=3`(PV) 재설정 → 재-enable. 이후 신선한 cmd_vel 수신 전까지 워치독으로 vel 0.
   - **조향축은 무영향** — 사용자 요구("구동바퀴")대로 현 위치 hold 지속.
3. **지령 억제**: freewheel 중 `set_command()`는 estop과 동일하게 무시(잔류목표 방지).
4. **ROS2 표면**: `/freewheel`(std_msgs/Bool) 구독 추가 → `backend.freewheel()`. `snapshot()`·`/diagnostics`에 freewheel 상태 노출(WARN "no holding torque").
5. 의존성 추가 없음. 신규 CAN 오브젝트 없음(기존 0x6040 Controlword/0x6060 Modes/0x60FF Target_velocity 재사용).
   > ⚠ 정정 (2026-08-03) — 원문의 `0x605N` 은 존재하지 않는 오브젝트 표기(오타)였다. 억제 대상은 0x60FF 다.

## Safety (안전 게이트)

- ⚠ freewheel은 **홀딩토크를 제거**한다 → 경사면에서 로봇이 굴러갈 수 있다. 정지·평지·촉(chock) 확보 후에만 사용하는 **정비/견인 전용** 모드다(docstring·diag WARN 명시).
- ⚠ **2026-07-27 추가 — 첫 사용 전 잭업 실측 필수**: 0x05 는 이 프로젝트에서 **한 번도 송신된 적이 없고**
  (Context §정정 (a)), 「전원 차단 = 자유회전」은 매뉴얼에 없는 **추론**이다(§정정 (b), 감속비 32 역구동성 미확인).
  ⇒ **첫 사용은 반드시 잭업(바퀴 뜬 상태)에서 free spin 여부를 실측 확인한 뒤** 지면 위 견인에 쓸 것.
  자유회전이 확인되지 않은 상태로 경사면·견인 상황에서 쓰면, **홀딩토크만 사라지고 굴러가지도 않는**
  최악 조합이 될 수 있다.
- estop과 독립 플래그. freewheel(servo-off)이 활성이면 구동 출력이 지배 → estop의 0-hold보다 servo-off가 우선. 두 모드 동시 사용 금지를 문서화(견인 시 로봇은 정지 상태 전제).
  ⚠ **함의**: freewheel 활성 중에는 E-stop 이 구동축을 0-hold(제동)로 되돌리지 못한다 — 굴러가는 로봇을 E-stop 으로 세울 수 없으므로, E-stop 을 유효 안전수단으로 쓰려면 먼저 freewheel 을 해제(재-enable)해야 한다.
- **runaway 방지 (2026-08-03 코드 반영, commit `8dc16a5`)**: engage 시 `_vel_units` 는 내부만 0 이 되고 전이 후 device write 가 스킵돼, 진입 전 잔류 목표속도가 장비에 남았다(정오표 A1). 이제 TX 전이가 **servo-off(0x05) 직전 각 구동 노드에 Target_velocity=0 을 명시 송신**한다 → 드라이브가 조용히 재-enable(debt-003)돼도 잔류속도 급발진 없음. (단 debt-003 의 servo-off 지속성 자체는 여전히 잭업 벤치 미검증.)
- 재-enable 경로는 기동 init의 구동축 부분(0x86+PV)과 동일 프레임 → 별도 재-init 불요(CAN 링크 유지 전제, ~~실측 §8 "무재초기화 재개"와 정합~~).
  > ⚠ **2026-07-27 정정 — §8 인용은 이 경로를 입증하지 않는다** (원문 이력 보존)
  > 인용된 `tongyi-canopen-protocol-reference.md` §8 은 **servo-off 후 재-enable 이 아니라 CAN 링크
  > dropout 재연결**에 관한 기록이다: 「링크 dropout: 마스터 무한 재시도(폴링 330fps로 감속)+guarding 유지.
  > 재연결 시 즉시 재개+**무재초기화**(CAN링크 한정; 전원까지 끊으면 재부팅→init 필요)」.
  > 링크 dropout 시나리오에서는 **서보가 disable 된 적이 없다** ⇒ `0x05 → 0x86+PV` 재-enable 경로의
  > 근거가 되지 못한다. 게다가 0x05 는 이제껏 송신 이력이 0 건이다(Context).
  > ⇒ **Not-tested**: `servo-off(0x05) → 재-enable(0x86 + 0x6060=3)` 시퀀스는 **실장비 미검증**이다.
  > (형제 ADR 들은 모두 Not-tested 절을 남기는데 본 ADR 에는 그 절이 없었다 — 아래 §Verification 신설.)
  > **판정에 필요한 측정**: 잭업 상태에서 0x05 송신 → 재-enable 프레임 송신 → 저속 지령이 실제로
  > 추종되는지, 0x603F(error code)·statusword 가 정상인지 확인. 부채 등록 대상(`docs/debt/registry.md`).

## Consequences (결과)

- (+) 견인/정비 시 바퀴 자유회전 가능. 단일 Bool 토픽으로 현장 조작 단순.
- (+) 단독 writer 불변식·estop 패턴 재사용 → 동시성 위험 최소.
- (−) 오조작 시 무제동 → 안전 문구·WARN으로 완화하나 물리 인터록(브레이크)은 범위 밖.
- (−) 재-enable 후 첫 지령까지 1워치독 창(≈200 ms) 무구동(의도된 안전 지연).

## Rollback (롤백)

- 가역. `freewheel()`·`_freewheel`·TX 전이 블록·`/freewheel` 구독·snapshot/diag 항목을 제거하면 기존 거동으로 완전 복귀(신규 영속상태·스키마·펌웨어 변경 없음). 런타임 롤백은 `/freewheel false` 발행으로 ~~즉시~~ 재-enable (⚠ **미검증** — §Verification 참조).

## Verification (2026-07-27 신설 — 미검증 항목 명시)

본 ADR 은 원래 Verification/Not-tested 절이 없었다. 감사 결과 아래는 **전부 실장비 미검증**이다.

| 항목 | 상태 | 근거 |
| --- | --- | --- |
| `0x6040 = 0x05` 가 이 장비에서 servo-off 를 실제로 일으키는가 | **미검증** | 송신 이력 0 건. 출처는 Handbook V7.0 p194 정의뿐(§Context 정정 (a)) |
| servo-off 시 바퀴가 **자유회전**하는가 | **미검증** | 매뉴얼에 언급 없음. 감속비 32 역구동성 미확인(§Context 정정 (b)) |
| `servo-off → 재-enable(0x86 + 0x6060=3)` 이 재-init 없이 성립하는가 | **미검증** | §8 인용은 CAN 링크 dropout 시나리오라 무관(§Safety 정정) |
| `/freewheel false` 발행 시 "즉시" 재-enable | **미검증** | 위 항목에 종속 |

**검증 순서(고정)**: ① 잭업 → ② 0x05 송신 후 손으로 회전 시도(육안·0x6064 교차확인) →
③ 재-enable 프레임 송신 → ④ 저속 지령 추종·error code 확인. ①~④ 전에 지면 위 견인 사용 금지.
결과는 `docs/verified_facts/` 에 §A 로 기록한다.
