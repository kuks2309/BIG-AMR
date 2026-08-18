"""Seer ``.rawmap`` (raw mapping log) decoder — pure standard library.

A ``.rawmap`` file is **one** serialized protobuf message, either
``rbk.protocol.Message_MapLog`` or ``rbk.protocol.Message_LocalMapLog``.
The two differ only in field 20 (``all_gnss_data`` vs ``localization_data``);
every other field number/type is identical.

Schema source (verbatim, recovered from the robot):
    References/seer/slam_mapping/proto/message_map.proto:41-62   Message_MapLog
    References/seer/slam_mapping/proto/message_map.proto:64-85   Message_LocalMapLog
    References/seer/slam_mapping/proto/message_map.proto:11-19   Message_MapLogData
    References/seer/slam_mapping/proto/message_map.proto:20-28   Message_MapOdo
    References/seer/slam_mapping/proto/message_header.proto:3-8  Message_Header
    References/seer/slam_mapping/proto/message_localization.proto:5-39
                                                                Message_Localization

Two traps this module encodes explicitly:

1. ``Message_MapLog.laser_pos_z`` (field 3) is **not** a height.  The proto
   comment at message_map.proto:44 states it holds the laser *install yaw*
   ("由于版本原因里面设置是激光安装yaw角，取激光高度数据从laser_install_height"),
   and the height lives in ``laser_install_height`` (field 8).  See
   :attr:`LaserPose.install_yaw_rad`.
2. Field 20 is schema-dependent.  This module classifies it structurally
   (:func:`classify_field20`) instead of assuming one variant.

No external dependency: the ``protobuf`` runtime is **not** required and no
``.proto`` compilation step is involved.  Only the protobuf *wire format* is
implemented here.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator, List, Optional, Sequence, Tuple

__all__ = [
    "MapLog",
    "LaserPose",
    "ScanRecord",
    "OdoRecord",
    "LocalizationRecord",
    "Header",
    "SchemaVariant",
    "RawmapDecodeError",
    "decode_maplog",
    "decode_maplog_bytes",
    "classify_field20",
    "iter_fields",
    "read_varint",
    "unpack_doubles",
]


# --- protobuf wire format constants -------------------------------------
# https://protobuf.dev/programming-guides/encoding/
WIRE_VARINT = 0
WIRE_FIXED64 = 1
WIRE_LENGTH_DELIMITED = 2
WIRE_START_GROUP = 3
WIRE_END_GROUP = 4
WIRE_FIXED32 = 5

_VARINT_PAYLOAD_MASK = 0x7F
_VARINT_CONTINUATION_BIT = 0x80
_VARINT_SHIFT_PER_BYTE = 7
_VARINT_MAX_BYTES = 10  # 64-bit value at 7 payload bits per byte
_TAG_WIRE_TYPE_MASK = 0x07
_TAG_FIELD_NUMBER_SHIFT = 3

_FIXED64_SIZE = 8
_FIXED32_SIZE = 4

_NSEC_PER_SEC = 1_000_000_000.0


# --- field numbers (all quoted from the recovered .proto files) ---------
class _MapLogField:
    """Field numbers of ``Message_MapLog`` / ``Message_LocalMapLog``.

    Source: message_map.proto:41-62 and message_map.proto:64-85.
    """

    LASER_POS_X = 1
    LASER_POS_Y = 2
    LASER_POS_Z = 3  # NOT height — install yaw (message_map.proto:44)
    LASER_STEP = 4
    LASER_RANGE_MAX = 5
    LOG_DATA = 6
    LASER_NAME = 7
    LASER_INSTALL_HEIGHT = 8
    ODOMETER = 9
    LOG_DATA_3D = 10
    LASER_INSTALL_YAW = 11
    LASER_INSTALL_PITCH = 12
    LASER_INSTALL_ROLL = 13
    IMU_DATA = 14
    GNSS_DATA = 15
    LASER_TYPE = 16
    FACTOR = 17
    AZIMUTH_CORRECTION = 18
    VERTICAL_CORRECTION = 19
    SCHEMA_DEPENDENT = 20  # all_gnss_data | localization_data


class _MapLogDataField:
    """Field numbers of ``Message_MapLogData`` (message_map.proto:11-19)."""

    ROBOT_ODO_X = 1
    ROBOT_ODO_Y = 2
    ROBOT_ODO_W = 3
    LASER_BEAM_DIST = 4
    LASER_BEAM_ANGLE = 5
    RSSI = 6
    HEADER = 7


class _MapOdoField:
    """Field numbers of ``Message_MapOdo`` (message_map.proto:20-28)."""

    TIMESTAMP = 1
    ODO_X = 2
    ODO_Y = 3
    ODO_W = 4
    ODO_VX = 5
    ODO_VY = 6
    ODO_VW = 7


class _HeaderField:
    """Field numbers of ``Message_Header`` (message_header.proto:3-8)."""

    PUB_NSEC = 1
    DATA_NSEC = 2
    SEQ = 3
    FRAME_ID = 4


class _LocalizationField:
    """Field numbers of ``Message_Localization`` (message_localization.proto:5-39)."""

    HEADER = 1
    X = 2
    Y = 3
    ANGLE = 4
    CONFIDENCE = 5
    CORRECTION_ERRS = 6
    RELIABILITIES = 7
    IN_FORBIDDEN_AREA = 8
    UPDATE_REASON = 9
    LOC_STATE = 10
    SIMILARITY = 11
    LOC_METHOD = 12


class RawmapDecodeError(ValueError):
    """Raised when a byte stream is not a decodable protobuf message."""


class SchemaVariant(str, Enum):
    """Which of the two on-the-wire-compatible schemas a file follows.

    ``MAP_LOG`` and ``LOCAL_MAP_LOG`` are byte-identical except for field 20,
    so a file without field 20 can only be reported as ``AMBIGUOUS``.
    """

    LOCAL_MAP_LOG = "Message_LocalMapLog"
    MAP_LOG = "Message_MapLog"
    AMBIGUOUS = "ambiguous(no-field-20)"


# --- low-level wire reader ----------------------------------------------
def read_varint(buf: bytes, pos: int) -> Tuple[int, int]:
    """Read one base-128 varint.

    Args:
        buf: Byte buffer.
        pos: Index of the varint's first byte.

    Returns:
        ``(value, next_pos)`` — the unsigned integer value and the index just
        past the varint.

    Raises:
        RawmapDecodeError: Buffer ends mid-varint, or the varint exceeds
            ``_VARINT_MAX_BYTES`` (malformed / not protobuf).
    """
    result = 0
    shift = 0
    consumed = 0
    while True:
        if pos >= len(buf):
            raise RawmapDecodeError(f"truncated varint at offset {pos}")
        byte = buf[pos]
        pos += 1
        consumed += 1
        result |= (byte & _VARINT_PAYLOAD_MASK) << shift
        if not byte & _VARINT_CONTINUATION_BIT:
            return result, pos
        shift += _VARINT_SHIFT_PER_BYTE
        if consumed >= _VARINT_MAX_BYTES:
            raise RawmapDecodeError(f"varint longer than 10 bytes at offset {pos}")


def iter_fields(buf: bytes) -> Iterator[Tuple[int, int, object]]:
    """Iterate the top-level fields of one serialized protobuf message.

    Args:
        buf: Serialized message body (no outer length prefix).

    Yields:
        ``(field_number, wire_type, value)``.  ``value`` is an ``int`` for
        ``WIRE_VARINT`` and ``bytes`` for ``WIRE_FIXED64`` (8 B),
        ``WIRE_FIXED32`` (4 B) and ``WIRE_LENGTH_DELIMITED`` (payload).

    Raises:
        RawmapDecodeError: Unsupported wire type (groups), or a
            length/fixed-width field that runs past the end of ``buf``.
    """
    pos = 0
    end = len(buf)
    while pos < end:
        tag, pos = read_varint(buf, pos)
        field_number = tag >> _TAG_FIELD_NUMBER_SHIFT
        wire_type = tag & _TAG_WIRE_TYPE_MASK
        if wire_type == WIRE_VARINT:
            value, pos = read_varint(buf, pos)
            yield field_number, wire_type, value
        elif wire_type == WIRE_FIXED64:
            stop = pos + _FIXED64_SIZE
            if stop > end:
                raise RawmapDecodeError(f"truncated fixed64 at offset {pos}")
            yield field_number, wire_type, buf[pos:stop]
            pos = stop
        elif wire_type == WIRE_LENGTH_DELIMITED:
            length, pos = read_varint(buf, pos)
            stop = pos + length
            if stop > end:
                raise RawmapDecodeError(
                    f"length-delimited field {field_number} claims {length} B "
                    f"but only {end - pos} B remain at offset {pos}"
                )
            yield field_number, wire_type, buf[pos:stop]
            pos = stop
        elif wire_type == WIRE_FIXED32:
            stop = pos + _FIXED32_SIZE
            if stop > end:
                raise RawmapDecodeError(f"truncated fixed32 at offset {pos}")
            yield field_number, wire_type, buf[pos:stop]
            pos = stop
        else:
            raise RawmapDecodeError(
                f"unsupported wire type {wire_type} for field {field_number} "
                f"at offset {pos}"
            )


def unpack_doubles(payload: bytes) -> List[float]:
    """Decode a packed ``repeated double`` payload.

    Args:
        payload: Length-delimited field body; little-endian IEEE-754 binary64
            values back to back.

    Returns:
        The decoded values, in wire order.

    Raises:
        RawmapDecodeError: ``len(payload)`` is not a multiple of 8.
    """
    if len(payload) % _FIXED64_SIZE:
        raise RawmapDecodeError(
            f"packed double payload of {len(payload)} B is not a multiple of "
            f"{_FIXED64_SIZE}"
        )
    count = len(payload) // _FIXED64_SIZE
    return list(struct.unpack(f"<{count}d", payload))


def _as_double(raw: bytes) -> float:
    """Decode one little-endian binary64 from an 8-byte fixed64 field body."""
    return struct.unpack("<d", raw)[0]


def _as_float(raw: bytes) -> float:
    """Decode one little-endian binary32 from a 4-byte fixed32 field body."""
    return struct.unpack("<f", raw)[0]


def _collect_doubles(wire_type: int, value: object, sink: List[float]) -> None:
    """Append a ``repeated double`` field occurrence to ``sink``.

    Handles both encodings: packed (``WIRE_LENGTH_DELIMITED``, the proto3
    default) and unpacked (one ``WIRE_FIXED64`` per element).

    Args:
        wire_type: Wire type observed for the field.
        value: Field value as produced by :func:`iter_fields`.
        sink: List extended in place.
    """
    if wire_type == WIRE_LENGTH_DELIMITED:
        sink.extend(unpack_doubles(value))  # type: ignore[arg-type]
    elif wire_type == WIRE_FIXED64:
        sink.append(_as_double(value))  # type: ignore[arg-type]


# --- decoded records ----------------------------------------------------
@dataclass
class Header:
    """``Message_Header`` (message_header.proto:3-8).

    Attributes:
        pub_nsec: Publish timestamp [ns].
        data_nsec: Data acquisition timestamp [ns].
        seq: Sequence counter.
        frame_id: Source frame name (the laser name, in practice).
    """

    pub_nsec: int = 0
    data_nsec: int = 0
    seq: int = 0
    frame_id: str = ""

    @property
    def timestamp_sec(self) -> float:
        """Best available timestamp [s]: ``data_nsec`` if set, else ``pub_nsec``.

        Returns:
            Seconds on the robot's log clock.  Observed values (~4.5e3 s) are a
            monotonic/uptime clock, **not** a UNIX epoch.
        """
        nsec = self.data_nsec or self.pub_nsec
        return nsec / _NSEC_PER_SEC


@dataclass
class LaserPose:
    """Laser mounting pose carried by the ``MapLog`` header fields.

    Attributes:
        x: Mount x offset [m] (field 1).
        y: Mount y offset [m] (field 2).
        pos_z_raw: Raw field 3 value.  Per message_map.proto:44 this is the
            install **yaw** [rad], not a height.
        install_height: ``laser_install_height`` [m] (field 8).
        install_yaw_field11: ``laser_install_yaw`` [rad] (field 11).
        install_pitch: ``laser_install_pitch`` [rad] (field 12).
        install_roll: ``laser_install_roll`` [rad] (field 13).
    """

    x: float = 0.0
    y: float = 0.0
    pos_z_raw: float = 0.0
    install_height: float = 0.0
    install_yaw_field11: float = 0.0
    install_pitch: float = 0.0
    install_roll: float = 0.0

    @property
    def install_yaw_rad(self) -> float:
        """Resolved laser install yaw [rad].

        Prefers ``laser_install_yaw`` (field 11) when it is non-zero; otherwise
        falls back to ``laser_pos_z`` (field 3), which older writers use for the
        yaw per message_map.proto:44.

        Returns:
            Yaw angle in radians.
        """
        if self.install_yaw_field11:
            return self.install_yaw_field11
        return self.pos_z_raw


@dataclass
class ScanRecord:
    """One ``Message_MapLogData`` entry (message_map.proto:11-19).

    Attributes:
        odo_x: Robot odometry x at scan time [m].
        odo_y: Robot odometry y at scan time [m].
        odo_w: Robot odometry heading at scan time [rad].
        dist: Per-beam range [m]; a large sentinel (e.g. 9999.999) marks
            "no return".
        angle: Per-beam bearing in the laser frame [rad].
        rssi: Per-beam return intensity (unitless, sensor-defined).
        header: Timestamps for this scan.
    """

    odo_x: float = 0.0
    odo_y: float = 0.0
    odo_w: float = 0.0
    dist: List[float] = field(default_factory=list)
    angle: List[float] = field(default_factory=list)
    rssi: List[float] = field(default_factory=list)
    header: Header = field(default_factory=Header)

    @property
    def timestamp_sec(self) -> float:
        """Scan timestamp [s] on the log clock."""
        return self.header.timestamp_sec

    @property
    def beam_count(self) -> int:
        """Number of range samples in this scan."""
        return len(self.dist)


@dataclass
class OdoRecord:
    """One ``Message_MapOdo`` entry (message_map.proto:20-28).

    Attributes:
        timestamp: Log-clock time [s] (``double``).
        x: Odometry x [m] (``float``).
        y: Odometry y [m] (``float``).
        w: Odometry heading [rad] (``float``).
        vx: Body-frame x velocity [m/s].
        vy: Body-frame y velocity [m/s].
        vw: Yaw rate [rad/s].
    """

    timestamp: float = 0.0
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vw: float = 0.0


@dataclass
class LocalizationRecord:
    """One ``Message_Localization`` entry (message_localization.proto:5-39).

    Present only in the ``Message_LocalMapLog`` variant, as field 20.

    Attributes:
        header: Timestamps for this fix.
        x: Localized pose x in the map frame [m].
        y: Localized pose y in the map frame [m].
        angle: Localized heading [rad].
        confidence: Match confidence (unitless).
        correction_errs: Per-axis correction residuals as logged by Seer.
    """

    header: Header = field(default_factory=Header)
    x: float = 0.0
    y: float = 0.0
    angle: float = 0.0
    confidence: float = 0.0
    correction_errs: List[float] = field(default_factory=list)


@dataclass
class MapLog:
    """A fully decoded ``.rawmap`` file.

    One ``MapLog`` corresponds to exactly one lidar, because ``laser_name``
    (field 7) is a scalar ``string`` (message_map.proto:48).

    Attributes:
        source_path: Path the data came from (``"<bytes>"`` when decoded from
            an in-memory buffer).
        laser_name: Lidar identifier, e.g. ``"SickSafe-UDP"``.
        laser_pose: Mounting pose / install angles.
        laser_step_rad: Angular step between beams [rad] (field 4).
        laser_range_max_m: Maximum sensor range [m] (field 5).
        laser_type: ``lasertype`` enum value (field 16); 0 when unset.
        scans: Decoded ``log_data`` entries, in file order.
        odometry: Decoded ``odometer`` entries, in file order.
        localization: Decoded field-20 entries when the file is a
            ``Message_LocalMapLog``; empty otherwise.
        schema_variant: Result of :func:`classify_field20`.
        raw_field20: Undecoded field-20 payloads when the variant is
            ``MAP_LOG`` (``all_gnss_data``); the ``Message_AllGNSS`` schema is
            not among the recovered ``.proto`` files.
        unknown_fields: ``(field_number, wire_type)`` pairs seen at top level
            that this decoder does not model.
    """

    source_path: str = "<bytes>"
    laser_name: str = ""
    laser_pose: LaserPose = field(default_factory=LaserPose)
    laser_step_rad: float = 0.0
    laser_range_max_m: float = 0.0
    laser_type: int = 0
    scans: List[ScanRecord] = field(default_factory=list)
    odometry: List[OdoRecord] = field(default_factory=list)
    localization: List[LocalizationRecord] = field(default_factory=list)
    schema_variant: SchemaVariant = SchemaVariant.AMBIGUOUS
    raw_field20: List[bytes] = field(default_factory=list)
    unknown_fields: List[Tuple[int, int]] = field(default_factory=list)

    @property
    def scan_count(self) -> int:
        """Number of decoded laser scans."""
        return len(self.scans)

    def time_range_sec(self) -> Optional[Tuple[float, float]]:
        """Scan time span on the log clock.

        Returns:
            ``(first, last)`` in seconds, or ``None`` when there are no scans
            or no scan carries a timestamp.
        """
        stamps = [s.timestamp_sec for s in self.scans if s.timestamp_sec]
        if not stamps:
            return None
        return min(stamps), max(stamps)

    def odometry_bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """Axis-aligned bounding box of the odometry trajectory.

        Returns:
            ``(min_x, min_y, max_x, max_y)`` in metres, or ``None`` when the
            file carries no ``odometer`` entries.
        """
        if not self.odometry:
            return None
        xs = [o.x for o in self.odometry]
        ys = [o.y for o in self.odometry]
        return min(xs), min(ys), max(xs), max(ys)

    def beam_counts(self) -> List[int]:
        """Distinct per-scan beam counts, ascending (usually a single value)."""
        return sorted({s.beam_count for s in self.scans})


# --- schema discrimination ----------------------------------------------
_HEADER_WIRE_SHAPE = {
    _HeaderField.PUB_NSEC: WIRE_VARINT,
    _HeaderField.DATA_NSEC: WIRE_VARINT,
    _HeaderField.SEQ: WIRE_VARINT,
    _HeaderField.FRAME_ID: WIRE_LENGTH_DELIMITED,
}
_LOCALIZATION_REQUIRED_DOUBLES = (
    _LocalizationField.X,
    _LocalizationField.Y,
    _LocalizationField.ANGLE,
)


def _is_header_shaped(payload: bytes) -> bool:
    """Report whether ``payload`` parses as a ``Message_Header``.

    Args:
        payload: Candidate submessage body.

    Returns:
        ``True`` when every field is one of ``Message_Header``'s four fields
        with the matching wire type.  An empty payload counts as header-shaped
        (all-default header).
    """
    try:
        for field_number, wire_type, _ in iter_fields(payload):
            if _HEADER_WIRE_SHAPE.get(field_number) != wire_type:
                return False
    except RawmapDecodeError:
        return False
    return True


def _is_localization_shaped(payload: bytes) -> bool:
    """Report whether ``payload`` parses as a ``Message_Localization``.

    The ``Message_AllGNSS`` schema is not among the recovered ``.proto`` files
    (checked with ``ls References/seer/slam_mapping/proto/`` — only header,
    imu, laser, localization, map and odometer are present), so field 20 is
    discriminated structurally rather than by a positive GNSS match.

    Args:
        payload: Candidate field-20 submessage body.

    Returns:
        ``True`` when field 1, if present, is a header-shaped submessage and
        fields 2/3/4 (x, y, angle) are all present as fixed64 doubles.
    """
    try:
        seen = {}
        for field_number, wire_type, value in iter_fields(payload):
            seen[field_number] = wire_type
            if field_number == _LocalizationField.HEADER:
                if wire_type != WIRE_LENGTH_DELIMITED:
                    return False
                if not _is_header_shaped(value):  # type: ignore[arg-type]
                    return False
    except RawmapDecodeError:
        return False
    return all(seen.get(n) == WIRE_FIXED64 for n in _LOCALIZATION_REQUIRED_DOUBLES)


def classify_field20(payloads: Sequence[bytes]) -> SchemaVariant:
    """Decide which ``MapLog`` schema a file follows, from its field-20 bodies.

    Args:
        payloads: Every field-20 length-delimited payload found at top level,
            in file order.

    Returns:
        ``SchemaVariant.AMBIGUOUS`` when ``payloads`` is empty (the two schemas
        are byte-identical without field 20), ``SchemaVariant.LOCAL_MAP_LOG``
        when every payload is ``Message_Localization``-shaped, else
        ``SchemaVariant.MAP_LOG`` (field 20 = ``all_gnss_data``).
    """
    if not payloads:
        return SchemaVariant.AMBIGUOUS
    if all(_is_localization_shaped(p) for p in payloads):
        return SchemaVariant.LOCAL_MAP_LOG
    return SchemaVariant.MAP_LOG


# --- submessage decoders ------------------------------------------------
def _decode_header(payload: bytes) -> Header:
    """Decode a ``Message_Header`` submessage body into a :class:`Header`."""
    header = Header()
    for field_number, wire_type, value in iter_fields(payload):
        if field_number == _HeaderField.PUB_NSEC and wire_type == WIRE_VARINT:
            header.pub_nsec = value  # type: ignore[assignment]
        elif field_number == _HeaderField.DATA_NSEC and wire_type == WIRE_VARINT:
            header.data_nsec = value  # type: ignore[assignment]
        elif field_number == _HeaderField.SEQ and wire_type == WIRE_VARINT:
            header.seq = value  # type: ignore[assignment]
        elif (
            field_number == _HeaderField.FRAME_ID and wire_type == WIRE_LENGTH_DELIMITED
        ):
            header.frame_id = value.decode("utf-8", "replace")  # type: ignore
    return header


def _decode_scan(payload: bytes) -> ScanRecord:
    """Decode a ``Message_MapLogData`` submessage body into a :class:`ScanRecord`."""
    scan = ScanRecord()
    for field_number, wire_type, value in iter_fields(payload):
        if field_number == _MapLogDataField.ROBOT_ODO_X and wire_type == WIRE_FIXED64:
            scan.odo_x = _as_double(value)  # type: ignore[arg-type]
        elif field_number == _MapLogDataField.ROBOT_ODO_Y and wire_type == WIRE_FIXED64:
            scan.odo_y = _as_double(value)  # type: ignore[arg-type]
        elif field_number == _MapLogDataField.ROBOT_ODO_W and wire_type == WIRE_FIXED64:
            scan.odo_w = _as_double(value)  # type: ignore[arg-type]
        elif field_number == _MapLogDataField.LASER_BEAM_DIST:
            _collect_doubles(wire_type, value, scan.dist)
        elif field_number == _MapLogDataField.LASER_BEAM_ANGLE:
            _collect_doubles(wire_type, value, scan.angle)
        elif field_number == _MapLogDataField.RSSI:
            _collect_doubles(wire_type, value, scan.rssi)
        elif (
            field_number == _MapLogDataField.HEADER
            and wire_type == WIRE_LENGTH_DELIMITED
        ):
            scan.header = _decode_header(value)  # type: ignore[arg-type]
    return scan


def _decode_odo(payload: bytes) -> OdoRecord:
    """Decode a ``Message_MapOdo`` submessage body into an :class:`OdoRecord`.

    ``timestamp`` is a ``double`` (fixed64) while ``odo_*`` are ``float``
    (fixed32) — message_map.proto:21-27.
    """
    odo = OdoRecord()
    for field_number, wire_type, value in iter_fields(payload):
        if field_number == _MapOdoField.TIMESTAMP and wire_type == WIRE_FIXED64:
            odo.timestamp = _as_double(value)  # type: ignore[arg-type]
        elif wire_type == WIRE_FIXED32:
            if field_number == _MapOdoField.ODO_X:
                odo.x = _as_float(value)  # type: ignore[arg-type]
            elif field_number == _MapOdoField.ODO_Y:
                odo.y = _as_float(value)  # type: ignore[arg-type]
            elif field_number == _MapOdoField.ODO_W:
                odo.w = _as_float(value)  # type: ignore[arg-type]
            elif field_number == _MapOdoField.ODO_VX:
                odo.vx = _as_float(value)  # type: ignore[arg-type]
            elif field_number == _MapOdoField.ODO_VY:
                odo.vy = _as_float(value)  # type: ignore[arg-type]
            elif field_number == _MapOdoField.ODO_VW:
                odo.vw = _as_float(value)  # type: ignore[arg-type]
    return odo


def _decode_localization(payload: bytes) -> LocalizationRecord:
    """Decode a ``Message_Localization`` submessage body."""
    loc = LocalizationRecord()
    for field_number, wire_type, value in iter_fields(payload):
        if (
            field_number == _LocalizationField.HEADER
            and wire_type == WIRE_LENGTH_DELIMITED
        ):
            loc.header = _decode_header(value)  # type: ignore[arg-type]
        elif field_number == _LocalizationField.X and wire_type == WIRE_FIXED64:
            loc.x = _as_double(value)  # type: ignore[arg-type]
        elif field_number == _LocalizationField.Y and wire_type == WIRE_FIXED64:
            loc.y = _as_double(value)  # type: ignore[arg-type]
        elif field_number == _LocalizationField.ANGLE and wire_type == WIRE_FIXED64:
            loc.angle = _as_double(value)  # type: ignore[arg-type]
        elif (
            field_number == _LocalizationField.CONFIDENCE and wire_type == WIRE_FIXED64
        ):
            loc.confidence = _as_double(value)  # type: ignore[arg-type]
        elif field_number == _LocalizationField.CORRECTION_ERRS:
            _collect_doubles(wire_type, value, loc.correction_errs)
    return loc


# --- top-level entry points ---------------------------------------------
_MODELLED_TOP_LEVEL_FIELDS = frozenset(
    {
        _MapLogField.LASER_POS_X,
        _MapLogField.LASER_POS_Y,
        _MapLogField.LASER_POS_Z,
        _MapLogField.LASER_STEP,
        _MapLogField.LASER_RANGE_MAX,
        _MapLogField.LOG_DATA,
        _MapLogField.LASER_NAME,
        _MapLogField.LASER_INSTALL_HEIGHT,
        _MapLogField.ODOMETER,
        _MapLogField.LASER_INSTALL_YAW,
        _MapLogField.LASER_INSTALL_PITCH,
        _MapLogField.LASER_INSTALL_ROLL,
        _MapLogField.LASER_TYPE,
        _MapLogField.SCHEMA_DEPENDENT,
    }
)


def decode_maplog_bytes(data: bytes, source_path: str = "<bytes>") -> MapLog:
    """Decode a serialized ``Message_MapLog`` / ``Message_LocalMapLog`` body.

    Args:
        data: The complete file contents; a ``.rawmap`` is a single message
            with no framing, length prefix or magic bytes.
        source_path: Label recorded in :attr:`MapLog.source_path`.

    Returns:
        The decoded :class:`MapLog`.

    Raises:
        RawmapDecodeError: The buffer is not a well-formed protobuf message.
    """
    log = MapLog(source_path=source_path)
    field20_payloads: List[bytes] = []
    seen_unknown = set()

    for field_number, wire_type, value in iter_fields(data):
        if field_number == _MapLogField.LASER_POS_X and wire_type == WIRE_FIXED64:
            log.laser_pose.x = _as_double(value)  # type: ignore[arg-type]
        elif field_number == _MapLogField.LASER_POS_Y and wire_type == WIRE_FIXED64:
            log.laser_pose.y = _as_double(value)  # type: ignore[arg-type]
        elif field_number == _MapLogField.LASER_POS_Z and wire_type == WIRE_FIXED64:
            log.laser_pose.pos_z_raw = _as_double(value)  # type: ignore[arg-type]
        elif field_number == _MapLogField.LASER_STEP and wire_type == WIRE_FIXED64:
            log.laser_step_rad = _as_double(value)  # type: ignore[arg-type]
        elif field_number == _MapLogField.LASER_RANGE_MAX and wire_type == WIRE_FIXED64:
            log.laser_range_max_m = _as_double(value)  # type: ignore[arg-type]
        elif (
            field_number == _MapLogField.LOG_DATA and wire_type == WIRE_LENGTH_DELIMITED
        ):
            log.scans.append(_decode_scan(value))  # type: ignore[arg-type]
        elif (
            field_number == _MapLogField.LASER_NAME
            and wire_type == WIRE_LENGTH_DELIMITED
        ):
            log.laser_name = value.decode("utf-8", "replace")  # type: ignore
        elif (
            field_number == _MapLogField.LASER_INSTALL_HEIGHT
            and wire_type == WIRE_FIXED64
        ):
            log.laser_pose.install_height = _as_double(value)  # type: ignore[arg-type]
        elif (
            field_number == _MapLogField.ODOMETER and wire_type == WIRE_LENGTH_DELIMITED
        ):
            log.odometry.append(_decode_odo(value))  # type: ignore[arg-type]
        elif (
            field_number == _MapLogField.LASER_INSTALL_YAW and wire_type == WIRE_FIXED64
        ):
            log.laser_pose.install_yaw_field11 = _as_double(value)  # type: ignore
        elif (
            field_number == _MapLogField.LASER_INSTALL_PITCH
            and wire_type == WIRE_FIXED64
        ):
            log.laser_pose.install_pitch = _as_double(value)  # type: ignore[arg-type]
        elif (
            field_number == _MapLogField.LASER_INSTALL_ROLL
            and wire_type == WIRE_FIXED64
        ):
            log.laser_pose.install_roll = _as_double(value)  # type: ignore[arg-type]
        elif field_number == _MapLogField.LASER_TYPE and wire_type == WIRE_VARINT:
            log.laser_type = value  # type: ignore[assignment]
        elif (
            field_number == _MapLogField.SCHEMA_DEPENDENT
            and wire_type == WIRE_LENGTH_DELIMITED
        ):
            field20_payloads.append(value)  # type: ignore[arg-type]
        elif field_number not in _MODELLED_TOP_LEVEL_FIELDS:
            key = (field_number, wire_type)
            if key not in seen_unknown:
                seen_unknown.add(key)
                log.unknown_fields.append(key)

    log.schema_variant = classify_field20(field20_payloads)
    if log.schema_variant is SchemaVariant.LOCAL_MAP_LOG:
        log.localization = [_decode_localization(p) for p in field20_payloads]
    else:
        log.raw_field20 = field20_payloads
    return log


def decode_maplog(path: str) -> MapLog:
    """Decode a ``.rawmap`` file from disk.

    Args:
        path: Filesystem path to the ``.rawmap`` file.

    Returns:
        The decoded :class:`MapLog`, with :attr:`MapLog.source_path` set to
        ``path``.

    Raises:
        OSError: The file cannot be read.
        RawmapDecodeError: The contents are not a well-formed protobuf message.
    """
    with open(path, "rb") as handle:
        data = handle.read()
    return decode_maplog_bytes(data, source_path=path)
