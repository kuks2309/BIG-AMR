"""FsmTask — one independent state machine, running on its own.

The whiteboard (2026-07-29) draws each FSM as:

    while (exit_flag == false)
        waitForEvent(&event)      <- blocks, costs nothing while idle
        ... do the work ...
        reset(&event)

That is the Active Object pattern. This is the same thing in Python, using an
asyncio task and an asyncio.Event rather than an OS thread and a Win32 event
object. Same structure, same guarantees, without one thread per machine — and
crucially, still testable.

Why asyncio rather than threads. The CSM is I/O-bound coordination: it
waits on sockets and makes a decision every few seconds. Threads would buy no
parallelism here (the GIL releases on I/O either way) but would cost shared
state, locks, and non-deterministic test ordering. The `waitForEvent` semantics
the design needs are exactly what `asyncio.Event` provides.

**The testability rule.** `step()` must be callable directly, with no event
loop, no timers and no waiting. Production drives it from the run loop; tests
drive it by hand. Every bug found this week was found because the job FSM could
be stepped one tick at a time with an injected clock — that property is not
worth losing.
"""

import asyncio
from abc import ABC, abstractmethod


class FsmTask(ABC):
    """Base class for a state machine that runs as an independent task.

    Subclass and implement `step()`. Optionally set `period` to also wake on a
    timer, which is what a machine-polling FSM needs.
    """

    #: Shown in logs and used by the supervisor. Set it in the subclass.
    name = "unnamed"

    #: Wake this often (seconds) even when no event arrives. None = only on
    #: an event. A poller sets this; a purely reactive FSM leaves it None.
    period = None

    def __init__(self, name=None, period=None):
        if name is not None:
            self.name = name
        if period is not None:
            self.period = period

        self._event = asyncio.Event()
        self._stopping = False

        #: How many times step() has run. Useful in tests and health checks.
        self.ticks = 0
        #: How many times step() raised. A crashing FSM must not be silent.
        self.errors = 0
        self.last_error = None

    # ------------------------------------------------------------- waking

    def notify(self):
        """Wake this FSM. Cheap, idempotent, safe to call repeatedly.

        This is the `SetEvent` half of the whiteboard sketch. Another FSM
        calls it to hand work over.
        """
        self._event.set()

    # ------------------------------------------------- subclass entry points

    async def on_start(self):
        """Called once before the loop begins. Open connections here."""

    async def on_stop(self):
        """Called once after the loop ends, even if it ended badly.

        Release here what on_start acquired — sockets, files, the gate.
        """

    @abstractmethod
    async def step(self):
        """One pass of this state machine.

        MUST be directly callable from a test with no event loop machinery
        around it. Keep it short: a slow step delays only this FSM, but it
        delays every one of its own events.
        """

    # ---------------------------------------------------------- the run loop

    async def run(self, stop_event, logger=print):
        """Loop until `stop_event` is set. Started by the Supervisor."""
        self._stopping = False
        try:
            await self.on_start()
        except Exception as exc:              # noqa: BLE001
            self.errors += 1
            self.last_error = exc
            logger(f"[{self.name}] on_start failed: {exc!r}")
            return

        logger(f"[{self.name}] started"
               + (f" (also wakes every {self.period}s)" if self.period else ""))

        try:
            while not stop_event.is_set():
                await self._wait_for_wake(stop_event)
                if stop_event.is_set():
                    break

                # The event is cleared BEFORE the work, not after. Clearing
                # afterwards would discard any notify() that arrived while
                # step() was running, and that work would be lost.
                self._event.clear()

                try:
                    await self.step()
                    self.ticks += 1
                except asyncio.CancelledError:
                    raise
                except Exception as exc:      # noqa: BLE001
                    # One misbehaving state machine must not take down the
                    # supervisor or its siblings. Record it and carry on.
                    self.errors += 1
                    self.last_error = exc
                    logger(f"[{self.name}] step failed ({self.errors}): {exc!r}")
        except asyncio.CancelledError:
            pass
        finally:
            try:
                await self.on_stop()
            except Exception as exc:          # noqa: BLE001
                logger(f"[{self.name}] on_stop failed: {exc!r}")
            logger(f"[{self.name}] stopped after {self.ticks} ticks"
                   + (f", {self.errors} errors" if self.errors else ""))

    async def _wait_for_wake(self, stop_event):
        """Block until notified, until the period elapses, or until shutdown."""
        waiters = [
            asyncio.ensure_future(self._event.wait()),
            asyncio.ensure_future(stop_event.wait()),
        ]
        try:
            await asyncio.wait(waiters, timeout=self.period,
                               return_when=asyncio.FIRST_COMPLETED)
        finally:
            for w in waiters:
                if not w.done():
                    w.cancel()

    def __repr__(self):
        return f"<{type(self).__name__} {self.name} ticks={self.ticks}>"
