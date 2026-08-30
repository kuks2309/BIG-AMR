#!/usr/bin/env bash
# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
#
# Normalize Orbbec Gemini E RGB camera controls for full-rate capture.
#
# The cameras ship with V4L2_CID_EXPOSURE_AUTO_PRIORITY ("exposure_dynamic_
# framerate") enabled, which lets them HALVE the frame rate to lengthen exposure
# in dim light (~30 -> ~15 fps). This disables it on every connected RGB camera.
#
# Controls reset when a camera is re-plugged, so re-run after (re)connecting.
# The usb_cam_publisher node does this automatically on startup; this script is
# for the benchmark and for raw v4l2/OpenCV use outside the publisher.
#
# Usage: ./apply_camera_controls.sh
set -euo pipefail

shopt -s nullglob
found=0
for link in /dev/v4l/by-id/*Orbbec_Gemini_E_RGB_Camera_*-video-index0; do
  dev="$(readlink -f "$link")"
  if v4l2-ctl -d "$dev" --set-ctrl exposure_dynamic_framerate=0 2>/dev/null; then
    val="$(v4l2-ctl -d "$dev" --get-ctrl exposure_dynamic_framerate 2>/dev/null)"
    echo "$dev : $val"
    found=$((found + 1))
  fi
done

if [ "$found" -eq 0 ]; then
  echo "No Orbbec Gemini E RGB cameras found under /dev/v4l/by-id/" >&2
  exit 1
fi
echo "Normalized $found camera(s) for constant frame rate."
