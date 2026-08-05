"""Job - one unit of transport work, and the context its state machine runs in.

A job is the CSM's reason to exist: "material must move from A to B".
Everything else in this package is machinery for getting jobs through their
lifecycle.
"""

from dataclasses import dataclass, field


@dataclass
class Job:
    """A transport job. Plain data — no behaviour, no protocol."""

    job_id: str
    from_station: str
    to_station: str
    priority: int = 0
    created_at: float = 0.0

    #: Name of the current FSM state, mirrored here so the record is readable
    #: without reaching into the machine.
    state_name: str = "IDLE"

    #: Wall-clock time this job entered its current state. The timeout guard is
    #: computed from this, so every waiting state gets an escape hatch.
    state_since: float = 0.0

    #: Set when the job ends badly, so an operator sees *why* and not just that.
    failure_reason: str = ""

    history: list = field(default_factory=list)

    def __str__(self):
        return (f"{self.job_id} [{self.state_name}] "
                f"{self.from_station} -> {self.to_station}")


class JobContext:
    """What the states and guards are allowed to see.

    Passed to every on_enter / execute / on_exit / guard call. Holding the
    adapters here — rather than letting states import them — is what keeps the
    FSM free of any protocol knowledge, and what makes it testable with mocks.
    """

    def __init__(self, job, equipment, acs, clock, logger=None,
                 job_timeout_s=600.0, retry_backoff_s=3.0):
        self.job = job
        self.equipment = equipment
        self.acs = acs
        self.clock = clock
        self.logger = logger
        self.job_timeout_s = job_timeout_s

        #: How long a job waits in IDLE before asking a busy ACS again.
        self.retry_backoff_s = retry_backoff_s

        #: Is a Dispatcher FSM deciding when this job may submit?
        #:
        #: False — the sequential default — means the job decides for itself as
        #: soon as its backoff allows, which is what every existing test
        #: describes. True hands that timing to the Dispatcher, so ten queued
        #: jobs do not all submit to a one-robot fleet on the same tick and
        #: collect nine BUSY answers.
        self.dispatch_gated = False

        #: May this job leave IDLE right now? Only consulted when gated. A
        #: permit authorises one attempt and is spent on leaving IDLE, so a job
        #: bounced back by t_busy must be granted afresh rather than retrying on
        #: its own.
        self.dispatch_permit = True
        #: Submissions attempted so far. The first is immediate; later ones are
        #: spaced by retry_backoff_s so a queued job does not hammer the ACS.
        self.submit_attempts = 0

        #: Last result the ACS reported, refreshed by the RUNNING state so the
        #: guards do not each poll the adapter separately.
        self.last_acs_result = None

        self.guard_errors = []

    # -- helpers used by states and guards --------------------------------

    def now(self):
        return self.clock()

    def time_in_state(self):
        return self.now() - self.job.state_since

    def timed_out(self):
        return self.time_in_state() > self.job_timeout_s

    def backoff_elapsed(self):
        """Has this job waited long enough since its own last ACS attempt?

        The first attempt goes immediately; later ones are spaced so a queued
        job does not re-ask a busy ACS on every tick.

        Lives here because two callers need the same answer: t1's guard, which
        decides whether to move, and the Dispatcher, which decides who to grant
        a permit to. A dispatcher using a different rule would hand permits to
        jobs the guard then refuses to act on — permits burned on jobs that
        cannot move, while jobs that could move wait.
        """
        return (self.submit_attempts == 0
                or self.time_in_state() >= self.retry_backoff_s)

    def fail(self, reason):
        """Record why a job is failing. Call before the transition fires."""
        self.job.failure_reason = reason

    def log(self, message):
        if self.logger:
            self.logger(f"[{self.job.job_id}] {message}")

    def report_guard_error(self, transition, exc):
        """Called by Transition when a guard raises.

        A broken guard is a bug, but it must not stall the main cycle and every
        other job with it. Record and carry on; the job will fall through to its
        timeout if nothing else fires.
        """
        self.guard_errors.append((transition.name, repr(exc)))
        self.log(f"guard error in {transition.name}: {exc!r}")
