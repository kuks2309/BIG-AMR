cmake_minimum_required(VERSION 3.10)
project(seer_tcp_ip CXX)

# rclcpp 무의존 순수 C++17 라이브러리 — 단독 실행파일·시험에서 그대로 쓴다.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra)

find_package(ament_cmake REQUIRED)
find_package(nlohmann_json REQUIRED)

add_library(seer_tcp_ip
  src/ports.cpp
  src/transport.cpp
  src/api.cpp
  src/control.cpp)
target_include_directories(seer_tcp_ip PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_link_libraries(seer_tcp_ip PUBLIC nlohmann_json::nlohmann_json)

# 진단 실행파일 — 라이다 장착 pose 조회(조회 포트만 쓴다).
add_executable(read_lidar_install tools/read_lidar_install.cpp)
target_link_libraries(read_lidar_install PRIVATE seer_tcp_ip)

# 파라미터 조회 — 실기에 직접 물어본다(한도처럼 상수로 두면 안 되는 값).
add_executable(seer_param tools/seer_param.cpp)
target_link_libraries(seer_param PRIVATE seer_tcp_ip)

install(DIRECTORY include/ DESTINATION include)
install(TARGETS seer_tcp_ip
  EXPORT export_seer_tcp_ip
  ARCHIVE DESTINATION lib LIBRARY DESTINATION lib RUNTIME DESTINATION bin)
install(TARGETS read_lidar_install seer_param DESTINATION lib/${PROJECT_NAME})
ament_export_targets(export_seer_tcp_ip HAS_LIBRARY_TARGET)
ament_export_dependencies(nlohmann_json)

# 시험 — 자체 CHECK 하니스(gtest 미도입).
# ⚠ 기본 빌드타입이 Release(-DNDEBUG) 라 assert 기반 시험은 무조건 통과한다.
#    하니스 매크로는 NDEBUG 와 무관하게 실패하며, harness_selftest 가 그것을 증명한다.
if(BUILD_TESTING)
  enable_testing()
  foreach(t harness_selftest test_transport test_api test_control)
    add_executable(${t} test/${t}.cpp)
    target_include_directories(${t} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/test)
    target_link_libraries(${t} PRIVATE seer_tcp_ip)
    add_test(NAME ${t} COMMAND ${t})
  endforeach()
endif()

ament_package()
