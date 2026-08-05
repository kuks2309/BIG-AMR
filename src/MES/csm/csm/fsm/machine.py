"""StateMachine - holds the current state and moves between them.

The whole engine is `step()`, and it never grows more complicated no matter how
many states are added:

    1. run the current state's execute()
    2. check only the transitions whose source is the current state
    3. if a guard is open: on_exit -> switch -> on_enter, then stop

Three details in there are deliberate.

**One transition per tick.** After firing, step() returns. Without that, a chain
of open guards could carry a job through three states in a single tick and never
run the intermediate execute() bodies.

**on_exit before on_enter.** Always leave properly before arriving. This is
where motors stop, connections close, the gate is released.

**Only transitions leaving the current state are examined.** That single filter
is what makes unreachable states genuinely unreachable.

Transition order matters when two guards are open on the same tick: the first
match in the list wins. Order the list so the more urgent exit comes first —
put failure and timeout before success, so a job that has both completed and
timed out is recorded as the failure it was.
"""


class StateMachine:

    def __init__(self, start, transitions, on_change=None):
        """
        :param start:       State instance to begin in
        :param transitions: list of Transition
        :param on_change:   optional callable(ctx, transition) fired after each
                            state change — useful for logging and persistence
        """
        self.current = start
        self.transitions = list(transitions)
        self.on_change = on_change
        self._entered = False

    def start(self, ctx):
        """Run the initial state's on_enter. Idempotent."""
        if not self._entered:
            self._entered = True
            self.current.on_enter(ctx)

    def step(self, ctx):
        """Advance one tick. Returns the Transition that fired, or None."""
        self.start(ctx)

        self.current.execute(ctx)

        for t in self.transitions:
            if t.source is not self.current:
                continue
            if not t.is_open(ctx):
                continue

            self.current.on_exit(ctx)
            self.current = t.target
            self.current.on_enter(ctx)
            if self.on_change:
                self.on_change(ctx, t)
            return t          # one transition per tick, never two

        return None

    def is_in(self, state):
        return self.current is state

    def __repr__(self):
        return f"<StateMachine at {self.current.name}>"
