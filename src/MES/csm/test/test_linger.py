"""RULE 6: a robot waits in the dock for its next job, for twenty seconds.

The cheapest place in the plant for a robot to stand is the one it is already
standing in. It is off the road, so no traffic rule applies to it and no lane
is blocked, and travel is what causes every problem this branch has had.

The cost is that a docked robot holds the station — the protocol carries
exactly one "AGV is inside" bit — so waiting there for ever would cost that
machine every robot that needed it. Twenty seconds is the compromise.
"""

import pytest

from csm import plant
from csm.adapters.sim_acs import EXIT_POSES, LINGER_SECONDS, SimRobot


class FakeLogger:
    def info(self, m): pass
    def warn(self, m): pass


class FakeClock:
    def __init__(self): self.t = 1000.0
    def now(self): return self
    @property
    def nanoseconds(self): return self.t * 1e9


class FakeNode:
    def __init__(self): self._log, self._clock = FakeLogger(), FakeClock()
    def get_logger(self): return self._log
    def get_clock(self): return self._clock


class FakeFleet:
    def __init__(self): self.released = []
    def release(self, station, robot): self.released.append((station, robot))


class FakePub:
    def publish(self, msg): pass


def finished_at(station="GRV1_LD"):
    """A robot that has just finished a job at `station` and is still docked."""
    r = object.__new__(SimRobot)
    r.name = "amr1"
    r.node = FakeNode()
    r.fleet = FakeFleet()
    r.pub_cmd = FakePub()
    r.pose = plant.DOCKS[station] + (0.0,)
    r._halt_reason = None
    r._stall_ref = r._stall_since = None
    r._exit_goal = None
    r._exit_station = station
    r._linger_until = r._now() + LINGER_SECONDS
    r._active_job = None
    r._holding_source = None
    return r


def test_it_waits_rather_than_backing_out():
    r = finished_at()

    assert r._exit_goal is None, "it must not have set off"
    assert r._linger_until == pytest.approx(r._now() + LINGER_SECONDS)


def test_it_is_still_free_while_it_waits():
    """The whole point is to be offered the next job from where it stands."""
    r = finished_at()

    assert r.busy is False


def test_it_still_holds_the_station_while_it_waits():
    """It is standing in the bay, so the bay is not free. Rule 3 says a
    station is free when the AMR has LEFT it."""
    r = finished_at()

    assert r._exit_station == "GRV1_LD"
    assert r.fleet.released == []


def test_after_twenty_seconds_it_leaves():
    r = finished_at()
    r.node._clock.t += LINGER_SECONDS + 0.1

    assert r._now() >= r._linger_until
    r._linger_until = None
    r._exit_goal = EXIT_POSES[r._exit_station]

    assert r._exit_goal == plant.JOINS_OUTER["GRV1_LD"]


def test_the_wait_is_twenty_seconds():
    """The number, so that changing it has to argue with the reason."""
    assert LINGER_SECONDS == 20.0


def test_a_job_ends_the_wait_and_frees_the_station():
    """Accepting work releases the bay there and then, because the route it
    has just planned begins by driving out of it."""
    import inspect

    src = inspect.getsource(SimRobot.accept)

    assert "_linger_until = None" in src
    assert "release(self._exit_station" in src


def test_waiting_is_not_a_stall():
    """Standing still in the dock is exactly right. Failing the robot for it
    would fail every job that ends anywhere."""
    import inspect

    src = inspect.getsource(SimRobot.drive)
    at = src.index("waiting in the dock for the next job")
    assert "_reset_stall()" in src[at - 200:at]
