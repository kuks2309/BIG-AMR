// Copyright 2026 Ford_CATL_AMR
// Licensed under the Apache License, Version 2.0.
//
// Pure, side-effect-free helpers for the USB camera publisher so they can be
// unit tested without opening a real device (coding SOP §4 TDD-lite).
#ifndef USB_CAM_PUBLISHER__PIXEL_FORMAT_HPP_
#define USB_CAM_PUBLISHER__PIXEL_FORMAT_HPP_

#include <cctype>
#include <string>

#include <opencv2/videoio.hpp>

namespace usb_cam_publisher
{

/// Convert a 4-character FOURCC pixel-format name (e.g. "MJPG", "YUYV") into the
/// integer FOURCC code OpenCV expects for cv::CAP_PROP_FOURCC.
///
/// @param name  Case-insensitive format name; padded with spaces if shorter
///              than 4 characters, truncated if longer.
/// @return      OpenCV FOURCC integer code.
inline int fourccFromString(const std::string & name)
{
  char c[4] = {' ', ' ', ' ', ' '};
  for (std::size_t i = 0; i < 4 && i < name.size(); ++i) {
    c[i] = static_cast<char>(std::toupper(static_cast<unsigned char>(name[i])));
  }
  return cv::VideoWriter::fourcc(c[0], c[1], c[2], c[3]);
}

/// Compute frames-per-second from a frame count over an elapsed interval.
///
/// @param frame_count    Frames observed in the interval (>= 0).
/// @param elapsed_sec    Elapsed wall-clock seconds; <= 0 yields 0.0.
/// @return               Measured FPS, or 0.0 when elapsed_sec is non-positive.
inline double computeFps(unsigned long long frame_count, double elapsed_sec)
{
  if (elapsed_sec <= 0.0) {
    return 0.0;
  }
  return static_cast<double>(frame_count) / elapsed_sec;
}

}  // namespace usb_cam_publisher

#endif  // USB_CAM_PUBLISHER__PIXEL_FORMAT_HPP_
