#!/usr/bin/env python3
"""Regression tests for the Seer ``.rawmap`` decoder.

Two tiers:

* ``TestWireFormat`` / ``TestSyntheticMapLog`` / ``TestSchemaDiscrimination`` /
  ``TestJsonlExport`` build protobuf bytes by hand and need no external asset —
  they run anywhere.
* ``TestRealAssets`` reads ``References/seer/slam_mapping/rawmaps/`` and is
  skipped when that (git-ignored, see ``.gitignore:12``) tree is absent.  A skip
  is **not** a pass; check the runner output for ``skipped=`` before claiming
  the real-asset tier ran.

Run:
    python3 -m unittest discover -s Tools/seer_rawmap/test -v
"""

from __future__ import annotations

import json
import io
import math
import os
import struct
import sys
import unittest

_TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TOOL_DIR not in sys.path:
    sys.path.insert(0, _TOOL_DIR)

import rawmap_decode as rd  # noqa: E402
import rawmap_to_jsonl as rj  # noqa: E402

_REPO_ROOT = os.path.dirname(os.path.dirname(_TOOL_DIR))
RAWMAP_DIR = os.path.join(_REPO_ROOT, "References", "seer", "slam_mapping", "rawmaps")

# Measured on 2026-08-08 from the recovered assets; see README.md result table.
LOCAL_MAP_LOG_SAMPLE = "robokit_2023-08-09_04-27-34.rawmap"
NO_FIELD20_SAMPLE = "robokit_2023-08-10_05-27-22.rawmap"
EXPECTED_LASER_NAME = "SickSafe-UDP"
EXPECTED_SAMPLE_SCANS = 149
EXPECTED_SAMPLE_ODOMETRY = 1618
EXPECTED_SAMPLE_LOCALIZATION = 1451
EXPECTED_SAMPLE_BEAMS = 541
EXPECTED_SAMPLE_POS_Z = -0.7853981633974483
EXPECTED_SAMPLE_STEP_RAD = 0.008726637937593242
EXPECTED_SAMPLE_RANGE_MAX_M = 40.0
EXPECTED_SAMPLE_FIRST_ODO_X = 22.190979786000398
# beam_count -> length of the leading uniform-`laser_step` run (measured).
UNIFORM_PREFIX_BY_BEAM_COUNT = {521: 521, 533: 533, 541: 541, 1041: 521}
UNIFORM_STEP_TOLERANCE_RAD = 1e-9


# --- minimal protobuf encoder (test-side, independent of the decoder) ----
def enc_varint(value: int) -> bytes:
    """Encode an unsigned integer as a base-128 varint."""
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def tag(field_number: int, wire_type: int) -> bytes:
    """Encode a protobuf key (field number + wire type)."""
    return enc_varint((field_number << 3) | wire_type)


def f_double(field_number: int, value: float) -> bytes:
    """Encode a scalar ``double`` field (wire type 1)."""
    return tag(field_number, rd.WIRE_FIXED64) + struct.pack("<d", value)


def f_float(field_number: int, value: float) -> bytes:
    """Encode a scalar ``float`` field (wire type 5)."""
    return tag(field_number, rd.WIRE_FIXED32) + struct.pack("<f", value)


def f_varint(field_number: int, value: int) -> bytes:
    """Encode a scalar varint field (wire type 0)."""
    return tag(field_number, rd.WIRE_VARINT) + enc_varint(value)


def f_bytes(field_number: int, payload: bytes) -> bytes:
    """Encode a length-delimited field (wire type 2)."""
    return (
        tag(field_number, rd.WIRE_LENGTH_DELIMITED) + enc_varint(len(payload)) + payload
    )


def f_string(field_number: int, text: str) -> bytes:
    """Encode a UTF-8 ``string`` field."""
    return f_bytes(field_number, text.encode("utf-8"))


def f_packed_doubles(field_number: int, values) -> bytes:
    """Encode a packed ``repeated double`` field."""
    return f_bytes(field_number, struct.pack(f"<{len(values)}d", *values))


def f_unpacked_doubles(field_number: int, values) -> bytes:
    """Encode a ``repeated double`` field in the non-packed (legacy) form."""
    return b"".join(f_double(field_number, v) for v in values)


def make_header(
    pub_nsec: int, data_nsec: int, seq: int = 0, frame_id: str = ""
) -> bytes:
    """Build a ``Message_Header`` body."""
    out = f_varint(1, pub_nsec) + f_varint(2, data_nsec)
    if seq:
        out += f_varint(3, seq)
    if frame_id:
        out += f_string(4, frame_id)
    return out


def make_scan(
    odo, dist, angle, rssi, header: bytes = b"", packed: bool = True
) -> bytes:
    """Build a ``Message_MapLogData`` body."""
    encode = f_packed_doubles if packed else f_unpacked_doubles
    out = f_double(1, odo[0]) + f_double(2, odo[1]) + f_double(3, odo[2])
    out += encode(4, dist) + encode(5, angle) + encode(6, rssi)
    if header:
        out += f_bytes(7, header)
    return out


def make_odo(timestamp, x, y, w, vx=0.0, vy=0.0, vw=0.0) -> bytes:
    """Build a ``Message_MapOdo`` body (timestamp double, poses float)."""
    return (
        f_double(1, timestamp)
        + f_float(2, x)
        + f_float(3, y)
        + f_float(4, w)
        + f_float(5, vx)
        + f_float(6, vy)
        + f_float(7, vw)
    )


def make_localization(header: bytes, x, y, angle, confidence=None, errs=()) -> bytes:
    """Build a ``Message_Localization`` body (the field-20 LocalMapLog payload)."""
    out = f_bytes(1, header) + f_double(2, x) + f_double(3, y) + f_double(4, angle)
    if confidence is not None:
        out += f_double(5, confidence)
    if errs:
        out += f_packed_doubles(6, errs)
    return out


# --- tier 1: no external asset required ---------------------------------
class TestWireFormat(unittest.TestCase):
    """Low-level varint / field-iteration / packed-double behaviour."""

    def test_varint_round_trip(self):
        for value in (0, 1, 127, 128, 300, 4460292444551, 2**64 - 1):
            decoded, pos = rd.read_varint(enc_varint(value), 0)
            self.assertEqual(decoded, value)
            self.assertEqual(pos, len(enc_varint(value)))

    def test_varint_truncated_raises(self):
        with self.assertRaises(rd.RawmapDecodeError):
            rd.read_varint(b"\x80\x80", 0)

    def test_iter_fields_all_wire_types(self):
        buf = f_varint(1, 300) + f_double(2, 1.5) + f_string(3, "hi") + f_float(4, 2.5)
        got = list(rd.iter_fields(buf))
        self.assertEqual(got[0], (1, rd.WIRE_VARINT, 300))
        self.assertEqual(got[1][:2], (2, rd.WIRE_FIXED64))
        self.assertEqual(struct.unpack("<d", got[1][2])[0], 1.5)
        self.assertEqual(got[2], (3, rd.WIRE_LENGTH_DELIMITED, b"hi"))
        self.assertEqual(struct.unpack("<f", got[3][2])[0], 2.5)

    def test_iter_fields_overlong_length_raises(self):
        bad = tag(1, rd.WIRE_LENGTH_DELIMITED) + enc_varint(99) + b"short"
        with self.assertRaises(rd.RawmapDecodeError):
            list(rd.iter_fields(bad))

    def test_iter_fields_rejects_group_wire_type(self):
        with self.assertRaises(rd.RawmapDecodeError):
            list(rd.iter_fields(tag(1, rd.WIRE_START_GROUP)))

    def test_unpack_doubles_round_trip(self):
        values = [1.613, 9999.999, -0.5, 0.0, 40.0]
        payload = struct.pack(f"<{len(values)}d", *values)
        self.assertEqual(rd.unpack_doubles(payload), values)

    def test_unpack_doubles_misaligned_raises(self):
        with self.assertRaises(rd.RawmapDecodeError):
            rd.unpack_doubles(b"\x00" * 12)


class TestSyntheticMapLog(unittest.TestCase):
    """Full-message round trip against hand-built protobuf bytes."""

    def setUp(self):
        self.dist = [1.25, 9999.999, 3.5]
        self.angle = [-2.356194490192345, 0.0, 2.356194490192345]
        self.rssi = [50.0, 0.0, 12.5]
        self.header = make_header(
            pub_nsec=4460292444551, data_nsec=4460292444340, seq=7, frame_id="L1"
        )
        self.blob = (
            f_double(1, 0.879)
            + f_double(2, -0.579)
            + f_double(3, EXPECTED_SAMPLE_POS_Z)
            + f_double(4, EXPECTED_SAMPLE_STEP_RAD)
            + f_double(5, EXPECTED_SAMPLE_RANGE_MAX_M)
            + f_bytes(
                6,
                make_scan(
                    (1.0, 2.0, 0.25), self.dist, self.angle, self.rssi, self.header
                ),
            )
            + f_bytes(6, make_scan((1.1, 2.1, 0.26), self.dist, self.angle, self.rssi))
            + f_string(7, EXPECTED_LASER_NAME)
            + f_double(8, 0.21)
            + f_bytes(9, make_odo(4460.278139518, 22.190979, 22.424225, -0.131400))
            + f_bytes(9, make_odo(4460.313779518, 22.190979, 22.424225, -0.131400))
            + f_varint(16, 3)
        )

    def test_scalar_fields(self):
        log = rd.decode_maplog_bytes(self.blob, source_path="synthetic")
        self.assertEqual(log.source_path, "synthetic")
        self.assertEqual(log.laser_name, EXPECTED_LASER_NAME)
        self.assertAlmostEqual(log.laser_pose.x, 0.879)
        self.assertAlmostEqual(log.laser_pose.y, -0.579)
        self.assertAlmostEqual(log.laser_pose.install_height, 0.21)
        self.assertEqual(log.laser_step_rad, EXPECTED_SAMPLE_STEP_RAD)
        self.assertEqual(log.laser_range_max_m, EXPECTED_SAMPLE_RANGE_MAX_M)
        self.assertEqual(log.laser_type, 3)
        self.assertEqual(log.unknown_fields, [])

    def test_scans_round_trip(self):
        log = rd.decode_maplog_bytes(self.blob)
        self.assertEqual(log.scan_count, 2)
        first = log.scans[0]
        self.assertEqual(first.dist, self.dist)
        self.assertEqual(first.angle, self.angle)
        self.assertEqual(first.rssi, self.rssi)
        self.assertEqual(first.beam_count, len(self.dist))
        self.assertAlmostEqual(first.odo_x, 1.0)
        self.assertAlmostEqual(first.odo_y, 2.0)
        self.assertAlmostEqual(first.odo_w, 0.25)
        self.assertEqual(first.header.seq, 7)
        self.assertEqual(first.header.frame_id, "L1")
        self.assertEqual(first.header.data_nsec, 4460292444340)
        self.assertAlmostEqual(first.timestamp_sec, 4460.29244434)
        self.assertEqual(log.beam_counts(), [len(self.dist)])

    def test_header_timestamp_falls_back_to_pub_nsec(self):
        blob = f_bytes(
            6, make_scan((0, 0, 0), [1.0], [0.0], [0.0], make_header(2_000_000_000, 0))
        )
        log = rd.decode_maplog_bytes(blob)
        self.assertAlmostEqual(log.scans[0].timestamp_sec, 2.0)

    def test_odometry_round_trip(self):
        log = rd.decode_maplog_bytes(self.blob)
        self.assertEqual(len(log.odometry), 2)
        self.assertAlmostEqual(log.odometry[0].timestamp, 4460.278139518)
        self.assertAlmostEqual(log.odometry[0].x, 22.190979, places=5)
        self.assertAlmostEqual(log.odometry[0].y, 22.424225, places=5)
        self.assertAlmostEqual(log.odometry[0].w, -0.131400, places=5)
        bbox = log.odometry_bounds()
        self.assertIsNotNone(bbox)
        self.assertAlmostEqual(bbox[0], 22.190979, places=5)

    def test_unpacked_repeated_double_is_accepted(self):
        blob = f_bytes(
            6,
            make_scan((0.0, 0.0, 0.0), self.dist, self.angle, self.rssi, packed=False),
        )
        log = rd.decode_maplog_bytes(blob)
        self.assertEqual(log.scans[0].dist, self.dist)
        self.assertEqual(log.scans[0].angle, self.angle)

    def test_unknown_top_level_field_is_recorded_not_fatal(self):
        blob = self.blob + f_varint(99, 1)
        log = rd.decode_maplog_bytes(blob)
        self.assertIn((99, rd.WIRE_VARINT), log.unknown_fields)
        self.assertEqual(log.scan_count, 2)

    def test_truncated_file_raises(self):
        # Chop bytes off the last log_data payload so its length prefix
        # over-claims; a whole-field chop would still be valid protobuf.
        scan_field = f_bytes(
            6, make_scan((1.0, 2.0, 0.25), self.dist, self.angle, self.rssi)
        )
        with self.assertRaises(rd.RawmapDecodeError):
            rd.decode_maplog_bytes(self.blob + scan_field[:-5])

    def test_laser_pos_z_is_install_yaw_when_field11_absent(self):
        """Trap 1: laser_pos_z (field 3) carries yaw — message_map.proto:44."""
        log = rd.decode_maplog_bytes(self.blob)
        self.assertEqual(log.laser_pose.pos_z_raw, EXPECTED_SAMPLE_POS_Z)
        self.assertEqual(log.laser_pose.install_yaw_rad, EXPECTED_SAMPLE_POS_Z)
        self.assertEqual(log.laser_pose.install_yaw_field11, 0.0)

    def test_field11_overrides_pos_z_for_install_yaw(self):
        blob = self.blob + f_double(11, 1.5707963267948966)
        log = rd.decode_maplog_bytes(blob)
        self.assertEqual(log.laser_pose.pos_z_raw, EXPECTED_SAMPLE_POS_Z)
        self.assertAlmostEqual(log.laser_pose.install_yaw_rad, 1.5707963267948966)


class TestSchemaDiscrimination(unittest.TestCase):
    """Trap 2: field 20 is ``all_gnss_data`` or ``localization_data``."""

    def test_absent_field20_is_ambiguous(self):
        log = rd.decode_maplog_bytes(f_string(7, EXPECTED_LASER_NAME))
        self.assertIs(log.schema_variant, rd.SchemaVariant.AMBIGUOUS)
        self.assertEqual(log.localization, [])
        self.assertEqual(log.raw_field20, [])

    def test_localization_shaped_field20_decodes_as_local_map_log(self):
        payload = make_localization(
            make_header(4465121005564, 4465121005564),
            13.761460156409306,
            -29.204088794714377,
            -1.959849238395691,
            confidence=0.87,
            errs=(0.00682538099999988, -0.004318915199999992),
        )
        log = rd.decode_maplog_bytes(f_bytes(20, payload))
        self.assertIs(log.schema_variant, rd.SchemaVariant.LOCAL_MAP_LOG)
        self.assertEqual(len(log.localization), 1)
        loc = log.localization[0]
        self.assertAlmostEqual(loc.x, 13.761460156409306)
        self.assertAlmostEqual(loc.y, -29.204088794714377)
        self.assertAlmostEqual(loc.angle, -1.959849238395691)
        self.assertAlmostEqual(loc.confidence, 0.87)
        self.assertEqual(len(loc.correction_errs), 2)
        self.assertEqual(loc.header.pub_nsec, 4465121005564)

    def test_localization_without_confidence_still_classifies(self):
        payload = make_localization(make_header(1, 1), 1.0, 2.0, 3.0)
        log = rd.decode_maplog_bytes(f_bytes(20, payload))
        self.assertIs(log.schema_variant, rd.SchemaVariant.LOCAL_MAP_LOG)
        self.assertEqual(log.localization[0].confidence, 0.0)

    def test_non_localization_field20_falls_back_to_map_log(self):
        # A submessage whose field 1 is a varint cannot be Message_Localization
        # (field 1 is Message_Header, wire type 2) — treat as all_gnss_data.
        payload = f_varint(1, 42) + f_string(2, "ANT0")
        log = rd.decode_maplog_bytes(f_bytes(20, payload))
        self.assertIs(log.schema_variant, rd.SchemaVariant.MAP_LOG)
        self.assertEqual(log.localization, [])
        self.assertEqual(log.raw_field20, [payload])

    def test_field20_missing_xy_is_not_localization(self):
        payload = f_bytes(1, make_header(1, 1)) + f_double(2, 1.0)
        log = rd.decode_maplog_bytes(f_bytes(20, payload))
        self.assertIs(log.schema_variant, rd.SchemaVariant.MAP_LOG)

    def test_classify_field20_direct(self):
        loc = make_localization(make_header(1, 1), 1.0, 2.0, 3.0)
        self.assertIs(rd.classify_field20([]), rd.SchemaVariant.AMBIGUOUS)
        self.assertIs(rd.classify_field20([loc]), rd.SchemaVariant.LOCAL_MAP_LOG)
        self.assertIs(
            rd.classify_field20([loc, f_varint(1, 1)]), rd.SchemaVariant.MAP_LOG
        )


class TestJsonlExport(unittest.TestCase):
    """Replay-record shape produced by ``rawmap_to_jsonl``."""

    def setUp(self):
        self.blob = (
            f_double(3, EXPECTED_SAMPLE_POS_Z)
            + f_double(4, EXPECTED_SAMPLE_STEP_RAD)
            + f_double(5, EXPECTED_SAMPLE_RANGE_MAX_M)
            + f_string(7, EXPECTED_LASER_NAME)
            + f_bytes(
                6,
                make_scan(
                    (1.0, 2.0, 0.25),
                    [1.0],
                    [0.0],
                    [50.0],
                    make_header(0, 1_000_000_000),
                ),
            )
            + f_bytes(
                6,
                make_scan(
                    (1.1, 2.1, 0.26),
                    [2.0],
                    [0.1],
                    [51.0],
                    make_header(0, 2_000_000_000),
                ),
            )
            + f_bytes(
                6,
                make_scan(
                    (1.2, 2.2, 0.27),
                    [3.0],
                    [0.2],
                    [52.0],
                    make_header(0, 3_000_000_000),
                ),
            )
        )
        self.log = rd.decode_maplog_bytes(self.blob, source_path="synthetic.rawmap")

    def test_record_keys_and_values(self):
        record = rj.scan_to_record(self.log.scans[0])
        self.assertEqual(list(record.keys()), ["odo", "dist", "angle", "rssi", "t"])
        self.assertEqual(record["odo"], [1.0, 2.0, 0.25])
        self.assertEqual(record["dist"], [1.0])
        self.assertEqual(record["angle"], [0.0])
        self.assertEqual(record["rssi"], [50.0])
        self.assertAlmostEqual(record["t"], 1.0)

    def test_write_jsonl_one_line_per_scan(self):
        buf = io.StringIO()
        written = rj.write_jsonl(self.log, buf)
        lines = buf.getvalue().strip().split("\n")
        self.assertEqual(written, 3)
        self.assertEqual(len(lines), 3)
        self.assertAlmostEqual(json.loads(lines[2])["t"], 3.0)

    def test_stride_selects_every_nth_scan(self):
        buf = io.StringIO()
        written = rj.write_jsonl(self.log, buf, stride=2)
        self.assertEqual(written, 2)
        stamps = [json.loads(line)["t"] for line in buf.getvalue().strip().split("\n")]
        self.assertAlmostEqual(stamps[0], 1.0)
        self.assertAlmostEqual(stamps[1], 3.0)

    def test_stride_below_one_raises(self):
        with self.assertRaises(ValueError):
            list(rj.iter_records(self.log, stride=0))

    def test_meta_carries_resolved_install_yaw(self):
        meta = rj.build_meta(self.log, stride=1, written=3)
        self.assertEqual(meta["laser_install_yaw_rad"], EXPECTED_SAMPLE_POS_Z)
        self.assertAlmostEqual(meta["laser_install_yaw_deg"], -45.0)
        self.assertEqual(meta["laser_name"], EXPECTED_LASER_NAME)
        self.assertEqual(meta["scan_count_written"], 3)
        json.dumps(meta)  # must stay JSON-serializable


# --- tier 2: recovered assets (skipped when References/ is absent) ------
_HAS_ASSETS = os.path.isdir(RAWMAP_DIR)


@unittest.skipUnless(
    _HAS_ASSETS, f"recovered assets not present at {RAWMAP_DIR} (git-ignored)"
)
class TestRealAssets(unittest.TestCase):
    """Decode the 26 recovered ``.rawmap`` files."""

    def test_every_rawmap_decodes(self):
        paths = [
            os.path.join(RAWMAP_DIR, n)
            for n in sorted(os.listdir(RAWMAP_DIR))
            if n.endswith(".rawmap")
        ]
        self.assertGreater(len(paths), 0)
        for path in paths:
            with self.subTest(path=os.path.basename(path)):
                log = rd.decode_maplog(path)
                self.assertEqual(log.laser_name, EXPECTED_LASER_NAME)
                self.assertGreater(log.scan_count, 0)
                self.assertGreater(len(log.odometry), 0)
                self.assertEqual(log.unknown_fields, [])
                for scan in log.scans:
                    self.assertEqual(len(scan.dist), len(scan.angle))
                    self.assertEqual(len(scan.dist), len(scan.rssi))

    def test_local_map_log_sample_matches_measured_values(self):
        log = rd.decode_maplog(os.path.join(RAWMAP_DIR, LOCAL_MAP_LOG_SAMPLE))
        self.assertIs(log.schema_variant, rd.SchemaVariant.LOCAL_MAP_LOG)
        self.assertEqual(log.scan_count, EXPECTED_SAMPLE_SCANS)
        self.assertEqual(len(log.odometry), EXPECTED_SAMPLE_ODOMETRY)
        self.assertEqual(len(log.localization), EXPECTED_SAMPLE_LOCALIZATION)
        self.assertEqual(log.beam_counts(), [EXPECTED_SAMPLE_BEAMS])
        self.assertEqual(log.laser_pose.pos_z_raw, EXPECTED_SAMPLE_POS_Z)
        self.assertEqual(log.laser_pose.install_yaw_rad, EXPECTED_SAMPLE_POS_Z)
        self.assertEqual(log.laser_step_rad, EXPECTED_SAMPLE_STEP_RAD)
        self.assertEqual(log.laser_range_max_m, EXPECTED_SAMPLE_RANGE_MAX_M)
        self.assertAlmostEqual(log.scans[0].odo_x, EXPECTED_SAMPLE_FIRST_ODO_X)

    def test_sample_without_field20_is_ambiguous(self):
        log = rd.decode_maplog(os.path.join(RAWMAP_DIR, NO_FIELD20_SAMPLE))
        self.assertIs(log.schema_variant, rd.SchemaVariant.AMBIGUOUS)
        self.assertEqual(log.localization, [])
        self.assertEqual(log.raw_field20, [])

    def test_angle_span_agrees_with_step_and_beam_count(self):
        """Only the 541-beam sample is a single uniform sweep end to end."""
        log = rd.decode_maplog(os.path.join(RAWMAP_DIR, LOCAL_MAP_LOG_SAMPLE))
        scan = log.scans[0]
        span = scan.angle[-1] - scan.angle[0]
        expected = log.laser_step_rad * (scan.beam_count - 1)
        self.assertAlmostEqual(span, expected, places=6)

    def test_beam_block_structure_matches_measurement(self):
        """1041-beam scans are 521 uniform beams + a 520-beam non-uniform tail.

        Locks the README result table: a replayer must not treat a 1041-beam
        scan as one sweep.
        """
        for name in sorted(os.listdir(RAWMAP_DIR)):
            if not name.endswith(".rawmap"):
                continue
            with self.subTest(name=name):
                log = rd.decode_maplog(os.path.join(RAWMAP_DIR, name))
                scan = log.scans[0]
                uniform = 1
                while uniform < scan.beam_count and math.isclose(
                    scan.angle[uniform] - scan.angle[uniform - 1],
                    log.laser_step_rad,
                    abs_tol=UNIFORM_STEP_TOLERANCE_RAD,
                ):
                    uniform += 1
                self.assertIn(scan.beam_count, UNIFORM_PREFIX_BY_BEAM_COUNT)
                self.assertEqual(uniform, UNIFORM_PREFIX_BY_BEAM_COUNT[scan.beam_count])

    def test_scan_odometry_matches_nearest_odometer_entry(self):
        log = rd.decode_maplog(os.path.join(RAWMAP_DIR, LOCAL_MAP_LOG_SAMPLE))
        scan = log.scans[0]
        nearest = min(log.odometry, key=lambda o: abs(o.timestamp - scan.timestamp_sec))
        self.assertAlmostEqual(nearest.x, scan.odo_x, places=4)
        self.assertAlmostEqual(nearest.y, scan.odo_y, places=4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
