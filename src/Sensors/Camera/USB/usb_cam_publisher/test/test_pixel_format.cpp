// Copyright 2026 Ford_CATL_AMR
// Licensed under the Apache License, Version 2.0.
//
// Unit tests for the pure helpers in pixel_format.hpp (coding SOP §4/§5:
// every changed public function gets >= 1 test).

#include <gtest/gtest.h>

#include <opencv2/videoio.hpp>

#include "usb_cam_publisher/pixel_format.hpp"

using usb_cam_publisher::computeFps;
using usb_cam_publisher::fourccFromString;

TEST(PixelFormat, MjpgMatchesOpenCvFourcc)
{
  EXPECT_EQ(fourccFromString("MJPG"), cv::VideoWriter::fourcc('M', 'J', 'P', 'G'));
}

TEST(PixelFormat, LowercaseIsUppercased)
{
  EXPECT_EQ(fourccFromString("mjpg"), fourccFromString("MJPG"));
}

TEST(PixelFormat, ShortNameIsSpacePadded)
{
  EXPECT_EQ(fourccFromString("Y8"), cv::VideoWriter::fourcc('Y', '8', ' ', ' '));
}

TEST(PixelFormat, YuyvMatchesOpenCvFourcc)
{
  EXPECT_EQ(fourccFromString("YUYV"), cv::VideoWriter::fourcc('Y', 'U', 'Y', 'V'));
}

TEST(ComputeFps, NormalInterval)
{
  EXPECT_DOUBLE_EQ(computeFps(150, 5.0), 30.0);
}

TEST(ComputeFps, ZeroElapsedReturnsZero)
{
  EXPECT_DOUBLE_EQ(computeFps(100, 0.0), 0.0);
}

TEST(ComputeFps, NegativeElapsedReturnsZero)
{
  EXPECT_DOUBLE_EQ(computeFps(100, -1.0), 0.0);
}

TEST(ComputeFps, ZeroFramesReturnsZero)
{
  EXPECT_DOUBLE_EQ(computeFps(0, 5.0), 0.0);
}
