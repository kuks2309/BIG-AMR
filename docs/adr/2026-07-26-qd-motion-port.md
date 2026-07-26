# ADR 2026-07-26 — QD 모션 스택(AMR-Motion) Big-AMR 이식 + NLopt 의존 추가

## 상태
채택(이식·빌드 검증 완료). ROS2 Humble / Jetson(Tegra, aarch64)에서 6개 패키지 colcon build error 0.
DD 경로는 본 이식 범위 밖(사용자 결정 — 별도 검증된 git 에서 반입 예정).

## 맥락
사용자 요청 "qt(=QD) motion 이식". 원본은 `kuks2309/TR_Nav_ros2_ws` 의 `src/Control/AMR-Motion/`
(quad-drive 대각 조향 모션 스택). Big-AMR 는 4륜 quad-drive 플랫폼이고 `src/Control/Motion_Control/{QD,4IS,DD,2WS}`
빈 스켈레톤을 보유. AMR-Motion 5개 패키지는 단독 빌드 불가 — 폴더 밖의 `trnav_msgs`(AMR-Msgs/),
`trnav_qd_kinematics`(Kinematics/) 를 transitive 의존으로 요구. 의존 폐포 조사 결과 그 외는 전부
표준 ROS2 Humble 패키지(`acs_msgs` 등 불필요).

## 결정
QD 경로 **6개 패키지**를 `src/Control/Motion_Control/QD/` 로 이식(원본 트리 구조 유지):

- `trnav_interfaces` — AMRMotion 9종 action + AMRControlStop srv (dep: nav_msgs)
- `trnav_msgs` — motor/wheel/odometry msg·srv (dep: builtin_interfaces, std_msgs, geometry_msgs; self-contained)
- `trnav_qd_kinematics` — inverse/crab IK + bicycle model (순수 C++ 라이브러리, msg 의존 0)
- `trnav_motion_core` — motion_profile · transient_guard · localization_monitor (dep: trnav_msgs, rclcpp, tf2)
- `trnav_motion_qd` — path/mpc controller · wheel_set_packer (dep: qd_kinematics, motion_core, trnav_msgs)
- `trnav_motion_action_server` — 9종 action server(mpc·mpc_reverse·spin·turn·translate_fwd/rev·yaw_control/rev·crab_linear) + SIL/HIL launch

빌드 순서(의존): interfaces·msgs·qd_kinematics → motion_core → motion_qd → action_server.
설치 노드 9종: `amr_{mpc,mpc_reverse,spin,turn,translate_forward,translate_reverse,yaw_control,yaw_control_reverse,crab_linear}_node`.

## 의존성 추가 — NLopt (License·취약점·대안 3필드)
`trnav_motion_qd/qd_mpc_controller.cpp` 의 MPC(Model Predictive Control) 가 NLopt(Nonlinear Optimization
library) SLSQP 솔버 사용(`#include <nlopt.hpp>`, CMake `find_library(NLOPT_LIB nlopt REQUIRED)`).

- **설치**: `sudo apt-get install -y libnlopt-cxx-dev libnlopt-dev` (Ubuntu 22.04 공식, 2.7.1-3build1). 사용자 수행 완료.
  결과: `/usr/include/nlopt.hpp`, `/usr/lib/aarch64-linux-gnu/libnlopt.so`(+`libnlopt_cxx.so`).
- **License**: NLopt = LGPL v2.1+ (core) / 일부 서브솔버 MIT·BSD. SLSQP 는 자유 재배포 가능. 상용 배포 시 LGPL 동적링크(현 방식) 준수 — 정적링크 아님(`libnlopt.so` shared).
- **취약점**: 수치최적화 순수 연산 라이브러리(네트워크·파서·직렬화 sink 없음). 알려진 CVE 없음. 입력은 로봇 내부 상태(외부 신뢰경계 횡단 아님).
- **대안**: (a) 자체 QP 솔버 구현 → 검증부담·회귀위험 큼, 기각. (b) OSQP/qpOASES 치환 → 원본 알고리즘(SLSQP NLP)과 불일치, 이식 동일성 훼손, 기각. (c) NLopt 채택 → 원본과 동일 동작 보장, 표준 저장소 제공, 채택.
- **원본 미선언 보완**: 원본 `package.xml` 이 nlopt 를 rosdep 로 선언하지 않아(system find_library 만) 이식 시 `<depend>nlopt</depend>` 추가 → 향후 `rosdep install` 자동 해결.

## 근거·검증
- 의존 폐포: 6개 내부 + 표준 ROS2(rclcpp, rclcpp_action, std/geometry/sensor/nav_msgs, tf2, tf2_ros, builtin_interfaces)만. `acs_msgs` 불요 확인.
- 빌드: `colcon build --packages-select <6> --cmake-args -DCMAKE_BUILD_TYPE=Release` → 6/6 finished, **error 0**. stderr 는 `-Wformat`(%d vs size_t) 경고뿐(원본 잔존, 동작 무영향).
- 설치 확인: `install/` 6개 패키지 + action_server 노드 9종 실행파일 생성.
- 미검증(정직 표기): 실차/SIL/HIL 런타임 동작·파라미터 튜닝은 본 이식 범위 밖(빌드·링크 검증까지). 실행 검증은 후속.

## 기각안
- AMR-Motion 전체(+dd) 이식 | 사용자가 DD 는 별도 검증 git 반입 결정 → QD 만.
- 기존 Motion_Control 스켈레톤(QD/4IS/DD/2WS)에 패키지 분해 재배치 | 원본 트리와 달라져 upstream 대조·동기화 곤란. 사용자 지정대로 `Motion_Control/QD/` 하위에 원본 구조 유지.

## 영향·주의
- Scope: 신규 패키지 6개 추가(기존 코드 무수정). 유일 소스 변경 = `trnav_motion_qd/package.xml` 에 `<depend>nlopt</depend>` 1줄.
- 런타임 전제: 배포 타깃마다 `libnlopt-cxx-dev`·`libnlopt-dev` 설치 필요(rosdep 또는 apt). 미설치 시 qd·action_server 빌드 실패.
- 세션 격리: 본 이식은 세션 9f9c8a0a 산출물. 커밋은 `session/9f9c8a0a` 브랜치(다중 세션 공유 워킹트리 §2-1) → master merge 는 사용자 소관.
- Confidence: high(빌드·링크·의존폐포). Not-tested: 런타임 거동, MPC 게인 실차 적합성.
