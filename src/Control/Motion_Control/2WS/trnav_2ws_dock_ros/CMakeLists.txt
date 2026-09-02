cmake_minimum_required(VERSION 3.10)
project(trnav_2ws_dock_ros)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(trnav_msgs REQUIRED)
find_package(trnav_2ws_interfaces REQUIRED)

# 이식 코어(형제 디렉터리, colcon 무시) 소스 직접 컴파일 — mcl2d/feature_localizer 관례
set(DOCK ${CMAKE_CURRENT_SOURCE_DIR}/../trnav_2ws_dock_control)
add_library(dock_core_lib STATIC
  ${DOCK}/src/dock_core.cpp
  ${DOCK}/src/dock_obs.cpp)
target_include_directories(dock_core_lib PUBLIC ${DOCK}/include)

add_executable(dock_approach_action_server src/dock_approach_action_server.cpp)
target_link_libraries(dock_approach_action_server dock_core_lib)
ament_target_dependencies(dock_approach_action_server
  rclcpp rclcpp_action geometry_msgs trnav_msgs trnav_2ws_interfaces)

install(TARGETS dock_approach_action_server DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})

ament_package()
