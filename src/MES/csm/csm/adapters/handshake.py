"""The docking handshake watchdog — the signal side of entering a machine.

`docking.py` is the MOTION side: how a robot crabs the last metres onto a port.
This is the SIGNAL side: whether it is allowed to be there at all, and whether
the machine is allowed to move.

Source: `AGV与主机设备对接流程及协议.xlsx`, sheet 主机与AGV交互变量表, analysed in the
project handbook (held outside this repository). Two rules carry almost all of
the safety here — `MC_Enter_Permitted` condition 7 and `AGV_Entering` rule 3:

    7.  Entry is permitted only if the time the AGV has been receiving this
        signal exceeds the comm-alarm time.

    3.  The AGV is considered outside the door only if the machine has not
        received `AGV_Entering` for longer than the comm-alarm time.

They form a MUTUAL WATCHDOG, and the important thing about it is that it fails
safe in BOTH directions, for opposite reasons:

  * the robot may only enter if it has been CONTINUOUSLY HEARING permission;
  * the machine may only assume the robot has left after PROLONGED SILENCE.

So silence never means "clear". On the robot's side silence means "you may not
enter". On the machine's side silence means "assume the robot is still inside".
The handbook is explicit that this must not be simplified into a plain boolean
check, and the reason is that a boolean cannot express either rule: both are
statements about a DURATION, and a signal that flickers 1-0-1 between two polls
satisfies a boolean test while violating the rule.

⚠ THE COMM-ALARM TIME IS NOT A NUMBER WE HAVE. It is the equipment's own
timeout and nobody has given it to us; the same gap that `debt-033` tracks for
the minimum signal hold time. It is therefore a required constructor argument
with no default. A default here would be an invented safety margin, which is
exactly the kind of number that gets believed later.
"""


class ContinuousSignal:
    """True only after a signal has been held UNBROKEN for long enough.

    This is `MC_Enter_Permitted` condition 7 from the robot's point of view.
    Any interruption, however brief, restarts the clock — that is the whole
    point, and it is why the accumulated time is discarded rather than paused.
    """

    def __init__(self, hold_seconds):
        if hold_seconds is None or hold_seconds <= 0:
            raise ValueError(
                "hold_seconds must be the equipment's comm-alarm time; "
                "there is no safe default for it")
        self.hold_seconds = float(hold_seconds)
        #: When the current unbroken run of True began. None means "not held".
        self._since = None
        self._now = None

    def update(self, asserted, now):
        """Feed one observation of the signal.

        `now` is passed in rather than read from a clock so that a test can
        drive this deterministically, and so the caller's poll timestamp is the
        one used — not the moment this happened to be called.
        """
        self._now = now
        if not asserted:
            self._since = None
        elif self._since is None:
            self._since = now
        return self.satisfied

    @property
    def held_for(self):
        if self._since is None or self._now is None:
            return 0.0
        return max(0.0, self._now - self._since)

    @property
    def satisfied(self):
        """Has it been held long enough, right now?"""
        return self._since is not None and self.held_for >= self.hold_seconds

    def drop(self):
        """Signal lost — e.g. the heartbeat stopped, so nothing is trustworthy.

        Distinct from `update(False)` only in intent; both restart the clock.
        """
        self._since = None


class BayOccupancy:
    """Is a robot inside the machine? Assume YES until proven otherwise.

    This is `AGV_Entering` rule 3 from the machine's point of view, and it is
    the mirror image of `ContinuousSignal`: there, silence withholds permission;
    here, silence WITHHOLDS RELEASE.

    Rule 2 of the same block — "the machine is not allowed to move after entry"
    — is what `occupied` gates. Getting this backwards, so that a dropped signal
    reads as "the robot left", is the failure that lets a machine move onto a
    robot that is still docked.
    """

    def __init__(self, clear_after_seconds):
        if clear_after_seconds is None or clear_after_seconds <= 0:
            raise ValueError(
                "clear_after_seconds must be the equipment's comm-alarm time; "
                "there is no safe default for it")
        self.clear_after = float(clear_after_seconds)
        self._entered = False
        #: When `AGV_Entering` was last seen true. None means never seen.
        self._last_seen = None
        self._now = None

    def update(self, entering, now):
        self._now = now
        if entering:
            self._entered = True
            self._last_seen = now
        return self.occupied

    @property
    def silent_for(self):
        if self._last_seen is None or self._now is None:
            return 0.0
        return max(0.0, self._now - self._last_seen)

    @property
    def occupied(self):
        """True while a robot must be assumed to be inside.

        Once entry has been seen at all, only prolonged silence clears it. A
        robot that never entered is not occupying anything, which is why
        `_entered` is tracked separately from the timestamp.
        """
        if not self._entered:
            return False
        return self.silent_for < self.clear_after

    @property
    def may_machine_move(self):
        """`AGV_Entering` rule 2, stated the way a caller wants to ask it."""
        return not self.occupied


class Heartbeat:
    """`MC_HeartBeat` / `AGV_HeartBeat` — a 1 s pulse, both directions.

    The pulse is what makes "communication normal" observable, and
    `MC_Enter_Permitted` condition 6 hangs off it: if communication is not
    normal the signal does not stay 1 and **the AGV stops**. So a lost heartbeat
    is not a logging matter; it withdraws entry permission.
    """

    #: The documented pulse period. Used only as the default staleness basis;
    #: the tolerance is the caller's to choose because it depends on the poll
    #: period, which is itself unresolved (`debt-033`).
    PERIOD_SECONDS = 1.0

    def __init__(self, timeout_seconds):
        if timeout_seconds is None or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout = float(timeout_seconds)
        self._last_pulse = None
        self._now = None

    def pulse(self, now):
        self._last_pulse = now
        self._now = now

    def update(self, now):
        self._now = now
        return self.alive

    @property
    def silent_for(self):
        if self._last_pulse is None or self._now is None:
            return float("inf")
        return max(0.0, self._now - self._last_pulse)

    @property
    def alive(self):
        """A heartbeat never seen is NOT alive — absence is not health."""
        return self._last_pulse is not None and self.silent_for < self.timeout


class DockingHandshake:
    """The two rules together, which is the only way they are safe.

    Holding them in one object stops a caller from checking one and forgetting
    the other, and gives one place to ask the two questions that matter:

        may_enter          -- may the robot cross the door?
        may_machine_move   -- may the machine start moving again?

    Both are pessimistic when the link is unhealthy, and they are pessimistic in
    OPPOSITE directions, which is what makes the pair safe rather than merely
    cautious.
    """

    def __init__(self, comm_alarm_seconds, heartbeat_timeout=None):
        self.permission = ContinuousSignal(comm_alarm_seconds)
        self.occupancy = BayOccupancy(comm_alarm_seconds)
        self.machine_heartbeat = Heartbeat(
            heartbeat_timeout or comm_alarm_seconds)

    def observe(self, now, enter_permitted, agv_entering,
                machine_heartbeat=False):
        """One poll of the whole handshake."""
        if machine_heartbeat:
            self.machine_heartbeat.pulse(now)
        else:
            self.machine_heartbeat.update(now)

        # Condition 6: without communication the permission is not trustworthy,
        # whatever the permission bit itself currently reads.
        if not self.machine_heartbeat.alive:
            self.permission.drop()
        else:
            self.permission.update(enter_permitted, now)

        self.occupancy.update(agv_entering, now)

    @property
    def may_enter(self):
        return self.permission.satisfied and self.machine_heartbeat.alive

    @property
    def may_machine_move(self):
        return self.occupancy.may_machine_move
