// Copyright 2026 Ford_CATL_AMR
// Licensed under the Apache License, Version 2.0.
//
// geometry.hpp 단위 시험 — 하드웨어·ROS 미들웨어 없이 돈다.

#include <gtest/gtest.h>

#include <cmath>

#include "depth_occupancy_3d/geometry.hpp"

using depth_occupancy_3d::FootprintHalfExtent;
using depth_occupancy_3d::GridSpec;
using depth_occupancy_3d::PinholeIntrinsics;
using depth_occupancy_3d::Point3;
using depth_occupancy_3d::ScanSpec;

namespace
{
PinholeIntrinsics makeIntrinsics()
{
  // 640x480 기준의 전형적인 값. 실제 값은 장치 펌웨어가 camera_info 로 준다.
  return PinholeIntrinsics{500.0, 500.0, 320.0, 240.0};
}
}  // namespace

TEST(BackProject, PrincipalPointMapsToOpticalAxis)
{
  const auto k = makeIntrinsics();
  const auto point = depth_occupancy_3d::backProject(k.cx, k.cy, 1.5, k);
  EXPECT_DOUBLE_EQ(point.x, 0.0);
  EXPECT_DOUBLE_EQ(point.y, 0.0);
  EXPECT_DOUBLE_EQ(point.z, 1.5);
}

TEST(BackProject, RightAndDownArePositive)
{
  // 광학 좌표계는 +x 우 / +y 하. 주점보다 오른쪽·아래 픽셀은 양수여야 한다.
  const auto k = makeIntrinsics();
  const auto point = depth_occupancy_3d::backProject(k.cx + 100.0, k.cy + 50.0, 2.0, k);
  EXPECT_GT(point.x, 0.0);
  EXPECT_GT(point.y, 0.0);
  EXPECT_DOUBLE_EQ(point.x, 100.0 * 2.0 / 500.0);
  EXPECT_DOUBLE_EQ(point.y, 50.0 * 2.0 / 500.0);
}

TEST(BackProject, ScalesLinearlyWithDepth)
{
  const auto k = makeIntrinsics();
  const auto near_point = depth_occupancy_3d::backProject(0.0, 0.0, 1.0, k);
  const auto far_point = depth_occupancy_3d::backProject(0.0, 0.0, 2.0, k);
  EXPECT_DOUBLE_EQ(far_point.x, near_point.x * 2.0);
  EXPECT_DOUBLE_EQ(far_point.y, near_point.y * 2.0);
}

TEST(BackProject, UnusableIntrinsicsYieldOriginInsteadOfDivideByZero)
{
  PinholeIntrinsics broken{};  // fx = fy = 0
  EXPECT_FALSE(broken.isUsable());
  const auto point = depth_occupancy_3d::backProject(10.0, 10.0, 1.0, broken);
  EXPECT_DOUBLE_EQ(point.x, 0.0);
  EXPECT_DOUBLE_EQ(point.y, 0.0);
  EXPECT_DOUBLE_EQ(point.z, 0.0);
}

TEST(Footprint, InsideAndOutside)
{
  // Big-AMR 실측 풋프린트 2027.62 x 1441.48 mm 의 반치수.
  const FootprintHalfExtent footprint{1.01381, 0.72074};

  EXPECT_TRUE(depth_occupancy_3d::isInsideFootprint(0.0, 0.0, footprint));
  EXPECT_TRUE(depth_occupancy_3d::isInsideFootprint(1.0, 0.7, footprint));
  EXPECT_TRUE(depth_occupancy_3d::isInsideFootprint(-1.0, -0.7, footprint));

  EXPECT_FALSE(depth_occupancy_3d::isInsideFootprint(1.1, 0.0, footprint));
  EXPECT_FALSE(depth_occupancy_3d::isInsideFootprint(0.0, 0.8, footprint));
}

TEST(Footprint, IgnoresHeight)
{
  // 무한 기둥 마스크 — z 인자를 아예 받지 않는다는 사실을 시험으로 고정한다.
  const FootprintHalfExtent footprint{1.0, 0.7};
  EXPECT_TRUE(depth_occupancy_3d::isInsideFootprint(0.5, 0.5, footprint));
}

TEST(Grid, CellCountMatchesExtent)
{
  GridSpec grid;
  grid.min_x = -3.0;
  grid.max_x = 3.0;
  grid.min_y = -3.0;
  grid.max_y = 3.0;
  grid.min_z = 0.0;
  grid.max_z = 2.0;
  grid.resolution = 0.05;

  EXPECT_TRUE(grid.isUsable());
  EXPECT_EQ(grid.sizeX(), 120u);
  EXPECT_EQ(grid.sizeY(), 120u);
  EXPECT_EQ(grid.sizeZ(), 40u);
  EXPECT_EQ(grid.cellCount(), 120u * 120u * 40u);
}

TEST(Grid, RejectsUnusableSpec)
{
  GridSpec zero_resolution;
  zero_resolution.resolution = 0.0;
  EXPECT_FALSE(zero_resolution.isUsable());
  EXPECT_EQ(zero_resolution.cellCount(), 0u);

  GridSpec inverted;
  inverted.max_x = inverted.min_x - 1.0;
  EXPECT_FALSE(inverted.isUsable());
}

TEST(Grid, IndexRoundTripsThroughVoxelCenter)
{
  GridSpec grid;
  grid.resolution = 0.1;

  const Point3 sample{0.35, -1.25, 0.65};
  std::size_t index = 0;
  ASSERT_TRUE(depth_occupancy_3d::voxelIndex(grid, sample, index));

  const auto center = depth_occupancy_3d::voxelCenter(grid, index);
  // 보셀 중심은 원래 점에서 한 셀 반경 안에 있어야 한다.
  EXPECT_LT(std::abs(center.x - sample.x), grid.resolution);
  EXPECT_LT(std::abs(center.y - sample.y), grid.resolution);
  EXPECT_LT(std::abs(center.z - sample.z), grid.resolution);

  // 그 중심을 다시 넣으면 같은 보셀로 떨어져야 한다.
  std::size_t reindex = 0;
  ASSERT_TRUE(depth_occupancy_3d::voxelIndex(grid, center, reindex));
  EXPECT_EQ(reindex, index);
}

TEST(Grid, RejectsPointsOutsideExtent)
{
  GridSpec grid;
  std::size_t index = 0;
  EXPECT_FALSE(depth_occupancy_3d::voxelIndex(grid, Point3{99.0, 0.0, 0.5}, index));
  EXPECT_FALSE(depth_occupancy_3d::voxelIndex(grid, Point3{0.0, 0.0, -0.1}, index));
  // 상한은 배타적이어야 인덱스가 넘치지 않는다.
  EXPECT_FALSE(depth_occupancy_3d::voxelIndex(grid, Point3{grid.max_x, 0.0, 0.5}, index));
}

TEST(AzimuthBin, ForwardMapsToMiddleBin)
{
  // angle_min = -pi, 360 빈 → 전방(0 rad)은 180 번 빈.
  const ScanSpec scan;
  std::size_t bin = 0;
  ASSERT_TRUE(depth_occupancy_3d::azimuthBin(scan, 1.0, 0.0, bin));
  EXPECT_EQ(bin, 180u);
}

TEST(AzimuthBin, LeftAndRightAreSymmetric)
{
  const ScanSpec scan;
  std::size_t left = 0;
  std::size_t right = 0;
  ASSERT_TRUE(depth_occupancy_3d::azimuthBin(scan, 0.0, 1.0, left));    // +90도
  ASSERT_TRUE(depth_occupancy_3d::azimuthBin(scan, 0.0, -1.0, right));  // -90도
  EXPECT_EQ(left, 270u);
  EXPECT_EQ(right, 90u);
}

TEST(AzimuthBin, AllBinsAreReachableAndInRange)
{
  const ScanSpec scan;
  for (std::size_t i = 0; i < scan.bin_count; ++i) {
    const double angle = scan.angle_min + (static_cast<double>(i) + 0.5) * scan.angleIncrement();
    std::size_t bin = 0;
    ASSERT_TRUE(depth_occupancy_3d::azimuthBin(scan, std::cos(angle), std::sin(angle), bin))
      << "bin " << i << " angle " << angle;
    EXPECT_EQ(bin, i);
  }
}

TEST(AzimuthBin, OriginHasNoDefinedAzimuth)
{
  const ScanSpec scan;
  std::size_t bin = 0;
  EXPECT_FALSE(depth_occupancy_3d::azimuthBin(scan, 0.0, 0.0, bin));
}

TEST(AzimuthBin, RejectsEmptyScan)
{
  ScanSpec scan;
  scan.bin_count = 0;
  std::size_t bin = 0;
  EXPECT_FALSE(depth_occupancy_3d::azimuthBin(scan, 1.0, 0.0, bin));
}

TEST(HorizontalRange, IgnoresHeight)
{
  EXPECT_DOUBLE_EQ(depth_occupancy_3d::horizontalRange(3.0, 4.0), 5.0);
  EXPECT_DOUBLE_EQ(depth_occupancy_3d::horizontalRange(0.0, 0.0), 0.0);
}
