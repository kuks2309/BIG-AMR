cmake_minimum_required(VERSION 3.10)
project(trnav_2ws_dock_control CXX)

# LGIT-C6-Cobot 7a2df984 의 dock_control 코어 무수정 이식(W1).
# package.xml 없음 = colcon 무시(mcl2d_core 관례) — ROS 조립은 W3 별도 패키지.
# 코어는 의존 0 — 골든·단위 검증이 ROS 워크스페이스 없이 돌아야 한다(원본 계약 승계).
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra -Wpedantic)

add_library(dock_control_core STATIC src/dock_core.cpp)
target_include_directories(dock_control_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

enable_testing()

# 골든 대조 — 정본(phase1_gui.py) 벡터와 1e-12 대조. 무수정 이식의 기계 증명.
add_executable(golden_check test/golden/golden_check.cpp)
target_link_libraries(golden_check PRIVATE dock_control_core)
add_test(NAME golden_check
         COMMAND golden_check ${CMAKE_CURRENT_SOURCE_DIR}/test/golden/golden.tsv)

# 단위 검사기 6종 (코어만 링크)
foreach(t phase4_steer_check phase4_axis_gate_check geom_entry_check
          return_home_check reachable_steer_check rear_frame_check)
  add_executable(${t} test/unit/${t}.cpp)
  target_link_libraries(${t} PRIVATE dock_control_core)
  add_test(NAME ${t} COMMAND ${t})
endforeach()

# 코어 SIL — 판정하지 않는 실행기(합격선은 결재 소관). 스모크로만 등록.
add_executable(dock_core_sil test/sil/dock_core_sil.cpp)
target_link_libraries(dock_core_sil PRIVATE dock_control_core)
add_test(NAME dock_core_sil_smoke COMMAND dock_core_sil)

# ── W2: 2WS 어댑터 (개작·신작 — 무수정 코어와 타깃 분리) ─────────────────────
# IK steer-hold 어댑터 — trnav_2ws_kinematics 소스를 직접 컴파일(plain cmake 관례)
set(KIN ${CMAKE_CURRENT_SOURCE_DIR}/../trnav_2ws_kinematics)
add_library(dock_ik_2ws STATIC
  src/dock_ik.cpp
  ${KIN}/src/qd_inverse_kinematics.cpp)
target_include_directories(dock_ik_2ws PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include ${KIN}/include)
target_link_libraries(dock_ik_2ws PUBLIC dock_control_core)

# 관측 어댑터 — /wall_pose 자세 → 코어 관측 3축
add_library(dock_obs_2ws STATIC src/dock_obs.cpp)
target_include_directories(dock_obs_2ws PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(dock_obs_2ws PUBLIC dock_control_core)

# 골든 위임 188건(orbit/fwd) 등가 — 우리 2WS IK 수학이 정본과 같은가 (QD 기하 주입).
# 허용오차 1e-12: 2WS 이식본은 QD 원본과 연산 순서가 달라 1~2 ulp(실측 최대 4.4e-16)
# 차이가 난다 — 골든의 기본 철학(비트 동일이 아니라 1e-12 상대오차, libm 차이 흡수)을 따른다.
add_executable(ik_parity_check test/golden/ik_parity_check.cpp)
target_link_libraries(ik_parity_check PRIVATE dock_ik_2ws)
add_test(NAME ik_parity_check
         COMMAND ik_parity_check ${CMAKE_CURRENT_SOURCE_DIR}/test/golden/golden.tsv 1e-12)

foreach(t dock_obs_check steer_hold_check)
  add_executable(${t} test/unit/${t}.cpp)
  target_link_libraries(${t} PRIVATE dock_ik_2ws dock_obs_2ws)
  add_test(NAME ${t} COMMAND ${t})
endforeach()
