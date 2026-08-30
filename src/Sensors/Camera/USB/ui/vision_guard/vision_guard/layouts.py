# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""Grid layout presets for the CCTV viewer.

Pure, Qt-free logic so it can be unit tested without a display server.
Each preset maps a label like "2x3" to a (rows, cols) tuple.
"""

from collections import OrderedDict

# Ordered so the combobox lists them small-to-large. "RxC" == rows x cols.
LAYOUT_PRESETS = OrderedDict(
    [
        ("1x1", (1, 1)),
        ("1x2", (1, 2)),
        ("1x3", (1, 3)),
        ("2x2", (2, 2)),
        ("2x3", (2, 3)),
        ("3x2", (3, 2)),
        ("3x3", (3, 3)),
    ]
)


def parse_layout(label):
    """Return (rows, cols) for a preset label or a raw "RxC" string.

    :param label: Preset key (e.g. "2x3"). Also accepts any "<rows>x<cols>".
    :returns: (rows, cols) tuple of positive ints.
    :raises ValueError: if the label is not a valid RxC spec.
    """
    if label in LAYOUT_PRESETS:
        return LAYOUT_PRESETS[label]
    parts = label.lower().split("x")
    if len(parts) != 2:
        raise ValueError(f"invalid layout '{label}', expected 'RxC'")
    rows, cols = int(parts[0]), int(parts[1])
    if rows < 1 or cols < 1:
        raise ValueError(f"layout '{label}' must have positive rows and cols")
    return (rows, cols)


def cell_capacity(label):
    """Return how many camera cells a layout holds (rows * cols)."""
    rows, cols = parse_layout(label)
    return rows * cols


def smallest_layout_for(camera_count):
    """Return the smallest preset label that fits ``camera_count`` cameras.

    Falls back to the largest preset if no preset is big enough.
    """
    if camera_count <= 0:
        return "1x1"
    for label in LAYOUT_PRESETS:
        if cell_capacity(label) >= camera_count:
            return label
    return next(reversed(LAYOUT_PRESETS))
