#!/usr/bin/env python3
"""Export a Seer ``.rawmap`` to JSONL for replay.

One output line = one laser scan:

    {"odo": [x, y, w], "dist": [...], "angle": [...], "rssi": [...], "t": <sec>}

Units: ``odo`` x/y in metres and w in radians; ``dist`` in metres; ``angle`` in
radians (laser frame); ``rssi`` unitless; ``t`` in seconds on the robot's log
clock (monotonic/uptime, **not** UNIX epoch).

Per-file constants that do not fit in a per-scan record (laser mounting pose,
angular step, max range, schema verdict) are written to a sidecar
``<output>.meta.json`` so the JSONL stays strictly one-scan-per-line.

Usage:
    python3 rawmap_to_jsonl.py INPUT.rawmap -o OUT.jsonl [--stride N] [--gzip]

Standard library only.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import sys
from typing import IO, Dict, Iterator, List, Optional

from rawmap_decode import MapLog, RawmapDecodeError, ScanRecord, decode_maplog

_DEG_PER_RAD = 180.0 / math.pi
META_SUFFIX = ".meta.json"
GZIP_SUFFIX = ".gz"
DEFAULT_STRIDE = 1


def scan_to_record(scan: ScanRecord) -> Dict[str, object]:
    """Convert one decoded scan into the replay record dict.

    Args:
        scan: A decoded :class:`~rawmap_decode.ScanRecord`.

    Returns:
        ``{"odo": [x_m, y_m, w_rad], "dist": [m...], "angle": [rad...],
        "rssi": [...], "t": seconds}`` — key order matches the documented
        replay contract.
    """
    return {
        "odo": [scan.odo_x, scan.odo_y, scan.odo_w],
        "dist": scan.dist,
        "angle": scan.angle,
        "rssi": scan.rssi,
        "t": scan.timestamp_sec,
    }


def iter_records(log: MapLog, stride: int = DEFAULT_STRIDE) -> Iterator[Dict]:
    """Yield replay records for a decoded log.

    Args:
        log: A decoded :class:`~rawmap_decode.MapLog`.
        stride: Emit every ``stride``-th scan (``1`` = all scans).

    Yields:
        Record dicts from :func:`scan_to_record`.

    Raises:
        ValueError: ``stride`` is less than 1.
    """
    if stride < 1:
        raise ValueError(f"stride must be >= 1, got {stride}")
    for index in range(0, len(log.scans), stride):
        yield scan_to_record(log.scans[index])


def build_meta(log: MapLog, stride: int, written: int) -> Dict[str, object]:
    """Build the sidecar metadata for an exported log.

    Args:
        log: The decoded source log.
        stride: Stride used for the export.
        written: Number of records actually written.

    Returns:
        A JSON-serializable dict describing the source file, the laser mounting
        pose (yaw resolved per the ``laser_pos_z`` trap), scan geometry and the
        schema verdict.
    """
    pose = log.laser_pose
    span = log.time_range_sec()
    bbox = log.odometry_bounds()
    return {
        "source_path": log.source_path,
        "source_basename": os.path.basename(log.source_path),
        "laser_name": log.laser_name,
        "laser_type": log.laser_type,
        "laser_pos_x_m": pose.x,
        "laser_pos_y_m": pose.y,
        "laser_install_yaw_rad": pose.install_yaw_rad,
        "laser_install_yaw_deg": pose.install_yaw_rad * _DEG_PER_RAD,
        "laser_install_height_m": pose.install_height,
        "laser_install_pitch_rad": pose.install_pitch,
        "laser_install_roll_rad": pose.install_roll,
        "laser_step_rad": log.laser_step_rad,
        "laser_range_max_m": log.laser_range_max_m,
        "schema_variant": log.schema_variant.value,
        "scan_count_total": log.scan_count,
        "scan_count_written": written,
        "stride": stride,
        "beam_counts": log.beam_counts(),
        "odometry_count": len(log.odometry),
        "localization_count": len(log.localization),
        "time_first_sec": span[0] if span else None,
        "time_last_sec": span[1] if span else None,
        "odo_bbox_m": list(bbox) if bbox else None,
    }


def write_jsonl(log: MapLog, handle: IO[str], stride: int = DEFAULT_STRIDE) -> int:
    """Write replay records to an open text stream.

    Args:
        log: The decoded source log.
        handle: Text-mode writable stream.
        stride: Emit every ``stride``-th scan.

    Returns:
        Number of records written.
    """
    written = 0
    for record in iter_records(log, stride):
        handle.write(json.dumps(record, separators=(",", ":")))
        handle.write("\n")
        written += 1
    return written


def _open_output(path: str, use_gzip: bool) -> IO[str]:
    """Open ``path`` for text writing, gzip-compressed when requested."""
    if use_gzip:
        return gzip.open(path, "wt", encoding="utf-8")
    return open(path, "w", encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point.

    Args:
        argv: Argument vector without the program name; ``None`` uses
            ``sys.argv[1:]``.

    Returns:
        Process exit code: ``0`` on success, ``1`` on decode/IO failure.
    """
    parser = argparse.ArgumentParser(
        description="Export a Seer .rawmap to one-scan-per-line JSONL.",
    )
    parser.add_argument("input", help="path to the .rawmap file")
    parser.add_argument(
        "-o",
        "--output",
        help="output path (default: <input basename>.jsonl in the cwd)",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=DEFAULT_STRIDE,
        help="emit every N-th scan (default: 1)",
    )
    parser.add_argument(
        "--gzip",
        action="store_true",
        help="gzip the output and append .gz to the path if absent",
    )
    parser.add_argument(
        "--no-meta",
        action="store_true",
        help="skip writing the <output>.meta.json sidecar",
    )
    args = parser.parse_args(argv)

    if args.stride < 1:
        print("error: --stride must be >= 1", file=sys.stderr)
        return 1

    output = args.output
    if output is None:
        base = os.path.basename(args.input)
        stem = base[: -len(".rawmap")] if base.endswith(".rawmap") else base
        output = f"{stem}.jsonl"
    if args.gzip and not output.endswith(GZIP_SUFFIX):
        output += GZIP_SUFFIX

    try:
        log = decode_maplog(args.input)
    except (OSError, RawmapDecodeError) as exc:
        print(f"error: {args.input}: {exc}", file=sys.stderr)
        return 1

    try:
        with _open_output(output, args.gzip) as handle:
            written = write_jsonl(log, handle, args.stride)
        if not args.no_meta:
            meta_path = output + META_SUFFIX
            with open(meta_path, "w", encoding="utf-8") as meta_handle:
                json.dump(build_meta(log, args.stride, written), meta_handle, indent=2)
                meta_handle.write("\n")
    except OSError as exc:
        print(f"error: writing {output}: {exc}", file=sys.stderr)
        return 1

    print(
        f"{output}: {written} scan record(s) of {log.scan_count} "
        f"(stride {args.stride}), schema {log.schema_variant.value}"
    )
    if not args.no_meta:
        print(f"{output}{META_SUFFIX}: per-file metadata")
    return 0


if __name__ == "__main__":
    sys.exit(main())
