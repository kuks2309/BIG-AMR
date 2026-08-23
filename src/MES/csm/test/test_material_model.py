"""What a roll is, as far as the routing rules care.

Every value here comes from two independent sources that agree — the CCS manual
§4.6.5 and the rack PLC variable table of 2026-08-19. Nothing is invented, so
each test names where its number comes from. See
`docs/adr/2026-08-20-material-attribute-and-pallet-model.md`.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.material import (KNOWN_DRUM_TYPES, SINGLE_BOBBIN_FROM,   # noqa: E402
                          TRAY_ERROR_FROM, TRAY_RESET, Face,
                          MaterialAttribute, MaterialState, Rotation,
                          SideStatus, TrayCondition, TrayStatus,
                          attribute_matches, classify_tray, is_dual_pallet,
                          pallet_capacity)
from csm.records import Material                                   # noqa: E402


# -- the four attributes ----------------------------------------------------

def test_the_four_attributes_are_the_customers_numbers():
    """`1-亮面顺时针；2-亮面逆时针；3-暗面顺时针；4-暗面逆时针` — §4.6.5."""
    assert MaterialAttribute.BRIGHT_CW.value == 1
    assert MaterialAttribute.BRIGHT_CCW.value == 2
    assert MaterialAttribute.DARK_CW.value == 3
    assert MaterialAttribute.DARK_CCW.value == 4


def test_each_attribute_decodes_to_a_face_and_a_rotation():
    assert MaterialAttribute.BRIGHT_CW.face is Face.BRIGHT
    assert MaterialAttribute.BRIGHT_CW.rotation is Rotation.CW
    assert MaterialAttribute.DARK_CCW.face is Face.DARK
    assert MaterialAttribute.DARK_CCW.rotation is Rotation.CCW


def test_rotating_a_pallet_keeps_the_face_and_flips_the_winding():
    """Turning the pallet cannot turn the foil over."""
    for attr in MaterialAttribute:
        turned = attr.rotated()
        assert turned.face is attr.face, "a 180 turn must not change the face"
        assert turned.rotation is not attr.rotation
        assert turned.rotated() is attr, "turning twice returns the original"


# -- the matching rule (§3.6) ----------------------------------------------

def test_the_face_must_match():
    assert not MaterialAttribute.BRIGHT_CW.matches(MaterialAttribute.DARK_CW)
    assert not MaterialAttribute.DARK_CCW.matches(MaterialAttribute.BRIGHT_CCW)


def test_the_winding_need_not_match_because_the_pallet_can_be_turned():
    """§3.6's escape hatch, and the reason rotate-then-feed is a task type."""
    assert MaterialAttribute.BRIGHT_CW.matches(MaterialAttribute.BRIGHT_CCW)
    assert MaterialAttribute.DARK_CCW.matches(MaterialAttribute.DARK_CW)


def test_a_non_rotatable_type_must_match_exactly():
    """§4.6.11 — some material types are configured non-rotatable."""
    cw, ccw = MaterialAttribute.BRIGHT_CW, MaterialAttribute.BRIGHT_CCW
    assert cw.matches(ccw, rotatable=True)
    assert not cw.matches(ccw, rotatable=False)
    assert cw.matches(cw, rotatable=False)


def test_unknown_never_silently_passes_a_match():
    """UNKNOWN IS NOT A WILDCARD.

    Material nobody characterised must not be fed to a machine that asked for a
    face. A deferred call is cheap; a machine loaded wrong-side-out is not.
    """
    assert not attribute_matches(None, MaterialAttribute.BRIGHT_CW)
    assert not attribute_matches(MaterialAttribute.BRIGHT_CW, None)
    assert not attribute_matches(None, None)
    assert not MaterialAttribute.BRIGHT_CW.matches(None)


def test_attribute_matches_agrees_with_the_method_when_both_are_known():
    assert attribute_matches(MaterialAttribute.BRIGHT_CW,
                             MaterialAttribute.BRIGHT_CCW)
    assert not attribute_matches(MaterialAttribute.BRIGHT_CW,
                                 MaterialAttribute.BRIGHT_CCW,
                                 rotatable=False)


# -- pallet capacity --------------------------------------------------------

def test_capacity_splits_at_exactly_500():
    """`>=500 single-bobbin pallet, <500 dual-bobbin pallet` — Rack_To_PCS[8].

    The boundary is the whole rule, so it is tested AT the boundary rather than
    on either side of it.
    """
    assert SINGLE_BOBBIN_FROM == 500
    assert pallet_capacity(499) == 2
    assert pallet_capacity(500) == 1
    assert pallet_capacity(501) == 1


def test_the_documented_drum_types_land_where_the_manual_says():
    assert [pallet_capacity(d) for d in KNOWN_DRUM_TYPES] == [2, 2, 1, 1]


def test_an_undocumented_drum_type_still_gets_a_capacity():
    """The field is an INT, not an enum — their list may grow."""
    assert pallet_capacity(640) == 1
    assert pallet_capacity(200) == 2


def test_unknown_drum_type_gives_no_capacity_and_is_not_dual():
    assert pallet_capacity(None) is None
    assert is_dual_pallet(None) is False, "unknown must not read as dual"


# -- tray status, including the two out-of-band values ---------------------

def test_the_six_documented_tray_states():
    for value, expected in enumerate([TrayStatus.NONE,
                                      TrayStatus.EMPTY_PALLET,
                                      TrayStatus.SINGLE_EMPTY_BOBBIN,
                                      TrayStatus.DOUBLE_EMPTY_BOBBIN,
                                      TrayStatus.SINGLE_MATERIAL,
                                      TrayStatus.DOUBLE_MATERIAL]):
        status, condition = classify_tray(value)
        assert status is expected
        assert condition is TrayCondition.NORMAL


def test_a_rack_error_is_not_read_as_a_tray_state():
    """`>900 means the rack is in error` — the failure a range check would hide.

    950 accepted as a tray state would mean a broken rack reading as a rack
    holding something.
    """
    assert TRAY_ERROR_FROM == 900
    for value in (900, 950, 9999):
        status, condition = classify_tray(value)
        assert status is None
        assert condition is TrayCondition.ERROR


def test_a_reset_is_its_own_thing():
    assert TRAY_RESET == 800
    status, condition = classify_tray(800)
    assert status is None
    assert condition is TrayCondition.RESET


def test_an_undocumented_in_range_value_is_unknown_not_an_error():
    status, condition = classify_tray(6)
    assert status is None
    assert condition is TrayCondition.NORMAL


def test_classify_never_raises_on_anything_the_wire_can_carry():
    for value in (None, 0, 5, 6, 799, 800, 801, 899, 900, 100_000):
        classify_tray(value)            # must not raise


# -- what the automatic flow will and will not move -------------------------

def test_only_a_full_double_pallet_moves_automatically():
    """§2.2 and §6: a dual pallet holding ONE roll needs a person."""
    assert TrayStatus.DOUBLE_MATERIAL.auto_transportable
    assert not TrayStatus.SINGLE_MATERIAL.auto_transportable


def test_an_empty_pallet_is_outside_the_automatic_flow_entirely():
    """*"中控系统自动流程业务逻辑不含空托盘的流转"* — stated outright."""
    assert not TrayStatus.EMPTY_PALLET.auto_transportable
    assert not TrayStatus.NONE.auto_transportable


def test_only_a_double_empty_bobbin_pallet_can_go_back():
    """§1.2.2 — the exit pallet must carry DOUBLE bobbins.

    This is §6 item 6: one of the things a human is told to go and fix daily.
    """
    assert TrayStatus.DOUBLE_EMPTY_BOBBIN.returnable
    assert not TrayStatus.SINGLE_EMPTY_BOBBIN.returnable
    assert not TrayStatus.DOUBLE_MATERIAL.returnable


def test_a_double_empty_bobbin_pallet_is_transportable_and_returnable():
    """It is the one state that is both, which is what makes return flow work."""
    assert TrayStatus.DOUBLE_EMPTY_BOBBIN.auto_transportable
    assert TrayStatus.DOUBLE_EMPTY_BOBBIN.returnable


# -- the side and state vocabularies ---------------------------------------

def test_side_and_state_values_are_the_customers():
    assert (SideStatus.NO_BOBBIN.value, SideStatus.EMPTY_BOBBIN.value,
            SideStatus.MATERIAL.value) == (1, 2, 3)
    assert (MaterialState.EMPTY.value, MaterialState.NG.value,
            MaterialState.OK.value) == (0, 1, 2)


# -- the record ------------------------------------------------------------

def test_material_carries_the_new_fields_and_defaults_them_to_unknown():
    m = Material(material_ref="R1", lot_id="20260820120000000")
    assert m.attribute is None
    assert m.drum_type is None
    assert m.material_type is None
    assert m.state is None


def test_material_holds_what_it_is_given():
    m = Material(material_ref="R1", lot_id="20260820120000000",
                 attribute=MaterialAttribute.DARK_CW, drum_type=430,
                 material_type=302, state=MaterialState.OK)
    assert m.attribute.face is Face.DARK
    assert pallet_capacity(m.drum_type) == 2
    assert m.material_type == 302, "carried, never interpreted"


# -- persistence -----------------------------------------------------------
#
# A dataclass field that the store does not know about is dropped on save and
# comes back None on load, with nothing reporting it. That is the quiet data
# loss `records_sqlite` exists to prevent, so the round trip is tested rather
# than assumed.

def test_the_new_fields_survive_a_restart(tmp_path):
    from csm.records_sqlite import SqliteRecords

    path = str(tmp_path / "records.db")
    store = SqliteRecords(path)
    registered = store.register_material(
        kind="roll", attribute=MaterialAttribute.DARK_CCW,
        drum_type=580, material_type=302, state=MaterialState.OK)

    reopened = SqliteRecords(path)
    material = reopened.material(registered.material_ref)
    assert material.attribute is MaterialAttribute.DARK_CCW
    assert material.drum_type == 580
    assert material.material_type == 302
    assert material.state is MaterialState.OK
    assert pallet_capacity(material.drum_type) == 1


def test_a_database_from_before_these_fields_still_opens(tmp_path):
    """`CREATE TABLE IF NOT EXISTS` never alters an existing table.

    Without the additive migration an older database keeps its old shape, every
    new column is dropped on save, and the store reports nothing wrong.
    """
    import sqlite3

    from csm.records_sqlite import SqliteRecords

    path = str(tmp_path / "old.db")
    old = sqlite3.connect(path)
    old.executescript("""
        CREATE TABLE materials (
            material_ref TEXT PRIMARY KEY,
            lot_id       TEXT NOT NULL,
            kind         TEXT,
            created_at   REAL,
            location     TEXT,
            ready_at     REAL,
            expires_at   REAL
        );
        INSERT INTO materials (material_ref, lot_id, kind)
        VALUES ('R-old', '20260101000000000', 'roll');
    """)
    old.commit()
    old.close()

    store = SqliteRecords(path)                 # must migrate, not fail

    columns = {r[1] for r in store.db.execute("PRAGMA table_info(materials)")}
    assert {"attribute", "drum_type", "material_type", "state"} <= columns

    # The old row survives, with the new fields honestly unknown.
    material = store.material("R-old")
    assert material is not None, "the pre-existing row must still load"
    assert material.attribute is None
    assert material.drum_type is None

    # And the migrated database can now hold them.
    fresh = store.register_material(kind="roll",
                                    attribute=MaterialAttribute.BRIGHT_CW,
                                    drum_type=360)
    again = SqliteRecords(path)
    assert again.material(fresh.material_ref).attribute \
        is MaterialAttribute.BRIGHT_CW


def test_the_migration_runs_twice_without_complaining(tmp_path):
    """Idempotent — every start runs it."""
    from csm.records_sqlite import SqliteRecords

    path = str(tmp_path / "twice.db")
    SqliteRecords(path)
    SqliteRecords(path)                          # must not raise
