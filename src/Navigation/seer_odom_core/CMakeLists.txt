cmake_minimum_required(VERSION 3.10)
project(seer_odom_core)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
# 원본 대조가 목적이라 최적화 수준이 결과를 바꾸지 않아야 한다. Release 로 고정하고
#   대조 시에는 양쪽 빌드 옵션을 함께 기록한다.
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra)
# 부동소수 축약(FMA) 금지. 켜 두면 `a - b*c` 가 fma 로 합쳐져 반올림이 달라진다 —
#   실측으로 normalize(1e6) 이 3.3e-11 만큼 갈렸다. 비트 대조가 목적인 코드라 끈다.
add_compile_options(-ffp-contract=off)

find_package(ament_cmake REQUIRED)
find_package(Eigen3 REQUIRED)

add_library(seer_odom_core src/multisteer_odometer.cpp)
target_include_directories(seer_odom_core PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_link_libraries(seer_odom_core Eigen3::Eigen)

install(TARGETS seer_odom_core DESTINATION lib)
install(DIRECTORY include/ DESTINATION include)

if(BUILD_TESTING)
  add_executable(test_odometer test/test_odometer.cpp)
  target_link_libraries(test_odometer seer_odom_core)
  add_test(NAME test_odometer COMMAND test_odometer)
endif()

ament_package()
