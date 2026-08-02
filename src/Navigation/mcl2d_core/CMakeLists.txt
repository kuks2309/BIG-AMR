cmake_minimum_required(VERSION 3.10)
project(mcl2d_core CXX)

# 프레임워크-독립 순수 C++17 코어 (외부 의존성 0). ROS2/non-ROS2 어댑터가 공유.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra)

add_library(mcl2d_core
  src/likelihood_grid.cpp
  src/motion_model.cpp
  src/observation_model.cpp
  src/observation_field.cpp   # Seer 관측 우도 충실 포팅 (RE 비트 일치, ADR 2026-07-12)
  src/particle_filter.cpp)
target_include_directories(mcl2d_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

# 테스트 (의존성 없는 자체 하니스)
# ※ 기본 빌드타입이 Release(-DNDEBUG) 라 assert 가 사라진다 — assert 기반 테스트는
#    -UNDEBUG 를 붙여야 실제로 실패할 수 있다(안 붙이면 무조건 PASS).
enable_testing()
add_executable(test_mcl2d test/test_mcl2d.cpp)
target_link_libraries(test_mcl2d PRIVATE mcl2d_core)
target_compile_options(test_mcl2d PRIVATE -UNDEBUG)
add_test(NAME test_mcl2d COMMAND test_mcl2d)

# 모션모델 단위 검증 (ADR 2026-07-31-mcl2d-motion-model-fidelity).
#   자체 CHECK 매크로를 쓰므로 NDEBUG 와 무관하게 실패할 수 있다.
add_executable(test_motion_model test/test_motion_model.cpp)
target_link_libraries(test_motion_model PRIVATE mcl2d_core)
add_test(NAME test_motion_model COMMAND test_motion_model)

# .smap 로더 테스트 — 로더는 형제 디렉터리(mcl2d_map, CMakeLists 없음)에 있어 여기서 함께 빌드.
#   인자 없이 실행하면 자체 픽스처로 검증(외부 자산 불요) → 항상 ctest 대상.
add_executable(test_smap ../mcl2d_map/test/test_smap.cpp ../mcl2d_map/src/smap.cpp)
target_include_directories(test_smap PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../mcl2d_map/include)
target_link_libraries(test_smap PRIVATE mcl2d_core)
add_test(NAME test_smap COMMAND test_smap)

# 실제 Seer 맵으로 하는 추가 검증(선택): 맵 파일은 저장소에 없으므로 경로를 줄 때만 등록.
#   cmake -B build -S . -DMCL2D_TEST_SMAP=<...>/map/xxx.smap
set(MCL2D_TEST_SMAP "" CACHE FILEPATH "실맵 회귀 테스트에 쓸 .smap 경로 (비우면 미등록)")
if(MCL2D_TEST_SMAP AND EXISTS ${MCL2D_TEST_SMAP})
  add_test(NAME test_smap_realmap COMMAND test_smap ${MCL2D_TEST_SMAP})
endif()

# RE 오라클 검증(선택): ObservationField ↔ 원본 getPostProb 비트 대조 Δ=0.
# 원본 libMCLoc.so + protobuf 3.6.1 헤더 필요 → 검증환경에서만 빌드(자산 부재 시 미빌드).
#   -DMCL2D_OBS_ORACLE=ON -DSEER_RBK=<rbk 경로> -DPROTOBUF_361_SRC=/tmp/protobuf-3.6.1/src
option(MCL2D_OBS_ORACLE "Build ObservationField RE oracle test (needs libMCLoc.so + protobuf3.6.1)" OFF)
if(MCL2D_OBS_ORACLE)
  add_executable(test_obs_field_oracle test/test_obs_field_oracle.cpp src/observation_field.cpp
                 ${CMAKE_CURRENT_SOURCE_DIR}/../mcl2d_map/src/smap.cpp)
  target_include_directories(test_obs_field_oracle PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../mcl2d_map/include
    ${PROTOBUF_361_SRC})
  target_link_libraries(test_obs_field_oracle PRIVATE
    -Wl,--no-as-needed ${SEER_RBK}/3rdlib/libprotobuf.so.17 -lz -ldl -pthread)
  add_test(NAME test_obs_field_oracle COMMAND test_obs_field_oracle ${MCL2D_OBS_ORACLE_SMAP})
endif()
