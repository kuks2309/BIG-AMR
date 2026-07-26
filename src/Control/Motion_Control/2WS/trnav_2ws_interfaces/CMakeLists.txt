cmake_minimum_required(VERSION 3.8)
project(trnav_2ws_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(nav_msgs REQUIRED)

# Wave 1 (2026-04-23): Spin 파일럿 활성화.
# Wave 3 (2026-04-24): Translate action 추가 — BICYCLE 모드 우선 구현 (Wave 4).
# Wave (2026-04-26): Crab action 추가 — 횡이동 (heading 유지), open-loop 적분.
# 2026-04-27: Translate 를 Forward/Reverse 로 분리. AMRMotionTranslate → AMRMotionTranslateForward.
# 2026-04-28: Turn (T-Robot ROS2 원본 그대로 이식) + YawControl (ROS1 개념 + bicycle + 거리 종료 신규 설계) 추가.
# 2026-04-28: YawControl 을 Forward(기본)/Reverse 로 분리 — translate_forward/reverse 와 일관된 카테고리.
#             reverse 는 vx_max magnitude(>0) + 내부 부호 반전. effective_yaw 보정 미적용 (PathController 미사용).
# 2026-04-29: PurePursuit 추가 — 폐기 (2026-05-28)
# 2026-04-29: PurePursuitReverse 추가 — 폐기 (2026-05-28)
# 2026-05-21: AMRMotionCrab → AMRMotionCrabLinear 단일 교체 (target_yaw 능동 유지 + start↔end 직선 closed-loop 추종).
#             source_id=4 슬롯 재사용. 기존 AMRMotionCrab 삭제.
# 2026-05-28: PurePursuit/Reverse → MPC/Reverse 정공법 교체 — kinematic bicycle MPC (NLopt SLSQP).
#             HF5 R=1m 90° arc 검증 결과 MPC hdg 0.22° vs PP 4.96° (20× 우위). DRIVE_MPC=8 / DRIVE_MPC_REVERSE=9.
rosidl_generate_interfaces(${PROJECT_NAME}
  "action/AMRMotionSpin.action"
  "action/AMRMotionTranslateForward.action"
  "action/AMRMotionTranslateReverse.action"
  "action/AMRMotionCrabLinear.action"
  "action/AMRMotionTurn.action"
  "action/AMRMotionYawControl.action"
  "action/AMRMotionYawControlReverse.action"
  "action/AMRMotionMpc.action"
  "action/AMRMotionMpcReverse.action"
  "srv/AMRControlStop.srv"
  DEPENDENCIES nav_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
