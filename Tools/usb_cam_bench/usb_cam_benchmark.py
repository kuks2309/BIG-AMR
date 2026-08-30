#!/usr/bin/env python3
# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""USB camera capture-layer performance benchmark.

Measures the *raw* V4L2 capture performance of the USB cameras, bypassing ROS2
entirely so DDS/serialization overhead does not distort the numbers (see ADR
0001). For each resolution it captures:

  * solo       - one camera alone (per-camera hardware ceiling)
  * concurrent - all cameras at once (exposes shared USB-bus contention)

and records actual FPS, inter-frame interval jitter, and grab failures. Results
are printed as a markdown table and saved to CSV + markdown under
docs/performance/usb_cam/.

Usage:
    python3 usb_cam_benchmark.py                       # defaults, all roster cams
    python3 usb_cam_benchmark.py --resolutions 1280x720 --duration 8
    python3 usb_cam_benchmark.py --modes solo          # skip the concurrent run
"""

import argparse
import csv
import os
import subprocess
import threading
import time
from datetime import datetime

import cv2
import yaml

# Number of initial frames to discard so auto-exposure/stream warm-up does not
# skew the steady-state measurement.
DEFAULT_WARMUP_FRAMES = 15

from bench_stats import fps_deficit_pct, fps_from, interval_stats_ms  # noqa: E402


def _script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def normalize_controls(devices):
    """Disable exposure_dynamic_framerate on each device so the camera holds a
    constant frame rate (otherwise it halves the rate in dim light). Best-effort:
    a missing control or v4l2-ctl is logged and ignored."""
    for device in devices:
        try:
            subprocess.run(
                ["v4l2-ctl", "-d", device,
                 "--set-ctrl", "exposure_dynamic_framerate=0"],
                check=False, capture_output=True, timeout=5,
            )
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            print(f"  (could not normalize {device}: {exc})")


def load_camera_specs(config_path):
    """Return [(name, device_path), ...] from the usb_cam_publisher roster."""
    with open(config_path, "r") as handle:
        config = yaml.safe_load(handle)
    prefix = config["by_id_prefix"]
    specs = []
    for cam in config["cameras"]:
        device = f"/dev/v4l/by-id/usb-{prefix}_{cam['serial']}-video-index0"
        specs.append((cam["name"], device))
    return specs


def capture_once(name, device, width, height, fps, duration, warmup, results, key,
                 buffersize=4):
    """Capture from one device for ``duration`` seconds, storing metrics in
    ``results[key]``. Safe to run in its own thread (writes only its own key).

    ``buffersize`` sets CAP_PROP_BUFFERSIZE. Keep it >= 2: a value of 1 starves
    the V4L2 queue and halves the effective FPS (see docs/performance)."""
    metric = {
        "name": name,
        "device": device,
        "opened": False,
        "actual_w": 0,
        "actual_h": 0,
        "actual_fps_driver": 0.0,
        "frames": 0,
        "elapsed": 0.0,
        "timestamps": [],
        "grab_failures": 0,
    }
    results[key] = metric

    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        return
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, buffersize)

    metric["opened"] = True
    metric["actual_w"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    metric["actual_h"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    metric["actual_fps_driver"] = float(cap.get(cv2.CAP_PROP_FPS))

    # Warm-up (not counted).
    for _ in range(warmup):
        cap.read()

    timestamps = []
    grab_failures = 0
    start = time.monotonic()
    while time.monotonic() - start < duration:
        ok, frame = cap.read()
        if not ok or frame is None:
            grab_failures += 1
            time.sleep(0.002)
            continue
        timestamps.append(time.monotonic())
    elapsed = time.monotonic() - start
    cap.release()

    metric["frames"] = len(timestamps)
    metric["elapsed"] = elapsed
    metric["timestamps"] = timestamps
    metric["grab_failures"] = grab_failures


def _row_from_metric(metric, mode, target_fps):
    """Flatten a raw capture metric into a report row dict."""
    stats = interval_stats_ms(metric["timestamps"])
    actual_fps = fps_from(metric["frames"], metric["elapsed"])
    return {
        "mode": mode,
        "camera": metric["name"],
        "req_fps": target_fps,
        "res": f"{metric['actual_w']}x{metric['actual_h']}",
        "opened": metric["opened"],
        "frames": metric["frames"],
        "elapsed_s": round(metric["elapsed"], 2),
        "actual_fps": round(actual_fps, 2),
        "fps_deficit_pct": round(fps_deficit_pct(actual_fps, target_fps), 1),
        "interval_mean_ms": round(stats["mean_ms"], 2),
        "interval_p95_ms": round(stats["p95_ms"], 2),
        "interval_max_ms": round(stats["max_ms"], 2),
        "jitter_ms": round(stats["jitter_ms"], 2),
        "grab_failures": metric["grab_failures"],
    }


def run_matrix(specs, resolutions, fps, duration, warmup, modes, buffersize):
    """Run the benchmark matrix and return a list of report rows."""
    rows = []
    for (width, height) in resolutions:
        if "solo" in modes:
            for name, device in specs:
                print(f"[solo] {name} {width}x{height}@{fps} for {duration}s ...")
                results = {}
                capture_once(
                    name, device, width, height, fps, duration, warmup, results, name,
                    buffersize,
                )
                rows.append(_row_from_metric(results[name], "solo", fps))

        if "concurrent" in modes and len(specs) > 1:
            print(
                f"[concurrent] {len(specs)} cams {width}x{height}@{fps} "
                f"for {duration}s ..."
            )
            results = {}
            threads = []
            for name, device in specs:
                t = threading.Thread(
                    target=capture_once,
                    args=(name, device, width, height, fps, duration, warmup,
                          results, name, buffersize),
                )
                threads.append(t)
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            for name, _ in specs:
                rows.append(_row_from_metric(results[name], "concurrent", fps))
    return rows


CSV_FIELDS = [
    "mode", "camera", "req_fps", "res", "opened", "frames", "elapsed_s",
    "actual_fps", "fps_deficit_pct", "interval_mean_ms", "interval_p95_ms",
    "interval_max_ms", "jitter_ms", "grab_failures",
]


def write_csv(rows, path):
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def render_markdown(rows, meta):
    """Render rows as a markdown report string."""
    lines = [
        "# USB Camera Capture-Layer Benchmark",
        "",
        f"- Date: {meta['date']}",
        f"- Host: {meta['host']}",
        f"- Duration per run: {meta['duration']} s (warmup {meta['warmup']} frames)",
        f"- CAP_PROP_BUFFERSIZE: {meta['buffersize']} (must be >= 2 for full FPS)",
        f"- Measurement point: raw V4L2 capture (no ROS2), MJPG",
        "",
        "| mode | camera | res | req fps | actual fps | deficit % | "
        "mean ms | p95 ms | max ms | jitter ms | grab fails |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        lines.append(
            f"| {r['mode']} | {r['camera']} | {r['res']} | {r['req_fps']} | "
            f"{r['actual_fps']} | {r['fps_deficit_pct']} | {r['interval_mean_ms']} | "
            f"{r['interval_p95_ms']} | {r['interval_max_ms']} | {r['jitter_ms']} | "
            f"{r['grab_failures']} |"
        )
    lines.append("")
    lines.append(
        "> Compare `solo` vs `concurrent` at the same resolution: the FPS drop "
        "when all cameras run together is the shared USB-bus contention cost."
    )
    lines.append("")
    return "\n".join(lines)


def parse_resolution(text):
    w, h = text.lower().split("x")
    return (int(w), int(h))


def main():
    default_config = os.path.normpath(
        os.path.join(_script_dir(), "..", "usb_cam_publisher", "config", "cameras.yaml")
    )
    default_outdir = os.path.normpath(
        os.path.join(_script_dir(), "..", "docs", "performance", "usb_cam")
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=default_config)
    parser.add_argument(
        "--resolutions", default="640x480,1280x720,1920x1080",
        help="comma-separated WxH list",
    )
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP_FRAMES)
    parser.add_argument(
        "--buffersize", type=int, default=4,
        help="V4L2 CAP_PROP_BUFFERSIZE. Use >=2 for full FPS; 1 halves the rate "
        "(pass --buffersize 1 to reproduce that pathology).",
    )
    parser.add_argument(
        "--modes", default="solo,concurrent",
        help="comma-separated subset of {solo,concurrent}",
    )
    parser.add_argument("--outdir", default=default_outdir)
    parser.add_argument(
        "--raw-controls", action="store_true",
        help="Do NOT normalize camera controls first (measures the camera's "
        "as-is state, including any dynamic-framerate halving).",
    )
    args = parser.parse_args()

    specs = load_camera_specs(args.config)
    if not specs:
        raise SystemExit("no cameras in roster")
    resolutions = [parse_resolution(r) for r in args.resolutions.split(",")]
    modes = [m.strip() for m in args.modes.split(",")]

    print(f"Cameras: {[s[0] for s in specs]}")
    if not args.raw_controls:
        print("Normalizing camera controls (exposure_dynamic_framerate=0) ...")
        normalize_controls([device for _, device in specs])
    rows = run_matrix(
        specs, resolutions, args.fps, args.duration, args.warmup, modes,
        args.buffersize,
    )

    now = datetime.now()
    meta = {
        "date": now.strftime("%Y-%m-%d %H:%M:%S"),
        "host": os.uname().nodename,
        "duration": args.duration,
        "warmup": args.warmup,
        "buffersize": args.buffersize,
    }
    os.makedirs(args.outdir, exist_ok=True)
    stamp = now.strftime("%Y-%m-%d_%H%M%S")
    csv_path = os.path.join(args.outdir, f"{stamp}.csv")
    md_path = os.path.join(args.outdir, f"{stamp}.md")
    write_csv(rows, csv_path)
    markdown = render_markdown(rows, meta)
    with open(md_path, "w") as handle:
        handle.write(markdown)

    print("\n" + markdown)
    print(f"\nSaved:\n  {csv_path}\n  {md_path}")


if __name__ == "__main__":
    main()
