cmake_minimum_required(VERSION 3.10)
project(slam_karto_core CXX)

# Seer SLAM 매핑 = Open Karto(front-end) + g2o(backend) 채용.
# 위치추정 코어(mcl2d_core, 의존성 0)와 달리 SLAM 은 upstream 을 채용하므로 외부 의존이 있다.
#
# Karto 는 third_party/open_karto 에 상류 소스 그대로 동봉돼 있다(LGPL-3.0).
#   - apt 에 ros-humble-open-karto 가 없다: `apt-cache policy ros-humble-open-karto` 출력 0줄,
#     `apt-cache search --names-only karto` 출력 0줄 (2026-08-08 이 장비 실측).
#   - LGPL-3.0 은 대응 소스 제공을 요구하므로 동봉이 배포 조건에도 맞는다.
#   - **공유 라이브러리로 분리 빌드**한다 — 정적 링크는 LGPL 조건을 복잡하게 만든다.
set(CMAKE_CXX_STANDARD 17)          # 저장소 표준(mcl2d_core/mcl2d_ros2 와 동일)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)     # ament 기본(-O0)이면 스캔매칭이 수배 느려진다
endif()
add_compile_options(-Wall -Wextra)

option(SLAM_KARTO_ALLOW_MISSING_DEPS
       "의존성이 없어도 조용히 건너뛴다 (기본 OFF — 조용한 미빌드는 '테스트 0개 통과'를 만든다)" OFF)

# ── 의존성 ───────────────────────────────────────────────────────────────────
find_package(Eigen3 QUIET)
find_package(Boost QUIET COMPONENTS thread system)      # Karto 전이 의존
find_package(g2o QUIET)                                  # ros-humble-libg2o 가 config 를 깐다

set(_missing "")
if(NOT EIGEN3_FOUND)
  list(APPEND _missing Eigen3)
endif()
if(NOT Boost_FOUND)
  list(APPEND _missing "Boost(thread,system)")
endif()
if(NOT g2o_FOUND)
  list(APPEND _missing g2o)
endif()

if(_missing)
  if(SLAM_KARTO_ALLOW_MISSING_DEPS)
    message(WARNING "slam_karto_core: 의존성 미탐지 ${_missing} → 모듈 빌드 생략(옵트인).")
    return()
  endif()
  message(FATAL_ERROR
    "slam_karto_core: 의존성 미탐지 ${_missing}.\n"
    "  설치: sudo apt install ros-<distro>-libg2o libeigen3-dev libboost-thread-dev libsuitesparse-dev\n"
    "  의도적으로 건너뛰려면 -DSLAM_KARTO_ALLOW_MISSING_DEPS=ON")
endif()

# ── 동봉 Open Karto ──────────────────────────────────────────────────────────
set(KARTO_DIR ${CMAKE_CURRENT_SOURCE_DIR}/third_party/open_karto)
add_library(karto_vendored SHARED
  ${KARTO_DIR}/src/Karto.cpp
  ${KARTO_DIR}/src/Mapper.cpp)
target_include_directories(karto_vendored PUBLIC ${KARTO_DIR}/include)
target_link_libraries(karto_vendored PUBLIC Boost::thread Boost::system)
# 상류 코드는 우리 경고 설정 대상이 아니다 — 고치지 않기로 했으므로 경고를 끈다(VENDORED.md).
target_compile_options(karto_vendored PRIVATE -w)

# ── 선형해법기: CSparse(원본 충실) 우선, 없으면 Eigen 폴백 ────────────────────
# g2o 의 csparse_extension 임포트 타깃은 SuiteSparse include 를 실어주지 않는다
# → cs.h 를 직접 찾아 넣지 않으면 `fatal error: cs.h: No such file or directory` 가 난다.
find_path(CSPARSE_INCLUDE_DIR cs.h PATHS /usr/include /usr/include/suitesparse)
set(_g2o_solver_targets "")
if(CSPARSE_INCLUDE_DIR AND TARGET g2o::solver_csparse)
  set(_g2o_solver_targets g2o::solver_csparse g2o::csparse_extension)
  set(_g2o_solver_def SLAM_G2O_USE_CSPARSE)
  message(STATUS "slam_karto_core: g2o CSparse 선형해법기 (원본 충실)")
elseif(TARGET g2o::solver_eigen)
  set(_g2o_solver_targets g2o::solver_eigen)
  set(_g2o_solver_def "")
  message(STATUS "slam_karto_core: g2o Eigen 선형해법기 (CSparse 부재 폴백 — 원본과 다름)")
else()
  message(FATAL_ERROR "slam_karto_core: g2o 선형해법기(csparse/eigen)를 하나도 찾지 못했다")
endif()

# ── 코어 ─────────────────────────────────────────────────────────────────────
add_library(slam_karto_core SHARED
  src/g2o_solver.cpp
  src/seer_mapper_config.cpp
  src/seer_slam_mapper.cpp)
target_include_directories(slam_karto_core PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${EIGEN3_INCLUDE_DIRS})
target_link_libraries(slam_karto_core PUBLIC
  karto_vendored g2o::core g2o::stuff g2o::types_slam2d ${_g2o_solver_targets})
if(CSPARSE_INCLUDE_DIR)
  target_include_directories(slam_karto_core PRIVATE ${CSPARSE_INCLUDE_DIR})
endif()
if(_g2o_solver_def)
  target_compile_definitions(slam_karto_core PRIVATE ${_g2o_solver_def})
endif()

# g2o 는 /opt/ros/<distro>/lib/<arch>/ 에 있고 그 경로는 ldconfig 캐시에 없다.
# 임포트 타깃이 직접 링크하는 것만으로는 전이 의존(libg2o_opengl_helper.so 등)이 런타임에 해석되지
# 않아 `error while loading shared libraries` 로 죽는다 — RPATH 에 g2o 라이브러리 경로를 박는다.
get_target_property(_g2o_core_loc g2o::core IMPORTED_LOCATION_NONE)
if(NOT _g2o_core_loc)
  get_target_property(_g2o_core_loc g2o::core IMPORTED_LOCATION_RELEASE)
endif()
if(NOT _g2o_core_loc)
  get_target_property(_g2o_core_loc g2o::core LOCATION)
endif()
if(_g2o_core_loc)
  get_filename_component(_g2o_libdir "${_g2o_core_loc}" DIRECTORY)
  # --disable-new-dtags 로 DT_RUNPATH 대신 **DT_RPATH** 를 낸다.
  #   DT_RUNPATH 는 그 객체의 직접 NEEDED 에만 적용되고 전이되지 않는다. 그런데
  #   libg2o_types_slam2d.so 는 libg2o_opengl_helper.so 를 NEEDED 로 갖고 자기 RUNPATH 가 없어
  #   (readelf -d 로 확인) 전이 해석에 실패한다. DT_RPATH 는 전이되므로 이걸 써야 한다.
  set(_rpath_flag "-Wl,--disable-new-dtags")
  set_target_properties(slam_karto_core PROPERTIES
    BUILD_RPATH "${_g2o_libdir}" INSTALL_RPATH "${_g2o_libdir}"
    LINK_FLAGS "${_rpath_flag}")
  message(STATUS "slam_karto_core: g2o RPATH = ${_g2o_libdir}")
else()
  message(WARNING "slam_karto_core: g2o 라이브러리 경로를 특정하지 못했다 — "
                  "실행 시 LD_LIBRARY_PATH 가 필요할 수 있다")
endif()

# ── 시험 ─────────────────────────────────────────────────────────────────────
# 검증 매크로는 NDEBUG 무관 CHECK 다(test/check.hpp) — assert 는 Release 에서 사라진다.
enable_testing()
add_executable(test_slam_mapping test/test_slam_mapping.cpp)
target_link_libraries(test_slam_mapping PRIVATE slam_karto_core)
if(_g2o_libdir)
  set_target_properties(test_slam_mapping PROPERTIES
    BUILD_RPATH "${_g2o_libdir}" LINK_FLAGS "${_rpath_flag}")
endif()
add_test(NAME test_slam_mapping COMMAND test_slam_mapping)
