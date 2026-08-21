cmake_minimum_required(VERSION 3.10)
project(wall_localizer_core CXX)

# 프레임워크-독립 순수 C++17 코어 (외부 의존성 0). ROS2 어댑터가 소스를 직접 컴파일한다.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra)

add_library(wall_localizer_core
  src/line_extractor.cpp
  src/wall_matcher.cpp
  src/pose_solver.cpp
  src/wall_localizer.cpp)
target_include_directories(wall_localizer_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

# 테스트 — 자체 CHECK 매크로(sim_scan.hpp)라 NDEBUG 와 무관하게 실패할 수 있다.
enable_testing()
foreach(t test_line_extractor test_pose_solver test_wall_localizer)
  add_executable(${t} test/${t}.cpp)
  target_link_libraries(${t} PRIVATE wall_localizer_core)
  add_test(NAME ${t} COMMAND ${t})
endforeach()
