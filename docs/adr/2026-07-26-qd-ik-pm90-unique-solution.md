# ADR 2026-07-26 — QD 역기구학 ±90° 정규화: 유일해(canonical) 확정 설계

## 상태
채택(설계 의도 확정 기록, 하드웨어 정합 확인 완료). 대상: `trnav_qd_kinematics/QdDualSteerIK`
(Big-AMR QD 정본 IK). 본 ADR 은 코드 변경이 아니라 **기존 ±90° 정규화의 설계 의도**를 정본화한다.
Seer 계열 `chassis_kinematics.py`(±140°)와의 대조에서 도출.

> **하드웨어 확인(2026-07-26, 사용자)**: Carrier AGV 실제 조향 한계는 **90°를 초과**한다.
> 따라서 ±90° 정규화는 **항상 물리 조향범위 안** → 한계초과 명령 위험 0. ±90° 는 하드웨어에
> 강제된 값이 아니라, 유일해·최소각을 얻기 위한 **의도적 소프트웨어 정규화**이며 물리적으로 완전 안전.

## 맥락 — "한 바퀴 = 등가해 2개" 문제
독립조향 바퀴의 속도벡터 `(vx_i, vy_i)` 는 **항상 두 가지 액추에이터 표현**을 가진다:

```
(θ, +v)  ≡  (θ ∓ 180°, −v)     — 물리적으로 동일한 바퀴 운동
예: (120°, 전진)  ≡  (−60°, 후진)
```

`atan2` 는 (−180°,180°] 중 하나만 뱉으므로, 후처리 정책이 없으면 **어느 표현을 액추에이터에
보낼지 비결정**이다. 이 비결정은 (a) 경로/상황에 따라 같은 기동에서 조향 목표가 튀고,
(b) 경계 근처에서 두 해 사이를 왕복(chattering)하며, (c) 상위 제어기의 heading/CTE 보정이
불연속 지점을 만나 진동하는 원인이 된다.

Seer 원본(`chassis_kinematics.py:64`, `STEER_LIMIT_RAD=2.443`=±140°)은 **±140° 초과 시에만
접기** → 접기 범위 280°(>반원)라 90°~140° 구간에서 **두 해가 공존**한다. 즉 유일해가 아니다.
이는 "하드웨어 조향범위(±140°)를 넓게 쓴다"는 다른 목적의 선택이다.

## 결정 — 반원(±90°) 정규화로 유일해 확정
Big-AMR QD IK 는 조향각을 **[−90°, +90°] 로 정규화**한다
(`qd_inverse_kinematics.cpp:71-85` `normalizeAngle`, 임계 `M_PI/2`):

```cpp
if (angle_rad >  M_PI/2) { angle_rad -= M_PI; direction = -direction; }
else if (angle_rad < -M_PI/2) { angle_rad += M_PI; direction = -direction; }
```

**의도(핵심)**:
1. **유일해(canonical) 확정** — [−90°,+90°] 는 정확히 **반원(180° 폭)**. 모든 방향을 1:1로
   한 번씩만 담으므로 등가 2해 중 **정확히 하나**만 남는다. atan2 분기·입력 이력에 무관한
   **결정론적 단일 출력**.
2. **최소 조향각 선택** — 두 해 중 항상 |θ| 작은 쪽 → 조향 이동량·시간 최소, 응답 빠름.
3. **부호 분리 표현** — 속도는 `wheel_speed≥0` 로 유지하고 방향은 `direction(±1)` 로 분리
   (`qd_inverse_kinematics.hpp:27-33`). 후진을 값 부호가 아닌 명시 필드로 → 하위 모터
   변환에서 부호 혼동 제거.

**경계 떨림 2차 방어(cruise)** — 순수 ±90° 접기는 경계(정확히 90°)에서 입력 미소변동에
`+90°/전진 ↔ −90°/후진` 토글이 생길 수 있다. CRAB 주행 IK(`qd_crab_inverse_kinematics.cpp:26-40`
`WRAP_MARGIN=25°` + `setInitial()` 상태 고정 hysteresis)가 Phase 0 에서 부호/방향을 1회 확정해
cruise 내내 고정 → **두 해 왕복을 원천 차단**. 즉 본 정규화의 "유일해" 의도를 주행 단에서
한 번 더 못박은 설계다.

## 근거·검증
- **수학**: 반원(180°) 정규화 ⇒ 방향↔각도 전단사(bijection) ⇒ 유일해. (경계 ±90° 는 측도 0,
  strict `>` 로 처리.) 280° 범위(Seer)는 90~140° 중복 ⇒ 비유일.
- **실측 대조**(동일 기하 Roll_A084, 실제 C++ 컴파일 실행): 자연각 120° 명령에서
  본 IK = `−60°/후진(dir=−1)`, Seer = `+120°/전진`. 물리 동일, 본 IK 만 **결정론적 단일해**.
  직진·후진·크랩·스핀 4케이스는 소수 4자리까지 Seer 와 동일(코어 분해식 등가).

## 기각안 (Seer ±140° 방식)
- 장점: ±140° 조향 하드웨어를 넓게 활용, 90~140°에서 방향반전 없이 전진 유지.
- 기각 사유: (a) 90~140°에서 **2해 공존 → 비결정**, (b) 경계·재측위에서 조향 목표 튐 위험,
  (c) Big-AMR 상위 제어(heading/CTE 폐루프)는 **연속·유일 출력**이 필수 — 유일해 canonical 이
  더 확실. Big-AMR 는 하드웨어 조향한계가 90°를 넘으므로 ±90° 정규화가 물리 범위를 절대 벗어나지
  않아, 유일해의 장점만 취하고 손해(범위 미활용)는 무해하다.

## 영향·주의
- Scope: 설계 의도 정본화(코드 로직 무변경). `normalizeAngle` 에 의도 주석 추가(trivial), 본 ADR 참조.
- **속도 포화 위치**: 본 IK 는 vmax 포화를 하지 않음(Seer 는 IK 내부에서 함) — 의도적 계층 분리.
  포화는 상위(path/mpc controller·`qd_wheel_set_packer`) 책임. IK = 순수 기하 canonical 변환.
- **하드웨어 정합: 확인 완료(2026-07-26)** — Carrier AGV 실제 조향 한계 > 90° → ±90° 정규화가
  물리 범위 내 상시 성립, 한계초과 위험 없음. 물리·수학 양면 정합 확정.
- 관련: [2026-07-26-qd-motion-port.md](2026-07-26-qd-motion-port.md)(6패키지 이식), 대조원본
  `Tools/Kinematics/chassis_kinematics.py`(Seer ±140°).
- Confidence: high(수학·실측·하드웨어 정합 확인). Not-tested: 경계 hysteresis 실주행 거동(정성).

---

## 부록 ② — 속도 포화·정렬 안전 (QD: body 레벨 균일 축소)

### 맥락 — "포화가 정렬을 깨뜨리는" 문제
독립조향 2륜에서 속도 제한(포화)을 **바퀴 레벨에서 비균일하게**(per-wheel clamp, 또는 vx만
줄이고 ω는 그대로) 적용하면, 두 바퀴의 속도 비율·조향각이 틀어져 암시 회전중심이 이동 →
**두 바퀴 정렬(하나의 body twist를 함께 만드는 상태)이 깨진다**. 균일 배율 축소만이 정렬을 보존한다
(조향각 `atan2` 는 양수배율 불변, 속도 비율 유지).

### 결정·발견 — QD 는 정렬을 구조적으로 보존
QD 는 속도 제한을 **IK 뒤 바퀴 레벨이 아니라 IK 앞 body twist 균일 축소**로 처리한다.
근거([translate_forward_action_server.cpp:673-683](../../src/Control/Motion_Control/QD/trnav_motion_action_server/src/translate_forward/translate_forward_action_server.cpp#L673-L683)):
```cpp
double body_speed = std::hypot(vel_cmd.vx, vel_cmd.vy);
if (body_speed > 1e-6) {
    double scale = vx_profile / body_speed;   // 단일 배율
    vel_cmd.vx *= scale; vel_cmd.vy *= scale; vel_cmd.omega *= scale;  // vx·vy·ω 동시
}
ik_expected = ik_->compute(vel_cmd);          // 그 다음 IK
```
- `qd_wheel_set_packer` 는 패킹만(per-wheel 속도 clamp 없음) — 정렬 깨질 자리 자체가 부재.
- 조향 미정렬 시 body 속도 감속(steer-convergence, :705-737)+조향 rate limit(:688-703) — 미정렬 상태 주행 억제.

### Seer 원본 대비 — 강점 3 / 트레이드 2 (정직 기록)
**강점(강화된 규칙)**:
1. **정렬 안전이 관례→구조**: Seer 는 바퀴 레벨 비율보존을 *올바르게 해야* 안전(관례 의존).
   QD 는 위험 지점(per-wheel 자르기)을 제거해 정렬이 **구조적으로 불가침**.
2. **유일해(부록 ① ±90° canonical)**: 결정론적 단일해·최소각. Seer ±140° 는 90~140° 2해 공존.
3. **강건성 계층 추가**: steer-convergence 감속·steer rate limit·TransientGuard (Seer=순수 수식엔 없음).

**트레이드(상위집합 아님 — 정직)**:
1. **범위 차이**: Seer 원본은 순수 기구학 참조 모듈(수식+selftest), QD 는 완전 모션 제어 스택.
   **순수 IK 수식 코어는 동등**(직진·후진·크랩·스핀 소수4자리 일치, 실측 대조).
2. **바퀴 vmax 상한 보장 위치 트레이드**: Seer 는 IK 안에서 최대 바퀴속도 ≤ vmax 를 그 자리서
   보장. QD 는 IK 에서 **정렬**을 보장하는 대신 개별 바퀴 vmax 상한은 다른 계층(운영 속도 영역/
   모터 드라이버)에 위임. 즉 "정렬 보장 ↔ 바퀴상한 명시 보장" 을 맞바꾼 것.

### 정리
QD 는 Seer 원본 대비 **정렬 안전·유일해·강건성을 구조적으로 강화**한 설계다(장점). 단
**IK 수식 코어는 동등**하며, **바퀴 vmax 상한 보장 위치는 트레이드**라는 단서를 함께 남긴다.
- 검증 범위: `translate_forward` 직접 확인(대표 병진). `spin`/`turn` 은 `computeSpin(ω)` 단일입력이라
  두 바퀴가 같은 ω 유도로 애초 정렬, `crab_linear` 은 `QdCrabIK` 상태고정 clamp — 균일 body→IK 원칙 일관.
  Not-verified: 최종단 `TransientGuard`(vy/ω 별도 제한)의 비균일 여지(2차 안전계층, 주 제한은 균일 축소).
