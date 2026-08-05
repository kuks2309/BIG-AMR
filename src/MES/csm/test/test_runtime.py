"""Tests for the supervisor and FSM scaffolding.

The important one is `test_step_is_callable_without_an_event_loop`. Every bug
found in the job FSM this week was found because a state machine could be
stepped one tick at a time, by hand, with no timers involved. Moving to
concurrent tasks must not cost that.
"""

import asyncio
import sys
import pathlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.runtime import FsmTask, Supervisor          # noqa: E402


class Counter(FsmTask):
    """Minimal FSM: counts how many times it was stepped."""

    def __init__(self, name="counter", period=None, fail_times=0):
        super().__init__(name=name, period=period)
        self.count = 0
        self.fail_times = fail_times
        self.started = False
        self.stopped = False

    async def on_start(self):
        self.started = True

    async def on_stop(self):
        self.stopped = True

    async def step(self):
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("boom")
        self.count += 1


def run(coro, timeout=5.0):
    return asyncio.run(asyncio.wait_for(coro, timeout))


# ------------------------------------------------ the testability guarantee

def test_step_is_callable_without_an_event_loop():
    """A test must be able to drive an FSM directly, one step at a time.

    No supervisor, no timers, no waiting. This is what made the job FSM's bugs
    findable, and the concurrency rewrite must not take it away.
    """
    fsm = Counter()
    asyncio.run(fsm.step())
    asyncio.run(fsm.step())
    assert fsm.count == 2
    assert fsm.ticks == 0        # ticks are the run loop's business, not step's


# ------------------------------------------------------------- the registry

def test_supervisor_starts_every_registered_fsm():
    a, b = Counter("a", period=0.02), Counter("b", period=0.02)
    sup = Supervisor(logger=lambda m: None)
    sup.register(a)
    sup.register(b)

    async def scenario():
        task = asyncio.ensure_future(sup.run(install_signal_handlers=False))
        await asyncio.sleep(0.15)
        sup.request_stop()
        return await task

    health = run(scenario())
    assert a.started and b.started
    assert a.stopped and b.stopped
    assert health["a"]["ticks"] > 0
    assert health["b"]["ticks"] > 0


def test_duplicate_names_are_refused():
    """Names appear in every log line; two FSMs sharing one is untraceable."""
    sup = Supervisor(logger=lambda m: None)
    sup.register(Counter("same"))
    with pytest.raises(ValueError, match="already registered"):
        sup.register(Counter("same"))


def test_supervisor_with_no_fsms_refuses_to_run():
    sup = Supervisor(logger=lambda m: None)
    with pytest.raises(RuntimeError, match="no FSMs registered"):
        run(sup.run(install_signal_handlers=False))


# ---------------------------------------------------------------- waking up

def test_a_reactive_fsm_sleeps_until_notified():
    """With no period, an FSM must not run at all until woken."""
    fsm = Counter("reactive")          # period is None
    sup = Supervisor(logger=lambda m: None)
    sup.register(fsm)

    async def scenario():
        task = asyncio.ensure_future(sup.run(install_signal_handlers=False))
        await asyncio.sleep(0.1)
        assert fsm.count == 0, "ran without being notified"

        fsm.notify()
        await asyncio.sleep(0.05)
        assert fsm.count == 1

        fsm.notify()
        await asyncio.sleep(0.05)
        assert fsm.count == 2

        sup.request_stop()
        await task

    run(scenario())


def test_a_periodic_fsm_wakes_on_its_own():
    fsm = Counter("poller", period=0.02)
    sup = Supervisor(logger=lambda m: None)
    sup.register(fsm)

    async def scenario():
        task = asyncio.ensure_future(sup.run(install_signal_handlers=False))
        await asyncio.sleep(0.15)
        sup.request_stop()
        await task

    run(scenario())
    assert fsm.count >= 3, f"only woke {fsm.count} times in 150ms at 20ms"


def test_one_fsm_can_hand_work_to_another():
    """notify() between machines — how the real FSMs will pass jobs."""
    receiver = Counter("receiver")

    class Sender(FsmTask):
        name = "sender"
        period = 0.02

        async def step(self):
            receiver.notify()

    sup = Supervisor(logger=lambda m: None)
    sup.register(Sender())
    sup.register(receiver)

    async def scenario():
        task = asyncio.ensure_future(sup.run(install_signal_handlers=False))
        await asyncio.sleep(0.15)
        sup.request_stop()
        await task

    run(scenario())
    assert receiver.count > 0, "the receiver was never woken by the sender"


# --------------------------------------------------------------- resilience

def test_a_crashing_fsm_does_not_stop_its_siblings():
    """One bad state machine must not take the system down."""
    bad = Counter("bad", period=0.02, fail_times=3)
    good = Counter("good", period=0.02)

    sup = Supervisor(logger=lambda m: None)
    sup.register(bad)
    sup.register(good)

    async def scenario():
        task = asyncio.ensure_future(sup.run(install_signal_handlers=False))
        await asyncio.sleep(0.2)
        sup.request_stop()
        return await task

    health = run(scenario())
    assert health["bad"]["errors"] == 3
    assert health["bad"]["last_error"] is not None
    assert bad.count > 0, "did not recover after its failures"
    assert good.errors == 0
    assert good.count > 0, "a sibling's crash stopped this one"


def test_on_stop_runs_even_when_step_keeps_failing():
    """Release must happen however the loop ends."""
    fsm = Counter("always_bad", period=0.02, fail_times=10_000)
    sup = Supervisor(logger=lambda m: None)
    sup.register(fsm)

    async def scenario():
        task = asyncio.ensure_future(sup.run(install_signal_handlers=False))
        await asyncio.sleep(0.1)
        sup.request_stop()
        await task

    run(scenario())
    assert fsm.stopped, "on_stop was skipped"


def test_notify_during_step_is_not_lost():
    """The event is cleared BEFORE the work, so a notify() arriving while
    step() runs still wakes the FSM again afterwards. Clearing afterwards
    would silently discard that work."""
    seen = []

    class Slow(FsmTask):
        name = "slow"

        async def step(self):
            seen.append(len(seen))
            await asyncio.sleep(0.03)

    fsm = Slow()
    sup = Supervisor(logger=lambda m: None)
    sup.register(fsm)

    async def scenario():
        task = asyncio.ensure_future(sup.run(install_signal_handlers=False))
        await asyncio.sleep(0.02)
        fsm.notify()                 # first wake
        await asyncio.sleep(0.01)
        fsm.notify()                 # arrives while step() is still running
        await asyncio.sleep(0.15)
        sup.request_stop()
        await task

    run(scenario())
    assert len(seen) >= 2, "a notify() during step() was swallowed"
