# trnav_2ws_kinematics — Code Updates

> 형식: `YYYY-MM-DD / HH:MM - 커밋해시(7자리) / 추가·수정·삭제 + 패키지 내 상대 경로`

2026-07-26 / 17:5x - (pending) / **QD → 2WS 리팩터 신설** (ADR 2026-07-26-2ws-motion-from-qd-refactor)

- `trnav_qd_kinematics`(QD) 복사 → `trnav_2ws_kinematics`. 네임스페이스 `trnav::motion::qd`→`two_ws`, 클래스 `Qd*`→`TwoWs*`(TwoWsDualSteerIK/TwoWsCrabIK/TwoWsBicycleModel), include dir `trnav_2ws_kinematics/`. QD 와 심볼·패키지명 분리(공존 가능).
- 코드 로직·수식 무변경(리네임만). 실물 Foil_A082 = inline 센터라인 2 조향휠 → 기하는 `trnav_2ws_core/config/robot_geometry_2ws.yaml`(W1 앞 +0.6039, W2 뒤 −0.5961, y=−0.0014, r=0.125)로 반영.
- 검증: colcon build error 0. `TwoWsDualSteerIK`(실측 기하) 출력 = Seer 원본 `chassis_kinematics.py` 소수4자리 일치(직진/크랩/스핀).

## 2026-07-26

2026-07-26 / 15:3x - (pending) / **수정 `src/qd_inverse_kinematics.cpp` — ±90° 정규화 설계의도 주석화(로직 무변경)**

- `computeWheel()` 의 `normalizeAngle` 호출부에 **의도 주석** 추가: ±90°(반원) 정규화 = 등가 2해 `(θ,+v)≡(θ∓180°,−v)` 를 유일해로 확정(방향↔각도 전단사)·최소 조향각·결정론적 출력. Seer(±140°, chassis_kinematics.py) 대비 90~140° 2해 공존을 제거.
- 하드웨어 정합 확인(사용자): Big-AMR 조향 한계 > 90° → ±90° 정규화 항상 물리범위 내, 한계초과 위험 0.
- 코드 로직·수치 출력 무변경(주석만). 재컴파일 PASS, 5케이스 출력 불변. 정본: `docs/adr/2026-07-26-qd-ik-pm90-unique-solution.md`.

## 2026-07-04

### 09:52 - (pending) / 신규 패키지 — QD 운동학 라이브러리 분리 이동 (AD-012 개정)

`trnav_2ws_motion` 에서 운동학 3종 분리 이동 (`git mv` 이력 보존). 사용자 지시 "기존 폴더 (Kinematics) 에 QD/DD 포함".
플랜: `docs/plan/2026-07-04_qd_kinematics_move.md`. 3중 prefix·namespace `trnav::motion::two_ws` 무변경.

- **추가** `package.xml` — deps: ament_cmake only (순수 수학, 이동 6파일 include 는 stdlib 뿐 — 원 CMake 의 `trnav_2ws_core` 의존은 실사용 없어 미승계, 빌드로 검증)
- **추가** `CMakeLists.txt` — STATIC 3 target (`qd_inverse_kinematics`, `qd_crab_inverse_kinematics`→IK 링크, `qd_bicycle_model`→IK 링크) + `trnav_2ws_kinematics_targets` export
- **이동+수정** `include/trnav_2ws_kinematics/{qd_inverse_kinematics,qd_crab_inverse_kinematics,qd_bicycle_model}.hpp`, `src/{동일 3종}.cpp` — include guard `TRNAV_2WS_MOTION__`→`TRNAV_2WS_KINEMATICS__`, include 경로 `trnav_2ws_motion/`→`trnav_2ws_kinematics/` (그 외 코드 무변경)
