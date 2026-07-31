cmake_minimum_required(VERSION 3.10)
project(icp_odometry_bringup)

# 코드 없는 bringup 패키지 — launch/config 설치만 한다.
find_package(ament_cmake REQUIRED)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
