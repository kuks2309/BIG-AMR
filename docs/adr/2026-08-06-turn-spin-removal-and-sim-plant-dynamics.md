# ADR 2026-08-06 — turn 내부 스핀 제거 + SIL 플랜트 동특성·엔코더 신설

- **Status**: Accepted — 2026-08-06 (**SIL 검증만**. 실기 검증 0회. 최종 verdict 는
  저자가 찍지 않는다 — `coding.md:88` never-self-approve, 외부 리뷰 패스 대기)

> ⚠ 본 ADR 은 **소급 작성**이다. `coding.md:68`(공개 API 신설 시 사전승인)을 어기고 구현·
> 커밋·푸시(`3b19537..acd3636`)를 먼저 했다. 경위는
> [실수 기록 2026-08-06-003](../claude-mistake/2026-08-06-003_coding-sop-skipped-tables-adr-selfapprove.md).

## Context

**(1) turn 이 spin 을 내부에서 재구현하고 있었다.**

`turn_action_server.cpp` 가 네 곳에서 `computeSpin` 을 썼다 — 미세보정 진입 시 ±90° 스핀
자세 계산(`:299`), 조향 재정렬(`:303`), 제자리 스핀으로 잔여각 소진(`:361`), 그리고
**미세보정 `if` 밖**의 "Stop driving"(`:407`). 마지막 것은 보정이 발동하지 않아도 **매 turn
마다** 조향을 ±90° 로 돌렸다.

사용자 지적: 「제자리 스핀을 따로 만든 이유가 turn 을 단순화한 것인데」. spin 은 별도
액션으로 분리돼 있으므로 turn 안에 있을 이유가 없다.

수치 사실:
- R=5 m 기준 추가 조향 이동 **173.1°** (기하에서 직접 계산 — 확정).
  > ⚠ **2026-08-06 자기 정정** — 초판은 여기에 「조향 슬루 57.1 deg/s 기준 **3.03 s** 이고
  > `fine_correction_timeout_sec` 3.0 s 라 예산 전부를 스윙에 쓴다」를 덧붙였다. **철회한다.**
  > 57.1 deg/s 는 `0x6081` 이 **0.1 rpm 단위라는 미검증 가정**에서 나온 값이고, 그 단위 근거가
  > 저장소·`References/` 어디에도 없다. 단위가 다르면 소요시간도 달라진다.
  > **조향 이동량 173.1° 는 유효하나, 그 소요시간을 근거로 한 주장은 실측 전까지 하지 않는다.**
- 그 ±90° 는 translator 영점 오프셋(−1.676°)을 거쳐 raw **91.55°** 가 되어 can_relay 클램프
  상한을 밀어올린 원인 중 turn 몫이었다.

**(2) SIL 플랜트가 이 문제들을 볼 수 없었다.**

`translate_sim_odom` 은 지령을 그대로 되울렸고(cmd echo), 엔코더를 발행하지 않았다. 그래서
① 정지 지령 후 계속 도는 각(실측 0.57~0.65 s,
`docs/verified_facts/2026-08-04-amr-test-gui-field-run.md:80-88`) ② 조향 자세 전환 소요 시간
③ 엔코더 기반 진행량 — 셋 다 **원리적으로 재현 불가**였다.

한편 엔코더는 **이미 체인 안에 있다** — can_relay 가 `fb_pos`(CiA 402 `0x6064`)를 4축 전부
싣고, translator 가 `wheel_motor_state_detailed` 로 내보낸다(기본 활성). 2WS 액션이 얇은
`WheelMotor`(속도·각만) 를 구독해 **위치를 참조하지 않을 뿐**이다(`fb_pos` 참조 0건).

**(3) 이 플랜트는 공유 자산이다.**

`grep -rln translate_sim_odom --include=*.launch.py src/` → **19개 런치**, 그중 **8개가
검증 완료된 QD 런치**(`QD/trnav_motion_action_server/launch/sil_*.launch.py`).

## Decision

**D1.** turn 에서 `computeSpin` 을 전부 제거한다. 원호 자세(`turn_steer_front/rear`)를 끝까지
유지하고, 잔여각은 `v` 와 `ω` 의 부호를 **함께** 뒤집어 보정한다 — `v/ω = turn_radius` 가
보존되므로 IK 출력 조향각이 원호 자세와 동일해 조향이 움직이지 않는다.

**D2.** `translate_sim_odom` 에 `/wheel_motor_state_detailed`(엔코더 counts)를 발행한다.
환산은 translator 와 같은 식: 구동 `주행거리/(2πr) × pulses_per_rev × gear_walk`,
조향 `각(rad)/2π × pulses_per_rev × gear_steer`(홈 기준 상대).

**D3.** 구동 가감속·조향 슬루·IMU yaw 잡음을 파라미터로 넣고 정기구학을 **실제값**으로 푼다.
**기본값은 전부 0(제한 없음) = 종전 즉응 거동** — 공유 런치 19개의 기존 결과를 보존하기 위해
런치가 **명시적으로 켤 때만** 작동시킨다. 엔코더 토픽 추가는 거동 변경이 아니므로 항상 켠다.

**D4.** 권장값과 그 출처를 코드 주석에 **추정과 실측을 구분해** 남긴다.
- `drive_*_mps2 = 0.0833` — **실측 유래**(50 mm/s → 0.57~0.65 s 역산).
  ⚠ 드라이브의 실제 `0x6084`(profile_dec)는 Seer 마스터가 설정한 값이고 우리가 읽어 확인한
  바 없다. 한 동작점에서의 역산이다.
- `steer_rate_dps = 57.1` — **설정 유도**(`steer_profile_velocity` 30000 → 모터 3000 rpm
  ÷ 조향 감속비 315 = 9.524 rpm). **실측 아님.**
  ⚠ 그 유도는 `0x6081` 이 **0.1 rpm 단위라는 가정**에 의존하며, 그 단위 근거는 저장소에도
  `References/Tongyi-Motor-Controller/` 에도 **없다**(`fb_vel`=0x606C 단위에서 유추).
  **자릿수 감으로만 쓰고 소요시간 주장의 근거로 삼지 않는다.**

**D5.** 「2WS = 검증된 QD + 승인된 이탈」을 유지한다. 현재 승인된 이탈은 두 건뿐이며 둘 다
사용자 지시다 — ① 본 ADR 의 D1 ② 베이스의 상류 조향 가드(`steer_cmd_limit_deg`).
`:233` 부호 처리와 엔코더 미사용은 **QD 와 동일**하므로 건드리지 않는다.

## Alternatives (기각)

- **turn 을 dual bicycle 경유로 재구조화** — 2WS 에서 dual bicycle 과 자유 IK 는 앞뒤 비대칭
  (0.6039 vs 0.5961)만 다르고 R 차이 **4 mm(0.65 %)** 라 실익이 없다. δ 한계 게이트
  (`max_delta_deg` 45° → R ≥ 0.600 m)가 새로 걸리는 것이 유일한 실질 변화인데, 그건 기능 축소다.
- **Phase 3.5 를 통째로 제거** — 잔여각 바닥값을 아직 측정하지 못했다. 측정 후 별건으로 판단.
- **플랜트 동특성을 기본 ON** — 초안에서 그렇게 넣었다가 되돌렸다. 검증된 QD SIL 8개의 결과가
  말없이 바뀐다.

## Consequences

**이득**
- turn 1회당 조향 이동이 148~173° 줄고, raw 91.55° 요구가 사라진다.
- SIL 이 관성·조향 소요시간·엔코더를 처음으로 재현할 수 있다 — 지금까지 「통과했지만 근거가
  아닌」 시험이 근거가 될 수 있는 축이 생겼다.

**비용**
- 플랜트 공개 표면이 늘었다(파라미터 8개·토픽 1개). 기본값이 종전과 같아 기존 런치는 무영향.
- `turn_action_server.cpp` 가 QD 상류와 갈라졌다 — 상류 변경을 들여올 때 이 구간은 수동 병합.

**남는 위험·부채**
- **실기 검증 0회.** SIL 만으로 확정했다(사용자 승인: 「실기 안 해도 됨」).
- `settling_delay_ms: 200` 이 관성(0.57~0.65 s)보다 짧아 **기체가 멈추기 전에 잔여각을 읽는다**
  — 미조치. 보정 오버슛(3 deg/s × 0.6 s ≈ 1.8°)이 임계 0.3° 의 6배라 **수렴 불가 구조**인
  것도 미조치. 둘 다 `trnav_2ws_action_server/docs/function_table.md` §알려진 미해결 사항
  B·C 에 등재.
- 액션은 여전히 엔코더를 구독하지 않는다(D5 에 따라 QD 와 동일 유지). 플랜트만 발행한다.
- 같은 패키지의 나머지 8개 액션에 함수표가 없어 `coding-inventory-gate.py` 가 그 파일들에
  대해서는 여전히 빈 통과한다.

## Rollback

**D1 (turn)** — 가역. `git revert 83167dd`. 되돌리면 조향이 다시 ±90° 로 스윙한다(돌연변이
확인으로 확정된 거동). 재빌드: `colcon build --packages-select trnav_2ws_action_server`.

**D2·D3 (플랜트)** — 가역, 2단계.
1. **코드 변경 없이 즉시 무력화**: 런치에서 `drive_accel_mps2`·`drive_decel_mps2`·
   `steer_rate_dps`·`imu_yaw_noise_deg` 를 주지 않으면(= 기본 0) 거동이 종전과 동일하다.
   `/wheel_motor_state_detailed` 는 계속 발행되나 **구독자가 없으므로 무해**하다.
2. **완전 원복**: `git revert e077972` 후
   `colcon build --packages-select translate_sim_odom`. 이 경우
   `Tools/motion_chain_check/plant_dynamics_check.py` 는 B 케이스에서 실패한다(정상 — 그
   기능이 사라졌으므로).

**영속 상태·스키마·펌웨어 변경 없음** — 되돌림에 데이터 마이그레이션이 필요하지 않다.

## 검증 근거

| 항목 | 도구·조건 | 결과 |
| --- | --- | --- |
| 플랜트 즉응(QD 회귀 없음) | `plant_dynamics_check.py`, `ROS_DOMAIN_ID=43` | 정지 0.020 s · 감속 중 중간 속도값 **0개** |
| 플랜트 동특성 | 동상 | 정지 0.620 s(실측 0.57~0.65 s 내) · 엔코더 +15.5 mm(v²/2a=15.0 mm) |
| 환산식 | `--selftest` | 5/5 |
| turn 기능 | SIL 45° · R=1.0 m | status 0 · 45.178° · 7.40 s |
| turn 조향 범위 | `sil_record_steer.py` | W1 +31.13° · W2 −30.80° · 90° 초과 0표본 |
| **turn 돌연변이** | `:381` 정지 블록만 종전 복원 | 조향 **90.00°/90.00°** 회귀(결과각·소요 동일) → 원인 확정 |
| 리베이스 후 재검증 | 타 세션 29커밋 흡수 후 | 6/6 유지 |
