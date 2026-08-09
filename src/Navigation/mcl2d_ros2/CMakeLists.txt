cmake_minimum_required(VERSION 3.10)
project(mcl2d_ros2)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
# ament 기본 빌드타입은 비어 있어 최적화 플래그가 붙지 않는다(-O0). 파티클필터가 핫패스라
# 그대로 두면 위치추정 주기가 34Hz 입력 대비 4.83Hz 까지 떨어진다(2026-08-02 실기 A/B,
# 인스턴스 1개 조건 30초 측정: Release 29.6Hz / 최적화없음 4.83Hz = 6.1배, 처리비율 0.95 vs 0.15).
# 형제 mcl2d_core/CMakeLists.txt 와 동일하게 기본을 Release 로.
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(tf2_ros REQUIRED)

# 프레임워크-독립 코어 + 맵 로더 (형제 디렉터리). ROS 의존 0인 순수 C++.
set(CORE ${CMAKE_CURRENT_SOURCE_DIR}/../mcl2d_core)
set(MAP  ${CMAKE_CURRENT_SOURCE_DIR}/../mcl2d_map)
set(NONROS ${CMAKE_CURRENT_SOURCE_DIR}/../../../Tools/mcl2d_standalone)
# PF 는 이제 Seer 충실 관측모델 ObservationField 사용(2026-07-13 이관). 레거시
# likelihood_grid/observation_model 은 loc_verification 스캐폴딩 전용이라 여기선 미포함.
add_library(mcl2d_core_lib STATIC
  ${CORE}/src/motion_model.cpp
  ${CORE}/src/observation_field.cpp ${CORE}/src/particle_filter.cpp
  ${CORE}/src/skid_detector.cpp
  ${MAP}/src/smap.cpp
  ${NONROS}/src/mcl2d_localizer.cpp)
target_include_directories(mcl2d_core_lib PUBLIC
  ${CORE}/include ${MAP}/include ${NONROS}/include)

set(DEPS rclcpp geometry_msgs nav_msgs sensor_msgs tf2_ros)

add_executable(mcl2d_localization_node src/mcl2d_localization_node.cpp)
target_include_directories(mcl2d_localization_node PRIVATE include)
target_link_libraries(mcl2d_localization_node mcl2d_core_lib)
ament_target_dependencies(mcl2d_localization_node ${DEPS})

# 맵 서버 — 측위와 책임이 다르다(맵 제공 vs 자세 추정). 내비게이션만 시험할 때 측위 없이
#   맵만 띄울 수 있도록 별도 실행파일로 둔다. visualization_msgs 는 반사판 마커에만 쓴다.
find_package(visualization_msgs REQUIRED)
add_executable(smap_map_server src/smap_map_server.cpp)
target_link_libraries(smap_map_server mcl2d_core_lib)
ament_target_dependencies(smap_map_server rclcpp nav_msgs visualization_msgs)

install(TARGETS mcl2d_localization_node smap_map_server DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_gtest QUIET)  # 미사용 — 자체 assert 하니스
  add_executable(compare_impls test/compare_impls.cpp)
  target_include_directories(compare_impls PRIVATE include)
  target_link_libraries(compare_impls mcl2d_core_lib)
  ament_target_dependencies(compare_impls ${DEPS})
  install(TARGETS compare_impls DESTINATION lib/${PROJECT_NAME})
endif()

ament_package()
