# 2WS 모션 자전거모델(bicycle model) ↔ QD 자전거모델 대조

> 2026-07-31 (KST) · 세션 목적: **AMR 모션 제어 모드 비교 확인**
> 대상: `src/Control/Motion_Control/2WS` ↔ `src/Control/Motion_Control/QD`
> 질문: **"2WS 모션에 QD 의 bicycle 이 적용되었나?"**
> 범위: 적용 여부·동일성·실행 시 파라미터까지. **결함 평가(code_review)·구조 문서(sw_structure)는 본 문서 소관이 아니다.**

## 0. 근거 등급

| 기호 | 의미 |
| --- | --- |
| **✓** | 이 세션이 저장소 파일을 직접 조회(`diff`/`grep`/`find`)해 확인 |
| **⚠** | 미판정 — 실기 실측이 있어야 확정 가능 |

본 문서의 ✓ 항목은 모두 아래 명령의 출력이 근거다(작업 디렉터리 `src/Control/Motion_Control/`).

```bash
diff -u QD/trnav_qd_kinematics/include/trnav_qd_kinematics/qd_bicycle_model.hpp \
        2WS/trnav_2ws_kinematics/include/trnav_2ws_kinematics/qd_bicycle_model.hpp
diff -u QD/trnav_qd_kinematics/src/qd_bicycle_model.cpp \
        2WS/trnav_2ws_kinematics/src/qd_bicycle_model.cpp
grep -rln "bicycle_model_\|BicycleModel" 2WS/trnav_2ws_action_server/src/
grep -rln "bicycle_model_\|BicycleModel" QD/trnav_motion_action_server/src/
grep -rl "robot_geometry_2ws" 2WS/trnav_2ws_action_server/launch/   # → 0건
```

## 1. 결론

**적용됐다 — QD 원본을 이름만 바꿔 복사한 것이다.** 다만 실행 시 로드되는 기하 파라미터가
QD(Carrier AGV) 값 그대로라서, 모델은 같아도 **입력 상수가 본 기체와 다르다**.

| 축 | 판정 | 등급 |
| --- | --- | --- |
| 모델 코드(수식·상수·분기) | QD 와 **완전 동일** | ✓ |
| 호출 지점(어느 액션이 쓰는가) | QD 와 **동일한 6종** | ✓ |
| 빌드 연결 | 연결됨(죽은 코드 아님) | ✓ |
| 기하 파라미터(휠베이스·휠반경·감속비) | **QD 값이 그대로 로드됨** | ✓ |
| 그 파라미터가 실주행에 미치는 영향의 크기 | 실측·주행 확인 전 미판정 | ⚠ |

## 2. 코드 동일성 ✓

`diff -u` 로 두 쌍을 비교한 결과, **차이는 네임스페이스·클래스명·include 경로뿐이고
수식·상수·분기·예외 메시지 구조는 1줄도 다르지 않다.** 줄 수도 같다(131 / 194).

| 항목 | QD | 2WS |
| --- | --- | --- |
| 헤더 | `QD/trnav_qd_kinematics/include/trnav_qd_kinematics/qd_bicycle_model.hpp` (131줄) | `2WS/trnav_2ws_kinematics/include/trnav_2ws_kinematics/qd_bicycle_model.hpp` (131줄) |
| 구현 | `QD/trnav_qd_kinematics/src/qd_bicycle_model.cpp` (194줄) | `2WS/trnav_2ws_kinematics/src/qd_bicycle_model.cpp` (194줄) |
| 클래스 | `QdBicycleModel` | `TwoWsBicycleModel` |
| 네임스페이스 | `trnav::motion::qd` | `trnav::motion::two_ws` |

핵심 수식이 그대로 보존됐음(양쪽 동일):

- `toVelocityCommand(DualBicycleCommand)` — `omega = vx * (tan(δf) − tan(δr)) / L`
- `deltaFromOmega` — `atan(ω·L/vx)` (주석의 "`atan2` 아님" 경고까지 동일)
- `L_ = |wheels[0].x − wheels[1].x|` (생성자에서 휠 좌표로부터 산출)
- `kDeltaMax = π/2 − 0.001`

같은 방식의 복사본이 자전거모델만은 아니다 — `qd_inverse_kinematics.*`,
`qd_crab_inverse_kinematics.*`, `qd_path_controller.*`, `qd_mpc_controller.*` 도 동일 패턴이다.
2WS 쪽 IK 구현에는 QD 에 없는 **2026-07-27 감사 주석 블록**이 추가돼 있으나(±90° 정규화의
물리한계 초과 여부 미판정), 코드·수치 변경은 0건이다.

### 2.1 개명되지 않고 남은 흔적

- 파일명이 여전히 `qd_` 접두사 (`2WS/trnav_2ws_kinematics/**/qd_bicycle_model.*`)
- 빌드 타깃명도 `qd_bicycle_model` / `qd_inverse_kinematics`
  (`2WS/trnav_2ws_kinematics/CMakeLists.txt:17,37`)
- 클래스 주석이 `"for QD diagonal platform"` (2WS 헤더 :43)
- config 의 `platform: "QD_DIAGONAL"` (아래 §4)

## 3. 적용 지점 — QD 와 동일한 6종 ✓

`bicycle_model_` 멤버를 실제로 생성·사용하는 액션 서버가 **양쪽 모두 정확히 같은 6개**다.

| 액션 | QD | 2WS |
| --- | --- | --- |
| `mpc` | ✓ | ✓ |
| `mpc_reverse` | ✓ | ✓ |
| `translate_forward` | ✓ | ✓ |
| `translate_reverse` | ✓ | ✓ |
| `yaw_control` | ✓ | ✓ |
| `yaw_control_reverse` | ✓ | ✓ |

빌드도 연결돼 있다 — `2WS/trnav_2ws_kinematics/CMakeLists.txt:37-45` 가
`qd_bicycle_model` STATIC 타깃을 만들고 `qd_inverse_kinematics` 를 링크하며,
`ament_export_targets` 로 하류(`trnav_2ws_motion`·`trnav_2ws_action_server`)에 내보낸다.

제어 모드 측면에서도 BICYCLE 이 사실상 유일한 경로다:

- PathController 기본 모드 `ControlMode::BICYCLE`
  (`translate_forward_action_server.hpp:88` — 주석 "BICYCLE 고정. Mode 2+ 는 후속 Wave.")
- 다른 모드는 런타임 거부 — `"control_mode=%u 미지원 (BICYCLE=1 만 지원)"`
  (`mpc_action_server.cpp:295`, `mpc_reverse_action_server.cpp:283`,
  `translate_reverse_action_server.cpp:250`)
- `crab_linear` 도 `ControlMode::BICYCLE` 강제 (`crab_linear_action_server.cpp:79,356`)
- `qd_path_controller.cpp:113-114` — "Wave 2: BICYCLE mode only. 후속 Wave 에서 switch 로 확장."

## 4. 기하 파라미터 — QD 값이 그대로 로드된다 ✓

액션별 `config/<action>_params.yaml` 도 QD 원본의 복사본이며, 파일 자체가 그 사실을
2026-07-27 감사 주석으로 이미 남기고 있다(`translate_forward_params.yaml:3-23`).

| 파라미터 | 2WS config 실제 값 | 본 기체(Foil_A082) 기록값 |
| --- | --- | --- |
| `platform` | `"QD_DIAGONAL"` | 인라인 센터라인 2조향휠 |
| `w1_x` / `w2_x` | `+0.330` / `−0.330` → **L = 0.660 m** | `robot_geometry_2ws.yaml:37,39,55` → **1.200 m** |
| `wheel_radius` | `0.080` | `robot_geometry_2ws.yaml:57` → `0.125` |
| `gear_walk` | `20.0` | `robot_geometry_2ws.yaml:60` → `32.0` |

**이 값이 실제로 로드된다는 근거** ✓ — 17종 launch 파일 중 `robot_geometry_2ws.yaml` 을
참조하는 것이 **0건**이고(`grep -rl robot_geometry_2ws 2WS/trnav_2ws_action_server/launch/` → 0),
2WS 트리 어느 소스·CMake 도 그 파일명을 참조하지 않는다. 각 launch 는 `<action>_params.yaml`
하나만 넘긴다(예: `translate_forward.launch.py:22`). 파라미터 미지정 시 코드 default 도
동일 값이다(`qd_action_server_base.hpp:189-194`).

⇒ 자전거모델의 `L_` 에는 **0.660 m**(기록 휠베이스 1.200 m 의 절반)가 들어가고,
곡률 `tan(δ)/L` · 각속도 `v·tan(δ)/L` 는 그만큼 커진다.
`robot_geometry_2ws.yaml` 은 현재 **참조되지 않는 문서용 파일**이다.

**⚠ 미판정**: 위 두 값 중 어느 쪽이 본 기체의 참값인지는 이 세션에서 판정하지 않았다.
`robot_geometry_2ws.yaml` 자체가 전/후 노드 귀속을 "미판정 모순"으로 표기하고 있고
(`:36`, `:47`), 관련 부채가 이미 `docs/debt/registry.md`(2026-07-28 이관 항목 2건 —
`track_width: 1.2` 의 의미, `module_x` 노드 배정)로 등록돼 있다. 판정에는 실측이 필요하다.

## 5. 요약

| 질문 | 답 |
| --- | --- |
| 2WS 에 QD bicycle 이 적용됐나 | **그렇다.** 이름만 바꾼 동일 코드이며 6개 액션이 실제로 호출한다 |
| 두 모델이 다른가 | **아니다.** 수식·상수·분기 차이 0 |
| 그대로 써도 되나 | 모델은 인라인 2WS 에도 성립하지만, **로드되는 기하가 QD 값**이다. 실기 적용 전 §4 정합 필요 |

---

**관련**: `docs/debt/registry.md`(휠베이스·노드 배정 부채) ·
`src/Control/Motion_Control/2WS/trnav_2ws_action_server/config/*.yaml`(파일 내 2026-07-27 감사 주석)
