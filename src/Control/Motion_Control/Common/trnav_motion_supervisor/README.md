# trnav_motion_supervisor

**Role**: Motion source activator for `motion_mux`.

⚠ **NOT a safety watchdog.** See [safety_watchdog](../../Safety/safety_watchdog/) for `/safe_to_move` publisher.

## What it does

Calls `/select_motion_source` (trnav_msgs/srv/SelectMotionSource) service at boot
to activate the configured default motion source in `motion_mux`.

## Parameters

- `target_source_id` (int, default 1) — source id to activate
- `target_service` (string, default "/select_motion_source")
- `call_retry_count` (int, default 3)
- `call_retry_interval_ms` (int, default 1000) — also used as timer period

## Not in scope

- `/safe_to_move` publishing (→ see `src/Safety/safety_watchdog/`)
- Safety state management
- E-stop handling

## Usage

```bash
ros2 launch trnav_motion_supervisor motion_supervisor.launch.py
```
