cmake_minimum_required(VERSION 3.10)
project(seer_rawmap_replay CXX)

# 비-ROS2 독립 도구 (저장소 규약: colcon 불요 → Tools/ 아래).
# `slam_karto_core` 는 src/Navigation 에 있는 순수 CMake 라이브러리라 add_subdirectory 로 그대로 끌어온다.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)   # 코어와 같은 기본값 — 스캔매칭은 -O0 이면 수배 느리다
endif()
add_compile_options(-Wall -Wextra)

set(SLAM_KARTO_CORE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../../src/Navigation/slam_karto_core"
    CACHE PATH "slam_karto_core 소스 디렉터리")
get_filename_component(SLAM_KARTO_CORE_DIR "${SLAM_KARTO_CORE_DIR}" ABSOLUTE)
if(NOT EXISTS "${SLAM_KARTO_CORE_DIR}/CMakeLists.txt")
  message(FATAL_ERROR
    "slam_karto_core 를 찾지 못했다: ${SLAM_KARTO_CORE_DIR}\n"
    "  -DSLAM_KARTO_CORE_DIR=<경로> 로 지정할 것")
endif()

# g2o 를 **여기(최상위)에서** 먼저 찾는다.
#   add_subdirectory 안에서만 find_package 하면 임포트 타깃이 그 디렉터리 스코프에 갇혀
#   이 실행 파일의 RPATH 계산에서 g2o::core 를 조회할 수 없다.
find_package(g2o REQUIRED)

add_subdirectory("${SLAM_KARTO_CORE_DIR}" slam_karto_core_build)

add_executable(replay_ours replay_ours.cpp)
target_link_libraries(replay_ours PRIVATE slam_karto_core)
target_include_directories(replay_ours PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# ── g2o RPATH 함정 ───────────────────────────────────────────────────────────
# g2o 는 /opt/ros/<distro>/lib/<arch>/ 에 있고 그 경로는 ldconfig 캐시에 없다.
# 게다가 libg2o_types_slam2d.so 는 libg2o_opengl_helper.so 를 NEEDED 로 갖는데 자기 RUNPATH 가 없다
# (`readelf -d` 로 확인) — DT_RUNPATH 는 **전이되지 않으므로** 그 의존이 런타임에 해석되지 않는다.
# `--disable-new-dtags` 로 DT_RPATH 를 내면 전이 탐색에 쓰여 해결된다.
# 코어(src/Navigation/slam_karto_core/CMakeLists.txt:94-118)와 **같은 방식**이다.
get_target_property(_g2o_core_loc g2o::core IMPORTED_LOCATION_NONE)
if(NOT _g2o_core_loc)
  get_target_property(_g2o_core_loc g2o::core IMPORTED_LOCATION_RELEASE)
endif()
if(NOT _g2o_core_loc)
  get_target_property(_g2o_core_loc g2o::core LOCATION)
endif()
if(_g2o_core_loc)
  get_filename_component(_g2o_libdir "${_g2o_core_loc}" DIRECTORY)
  set_target_properties(replay_ours PROPERTIES
    BUILD_RPATH "${_g2o_libdir}" INSTALL_RPATH "${_g2o_libdir}"
    LINK_FLAGS "-Wl,--disable-new-dtags")
  message(STATUS "replay_ours: g2o RPATH = ${_g2o_libdir}")
else()
  message(WARNING "replay_ours: g2o 라이브러리 경로를 특정하지 못했다 — "
                  "실행 시 LD_LIBRARY_PATH 가 필요할 수 있다")
endif()
