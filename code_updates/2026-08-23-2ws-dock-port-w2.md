# 2026-08-23 — 2WS 도킹 이식 W2: IK steer-hold + `/wall_pose` 관측 어댑터 (11/11 PASS)

> 약어: IK(Inverse Kinematics) · ulp(unit in the last place)

- 선행: `code_updates/2026-08-23-2ws-dock-port-w1.md` (코어 무수정 이식, 골든 1,805건 0 불일치)
- 사용자 지시: "진행합시다" (W2 착수 승인)

## 변경 (trnav_2ws_dock_control)

- **dock_ik(개작 2곳)**: 원본 steer-hold 어댑터의 IK 타입만
  `trnav_2ws_kinematics::TwoWsDualSteerIK` 로 교체(+주석의 상류 참조 경로·임계 위치 정정).
  바퀴별 임계 판정·resetHold·lastSteer 계약 그대로. 우리 2WS IK 에도 `|v|<1e-6` 조향 0
  복귀가 실재함을 확인(qd_inverse_kinematics.cpp:45-48·84-86) — 어댑터가 덮는다.
- **ik_parity_check(개작)**: 골든 위임 188건(orbit/fwd)을 우리 IK 로 재계산.
  **임계 밖 불일치 0** — 단 허용오차를 0(비트 동일)에서 **1e-12** 로: 2WS 이식본은 QD
  원본과 연산 순서가 달라 1~2 ulp(실측 최대 4.4e-16) 차이. 골든의 기본 철학(1e-12
  상대오차로 libm 차이 흡수)을 따른 것으로 CMake 주석에 근거 명기.
- **dock_obs(신작)**: `/wall_pose`(T_station_base) + 도킹 목표(스테이션 프레임) →
  코어 관측 {e_d, e_lat, e_yaw_deg}. 접근축은 base_link 기준 각도 주입(0=전방·±π/2=측면
  — 실기 검증으로 확정). 비유한 입력은 valid=false 로 소비 차단.
- 단위 검사 신설 2본: `dock_obs_check`(8케이스 — 항등·축분해·로봇 회전·접근축 90°·
  지나침 음수·yaw wrap·NaN), `steer_hold_check`(5케이스 — 저속 유지·reset·회전 표현).
  개발 중 수정 1건: 자유 IK 의 제자리 회전 표현은 「조향 부호 반대 + 속도 양수」 —
  「속도 반대」로 가정한 초기 단정을 물리 동일 표현으로 정정.

## 검증

- **ctest 11/11 PASS** (W1 8종 + ik_parity + dock_obs + steer_hold)
- 변이 검증: dock_obs 의 e_lat 부호 고의 반전 → dock_obs_check 실패 → 원복 11/11

## 다음 (W3, 별도 승인)

- 액션 서버(`trnav_2ws_dock_ros`): 페이즈 구성(정렬→접근→검증), `/wall_pose` 구독,
  `DockWheelCommand` → 모터 지령 체인(translator) 결합, 우리 sim 킷 SIL → HIL
- 게인 재환산: 원본 px 단위 수평 게인 → m 단위 (게인·arm_m=±0.6039 실기 튜닝)
