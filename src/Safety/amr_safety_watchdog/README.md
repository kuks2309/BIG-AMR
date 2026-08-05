# safety_watchdog

**Role**: Central safety arbitration node. Sole publisher of `/safe_to_move`.

⚠ **Not related to motion_supervisor** (which is a separate package in `src/Control-Abstract/motion_supervisor/`).

## What it does

1. Subscribes to multiple safety sources (defined in `config/safety_watchdog.yaml`).
2. Aggregates them via AND logic (all enabled sources must be safe).
3. Publishes `/safe_to_move` (std_msgs/Bool) at 10Hz as a dead man's switch.

## Supported source types

- `bool` — std_msgs/Bool (e.g., E-stop, bumper)
- `safety_status` — trnav_msgs/SafetyStatus (e.g., LiDAR safety)

## Failsafe

- **Boot**: `/safe_to_move=false` until all sources reported safe.
- **Source timeout** (no message in `timeout_ms`): treated as unsafe.
- **Node crash**: topic silence → consumer should timeout and stop.

## Consumer contract

Subscribers to `/safe_to_move` should follow this pattern:

```cpp
safe_sub_ = create_subscription<std_msgs::msg::Bool>(
  "/safe_to_move",
  rclcpp::QoS(1).reliable().transient_local(),
  callback);

// On receive: save data + timestamp
// On control loop: if (!data || now - timestamp > 300ms) stop()
```

Key requirements:
- **QoS**: `RELIABLE + TRANSIENT_LOCAL` (matches publisher)
- **Timeout**: Monitor message arrival; if stale or missing, stop motion
- **Atomicity**: Check data value AND freshness before each control step

## Usage

```bash
ros2 launch safety_watchdog safety_watchdog.launch.py
```

## Configuration

Edit `config/safety_watchdog.yaml` to add/remove safety sources:

```yaml
safety_watchdog:
  ros__parameters:
    output_topic: "/safe_to_move"
    publish_rate_hz: 10.0
    failsafe_on_boot: true
    
    source_names:
      - "estop"
      - "lidar_safety"
      - "bumper"
    
    estop:
      topic: "/estop_signal"
      type: "bool"
      enabled: true
      invert: false
      timeout_ms: 500
    
    lidar_safety:
      topic: "/lidar_safety_status"
      type: "safety_status"
      enabled: true
      invert: false
      timeout_ms: 300
    
    bumper:
      topic: "/bumper_contact"
      type: "bool"
      enabled: true
      invert: true          # true=touched, invert to safe=false
      timeout_ms: 500
```

## Architecture doc

See `src/Control-Abstract/docs/safety_watchdog_architecture.md` for detailed architecture and interaction with motion_supervisor.
