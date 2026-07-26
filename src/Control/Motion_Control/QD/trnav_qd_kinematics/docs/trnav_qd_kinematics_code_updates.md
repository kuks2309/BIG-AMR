# trnav_qd_kinematics — Code Updates

> 형식: `YYYY-MM-DD / HH:MM - 커밋해시(7자리) / 추가·수정·삭제 + 패키지 내 상대 경로`

## 2026-07-04

### 09:52 - (pending) / 신규 패키지 — QD 운동학 라이브러리 분리 이동 (AD-012 개정)

`trnav_motion_qd` 에서 운동학 3종 분리 이동 (`git mv` 이력 보존). 사용자 지시 "기존 폴더 (Kinematics) 에 QD/DD 포함".
플랜: `docs/plan/2026-07-04_qd_kinematics_move.md`. 3중 prefix·namespace `trnav::motion::qd` 무변경.

- **추가** `package.xml` — deps: ament_cmake only (순수 수학, 이동 6파일 include 는 stdlib 뿐 — 원 CMake 의 `trnav_motion_core` 의존은 실사용 없어 미승계, 빌드로 검증)
- **추가** `CMakeLists.txt` — STATIC 3 target (`qd_inverse_kinematics`, `qd_crab_inverse_kinematics`→IK 링크, `qd_bicycle_model`→IK 링크) + `trnav_qd_kinematics_targets` export
- **이동+수정** `include/trnav_qd_kinematics/{qd_inverse_kinematics,qd_crab_inverse_kinematics,qd_bicycle_model}.hpp`, `src/{동일 3종}.cpp` — include guard `TRNAV_MOTION_QD__`→`TRNAV_QD_KINEMATICS__`, include 경로 `trnav_motion_qd/`→`trnav_qd_kinematics/` (그 외 코드 무변경)
