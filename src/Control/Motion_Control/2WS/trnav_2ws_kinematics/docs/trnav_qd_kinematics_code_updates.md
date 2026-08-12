# trnav_2ws_kinematics — Code Updates

> 형식: `YYYY-MM-DD / HH:MM - 커밋해시(7자리) / 추가·수정·삭제 + 패키지 내 상대 경로`

2026-08-13 / 04:21 - (pending) / **주석 라인 단위 재독 — 남은 모순 정정 + 주석에서 이력 제거** (코드 무변경)

- 규약 확정: **코드 주석에는 이력을 넣지 않는다.** 주석은 코드가 지금 무엇을 하는지만 적고,
  「무엇을 언제 왜 바꿨나」는 본 문서(code updates)가 보유한다. 직전 커밋 `6fb9663` 이 주석에
  변경 이력·감사 서술(「종전 …이었다」·「…교체됐고」·「…정정해 해소했다」·「(YYYY-MM-DD 확인)」·
  「… 는 이 저장소에 없다」)을 섞어 넣었던 것을 이번에 전량 걷어냈다.
- 범위: 2WS 스택 **16,174줄 전량**을 12 슬라이스로 나눠 라인 단위 재독.
  슬라이스마다 적대적 반박 2인(원문 변호 / 대체문 감사)이 코드로 재검증.
  86후보 → **69 적용**(모순 정정 47 + 이력 제거 22) / **17 기각**(변호 성립으로 원상 유지).
- 코드 무변경 증명: 변경 45파일을 언어별 파서로 대조 — C++ 16개 `gcc -fpreprocessed -E -P` 출력 동일,
  Python 13개 AST(Abstract Syntax Tree) 동일(모듈 docstring 제외), YAML/`.action`/CMake 13개
  `#` 주석 제거 후 동일, `package.xml` 3개 `<description>` 제외 XML 동일. **차이 0건.**
  이력 문구 잔존 스캔(`종전|정정해|해소했|교체됐|이 저장소에 없다|확인\)|not present in this repository`) **0건**.
- 검증: `colcon build --packages-up-to trnav_2ws_action_server …` 6패키지 PASS(0 error) ·
  `colcon test --packages-select trnav_2ws_core trnav_2ws_kinematics` 67 tests / 0 failures / 0 errors.
- 기각 사례(재발 방지용 기록) — 지적이 틀렸던 것들:
  · `amr_dock_align` 은 패키지가 아니라 **노드(실행파일) 이름**이라 「부재 패키지」 지적이 오독이었다.
  · turn 의 `R > 1.44 m`(v=0.05 기준 ω_max < 하한 2.0 dps)를 `1.43` 으로 「정밀화」하려 했으나
    R=1.431 m 에서 ω_max=2.0019 dps 라 **거짓이 된다** — 원문이 옳다.
  · `−dir × delta_heading` 은 죽은 표기가 아니라 QD 형제 코드(`trnav_qd_kinematics`)에 살아 있는
    grep 앵커이자 미결 쟁점의 참조점이라 토큰을 보존했다.
  · `분산 TF lookup 폐기`·`src/Control/Kinematics/` 언급은 이력이 아니라 **설계 근거·범위 제약**이라 유지.
- 수정 `src/qd_crab_inverse_kinematics.cpp` — wrap 마진 블록에서 이력 서술 제거, 남긴 것은 기능뿐:
  하류 클램프 115°(`can_relay` machine yaml `steer_limit_deg`)·상류 가드 113.32°(`qd_action_server_base.hpp:58`)가
  이 ±25° 마진을 수용한다. (직전 커밋이 적었던 「2026-08-06 결정」은 실제 `foil_a082.yaml` 변경일이 **2026-08-05** 라 날짜도 틀렸다.)
  rear offset 주석도 「헤더를 정정해 해소했다」 대신 현재 사실(`dir` 계수 없이 −delta_heading)만 남겼다.
- 수정 `include/…/qd_crab_inverse_kinematics.hpp` — rear offset 가정에서 개정 경위 안내 삭제,
  구현 상호참조 줄 앵커를 `.cpp:62` → `:63`(`rear_raw` 실제 위치)으로 정정.
- 수정 `package.xml` — `<description>` 표제 `QD (Quad-Drive diagonal) platform kinematics`
  → `2WS (inline dual-steer) platform kinematics`. 이 패키지의 대상 기체는 대각이 아니라 인라인이며
  같은 패키지 헤더 2종은 이미 그렇게 서술하고 있었다.

---

2026-08-11 / 22:37 - (pending) / **주석 감사 — 코드와 모순되는 주석 일괄 정정** (코드 무변경)

- 범위: 2WS 스택 전체(~15,400줄). **주석·docstring·`<description>` 만 수정, 실행 코드는 한 줄도 바꾸지 않았다.**
- 방법: 10인 독립 리더가 슬라이스별로 후보를 내고 슬라이스마다 적대적 반박 2인(원문 변호 / 대체문 감사)이
  코드로 재검증. 1차 82후보 → 반박 통과 79 + 저자 판정 3 = 82 적용. 2차(죽은 참조·inline↔대각 잔재·
  1차 0건 파일 전수 재독) 39후보 → 29 적용, 9 기각(변호인 반박 성립), 1 중복.
- 코드 무변경 증명: 변경 63파일 전부를 언어별 파서로 대조 — C++ 28개 `gcc -fpreprocessed -E -P` 출력 동일,
  Python 13개 AST(Abstract Syntax Tree) 동일(모듈 docstring 제외), YAML/`.action`/CMake 19개 `#` 주석 제거 후 동일,
  `package.xml` 3개 `<description>` 제외 XML 동일. **차이 0건.**
- 검증: `colcon build --packages-up-to trnav_2ws_action_server …` 6패키지 PASS(0 error) ·
  `colcon test` 67 tests / 0 failures / 0 errors.
- 기각 사례(기록): 상류 설계문서 인용(`AMR_Motion_Control_Implementation_Plan.md` §1.6.2,
  `Implementation Plan §5.4.3`, `trnav_motion_mux_architecture.md`, `dual_steer_engine.py … lines N-M`,
  `ADR-012`)을 「죽은 참조」로 고치려던 5건은 **반박당해 원상 유지**했다 — 저장소 상대경로가 아니라
  이식물의 정상적인 출처 표기이고, 「고치면」 오히려 이 저장소에서 확인되지 않는 상류 소재를
  새로 심게 된다. `Platform::QD_DIAGONAL` enum 정의 주석 계열 4건도 taxonomy 서술이라 기각.
- 수정 `src/qd_crab_inverse_kinematics.cpp` — wrap 마진 주석 **±20°/임계 ±110° → ±25°/±115°**(코드 `WRAP_MARGIN=25°` 와 어긋나 있었다);
  「모터 ±90° 한계」 서술을 「IK 유일해 정규화 기준」으로 정정하고 하류 클램프 115°(`foil_a082.yaml:200`)·상류 가드 113.32° 명시;
  `CLAMP_MARGIN` 의 「(어제 결정)」 상대시점 제거; 헤더 정정에 딸린 상호참조 정합.
- 수정 `include/…/qd_crab_inverse_kinematics.hpp` — `rear_steer_offset = −dir × delta_heading` → 구현 기준
  `rear_raw = base_raw − delta_heading`(dir 계수 없음); `wheels[0]=W1(front-left)` → `(front, w1_x>0)`.
- 수정 `include/…/qd_inverse_kinematics.hpp` — 클래스 표제 `QD diagonal-pair platform` → `inline dual-steer platform`
  (같은 파일 :83-84 가 「이 클래스는 그 배치가 아니다」라고 못 박고 있었다); wheels 인덱스 좌/우 표기 제거.
- 수정 `include/…/qd_bicycle_model.hpp` — 표제 `for QD diagonal platform` → `for the inline dual-steer platform`.
- 수정 `src/qd_inverse_kinematics.cpp` — `chassis_kinematics.py:64` → `:56`(±140° 선언 위치).
- 수정 `package.xml` — 존재하지 않는 클래스명(`TwoWsInverseKinematics`·`TwoWsCrabInverseKinematics`) → 실제
  `TwoWsDualSteerIK`·`TwoWsCrabIK`, 부재 경로 `src/Control/Kinematics/` 정정.

---

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
