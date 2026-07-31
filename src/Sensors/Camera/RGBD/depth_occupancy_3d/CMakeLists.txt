cmake_minimum_required(VERSION 3.10)
project(depth_occupancy_3d)

# 언어 원칙: ROS2 노드는 C++ (UI 는 예외). 표준은 C++17.
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()

# 빌드 타입 기본값 — colcon 은 지정하지 않으면 CMAKE_BUILD_TYPE 을 비워 두고, 그러면
# 최적화 플래그가 하나도 붙지 않는다(-O 없음). 이 노드는 주기마다 6대 x 19,200 픽셀을
# 역투영하는 핫패스라 그 차이가 그대로 처리율로 나타난다.
# 2026-07-31 실측: 무최적화 빌드에서 융합이 10 Hz 설정 대비 5.6 Hz 에 그쳤고 노드가
# CPU 104% 를 썼다(픽셀당 약 4,800 사이클 — 산술과 두 자릿수 차이).
# 다른 타입이 필요하면 colcon 인자로 덮어쓴다: --cmake-args -DCMAKE_BUILD_TYPE=Debug
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "빌드 타입 (기본 Release)" FORCE)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(orbbec_camera_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_eigen REQUIRED)
find_package(Eigen3 REQUIRED)

set(DEPENDENCIES
  rclcpp
  rclcpp_components
  sensor_msgs
  orbbec_camera_msgs
  geometry_msgs
  tf2
  tf2_ros
  tf2_eigen
)

# 순수 기하 연산은 헤더 온리 인터페이스 라이브러리로 분리한다.
# ROS 의존이 없어 단위 시험이 미들웨어 없이 돈다(test/test_geometry.cpp).
add_library(${PROJECT_NAME}_geometry INTERFACE)
target_include_directories(${PROJECT_NAME}_geometry INTERFACE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

# 노드 본체. 컴포넌트로도, 단독 실행파일로도 쓸 수 있게 공유 라이브러리로 만든다.
add_library(${PROJECT_NAME}_component SHARED
  src/depth_occupancy_node.cpp
)
target_include_directories(${PROJECT_NAME}_component PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
target_link_libraries(${PROJECT_NAME}_component
  ${PROJECT_NAME}_geometry
  Eigen3::Eigen
)
ament_target_dependencies(${PROJECT_NAME}_component ${DEPENDENCIES})
rclcpp_components_register_nodes(${PROJECT_NAME}_component
  "depth_occupancy_3d::DepthOccupancyNode")

add_executable(${PROJECT_NAME}_node src/main.cpp)
target_link_libraries(${PROJECT_NAME}_node ${PROJECT_NAME}_component)
ament_target_dependencies(${PROJECT_NAME}_node ${DEPENDENCIES})

install(DIRECTORY include/
  DESTINATION include
)
install(TARGETS ${PROJECT_NAME}_component
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)
install(TARGETS ${PROJECT_NAME}_node
  DESTINATION lib/${PROJECT_NAME}
)
install(DIRECTORY launch config rviz
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)

  ament_add_gtest(test_geometry test/test_geometry.cpp)
  target_link_libraries(test_geometry ${PROJECT_NAME}_geometry)
endif()

ament_package()
