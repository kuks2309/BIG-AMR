#!/usr/bin/env python3
# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""USB CCTV 내구(soak) 테스트 감시자 — 수동적 관측만 한다.

퍼블리셔·뷰어 로그를 따라 읽고 프로세스 자원(RSS·CPU)을 표본화해 CSV 로 남긴다.
**구독자를 새로 만들지 않는다** — 관측 자체가 DDS 부하를 더해 시험 대상을 바꾸면
안 되기 때문이다(raw bgr8 6대 = 약 166MB/s).

수집 항목(표본마다 1행):
  - 카메라별 캡처 FPS / grab_failures (퍼블리셔 로그)
  - 카메라별 표시 FPS / 구간 렌더 프레임 (뷰어 로그)
  - 뷰어·퍼블리셔 RSS·CPU (/proc)
  - 프로세스 생존 수, /dev/shm FastDDS 세그먼트 수

이상이 나와도 개입하지 않는다(기록만). 사후 분석용 증거 확보가 목적이다.

사용:
  python3 soak_monitor.py --pub-log <pub.log> --viewer-log <viewer.log> \
      --out-dir <dir> --duration-h 24 --interval 30
"""

import argparse
import csv
import datetime
import os
import time

from soak_stats import (
    parse_capture_line,
    parse_display_line,
    rss_growth_mb,
    summarize_capture,
    summarize_display,
)

CLK_TCK = os.sysconf("SC_CLK_TCK")
PAGE_MB = os.sysconf("SC_PAGE_SIZE") / (1024 * 1024)


def find_processes():
    """감시 대상 PID 수집 → {"viewer": [pid], "publishers": {cam: pid}}."""
    viewer = []
    publishers = {}
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/cmdline", "rb") as handle:
                cmdline = handle.read().decode("utf-8", "replace").replace("\0", " ")
        except OSError:
            continue
        if "install/vision_guard/lib/vision_guard/vision_guard" in cmdline:
            viewer.append(int(entry))
        elif "usb_cam_publisher_node" in cmdline and "__node:=" in cmdline:
            for token in cmdline.split():
                if token.startswith("__node:=usb_cam_publisher_"):
                    publishers[token.rsplit("_", 1)[-1]] = int(entry)
    return {"viewer": viewer, "publishers": publishers}


def read_proc_times(pid):
    """(utime+stime jiffies, RSS MB). 프로세스가 없으면 None."""
    try:
        with open(f"/proc/{pid}/stat") as handle:
            fields = handle.read().rsplit(") ", 1)[1].split()
    except (OSError, IndexError):
        return None
    # stat 필드는 ") " 뒤부터 state(0) 기준 — utime=11, stime=12, rss=21
    jiffies = int(fields[11]) + int(fields[12])
    rss_mb = int(fields[21]) * PAGE_MB
    return jiffies, rss_mb


class LogTail:
    """로그 파일을 증분으로 따라 읽는다(회전 없음 가정, 없으면 대기)."""

    def __init__(self, path):
        self.path = path
        self._offset = 0

    def read_new_lines(self):
        if not self.path or not os.path.exists(self.path):
            return []
        with open(self.path, "r", errors="replace") as handle:
            handle.seek(self._offset)
            lines = handle.readlines()
            self._offset = handle.tell()
        return lines


def cpu_percent(previous, current, elapsed):
    """두 표본의 jiffies 차 → CPU %(코어 1개 기준 100%)."""
    if previous is None or current is None or elapsed <= 0:
        return 0.0
    return (current - previous) / CLK_TCK / elapsed * 100.0


def camera_names(explicit=None):
    """감시할 카메라 이름 목록.

    이름은 로스터(`config/camera/camera_common.yaml`)가 정한다 — 여기서 `cam0..N` 을 만들어
    쓰면 위치 기준 이름(`cam_lf` 등)으로 개명했을 때 전 열이 공란이 된다(2026-07-30).
    로스터를 못 찾으면 빈 목록을 돌려주고, 호출부는 로그에서 발견된 이름으로 채운다.
    """
    if explicit:
        return [name.strip() for name in explicit.split(",") if name.strip()]
    env = os.environ.get("CAMERA_CONFIG")
    candidates = [env] if env else []
    directory = os.path.dirname(os.path.realpath(__file__))
    for _ in range(10):
        candidates.append(os.path.join(directory, "config", "camera", "camera_common.yaml"))
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    for path in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            import yaml
            with open(path, "r") as handle:
                config = yaml.safe_load(handle) or {}
        except Exception:
            continue
        names = [c["name"] for c in (config.get("cameras") or []) if c.get("name")]
        if names:
            return names
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pub-log", required=True)
    parser.add_argument("--viewer-log", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--duration-h", type=float, default=24.0)
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--cameras", default=None,
                        help="카메라 이름 쉼표 목록. 생략하면 공용 로스터에서 읽는다.")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    cams = camera_names(args.cameras)
    if not cams:
        # CSV 열은 헤더 작성 시 고정되므로 이름을 여기서 확정해야 한다. 로스터를 못 찾았으면
        # 종전 관례로 되돌리되, 이름이 다르면 해당 열이 공란이 되므로 크게 알린다.
        cams = [f"cam{i}" for i in range(6)]
        print(f"경고: 로스터를 찾지 못해 이름을 {cams} 로 가정한다 "
              "(--cameras 로 명시하거나 CAMERA_CONFIG 를 지정할 것)", flush=True)
    print(f"감시 대상 카메라: {', '.join(cams)}", flush=True)
    csv_path = os.path.join(args.out_dir, "soak_samples.csv")
    report_path = os.path.join(args.out_dir, "soak_report.md")

    columns = (
        ["iso_time", "elapsed_h", "viewer_alive", "publishers_alive", "shm_segments",
         "viewer_rss_mb", "viewer_cpu_pct", "publishers_rss_mb", "publishers_cpu_pct"]
        + [f"{c}_capture_fps" for c in cams]
        + [f"{c}_grab_failures" for c in cams]
        + [f"{c}_display_fps" for c in cams]
        + [f"{c}_rendered_delta" for c in cams]
    )

    pub_tail = LogTail(args.pub_log)
    viewer_tail = LogTail(args.viewer_log)

    capture_samples = []
    display_samples = []
    viewer_rss_series = []
    previous_jiffies = {}

    start = time.monotonic()
    deadline = start + args.duration_h * 3600.0

    with open(csv_path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        handle.flush()

        while time.monotonic() < deadline:
            loop_start = time.monotonic()

            # --- 로그 증분 파싱 ---
            latest_capture = {}
            for line in pub_tail.read_new_lines():
                parsed = parse_capture_line(line)
                if parsed:
                    capture_samples.append(parsed)
                    latest_capture[parsed["camera"]] = parsed

            latest_display = {}
            for line in viewer_tail.read_new_lines():
                parsed = parse_display_line(line)
                if parsed:
                    display_samples.append(parsed)
                    latest_display = parsed["cameras"]

            # --- 프로세스 자원 ---
            procs = find_processes()
            elapsed = max(loop_start - start, 1e-6)
            row = {
                "iso_time": datetime.datetime.now().isoformat(timespec="seconds"),
                "elapsed_h": round((loop_start - start) / 3600.0, 4),
                "viewer_alive": len(procs["viewer"]),
                "publishers_alive": len(procs["publishers"]),
                "shm_segments": sum(
                    1 for name in os.listdir("/dev/shm") if name.startswith("fastrtps")
                ),
            }

            interval = args.interval
            viewer_rss = viewer_cpu = 0.0
            for pid in procs["viewer"]:
                times = read_proc_times(pid)
                if times is None:
                    continue
                jiffies, rss_mb = times
                viewer_rss += rss_mb
                viewer_cpu += cpu_percent(previous_jiffies.get(pid), jiffies, interval)
                previous_jiffies[pid] = jiffies

            pub_rss = pub_cpu = 0.0
            for pid in procs["publishers"].values():
                times = read_proc_times(pid)
                if times is None:
                    continue
                jiffies, rss_mb = times
                pub_rss += rss_mb
                pub_cpu += cpu_percent(previous_jiffies.get(pid), jiffies, interval)
                previous_jiffies[pid] = jiffies

            row["viewer_rss_mb"] = round(viewer_rss, 1)
            row["viewer_cpu_pct"] = round(viewer_cpu, 1)
            row["publishers_rss_mb"] = round(pub_rss, 1)
            row["publishers_cpu_pct"] = round(pub_cpu, 1)
            if viewer_rss > 0:
                viewer_rss_series.append(viewer_rss)

            for cam in cams:
                capture = latest_capture.get(cam)
                row[f"{cam}_capture_fps"] = capture["fps"] if capture else ""
                row[f"{cam}_grab_failures"] = capture["grab_failures"] if capture else ""
                display = latest_display.get(cam)
                if display:
                    row[f"{cam}_display_fps"] = display["fps"]
                    # 뷰어가 이미 구간 증분을 찍으므로 그대로 기록한다(재차 차분 금지).
                    row[f"{cam}_rendered_delta"] = display["frames_delta"]
                else:
                    row[f"{cam}_display_fps"] = ""
                    row[f"{cam}_rendered_delta"] = ""

            writer.writerow(row)
            handle.flush()

            sleep_for = args.interval - (time.monotonic() - loop_start)
            if sleep_for > 0:
                time.sleep(sleep_for)

    write_report(report_path, args, capture_samples, display_samples, viewer_rss_series)


def write_report(path, args, capture_samples, display_samples, viewer_rss_series):
    """최종 요약 마크다운 작성 — 판정은 사람이 한다(수치와 사실만 적는다)."""
    capture = summarize_capture(capture_samples)
    display = summarize_display(display_samples)
    rss = rss_growth_mb(viewer_rss_series)
    now = datetime.datetime.now().isoformat(timespec="seconds")

    lines = [
        "# USB CCTV 내구 테스트 결과",
        "",
        f"- 종료 시각: {now}",
        f"- 설정: {args.duration_h}시간, 표본 주기 {args.interval}초, 카메라 {args.cameras}대",
        f"- 원시 로그: `{args.pub_log}`, `{args.viewer_log}`",
        "",
        "## 캡처 (퍼블리셔)",
        "",
        "| 카메라 | 표본 | min fps | mean fps | max fps | 25fps 미만 표본 | grab_failures |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cam in sorted(capture):
        s = capture[cam]
        lines.append(
            f"| {cam} | {s['samples']} | {s['min_fps']:.2f} | {s['mean_fps']:.2f} | "
            f"{s['max_fps']:.2f} | {s['degraded_samples']} | {s['grab_failures']} |"
        )

    lines += [
        "",
        "## 표시 (뷰어)",
        "",
        "| 카메라 | 표본 | min fps | mean fps | 정지 구간 | 누적 렌더 프레임 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for cam in sorted(display):
        s = display[cam]
        lines.append(
            f"| {cam} | {s['samples']} | {s['min_fps']:.2f} | {s['mean_fps']:.2f} | "
            f"{s['stall_intervals']} | {s['total_frames']} |"
        )

    lines += [
        "",
        "## 뷰어 메모리 (RSS)",
        "",
        f"- 시작 {rss['first_mb']:.1f} MB → 종료 {rss['last_mb']:.1f} MB "
        f"(최대 {rss['max_mb']:.1f} MB, 증가 {rss['growth_mb']:+.1f} MB)",
        "",
        "> 판정 기준은 이 문서가 정하지 않는다 — 수치·사실만 기록한다.",
        "",
    ]

    with open(path, "w") as handle:
        handle.write("\n".join(lines))


if __name__ == "__main__":
    main()
