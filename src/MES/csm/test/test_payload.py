"""What a robot is carrying — in the record, and on the map.

THE RECORD WAS FALSE FOR THE WHOLE JOURNEY. `move_material` was called once, on
DONE, so a roll sat in the records at its source while a robot drove it across
the plant, and then teleported. "Where is roll X" had no true answer for
minutes at a time, and the movement history recorded a jump that never
happened. That is what these tests are about; the drawing is the visible part.
"""

from csm.material import Face, MaterialAttribute
from csm.records import InMemoryRecords


# ------------------------------------------- the vehicle knows it is loaded

def test_the_robot_reports_whether_it_is_carrying_something():
    import inspect

    from csm.adapters.sim_acs import SimAcs, SimRobot

    assert "_loaded = True" in inspect.getsource(SimRobot._begin_delivery), \
        "nothing marks the robot loaded when the source dwell finishes"
    assert "_loaded = False" in inspect.getsource(SimRobot._finish), \
        "the robot never puts anything down"
    assert '"loaded"' in inspect.getsource(SimAcs.fleet_status), \
        "the CSM cannot see whether a robot is carrying anything"


def test_the_robot_does_not_keep_its_own_copy_of_the_material():
    """A second copy is a second copy that drifts. The vehicle layer observes
    only that something is on the deck; WHAT it is belongs to the record, and
    the two are joined by job id."""
    from csm.adapters.sim_acs import SimRobot

    fields = set(vars(object.__new__(SimRobot)))
    assert "material_ref" not in fields
    assert "_material" not in fields


# --------------------------------------- the record follows it in transit

def test_the_store_moves_material_onto_the_carrier():
    import inspect

    from csm.runtime.job_store import JobStore

    src = inspect.getsource(JobStore)
    assert "_follow_the_material" in src
    assert "_carrier_of" in src
    step = inspect.getsource(JobStore.step_all)
    assert "_follow_the_material" in step, \
        "the material is only moved on completion, so the record is false " \
        "for the whole journey"


def test_it_writes_one_move_not_one_per_tick():
    """Guarded on the location actually changing. The tracker steps four times
    a second; a move per tick would be all I/O and no information."""
    import inspect

    from csm.runtime.job_store import JobStore

    src = inspect.getsource(JobStore._follow_the_material)
    assert "known.location == carrier" in src


# ------------------------------ and completion hands identity to the rack

def test_delivery_writes_the_identity_into_a_rack_destination():
    """CCS manual §4.6.6. This is the row the audit called hollow: the store
    could do it and nothing called it."""
    import inspect

    from csm.runtime.job_store import JobStore

    assert "_hand_identity_to" in inspect.getsource(JobStore._on_change)
    src = inspect.getsource(JobStore._hand_identity_to)
    assert "material_attribute=known.attribute" in src
    assert "bobbin_type=known.drum_type" in src


def test_a_machine_port_is_not_given_an_identity():
    """A machine port is not modelled as a rack and deliberately so — the ACS
    team described their own system the same way: carrier identity vanishes at
    an equipment station and persists at the buffer."""
    import inspect

    from csm.runtime.job_store import JobStore

    src = inspect.getsource(JobStore._hand_identity_to)
    assert "if not self.records.slots(job.to_station)" in src


# ----------------------------------------------- what the map is given

def test_the_payload_carries_size_face_and_kind():
    from csm.ui.state import _DRUM_SIZES, _payload

    records = InMemoryRecords()
    m = records.register_material(kind="roll", at=0.0, drum_type=430,
                                  attribute=MaterialAttribute.BRIGHT_CW)

    class Job:
        job_id, material_ref = "job_0001", m.material_ref

    class Record:
        job = Job()

    class Store:
        active = [Record()]
        def __init__(self):
            self.records = records

    got = _payload(Store(), {"loaded": True, "job_id": "job_0001"})

    assert got["kind"] == "roll"
    assert got["drum_type"] == 430
    assert got["size"] == _DRUM_SIZES[430]
    assert got["face"] == Face.BRIGHT.value


def test_an_empty_robot_carries_nothing():
    from csm.ui.state import _payload

    assert _payload(None, {"loaded": False}) is None


def test_a_robot_loaded_with_something_unknown_still_draws():
    """"Loaded with something we cannot name" is a real state and worth
    seeing. Drawing nothing would report an empty robot, which is worse than
    admitting ignorance."""
    from csm.ui.state import _payload

    got = _payload(None, {"loaded": True, "job_id": None})

    assert got == {"kind": "roll"}


def test_the_four_drum_types_have_sizes():
    from csm.ui.state import _DRUM_SIZES

    assert sorted(_DRUM_SIZES) == [360, 430, 500, 580]
    sizes = [_DRUM_SIZES[d] for d in sorted(_DRUM_SIZES)]
    assert sizes == sorted(sizes), "a bigger drum must draw bigger"


def test_the_map_draws_it_inside_the_robots_own_transform():
    """So it turns with the body — a crab across a lane reads as one robot
    carrying something sideways, not two unrelated shapes."""
    from csm.ui.page import PAGE

    assert "function carried(r)" in PAGE
    at = PAGE.index("${carried(r)}")
    assert PAGE.rindex("<g transform=", 0, at) < at < PAGE.index("</g>", at)


def test_an_empty_bobbin_is_hollow_and_a_roll_is_filled():
    from csm.ui.page import PAGE

    assert "L.kind === 'bobbin' ? ' hollow'" in PAGE
    assert ".load.hollow { fill:none; }" in PAGE


# ------------------------- the face is the hard half, rotation the soft half

def test_the_payload_reports_rotation_and_the_customers_1_to_4():
    from csm.ui.state import _payload

    records = InMemoryRecords()
    m = records.register_material(kind="roll", at=0.0, drum_type=430,
                                  attribute=MaterialAttribute.DARK_CCW)

    class Job:
        job_id, material_ref = "job_0001", m.material_ref

    class Record:
        job = Job()

    class Store:
        active = [Record()]
        def __init__(self):
            self.records = records

    got = _payload(Store(), {"loaded": True, "job_id": "job_0001"})

    assert got["face"] == "dark"
    assert got["rotation"] == "anticlockwise"
    assert got["attribute"] == 4, "the customer's own value, 4 = 暗面逆时针"


def test_the_map_colours_by_FACE_because_the_face_cannot_be_fixed():
    """CCS manual §1.3: to feed a machine the material must have the SAME
    bright/dark face; rotation direction NEED NOT match, because a 180° turn
    of the pallet swaps it and that turn is a first-class AGV task. So the
    face is the hard constraint and gets the colour."""
    from csm.ui.page import PAGE

    assert "L.face === 'bright' ? 'bright'" in PAGE
    assert ".load.bright" in PAGE and ".load.dark" in PAGE


def test_rotation_is_drawn_as_a_hand_not_a_colour():
    from csm.ui.page import PAGE

    assert "class=\"spin\"" in PAGE
    assert "L.rotation === 'clockwise'" in PAGE


def test_unknown_rotation_draws_no_hand():
    """Unknown must not look like a value. An empty core has no winding at
    all, and a roll we cannot describe has none we know of."""
    from csm.ui.page import PAGE

    at = PAGE.index("L.rotation === 'clockwise'")
    guard = PAGE[at:at + 120]
    assert "anticlockwise" in guard, \
        "the hand must be drawn only for the two known values"


def test_the_legend_says_what_the_face_MEANS():
    """"bright / dark" on its own is a colour key. It has to say that the
    face is what must match, or the reader learns nothing from it."""
    from csm.ui.page import PAGE

    assert "must match" in PAGE
    assert "亮面" in PAGE and "暗面" in PAGE
    assert "180" in PAGE, "the legend should say rotation is fixable"
