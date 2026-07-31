// Copyright 2026 Ford_CATL_AMR
// Licensed under the Apache License, Version 2.0.
//
// 단독 실행용 진입점. 컴포넌트 컨테이너에 넣어 쓸 수도 있다
// (RCLCPP_COMPONENTS_REGISTER_NODE 는 depth_occupancy_node.cpp 에 있다).

#include <memory>

#include <rclcpp/rclcpp.hpp>

#include "depth_occupancy_3d/depth_occupancy_node.hpp"

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(
    std::make_shared<depth_occupancy_3d::DepthOccupancyNode>(rclcpp::NodeOptions()));
  rclcpp::shutdown();
  return 0;
}
