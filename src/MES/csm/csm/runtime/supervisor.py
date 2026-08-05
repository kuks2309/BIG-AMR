"""Supervisor — the core loop from the whiteboard.

    core loop
      while (exit_flag == false)
          activate FSM
          listed on [ | | | | ]

It holds a **list** of state machines, starts each one, and watches the exit
flag. That is all it does.

**It contains no logic of its own, deliberately.** Every decision lives inside
an FSM. The system is extended by registering another machine, never by editing
this file — which is what stops a supervisor slowly turning into the place where
everything ends up.

Usage:

    sup = Supervisor()
    sup.register(EquipmentMonitor())
    sup.register(Dispatcher())
    asyncio.run(sup.run())

Ctrl-C, SIGTERM, or `sup.request_stop()` shuts it down; every FSM gets its
`on_stop()` called before the process exits.
"""

import asyncio
import signal


class Supervisor:

    def __init__(self, logger=print):
        self.logger = logger
        self._fsms = []
        self._stop_event = None      # created inside run(), see below
        self._tasks = []

    # ------------------------------------------------------------- registry

    def register(self, fsm):
        """Add a state machine to the list. Returns it, so it can be chained."""
        if any(f.name == fsm.name for f in self._fsms):
            raise ValueError(
                f"an FSM named {fsm.name!r} is already registered — names are "
                f"used in logs and must be unique")
        self._fsms.append(fsm)
        return fsm

    @property
    def fsms(self):
        return tuple(self._fsms)

    # ------------------------------------------------------------ lifecycle

    def request_stop(self):
        """Ask every FSM to finish. Safe to call more than once."""
        if self._stop_event is not None:
            self._stop_event.set()

    async def run(self, install_signal_handlers=True):
        """Start every registered FSM and wait until stop is requested."""
        if not self._fsms:
            raise RuntimeError("no FSMs registered — nothing to supervise")

        # Created here rather than in __init__: an asyncio.Event binds to the
        # running loop, and a Supervisor built before the loop exists would
        # otherwise attach to the wrong one.
        self._stop_event = asyncio.Event()

        if install_signal_handlers:
            self._install_signal_handlers()

        names = ", ".join(f.name for f in self._fsms)
        self.logger(f"supervisor starting {len(self._fsms)} FSMs: {names}")

        self._tasks = [
            asyncio.ensure_future(f.run(self._stop_event, self.logger))
            for f in self._fsms
        ]

        await self._stop_event.wait()
        self.logger("supervisor stopping — waiting for FSMs to finish")

        # Give each one a moment to unwind through its own on_stop(), then
        # cancel whatever is still hanging so shutdown cannot itself hang.
        done, pending = await asyncio.wait(self._tasks, timeout=5.0)
        for t in pending:
            self.logger("an FSM did not stop in time — cancelling it")
            t.cancel()
        if pending:
            await asyncio.wait(pending, timeout=2.0)

        self.logger("supervisor stopped")
        return self.health()

    def _install_signal_handlers(self):
        """Ctrl-C and SIGTERM request a clean stop rather than killing us.

        Falls back silently where the platform or loop does not support it.
        """
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.request_stop)
            except (NotImplementedError, RuntimeError):
                pass

    # --------------------------------------------------------------- health

    def health(self):
        """A snapshot of every FSM: how many ticks, how many failures.

        An FSM sitting at zero ticks is either genuinely idle or wedged, and
        that distinction is worth being able to see from outside.
        """
        return {
            f.name: {
                "ticks": f.ticks,
                "errors": f.errors,
                "last_error": repr(f.last_error) if f.last_error else None,
            }
            for f in self._fsms
        }

    def __repr__(self):
        return f"<Supervisor fsms={[f.name for f in self._fsms]}>"
