# 2026-08-23 — LGIT 도킹 코어 2WS 이식 W1 (무수정 코어 + 검증 자산, 8/8 PASS)

> 약어: IK(Inverse Kinematics) · SIL(Software-In-the-Loop) · PID(Proportional Integral Derivative)

- 사용자 지시: "LGIT AMR 에서 QD 방식의 주차 제어가 구현되었으므로 2WS 방식으로 이식이
  가능할 것 같습니다" → 스냅샷 지금 시점·관측은 벽 3면 `/wall_pose`·접근 방향은 실기 검증.
- 사전승인: `docs/adr/2026-08-23-2ws-dock-port.md`
- 경위: 로봇 PC(lgit-c6-4) 무응답 → 정본 저장소 `kuks2309/LGIT-C6-Cobot` 얕은 클론,
  스냅샷 `7a2df984`(2026-08-23 21:02) 고정.

## 신설 — `src/Control/Motion_Control/2WS/trnav_2ws_dock_control/`

- **무수정 복사**(cp, md5 동일 확인): 코어 `dock_core.hpp/cpp`(순수함수 20종 — PID 엔진
  3중 anti-windup·기하 진입 crab·과조향 바이어스·crab 속도차 yaw 합성·조향 도달성·
  IMU runaway·원위치 판정), 골든(`golden.tsv`+대조기), 단위 검사기 6종, 코어 SIL,
  원본 함수표·이력 문서
- **신작**: CMakeLists(plain cmake·의존 0·ctest 8종 등록, package.xml 없음 = colcon 무시),
  README(출처 스냅샷·무수정 계약·W2/W3 예정)
- **미이식(의도)**: `dock_ik.*`(QD IK 의존 — W2 에서 trnav_2ws_kinematics 로 신작),
  `gen_golden.py`(정본 파이썬 필요 — TSV 만 자산화), ROS 조립(W3)

## 검증 (이 장비)

- **ctest 8/8 PASS**: 골든 대조 **1,805건 0 불일치**(1e-12) + 단위 검사기 6종 + SIL 스모크
- 골든 위임 188건(orbit/fwd)은 W2 IK 어댑터의 등가 검증(ik_parity) 소관으로 명시 이월

## 다음 (별도 승인)

- W2: 관측 어댑터(`/wall_pose`→거리·수평·자세, px→m 게인 재환산) + 2WS steer-hold IK
  (우리 IK 의 저속 조향 0 복귀 여부 실측 후) + 코어 SIL 재검
- W3: 액션 서버 + 지령 체인(translator) 결합 + 우리 sim 킷 SIL + HIL
- `arm_m` 은 2WS 인라인 ±0.6039(실측 정본) 주입 예정 — 게인 전면 재튜닝 필요
