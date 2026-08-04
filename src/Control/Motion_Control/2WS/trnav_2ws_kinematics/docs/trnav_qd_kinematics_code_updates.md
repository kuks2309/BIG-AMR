# trnav_2ws_kinematics — Code Updates

> 형식: `YYYY-MM-DD / HH:MM - 커밋해시(7자리) / 추가·수정·삭제 + 패키지 내 상대 경로`

2026-07-26 / 17:5x - (pending) / **QD → 2WS 리팩터 신설** (ADR 2026-07-26-2ws-motion-from-qd-refactor)

- `trnav_qd_kinematics`(QD) 복사 → `trnav_2ws_kinematics`. 네임스페이스 `trnav::motion::qd`→`two_ws`, 클래스 `Qd*`→`TwoWs*`(TwoWsDualSteerIK/TwoWsCrabIK/TwoWsBicycleModel), include dir `trnav_2ws_kinematics/`. QD 와 심볼·패키지명 분리(공존 가능).
- 코드 로직·수식 무변경(리네임만). 실물 Foil_A082 = inline 센터라인 2 조향휠 → 기하는 `trnav_2ws_core/config/robot_geometry_2ws.yaml`(W1 앞 +0.6039, W2 뒤 −0.5961, y=−0.0014, r=0.125)로 반영.
- 검증: colcon build error 0. `TwoWsDualSteerIK`(실측 기하) 출력 = Seer 원본 `chassis_kinematics.py` 소수4자리 일치(직진/크랩/스핀).

> **⚠ 2026-07-27 감사 정정 — 위 2줄(8·9행)의 「반영」·「검증」 서술에 빠진 조건.**
> 원문은 이력 보존용으로 남기며, **값 변경 0건**이다.
>
> 1. **「기하는 robot_geometry_2ws.yaml 로 반영」 → 런타임에는 반영되지 않았다.**
>    기하 파일을 작성한 것은 사실이나 **어떤 launch 도 그 파일을 로드하지 않는다.**
>    `trnav_2ws_action_server/launch/` 의 9종 launch 는 전부 `<action>_params.yaml` 하나만 넘긴다
>    (예: `trnav_2ws_action_server/launch/spin.launch.py:14-17`), 2WS 전 트리에서
>    `robot_geometry_2ws` 참조처는 docs/CMakeLists 뿐이다.
>    실행 시 실제 로드되는 값은 **Carrier AGV 플레이스홀더**다 —
>    `trnav_2ws_action_server/config/spin_params.yaml:30-34` (w1_x 0.330, w1_y 0.135,
>    w2_x −0.330, w2_y −0.135, wheel_radius 0.080). 파라미터 미지정 시 코드 default 도 동일하다
>    (`trnav_2ws_motion/include/trnav_2ws_motion/qd_action_server_base.hpp:189-194`).
>    그 결과 `trnav_2ws_action_server/src/mpc/mpc_action_server.cpp:119`
>    `wheelbase_ = std::fabs(w1_x - w2_x)` = **0.660 m** 가 되어,
>    `References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md:15`
>    의 휠베이스 **1.20 m** 의 절반이 MPC 자전거모델(`qd_mpc_controller.cpp` tan(δ)/wheelbase)에 들어간다.
> 2. **「TwoWsDualSteerIK(실측 기하) 출력 = Seer 원본 소수4자리 일치」는 오프라인 대조다.**
>    파일의 기하 값을 **직접 주입해 실행한 결과**이지 런타임(launch→노드) 경로 검증이 아니다.
>    또한 그 「실측 기하」 라벨 자체가 미판정이다 — `trnav_2ws_core/config/robot_geometry_2ws.yaml`
>    상단 주석의 2026-07-27 정정 (가)/(나), 및
>    `docs/adr/2026-07-26-2ws-motion-from-qd-refactor.md` §근거·검증 아래
>    「⚠ 2026-07-27 정정」 블록 ①「Foil_A082 실측 기하 = 미판정 모순」(2026-07-27 기준 :37-45) 참조.
> 3. 배선 수정(기하 파라미터를 각 노드에 병합/로드)은 **별도 승인 후** 별건으로 진행할 것.
>    승인 없이 파라미터 값을 갈아끼우면 실기 거동이 즉시 바뀐다.

## 2026-07-26

2026-07-26 / 15:3x - (pending) / **수정 `src/qd_inverse_kinematics.cpp` — ±90° 정규화 설계의도 주석화(로직 무변경)**

- `computeWheel()` 의 `normalizeAngle` 호출부에 **의도 주석** 추가: ±90°(반원) 정규화 = 등가 2해 `(θ,+v)≡(θ∓180°,−v)` 를 유일해로 확정(방향↔각도 전단사)·최소 조향각·결정론적 출력. Seer(±140°, chassis_kinematics.py) 대비 90~140° 2해 공존을 제거.
- 하드웨어 정합 확인(사용자): Big-AMR 조향 한계 > 90° → ±90° 정규화 항상 물리범위 내, 한계초과 위험 0.
  > **⚠ 2026-07-27 감사 정정 (위 줄은 이력 보존용으로 남김. 값·로직 변경 0건).**
  > 이 「위험 0」 단정은 **본 기체 확인이 아니다.** 근거 ADR 은 다른 기체를 확인한 것이다 —
  > `docs/adr/2026-07-26-qd-ik-pm90-unique-solution.md:71-72` 「하드웨어 정합: 확인 완료(2026-07-26)
  > — **Carrier AGV** 실제 조향 한계 > 90°」. 본 기체는 Foil_A082 다
  > (`docs/verified_facts/2026-07-27.md:11` 「장비: Foil_A082 실기」).
  > 또한 같은 패키지가 정반대로 서술한다 — `src/qd_crab_inverse_kinematics.cpp:23` 「모터 **±90° 한계** 반영」.
  > 게다가 「물리범위 내」 판정의 기준점인 **조향 절대 원점 자체가 미판정**이다
  > (`docs/verified_facts/2026-07-27.md` §B-1: Seer 1040 encoder 와 판다 read 가 조향 노드에서만
  > 7.87 M counts = 137° 어긋남, 원인 (a)판다 read 오염 / (b)호밍 후 기준 재설정 중 미판정).
  > ⇒ 확정 가능한 것은 「±90° 정규화 **출력**은 홈 기준 상대각 ±90° 이내」 뿐이다.
  > 물리 한계 초과 여부는 (a) 본 기체 조향 한계값, (b) 조향 절대 원점 이 둘 다 확정된 뒤에만 판정된다.
- 코드 로직·수치 출력 무변경(주석만). 재컴파일 PASS, 5케이스 출력 불변. 정본: `docs/adr/2026-07-26-qd-ik-pm90-unique-solution.md`.

## 2026-07-04

### 09:52 - (pending) / 신규 패키지 — QD 운동학 라이브러리 분리 이동 (AD-012 개정)

`trnav_2ws_motion` 에서 운동학 3종 분리 이동 (`git mv` 이력 보존). 사용자 지시 "기존 폴더 (Kinematics) 에 QD/DD 포함".
플랜: `docs/plan/2026-07-04_qd_kinematics_move.md`. 3중 prefix·namespace `trnav::motion::two_ws` 무변경.

- **추가** `package.xml` — deps: ament_cmake only (순수 수학, 이동 6파일 include 는 stdlib 뿐 — 원 CMake 의 `trnav_2ws_core` 의존은 실사용 없어 미승계, 빌드로 검증)
- **추가** `CMakeLists.txt` — STATIC 3 target (`qd_inverse_kinematics`, `qd_crab_inverse_kinematics`→IK 링크, `qd_bicycle_model`→IK 링크) + `trnav_2ws_kinematics_targets` export
- **이동+수정** `include/trnav_2ws_kinematics/{qd_inverse_kinematics,qd_crab_inverse_kinematics,qd_bicycle_model}.hpp`, `src/{동일 3종}.cpp` — include guard `TRNAV_2WS_MOTION__`→`TRNAV_2WS_KINEMATICS__`, include 경로 `trnav_2ws_motion/`→`trnav_2ws_kinematics/` (그 외 코드 무변경)
