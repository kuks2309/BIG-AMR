# AMR USB CCTV Monitoring System

CCTV-style surround monitoring for the AMR using Orbbec Gemini E RGB cameras.
USB camera performance testing is the primary goal, so FPS/latency is measured
at the V4L2 capture layer.

> **⚠ Hardware limit: max 4 RGB cameras. 6 is not supported.** All cameras share
> a single USB 2.0 host controller (Bus 001) and RGB video is isochronous
> (reserved bandwidth); 6 cameras only bind 2. A USB 3.0 hub does **not** help —
> the Gemini E is USB 2.0-only. See
> `performance/2026-07-22_usb_topology_limit.md`.

## Architecture (see `adr/0001-usb-cctv-architecture.md`)

```
[usb_cam_publisher]  (C++ / rclcpp, one node per camera)
   V4L2 + OpenCV MJPG capture  ->  sensor_msgs/Image (bgr8)
   capture-layer FPS logging
        |
        |  ROS2 topic  /<camera_name>/image_raw  (+ /compressed via image_transport)
        v
[vision_guard]  (Python / PyQt5 + rclpy)   ==  "AMR VisionGuard"
   subscribe -> selectable grid (1x1 / 1x3 / 2x3 / ...)
```

Two packages:

| Package | Lang | Role |
| --- | --- | --- |
| `usb_cam_publisher` | C++ (ament_cmake) | Capture each camera, publish ROS2 image topics, log capture FPS |
| `vision_guard` | Python (ament_python) | AMR VisionGuard PyQt5 viewer with grid-layout selector |

## Build

```bash
cd /home/tr-orin-22/Project/Ford_CATL_AMR
colcon build --packages-select usb_cam_publisher vision_guard
source install/setup.bash
```

## Run

1. Start the publishers (reads `usb_cam_publisher/config/cameras.yaml`):

   ```bash
   ros2 launch usb_cam_publisher usb_cam_cctv.launch.py
   ```

   Confirm topics and capture FPS:

   ```bash
   ros2 topic list | grep image_raw
   ros2 topic hz /cam0/image_raw
   ```

2. Start the viewer:

   ```bash
   ros2 launch vision_guard vision_guard.launch.py
   # options:  layout:=2x3   image_transport:=compressed
   ```

   Pick the grid layout from the **Layout** dropdown at runtime.

## Adding cameras (up to 6)

1. Plug the camera in, find its serial:

   ```bash
   ls /dev/v4l/by-id/          # usb-...Orbbec_Gemini_E_RGB_Camera_<SERIAL>-video-index0
   ```

2. Add an entry to `usb_cam_publisher/config/cameras.yaml`
   (`name: cam3`, `serial: <SERIAL>`).
3. Add `/cam3/image_raw` to `camera_topics` in
   `vision_guard/launch/vision_guard.launch.py`.

## Performance benchmark

`Tools/usb_cam_bench/usb_cam_benchmark.py` measures the **raw V4L2 capture**
performance (bypassing ROS2) across resolutions and camera counts, and writes a
CSV + markdown report under `performance/usb_cam/`.

```bash
cd Tools/usb_cam_bench
python3 usb_cam_benchmark.py                       # 640x480/720p/1080p, solo + concurrent
python3 usb_cam_benchmark.py --resolutions 1280x720 --duration 8
python3 usb_cam_benchmark.py --buffersize 1        # reproduce the half-FPS pathology
```

- `solo` = one camera alone (per-camera ceiling); `concurrent` = all cameras at
  once (exposes shared-bus contention).
- For raw USB throughput/latency, read the **capture FPS** here or in the
  `usb_cam_publisher` log — not the viewer's display FPS (which adds DDS +
  render overhead).

### Key findings (2026-07-21, 4x Orbbec Gemini E)

- **All cameras sustain ~29.7 fps simultaneously at up to 1920x1080 MJPG**,
  0 grab failures, ~2 ms jitter, once both issues below are fixed. USB 2.0
  bandwidth is **not** a bottleneck for these MJPG streams (MJPG is compressed
  on the wire).
- There are **two independent causes of a half (~15 fps) rate**, each verified
  by toggling it and re-measuring:
  1. **`CAP_PROP_BUFFERSIZE=1`** (software): a single V4L2 buffer cannot be
     refilled while userspace holds it, so the stream degrades to
     every-other-frame. Fix: use `>= 2` (publisher and benchmark do). This was
     the real cause of the earlier ~13 fps reading — **not** USB-bus contention.
  2. **`exposure_dynamic_framerate` / `V4L2_CID_EXPOSURE_AUTO_PRIORITY = 1`**
     (Orbbec default): in dim light the camera halves its rate to lengthen
     exposure. Fix: set it to `0`. The publisher does this automatically at
     startup (`disable_dynamic_framerate` param, default true). For raw
     v4l2/OpenCV or the benchmark, run `Tools/usb_cam_bench/apply_camera_controls.sh`
     (the benchmark also normalizes it unless `--raw-controls` is passed).
     *(An earlier note here claimed this control had no effect — that was
     measured while cause #1 masked it, and is corrected.)*
- With 6 cameras, prefer `image_transport:=compressed` on the viewer to cut DDS
  loopback bandwidth, and watch CPU for 6x MJPG decode on the Orin.
