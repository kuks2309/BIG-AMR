"""The docking controller ported from the docking project.

Two things these tests exist to protect, both of which that project got wrong
first and fixed only after hardware testing:

  * driving before the steering has settled, under servo lag
  * hunting for a marker that has been lost, instead of stopping
"""

import math

import pytest

from csm.adapters import docking
from csm.adapters.docking import DockController, Observation, Result


def obs(range_m, cte=0.0, axis=math.pi / 2, stamp=0.0):
    return Observation(range_m, cte, axis, stamp)


def step(c, range_m, now, cte=0.0, steer=(0.0, 0.0)):
    """Step with a FRESH observation.

    Stamping every observation at `now` matters: the controller treats anything
    older than OBS_STALE as a lost marker, so a test that reuses stamp=0 while
    advancing the clock is testing the staleness guard by accident.
    """
    return c.step(obs(range_m, cte, stamp=now), list(steer), now)


# ------------------------------------------------------------------- settle

def test_settle_commands_steering_but_no_speed():
    c = DockController()
    speed, steer, status = c.step(obs(1.5), steer_actual=[0.0, 0.0], now=0.0)
    assert speed == 0.0, "must not drive before the wheels have settled"
    assert status == Result.RUNNING
    assert c.phase == "settle"


def test_settle_ends_once_the_wheels_have_arrived():
    c = DockController()
    _, steer, _ = step(c, 1.5, 0.0)
    step(c, 1.5, 0.1, steer=(steer, steer))
    assert c.phase == "run"


def test_settle_times_out_so_a_stuck_servo_cannot_hang_the_dock():
    c = DockController()
    step(c, 1.5, 0.0)
    step(c, 1.5, docking.SETTLE_TIMEOUT + 0.1)
    assert c.phase == "run"


def test_driving_only_starts_after_settling():
    """The whole point of settle-then-drive: no motion until the wheels agree."""
    c = DockController()
    for t in range(10):
        speed, steer, _ = step(c, 1.5, t * 0.1)
        assert speed == 0.0


# -------------------------------------------------------------------- guards

def test_a_lost_marker_stops_the_robot_and_never_hunts():
    c = DockController()
    speed, _, status = c.step(None, [0.0, 0.0], 0.0)
    assert speed == 0.0
    assert status == Result.FAILED
    assert "lost" in c.reason


def test_a_stale_observation_counts_as_lost():
    c = DockController()
    speed, _, status = c.step(obs(1.5, stamp=0.0), [0.0, 0.0],
                              now=docking.OBS_STALE + 0.1)
    assert status == Result.FAILED
    assert speed == 0.0


def test_timeout_fails_the_dock():
    c = DockController()
    _, _, status = c.step(obs(1.5), [0.0, 0.0], docking.TIMEOUT + 1.0)
    assert status == Result.FAILED
    assert c.reason == "timeout"


def test_over_approach_needs_five_samples_so_one_bad_reading_cannot_stop_it():
    c = _running()
    # Settle the filter at a low range first, so the jump-reject does not mask
    # the guard: this test is about the debounce, not the filter.
    for i in range(30):
        step(c, 0.10, 0.2 + i * 0.01)
    _, _, status = step(c, 0.10, 0.6)
    assert status == Result.FAILED
    assert "over-approach" in c.reason


# -------------------------------------------------------------------- filter

def test_a_single_wild_range_sample_is_rejected():
    c = _running()
    step(c, 1.00, 0.2)
    before = c.d_filt
    step(c, 0.25, 0.3)                          # lidar spike
    assert c.d_filt == pytest.approx(before), "a 0.75 m jump is noise, not motion"


def test_the_filter_resets_between_docks():
    """A stale estimate made the source project declare docked and never move."""
    c = _running()
    step(c, 0.45, 0.2)
    assert c.d_filt is not None
    c.reset(now=10.0)
    assert c.d_filt is None


# ------------------------------------------------------------------ control

def test_it_closes_the_gap_and_declares_docked():
    c = _running()
    status = None
    for i in range(docking.CONV_N + 40):
        _, _, status = step(c, docking.D_TARGET, 0.2 + i * 0.05)
        if status == Result.DOCKED:
            break
    assert status == Result.DOCKED
    assert "docked" in c.reason


def test_one_wild_sample_cannot_flip_the_docked_decision():
    """Jump rejection plus a 0.85 low-pass caps any single sample at 0.015 m of
    influence — half the 0.03 m tolerance. So convergence is always decided on a
    filtered range over CONV_N cycles, never on one reading. That is the point
    of the filter, and it is why the guard below needs a debounce too."""
    c = _running()
    step(c, docking.D_TARGET, 0.2)
    assert c.conv_count == 1
    _, _, status = step(c, 1.2, 0.3)                      # a wild single sample
    assert status == Result.RUNNING
    assert c.d_filt == pytest.approx(docking.D_TARGET)


def test_a_sustained_drift_out_of_tolerance_resets_convergence():
    c = _running()
    step(c, docking.D_TARGET, 0.2)
    assert c.conv_count == 1
    t = 0.3
    for _ in range(60):
        step(c, c.d_filt + 0.09, t)       # drift outward, within the jump limit
        t += 0.05
        if c.conv_count == 0:
            break
    assert c.conv_count == 0, "drifting off target must un-declare convergence"


def test_lateral_error_alone_prevents_docking():
    c = _running()
    for i in range(docking.CONV_N + 2):
        _, _, status = step(c, docking.D_TARGET, 0.2 + i * 0.05, cte=0.5)
    assert status == Result.RUNNING, "centred on distance but not on the marker"


def test_combined_speed_is_capped_not_each_axis():
    """Capping axes separately lets the diagonal reach sqrt(2) x the limit."""
    c = _running()
    speed, _, _ = step(c, 10.0, 0.2, cte=10.0)
    assert speed <= docking.V_MAX + 1e-9


def test_the_original_geometry_is_the_axis_ninety_case():
    """With the dock along body +y this must reduce to the source controller."""
    c = _running()
    e_d, cte = 1.0, 0.2
    speed, steer = c._command(e_d, cte, math.pi / 2)
    vy = docking.KP_DIST * e_d
    vx = docking.KP_LAT * cte
    assert steer == pytest.approx(math.atan2(vy, vx))
    assert speed == pytest.approx(min(math.hypot(vx, vy), docking.V_MAX))


# -------------------------------------------------------------- observation

def test_a_marker_out_of_range_is_not_seen():
    assert docking.observe((0.0, 0.0, 0.0), (100.0, 0.0, math.pi)) is None


def test_a_marker_behind_the_robot_is_not_seen():
    assert docking.observe((0.0, 0.0, 0.0), (-2.0, 0.0, 0.0)) is None


def test_range_and_offset_are_measured_against_the_marker_not_the_map():
    """Robot 2 m to the side of a marker facing it: range 2, no lateral offset.

    To the SIDE, because the cameras are side-mounted and the robot crabs in.
    """
    o = docking.observe((0.0, 0.0, 0.0), (0.0, 2.0, -math.pi / 2))
    assert o is not None
    assert o.range_m == pytest.approx(2.0)
    assert o.cte == pytest.approx(0.0, abs=1e-9)


def test_a_sideways_offset_shows_up_as_lateral_error():
    o = docking.observe((0.0, 0.0, 0.0), (0.3, 2.0, -math.pi / 2))
    assert o is not None
    assert o.range_m == pytest.approx(2.0)
    assert o.cte == pytest.approx(0.3)


def test_a_marker_straight_ahead_is_not_seen_by_side_cameras():
    """The cameras look left and right, not forward — so approaching nose-first
    sees nothing. This is why the spur runs perpendicular to the aisle."""
    assert docking.observe((0.0, 0.0, 0.0), (2.0, 0.0, math.pi)) is None


def test_a_marker_on_either_side_is_seen():
    """d435_left and d435_right: a machine on either side of the aisle works."""
    assert docking.observe((0.0, 0.0, 0.0), (0.0, 2.0, -math.pi / 2)) is not None
    assert docking.observe((0.0, 0.0, 0.0), (0.0, -2.0, math.pi / 2)) is not None


def _running():
    """A controller past the settle phase, ready to drive."""
    c = DockController()
    _, steer, _ = step(c, 1.5, 0.0)
    step(c, 1.5, 0.1, steer=(steer, steer))
    assert c.phase == "run"
    return c


# ------------------------------------------------------------ marker identity

def test_the_wrong_marker_refuses_the_approach():
    """Docking against the wrong machine reports SUCCESS, which is worse than
    a failure: the CSM then believes material is somewhere it is not."""
    c = DockController(expect_id=7)
    o = obs(1.5, stamp=0.0)
    o.marker_id = 12
    speed, _, status = c.step(o, [0.0, 0.0], 0.0)
    assert status == Result.FAILED
    assert speed == 0.0, "refuse before moving, not after docking"
    assert "wrong marker" in c.reason


def test_the_right_marker_is_accepted():
    c = DockController(expect_id=7)
    o = obs(1.5, stamp=0.0)
    o.marker_id = 7
    _, _, status = c.step(o, [0.0, 0.0], 0.0)
    assert status == Result.RUNNING


def test_an_unidentified_marker_is_refused_when_an_id_is_expected():
    c = DockController(expect_id=7)
    _, _, status = c.step(obs(1.5, stamp=0.0), [0.0, 0.0], 0.0)
    assert status == Result.FAILED
    assert "wrong marker" in c.reason


def test_observe_reports_which_marker_it_saw():
    o = docking.observe((0.0, 0.0, 0.0), (0.0, 2.0, -math.pi / 2), marker_id=42)
    assert o is not None and o.marker_id == 42
