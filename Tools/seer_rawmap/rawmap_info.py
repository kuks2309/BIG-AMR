#!/usr/bin/env python3
"""Summarize Seer ``.rawmap`` files: scans, beams, time span, odometry, schema.

Usage:
    python3 rawmap_info.py FILE_OR_DIR [FILE_OR_DIR ...] [--json] [--sort NAME]

Standard library only; see ``rawmap_decode.py`` for the wire-format decoder and
for the ``.proto`` line citations behind every field.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Dict, List, Optional

from rawmap_decode import MapLog, RawmapDecodeError, decode_maplog

RAWMAP_SUFFIX = ".rawmap"
_DEG_PER_RAD = 180.0 / math.pi
_BYTES_PER_MIB = 1024.0 * 1024.0

_SORT_KEYS = ("name", "scans", "size", "duration")

_TABLE_COLUMNS = (
    ("file", 34),
    ("MiB", 7),
    ("scans", 6),
    ("beams", 7),
    ("odo", 6),
    ("loc", 6),
    ("t0..t1 [s]", 21),
    ("dur", 8),
    ("odo bbox x/y [m]", 30),
    ("laser x,y,yaw", 22),
    ("step", 7),
    ("rmax", 6),
    ("name", 13),
    ("schema", 24),
)


def collect_rawmap_paths(targets: List[str]) -> List[str]:
    """Expand CLI targets into a sorted list of ``.rawmap`` file paths.

    Args:
        targets: Files and/or directories given on the command line.
            Directories are scanned one level deep for ``*.rawmap``.

    Returns:
        Deduplicated, sorted absolute-or-given paths.

    Raises:
        FileNotFoundError: A target does not exist.
    """
    paths: List[str] = []
    for target in targets:
        if os.path.isdir(target):
            for name in sorted(os.listdir(target)):
                if name.endswith(RAWMAP_SUFFIX):
                    paths.append(os.path.join(target, name))
        elif os.path.isfile(target):
            paths.append(target)
        else:
            raise FileNotFoundError(target)
    return sorted(dict.fromkeys(paths))


def summarize(log: MapLog) -> Dict[str, object]:
    """Build a JSON-serializable summary of one decoded ``.rawmap``.

    Args:
        log: A decoded :class:`~rawmap_decode.MapLog`.

    Returns:
        A dict with counts, the scan time span [s], the odometry bounding box
        [m], the laser pose (yaw in rad **and** deg), the angular step [rad],
        max range [m], laser name and schema verdict.  Missing values are
        ``None``.
    """
    span = log.time_range_sec()
    bbox = log.odometry_bounds()
    pose = log.laser_pose
    return {
        "file": os.path.basename(log.source_path),
        "path": log.source_path,
        "size_bytes": _file_size(log.source_path),
        "scan_count": log.scan_count,
        "beam_counts": log.beam_counts(),
        "odometry_count": len(log.odometry),
        "localization_count": len(log.localization),
        "raw_field20_count": len(log.raw_field20),
        "time_first_sec": span[0] if span else None,
        "time_last_sec": span[1] if span else None,
        "duration_sec": (span[1] - span[0]) if span else None,
        "odo_bbox_m": list(bbox) if bbox else None,
        "laser_pos_x_m": pose.x,
        "laser_pos_y_m": pose.y,
        "laser_install_yaw_rad": pose.install_yaw_rad,
        "laser_install_yaw_deg": pose.install_yaw_rad * _DEG_PER_RAD,
        "laser_pos_z_raw": pose.pos_z_raw,
        "laser_install_height_m": pose.install_height,
        "laser_install_yaw_field11_rad": pose.install_yaw_field11,
        "laser_step_rad": log.laser_step_rad,
        "laser_step_deg": log.laser_step_rad * _DEG_PER_RAD,
        "laser_range_max_m": log.laser_range_max_m,
        "laser_name": log.laser_name,
        "laser_type": log.laser_type,
        "schema_variant": log.schema_variant.value,
        "unknown_fields": [list(pair) for pair in log.unknown_fields],
    }


def _file_size(path: str) -> Optional[int]:
    """Return the file size in bytes, or ``None`` when it cannot be stat'ed."""
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def _fmt_beams(beam_counts: List[int]) -> str:
    """Render a beam-count list compactly (``541`` or ``521..1041``)."""
    if not beam_counts:
        return "-"
    if len(beam_counts) == 1:
        return str(beam_counts[0])
    return f"{beam_counts[0]}..{beam_counts[-1]}"


def _fmt_bbox(bbox: Optional[List[float]]) -> str:
    """Render an odometry bounding box as ``x[min,max] y[min,max]``."""
    if not bbox:
        return "-"
    min_x, min_y, max_x, max_y = bbox
    return f"x[{min_x:.2f},{max_x:.2f}] y[{min_y:.2f},{max_y:.2f}]"


def format_table(rows: List[Dict[str, object]]) -> str:
    """Render summaries as a fixed-width text table.

    Args:
        rows: Summary dicts from :func:`summarize`.

    Returns:
        The table as a single string, without a trailing newline.
    """
    header = "  ".join(name.ljust(width) for name, width in _TABLE_COLUMNS)
    rule = "  ".join("-" * width for _, width in _TABLE_COLUMNS)
    lines = [header, rule]
    for row in rows:
        size = row["size_bytes"]
        t0 = row["time_first_sec"]
        t1 = row["time_last_sec"]
        dur = row["duration_sec"]
        cells = [
            str(row["file"]),
            f"{size / _BYTES_PER_MIB:.2f}" if size is not None else "-",
            str(row["scan_count"]),
            _fmt_beams(row["beam_counts"]),  # type: ignore[arg-type]
            str(row["odometry_count"]),
            str(row["localization_count"] or row["raw_field20_count"] or 0),
            f"{t0:.1f}..{t1:.1f}" if t0 is not None else "-",
            f"{dur:.1f}" if dur is not None else "-",
            _fmt_bbox(row["odo_bbox_m"]),  # type: ignore[arg-type]
            (
                f"{row['laser_pos_x_m']:.3f},{row['laser_pos_y_m']:.3f},"
                f"{row['laser_install_yaw_deg']:.1f}deg"
            ),
            f"{row['laser_step_deg']:.3f}d",
            f"{row['laser_range_max_m']:.0f}",
            str(row["laser_name"]),
            str(row["schema_variant"]),
        ]
        lines.append(
            "  ".join(
                cell.ljust(width) for cell, (_, width) in zip(cells, _TABLE_COLUMNS)
            )
        )
    return "\n".join(lines)


def _sort_rows(rows: List[Dict[str, object]], key: str) -> List[Dict[str, object]]:
    """Sort summary rows by one of :data:`_SORT_KEYS`."""
    if key == "scans":
        return sorted(rows, key=lambda r: r["scan_count"], reverse=True)  # type: ignore
    if key == "size":
        return sorted(rows, key=lambda r: r["size_bytes"] or 0, reverse=True)  # type: ignore
    if key == "duration":
        return sorted(rows, key=lambda r: r["duration_sec"] or 0.0, reverse=True)  # type: ignore
    return sorted(rows, key=lambda r: str(r["file"]))


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point.

    Args:
        argv: Argument vector without the program name; ``None`` uses
            ``sys.argv[1:]``.

    Returns:
        Process exit code: ``0`` when every target decoded, ``1`` otherwise.
    """
    parser = argparse.ArgumentParser(
        description="Summarize Seer .rawmap mapping logs.",
    )
    parser.add_argument(
        "targets",
        nargs="+",
        help="`.rawmap` files and/or directories containing them",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a JSON array of summaries instead of the text table",
    )
    parser.add_argument(
        "--sort",
        choices=_SORT_KEYS,
        default="name",
        help="row ordering (default: name)",
    )
    args = parser.parse_args(argv)

    try:
        paths = collect_rawmap_paths(args.targets)
    except FileNotFoundError as exc:
        print(f"error: no such file or directory: {exc}", file=sys.stderr)
        return 1
    if not paths:
        print("error: no .rawmap files found", file=sys.stderr)
        return 1

    rows: List[Dict[str, object]] = []
    failures = 0
    for path in paths:
        try:
            rows.append(summarize(decode_maplog(path)))
        except (OSError, RawmapDecodeError) as exc:
            failures += 1
            print(f"error: {path}: {exc}", file=sys.stderr)

    rows = _sort_rows(rows, args.sort)
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(format_table(rows))
        print(f"\n{len(rows)} file(s) decoded, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
