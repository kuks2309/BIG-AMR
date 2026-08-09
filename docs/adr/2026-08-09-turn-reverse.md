# ADR 2026-08-09 — 후진 원호 액션 `turn_reverse` 신설 (기존 방향쌍 패턴 준수)

- **Status**: Proposed — 2026-08-09 (사용자 승인 후 구현. SIL·실기 근거는 아래 「검증 결과」에
  수집했으나 **회귀 시험은 미수행**이며, 최종 verdict 는 저자가 찍지 않는다 —
  `coding.md:88` never-self-approve)

## Context

현장에서 `turn`(R-turn 원호)을 쓰려 했으나 **전방 공간이 없고 후방만 2 m 여유**였다.
확인해 보니 `turn` 은 **전진 전용**이다:

```
turn_action_server.cpp:43-45   max_linear_speed <= 0 이면 goal 거부
turn_action_server.cpp:118     ik_->compute({ max_v, 0.0, sign * max_omega_rad});
turn_action_server.cpp:213     ik_->compute({ v,     0.0, sign * omega_rad});
                                              ^^^^^ vx 항상 양수
```

`target_angle` 의 부호는 **회전 방향**(CCW/CW)만 고르고 진행 방향과는 무관하다. 즉 음수를
줘도 「전진하며 시계방향 원호」일 뿐 후진이 되지 않는다.

그리고 이 저장소는 **방향쌍을 별도 액션으로 두는 패턴**이 이미 정립돼 있는데 `turn` 만 짝이 없다:

```
translate_forward(1) ↔ translate_reverse(2)
yaw_control(6)       ↔ yaw_control_reverse(7)
mpc(8)               ↔ mpc_reverse(9)
turn(5)              ↔ (없음)                  ← 본 ADR 이 메운다
단일: spin(3) · crab_linear(4) · dock(40)
```

## Decision

**`turn_reverse` 를 별도 액션·별도 노드로 신설한다.** 기존 짝 패턴을 그대로 따른다.

### D1. 별도 `.action` 타입 (`AMRMotionTurnReverse`)

`AMRMotionTurn` 에 방향 플래그를 넣지 않는다. 저장소가 이미 `AMRMotionTranslateForward`/
`Reverse`, `AMRMotionYawControl`/`Reverse`, `AMRMotionMpc`/`Reverse` 를 별도 타입으로 두고
있고, `AMRMotionYawControlReverse` 주석이 그 규약을 명시한다 —
「`vx_max` 는 magnitude 만 받음(>0). 내부적으로 항상 `-vx` 로 사용(후진)」.

필드는 `AMRMotionTurn` 과 동일하게 두고 `max_linear_speed` 의 의미만 **magnitude** 로 문서화한다.

### D2. 구현 = `turn` 복제 + IK 입력 `vx` 부호 반전

실질 변경은 두 줄이다:

```cpp
ik_->compute({-max_v, 0.0, sign * max_omega_rad});   // Phase 0 조향 정렬용
ik_->compute({-v,     0.0, sign * omega_rad});       // 주 루프
```

**`ω` 부호는 유지한다.** `target_angle` 은 그대로 **헤딩 변화량**(+CCW)이고, `vx` 만 음수가
되면 `R = v/ω` 의 부호가 뒤집혀 ICR(Instantaneous Center of Rotation)이 반대편으로 옮겨간다
— 물리적으로 「후진하면서 그 각도만큼 도는」 동작이다. `translate_reverse`·`yaw_control_reverse`
와 같은 규약이라 사용자가 두 액션을 오갈 때 `target_angle` 의 의미가 바뀌지 않는다.

**나머지는 `turn` 을 그대로 상속한다** — IMU yaw 델타 누적(계상 지점 3곳)·Phase 0 조향 정렬·
Phase 1-3 사다리꼴·Phase 3.5 미세보정·Phase 4 조향 복귀. 2026-08-06 의 각도 계상 부호 수정
(`docs/adr/2026-08-06-turn-angle-accounting-sign.md`)도 함께 상속된다.

### D3. mux 소스 id = **12**

10·11 은 `stanley`/`stanley_reverse` 로 **예약**돼 있다(미구현). 예약을 침범하지 않고 12 를 쓴다.

```
0 joystick · 1 translate_forward · 2 translate_reverse · 3 spin · 4 crab_linear
5 turn · 6 yaw_control · 7 yaw_control_reverse · 8 mpc · 9 mpc_reverse
10 stanley(예약) · 11 stanley_reverse(예약) · 12 turn_reverse(본 ADR) · 40 dock
```

짝 패턴 표기도 `(5,12) turn` 으로 갱신하고 「단일」 목록에서 `turn(5)` 을 뺀다.

### D4. `turn` 은 개명하지 않는다

`translate` 는 `_forward`/`_reverse` 로 양쪽에 방향을 붙였지만 `yaw_control`·`mpc` 는 전진 쪽에
접미사가 없다(3쌍 중 2쌍). `turn` → `turn_forward` 개명은 기존 런치·params·소스 id 5·
함수표 인용을 전부 깨뜨리므로 하지 않는다.

## Consequences

**얻는 것** — 후방 공간만 있는 현장에서 원호 선회가 가능해진다. 기존 `turn` 의 검증 자산
(잔여각 프로브 `turn_residual_probe.py`)을 그대로 재사용할 수 있다. ⚠ 2026-08-10 정정: 함께 적었던 `turn_angle_accounting_check.py` 는 **폐기**됐다(검사 대상인 델타 누적이 구조 변경으로 소멸).

**비용** — 액션 타입·노드·런치·params·mux 항목이 하나씩 늘어난다. `turn` 과 `turn_reverse` 가
**코드 중복**이 되므로, 한쪽을 고치면 다른 쪽도 고쳐야 한다. 이는 이미 `translate`·`mpc`·
`yaw_control` 쌍이 지고 있는 비용과 같은 성질이며, 본 ADR 은 그 패턴을 깨지 않는 쪽을 택했다.

**⚠ 미해결로 남기는 것**
- **후진 원호의 조향 자세가 전진과 어떻게 다른지 실측한 적이 없다.** SIL 로 먼저 확인한다.
- `turn` 의 IMU 델타 누적이 후진에서도 같은 부호 규약으로 동작하는지는 **검증 대상**이다
  (전진 기준으로 작성된 계상 로직이므로).
- 코드 중복 해소(공통 코어 추출)는 본 ADR 범위 밖이다.

## 검증 계획

```
1  SIL    소각도 후진 원호 — 헤딩 변화·진행 방향(후진 확인)·조향 자세·중심 이탈   ✔ 수행
2  회귀   ~~turn_angle_accounting_check.py 적용~~  → 2026-08-10 **폐기**(대상 소멸)   해당없음
3  실기   후방 2 m 여유 안에서 작은 호                                            ✔ 수행(±10° · 90°)
```

## 검증 결과 (2026-08-09 실기)

전문·수치는 `docs/issues_and_fixes/issues_and_fixes.md` 2026-08-09
`[Verify] turn·turn_reverse 90° 실기 검증`.

```
±10°  후진→전진 왕복 폐합   5 mm / +0.15°   ·   6 mm / −0.38°
 90°  후진→전진 왕복 폐합  14 mm / +0.64° (mcl2d)   14 mm / +0.46° (Seer, 독립 확인)
```

**「⚠ 미해결로 남기는 것」 3건의 현재 상태**

1. **후진 원호의 조향 자세** — 해소. 전진과 **같다**. 조향각은 목표각이 아니라 **반경**이 정하며,
   `R = 1.0 m` 에서 양방향 모두 `F = +31.13° / R = −30.80°` 로 `atan(w1_x/R)` · `atan(w2_x/R)` 와
   정확히 일치했다. 후진 여부는 ICR 위치(부호)만 바꾼다.
2. **IMU 델타 계상이 후진에서도 같은 부호 규약으로 동작하는가** — 부호 규약은 정상(후진 다리가
   전진 다리와 거울 대칭으로 나왔고 왕복이 닫힌다). 다만 **크기**에 문제가 남는다 — 자기보고가
   맵 절대 측위보다 양쪽 다리 모두 작다(0.3~0.5°). 누적기의 **0 클램프 래칫**을 의심해 `debt-048`
   로 등록했다. ⚠ **2026-08-10 정정: 그 의심은 틀렸다.** 원인은 ① AHRS 기동 후 완화(외부 계측이
   정지 후 3초를 기다려 잡음 — 차체는 안 움직인다) ② 당시 mcl2d 미수렴이었다. 정지 순간 기준으로는
   자기보고와 IMU 가 +0.056° 로 맞는다. `debt-048` 은 구조 교체로 **상환 완료**됐으나 등록 사유는
   오진이었다. 전말: `issues_and_fixes.md` 2026-08-10 `[Closed]`.
3. **코드 중복 해소** — 범위 밖, 그대로 남는다. `debt-048` 상환 시 **두 파일을 함께** 고쳐야 한다.

**새로 드러난 미결 → 2026-08-10 해소** — `turn` 계열 허용 규격 **|오차| ≤ 0.5°** 사용자 승인.
⚠ 여기 적었던 「n = 4」는 **틀렸다**(실제 6다리, 두 다리 누락 + 부호 규약 혼용 —
`claude-mistake/2026-08-09-001`). 오차 피드백 도입 후 실기 n=8 은 −0.381 ~ −0.438° 이며
전수는 `issues_and_fixes.md` 2026-08-10 `[Verify]`. ⚠ 변경 전후 수치는 계측 방식이 달라
직접 비교하지 말 것.

## 부수 — 끊긴 참조 1건

`trnav_motion_mux.yaml:7` 이 소스 id 계약의 SSOT 로 `docs/abstraction/motion_source_id_contract.md`
를 지목하는데 **그 파일은 존재하지 않는다**(2026-08-09 확인). 계약 내용은 yaml 주석에만 있으므로
그 주석을 정본으로 명시하고 끊긴 참조를 정리한다.

⚠ 최종 verdict 는 저자가 찍지 않는다(`coding.md:88`).
