cmake_minimum_required(VERSION 3.8)
project(trnav_2ws_msgs)


# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()


# find dependencies
find_package(ament_cmake REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

set(msg_files
  "msg/AmrStatusForSafety.msg"
  "msg/AmrAlarm.msg"
  "msg/Location.msg"
  "msg/MotorDriver.msg"
  "msg/MotorStatus.msg"
  "msg/Odometry.msg"
  "msg/SafetyDebug.msg"
  "msg/SafetyStatus.msg"
  "msg/SafetyStatusLidar.msg"
  "msg/WheelMotor.msg"
  "msg/WheelMotorState.msg"
  "msg/WheelControl.msg"
  "msg/WheelState.msg"
  "msg/WheelSet.msg"
  "msg/WheelSetArray.msg"
  "msg/MotorCmd.msg"
  "msg/MotorCmdArray.msg"
  "msg/MotorState.msg"
  "msg/MotorStateArray.msg"
  "msg/Spin.msg"
  "msg/Io.msg"

  "srv/LidarSafety.srv"
  "srv/SafetyZone.srv"
  "srv/SafetyRelease.srv"
  "srv/Rotation.srv"
  "srv/MotionAction.srv"
  "srv/Antloc.srv"
  "srv/Io.srv"
  "srv/SelectMotionSource.srv"

  "action/RotateAngle.action"
  "action/TranslateDistance.action"
)

rosidl_generate_interfaces(${PROJECT_NAME}
  ${msg_files}
  DEPENDENCIES builtin_interfaces std_msgs geometry_msgs
  ADD_LINTER_TESTS
)

ament_export_dependencies(rosidl_default_runtime)

ament_package()
