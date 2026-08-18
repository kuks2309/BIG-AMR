cmake_minimum_required(VERSION 3.10)
project(slam_karto_ros2)

# ── 코어 결합 방식 ────────────────────────────────────────────────────────────
# slam_karto_core 는 **설치 규칙이 없는** 순수 CMake 프로젝트다
# (`grep -n "install(" ../slam_karto_core/CMakeLists.txt` → 0건). 즉 find_package 로 쓸
# 임포트 타깃도, export 세트도 없다. 그래서 형제 mcl2d_ros2 의 선례
# (mcl2d_ros2/CMakeLists.txt:24-36 — 코어 소스를 이 패키지에서 직접 컴파일)를 따른다.
# add_subdirectory 는 쓰지 않는다 — 코어의 enable_testing/기본 빌드타입/타깃 이름이
# ament 빌드에 섞여 들어온다.
#
# 다만 mcl2d 와 달리 **정적 라이브러리로 뭉치지 않는다.** 동봉 Open Karto 는 LGPL-3.0 이고
# 코어 CMakeLists.txt:11 이 "공유 라이브러리로 분리 빌드" 를 명시한다 — 여기서도 SHARED 다.

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()
# ament 기본 빌드타입은 비어 있어 -O0 다. 스캔매칭·루프클로저·g2o 가 전부 핫패스라
# 코어(slam_karto_core/CMakeLists.txt:16)와 동일하게 Release 를 기본으로 둔다.
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
add_compile_options(-Wall -Wextra)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_srvs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)

# 코어의 비-ROS 의존 (slam_karto_core/CMakeLists.txt:24-26 과 동일).
find_package(Eigen3 REQUIRED)
find_package(Boost REQUIRED COMPONENTS thread system)
find_package(g2o REQUIRED)

set(CORE       ${CMAKE_CURRENT_SOURCE_DIR}/../slam_karto_core)
set(KARTO_DIR  ${CORE}/third_party/open_karto)
set(MAP        ${CMAKE_CURRENT_SOURCE_DIR}/../mcl2d_map)

# ── 동봉 Open Karto (LGPL-3.0 → SHARED) ──────────────────────────────────────
add_library(karto_vendored SHARED
  ${KARTO_DIR}/src/Karto.cpp
  ${KARTO_DIR}/src/Mapper.cpp)
target_include_directories(karto_vendored PUBLIC $<BUILD_INTERFACE:${KARTO_DIR}/include>)
target_link_libraries(karto_vendored PUBLIC Boost::thread Boost::system)
target_compile_options(karto_vendored PRIVATE -w)  # 상류 코드는 우리 경고 대상이 아니다

# ── 선형해법기 선택: CSparse(원본 충실) 우선, 없으면 Eigen 폴백 ───────────────
# g2o 의 csparse_extension 임포트 타깃은 SuiteSparse include 를 실어주지 않는다
# → cs.h 를 직접 찾아 넣지 않으면 `fatal error: cs.h: No such file or directory`.
find_path(CSPARSE_INCLUDE_DIR cs.h PATHS /usr/include /usr/include/suitesparse)
set(_g2o_solver_targets "")
set(_g2o_solver_def "")
if(CSPARSE_INCLUDE_DIR AND TARGET g2o::solver_csparse)
  set(_g2o_solver_targets g2o::solver_csparse g2o::csparse_extension)
  set(_g2o_solver_def SLAM_G2O_USE_CSPARSE)
  message(STATUS "slam_karto_ros2: g2o CSparse 선형해법기 (원본 충실)")
elseif(TARGET g2o::solver_eigen)
  set(_g2o_solver_targets g2o::solver_eigen)
  message(STATUS "slam_karto_ros2: g2o Eigen 선형해법기 (CSparse 부재 폴백 — 원본과 다름)")
else()
  message(FATAL_ERROR "slam_karto_ros2: g2o 선형해법기(csparse/eigen)를 하나도 찾지 못했다")
endif()

# ── SLAM 코어 ────────────────────────────────────────────────────────────────
add_library(slam_karto_core SHARED
  ${CORE}/src/g2o_solver.cpp
  ${CORE}/src/seer_mapper_config.cpp
  ${CORE}/src/seer_slam_mapper.cpp)
target_include_directories(slam_karto_core PUBLIC
  $<BUILD_INTERFACE:${CORE}/include>
  ${EIGEN3_INCLUDE_DIRS})
target_link_libraries(slam_karto_core PUBLIC
  karto_vendored g2o::core g2o::stuff g2o::types_slam2d ${_g2o_solver_targets})
if(CSPARSE_INCLUDE_DIR)
  target_include_directories(slam_karto_core PRIVATE ${CSPARSE_INCLUDE_DIR})
endif()
if(_g2o_solver_def)
  target_compile_definitions(slam_karto_core PRIVATE ${_g2o_solver_def})
endif()

# ── .smap 세이버 (형제 mcl2d_map, 의존성 0) ──────────────────────────────────
add_library(smap_io SHARED ${MAP}/src/smap.cpp)
target_include_directories(smap_io PUBLIC $<BUILD_INTERFACE:${MAP}/include>)

# ── g2o RPATH 함정 ───────────────────────────────────────────────────────────
# g2o 는 /opt/ros/<distro>/lib/ 에 있고 그 경로는 ldconfig 캐시에 없다. 게다가
# libg2o_types_slam2d.so 는 libg2o_opengl_helper.so 를 NEEDED 로 갖는데 자기 RUNPATH 가 없다
# (readelf -d 로 확인). DT_RUNPATH 는 그 객체의 직접 NEEDED 에만 적용되고 전이되지 않으므로
# 기본 링크(--enable-new-dtags)로는 전이 해석에 실패해 실행이 죽는다.
# 코어(slam_karto_core/CMakeLists.txt:106-113)와 동일하게 --disable-new-dtags 로 DT_RPATH 를 낸다.
get_target_property(_g2o_core_loc g2o::core IMPORTED_LOCATION_NONE)
if(NOT _g2o_core_loc)
  get_target_property(_g2o_core_loc g2o::core IMPORTED_LOCATION_RELEASE)
endif()
if(NOT _g2o_core_loc)
  get_target_property(_g2o_core_loc g2o::core LOCATION)
endif()
if(_g2o_core_loc)
  get_filename_component(_g2o_libdir "${_g2o_core_loc}" DIRECTORY)
  set(_rpath_flag "-Wl,--disable-new-dtags")
  message(STATUS "slam_karto_ros2: g2o RPATH = ${_g2o_libdir}")
else()
  set(_g2o_libdir "")
  set(_rpath_flag "")
  message(WARNING "slam_karto_ros2: g2o 라이브러리 경로를 특정하지 못했다 — "
                  "실행 시 LD_LIBRARY_PATH 가 필요할 수 있다")
endif()

# 설치 배치: 라이브러리는 lib/, 실행파일은 lib/${PROJECT_NAME}/ 이므로
# 실행파일에서 우리 .so 로 가는 상대경로는 $ORIGIN/.. 다(워크스페이스 setup 의
# LD_LIBRARY_PATH 에 의존하지 않고도 뜨도록 함께 박아 둔다).
function(slam_karto_ros2_set_rpath target extra)
  if(_g2o_libdir)
    set_target_properties(${target} PROPERTIES
      BUILD_RPATH "${_g2o_libdir}"
      INSTALL_RPATH "${_g2o_libdir};${extra}"
      LINK_FLAGS "${_rpath_flag}")
  endif()
endfunction()

slam_karto_ros2_set_rpath(karto_vendored  "\$ORIGIN")
slam_karto_ros2_set_rpath(slam_karto_core "\$ORIGIN")

# ── 노드 ─────────────────────────────────────────────────────────────────────
set(DEPS rclcpp sensor_msgs nav_msgs geometry_msgs std_srvs tf2 tf2_ros tf2_geometry_msgs)

add_executable(slam_mapping_node src/slam_mapping_node.cpp)
target_link_libraries(slam_mapping_node slam_karto_core smap_io)
ament_target_dependencies(slam_mapping_node ${DEPS})
slam_karto_ros2_set_rpath(slam_mapping_node "\$ORIGIN;\$ORIGIN/..")

install(TARGETS karto_vendored slam_karto_core smap_io
        DESTINATION lib)
install(TARGETS slam_mapping_node
        DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})

ament_package()
