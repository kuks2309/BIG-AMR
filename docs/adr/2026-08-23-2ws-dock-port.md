# ADR 2026-08-23 — LGIT 도킹 제어 코어의 2WS 이식 (W1: 무수정 코어 + 검증 자산)

- **Status**: Accepted — 2026-08-23 (사용자 승인: "지금 시점 코어를 이식 시작" ·
  "3면 도킹[벽 3면 /wall_pose 관측]으로 문제 없을 것" · "방향은 실기로 검증")

## Context

- 도킹 모션이 필요한데 우리 모션 계층(2WS 11·QD 9 액션)에는 도킹 액션이 없다.
- LGIT(LG Innotek) 장비 저장소 `github.com/kuks2309/LGIT-C6-Cobot` 의
  `src/Skills/Docking_Control/dock_control` 에 QD(Quad Drive) 도킹 코어가 구현·검증돼 있다:
  실차 검증 정본(`references/tc_docking/phase1_gui.py`, 무수정 보존) ↔ C++ 이식본의
  **골든 대조**(1e-12, 188+벡터), 단위 검사기 6종, 코어 SIL(진입 조건 지도 3,402회),
  자체 함수표·code_updates·강제 태그 4종까지 갖춘 상태. M1 승인 완료·HIL 진행 중.
- **스냅샷 고정**: 커밋 `7a2df9842a121b97fbdf93fe1b4dd5596cf20ea2` (2026-08-23 21:02,
  "후방(REAR) 접근 개방"). LGIT 쪽은 계속 진화 중이나 코어 순수함수부는 안정 —
  사용자 결정으로 지금 시점 이식.
- 적합성 3가지: ① 출력 `DockWheelCommand{vf,af,vr,ar}` 가 우리 2WS 인라인 듀얼스티어
  지령 채널과 동형 ② 관측이 주입형이라 카메라 px+라이다 3원 융합을 우리
  `/wall_pose`(sub-mm, 3축 단일 소스)로 대체 가능 ③ 기하 차이는 `arm_m`
  (QD 유효 0.356 → 2WS 인라인 ±0.6039 실측 정본) 주입 값 하나.

## Decision

**W1 (본 ADR 범위)** — 코어를 **무수정 이식**한다:

- 위치: `src/Control/Motion_Control/2WS/trnav_2ws_dock_control/` (패키지명
  `trnav_2ws_dock_control`, 내부 include 경로·namespace `dock_control` 은 원본 유지 —
  향후 LGIT 상류와의 대조·재동기화 용이성 우선)
- 복사 대상(파일 내용 무수정, `cp` — 전사 오류 원천 차단):
  `dock_core.hpp`·`dock_core.cpp`(코어 594줄), 골든(`golden.tsv`·`golden_check.cpp`),
  단위 검사기 6종(`phase4_steer`·`phase4_axis_gate`·`geom_entry`·`return_home`·
  `reachable_steer`·`rear_frame`), 코어 SIL(`dock_core_sil.cpp`)
- **이식하지 않는 것**: `dock_ik.*`(QD IK 어댑터 — W2 에서 `trnav_2ws_kinematics` 기반
  신작), `gen_golden.py`(정본 `phase1_gui.py` 가 있어야 재생성 가능 — TSV 만 자산으로
  가져오고 출처를 기록), ROS 조립(`dock_ros` — W3)
- CMakeLists·package.xml 만 신작(코어 의존 0 유지, ctest 등록)
- 검증: 골든 대조 0 불일치 + 단위 검사기 전 PASS 를 **우리 빌드에서 재실행**으로 증명

**후속 단계(별도 ADR)** — W2: 관측 어댑터(`/wall_pose` → 거리·수평·자세축) +
2WS IK steer-hold 어댑터 + 코어 SIL 재검, W3: 액션 서버 + 우리 sim 킷 SIL + HIL.
접근 방향(좌/우/후방)은 코어의 `steerFrameOffset`/`approach_sign` 설정으로 열어 두고
**실기에서 검증·확정**한다(사용자 지시).

## Consequences

- 이득: 실차에서 배운 실패 지식(조향 정착·steer-hold·재접근·runaway 방어·완료 게이트
  단독 축 규약 등)을 검증 자산째 승계. 골든이 함께 오므로 "이식이 정본과 같다"가
  우리 쪽에서도 기계 검증됨.
- 비용: 신규 패키지 1 + 인벤토리·이력 기록. LGIT 상류가 계속 진화하므로 재동기화
  시점마다 스냅샷 해시 갱신 필요.
- 남는 위험: ① `arm_m`·게인은 QD 기체 값 — 2WS 실기 재튜닝 전 미검증
  ② 골든 [B] 등급 항목은 "정본 줄 인용과 동일"까지만 담보(원본 한계 승계)
  ③ 관측을 px→m 로 바꾸는 W2 에서 게인 단위 재환산 필요.

## Rollback

N/A (가역) — 신규 디렉토리 삭제로 원복. 기존 코드 무수정.
