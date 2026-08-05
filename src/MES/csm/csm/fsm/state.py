"""State - one situation the machine can be in.

Every state is an object, as specified on the 2026-07-28 whiteboard.

Three hooks, and the distinction between them matters:

    on_enter   runs once, on arrival
    execute    runs every cycle, for as long as the machine stays here
    on_exit    runs once, on leaving

Put acquisition in on_enter and release in on_exit — starting a motion, opening
a connection, taking the gate. The machine guarantees on_exit runs before the
next state's on_enter, so a state can always clean up after itself even when the
transition out of it was unexpected.

Keep execute cheap. It is called at the main cycle rate, and a slow execute
delays every other job in the queue.
"""


class State:
    """Base class for all states. Subclass and override what you need."""

    #: Shown in logs and stored on the job record. Set it in the subclass.
    name = "unnamed"

    def on_enter(self, ctx):
        """Called once, immediately after this state becomes current."""

    def execute(self, ctx):
        """Called once per main-cycle tick while this state is current."""

    def on_exit(self, ctx):
        """Called once, immediately before leaving this state."""

    def __repr__(self):
        return f"<State {self.name}>"
