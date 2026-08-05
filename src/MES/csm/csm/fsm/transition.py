"""Transition - the only door between two states.

t1, t2, t3 ... on the whiteboard. Each is an object.

A transition carries two things:

    where it goes    source -> target
    when it opens    guard(ctx) -> bool

The guard is the point. A transition exists permanently, but only *fires* on the
tick where its guard returns True. That is what stops a job jumping to a state it
has not earned.

And what is not written down matters as much as what is. If no transition has
IDLE as source and DONE as target, then IDLE -> DONE is impossible — not
"we remembered to prevent it", but structurally unable to occur. Reachability is
decided by the transition list, not by defensive checks scattered through the
states.
"""


class Transition:

    def __init__(self, name, source, target, guard):
        """
        :param name:   label used in logs, e.g. "t1"
        :param source: State instance this transition leaves from
        :param target: State instance it arrives at
        :param guard:  callable(ctx) -> bool; True means "fire now"
        """
        self.name = name
        self.source = source
        self.target = target
        self.guard = guard

    def is_open(self, ctx):
        """True if this transition may fire on this tick.

        A guard that raises is treated as closed rather than propagating: one
        badly-behaved guard should not take down the whole main cycle and stall
        every other job. The machine reports it instead.
        """
        try:
            return bool(self.guard(ctx))
        except Exception as exc:  # noqa: BLE001 - deliberately broad
            ctx.report_guard_error(self, exc)
            return False

    def __repr__(self):
        return f"<Transition {self.name}: {self.source.name} -> {self.target.name}>"
