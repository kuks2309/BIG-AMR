"""The job lifecycle state machine - the FSM from the 2026-07-28 whiteboard.

    IDLE --t1--> ASSIGNED --t2--> RUNNING --t3--> DONE
                                     |
                                     +--t4--> FAILED   (something broke)
                                     +--t5--> FAILED   (timeout)
    FAILED --t6--> IDLE                                (operator retry)

Two properties are worth stating explicitly, because they are the reason for
using a state machine rather than a pile of flags.

**RUNNING has three exits.** Success (t3), failure (t4) and timeout (t5). A state
that waits on something outside itself and has only a success arrow is a place
the system can hang forever. That is not hypothetical here: while the Panda gate
is engaged, the layers above are blind by design — if the Jetson dies mid-move,
Seer keeps reporting "parked, all normal" and nothing upstream notices. t5 is the
only thing that ends such a job. Compare Seer alarm 52954, which is precisely a
re-homing state that timed out after 20 minutes.

**There is no IDLE -> DONE arrow.** So that jump cannot occur. Not "we check for
it" — the machine has no way to express it.

Transition order matters: failure and timeout are listed before success, so a job
that both completed and timed out on the same tick is recorded as the failure it
actually was.
"""

from .adapters.base import TransportResult
from .fsm.machine import StateMachine
from .fsm.state import State
from .fsm.transition import Transition


class Idle(State):
    name = "IDLE"

    def on_enter(self, ctx):
        ctx.log("waiting to be dispatched")

    def on_exit(self, ctx):
        """Spend the dispatch permit on the way out.

        A permit authorises one attempt, not a standing right to retry. Without
        this, a job bounced back here by t_busy would still hold its permit and
        would re-submit on its own the moment the backoff elapsed — precisely
        the behaviour the Dispatcher exists to take away from it.

        Only when gated. Clearing it unconditionally would strand a bounced job
        in the sequential driver, where nothing ever grants a permit back.
        """
        if ctx.dispatch_gated:
            ctx.dispatch_permit = False


class Assigned(State):
    name = "ASSIGNED"

    def on_enter(self, ctx):
        """Hand the job to the ACS exactly once, on arrival.

        Submission belongs in on_enter rather than execute: execute runs every
        tick, and submitting a job twenty times a second would be a very
        expensive bug.

        Three answers, three different meanings:
          ACCEPTED - a robot is on it (t2 -> RUNNING)
          BUSY     - valid job, no free robot (t_busy -> IDLE, retry later)
          REJECTED - the job itself is wrong and never will work (-> FAILED)

        Collapsing BUSY into REJECTED is a mistake worth naming: with a
        single-robot fleet, every job created while another was in flight was
        marked FAILED on the spot. The line produced work and the MES threw it
        away. A busy fleet means wait, not give up.
        """
        ctx.submit_attempts += 1
        result = ctx.acs.submit_job(ctx.job)
        ctx.last_acs_result = result

        if result is TransportResult.BUSY:
            # Logged once per attempt, and attempts are spaced by the backoff,
            # so a long queue does not flood the log.
            ctx.log(f"ACS busy — waiting (attempt {ctx.submit_attempts})")
            return

        ctx.log(f"submitted to ACS -> {result.value}")
        if result is TransportResult.REJECTED:
            ctx.fail("ACS rejected the job")


class Running(State):
    name = "RUNNING"

    def on_enter(self, ctx):
        ctx.log("robot is moving")

    def execute(self, ctx):
        """Poll the ACS once per tick and cache the answer.

        Cached deliberately: t3, t4 and t5 all need to know the outcome, and
        three guards each calling the adapter would triple the traffic and could
        see three different answers within one tick.
        """
        ctx.last_acs_result = ctx.acs.get_job_result(ctx.job.job_id)


class Done(State):
    name = "DONE"

    def on_enter(self, ctx):
        """Close the loop at both ends of the transport.

        Both notifications matter, and the source one is easy to forget:

        - the SOURCE is told "collected", which frees it. Without this the
          station stays FINISHED for ever, the main cycle's latch keeps it
          suppressed, and that station never produces another job. Observed
          symptom: the line runs two or three jobs and then goes quiet while
          batches keep completing.
        - the DESTINATION is told "delivered", so it knows material arrived.

        This is the command direction of the equipment link. Whether the CSM
        is permitted to command equipment is not yet formally settled — see
        adapters/base.py. Both calls sit behind the adapter, easy to remove.

        The transport itself succeeded, so a rejected notification does not undo
        the job — but it is logged rather than swallowed. Silently ignoring the
        return value would let an unknown or unreachable station look exactly
        like a clean completion.
        """
        if not ctx.equipment.send_station_command(ctx.job.from_station,
                                                  "collected"):
            ctx.log(f"WARNING: source {ctx.job.from_station} did not accept "
                    f"the 'collected' notification — it may stay blocked")

        if not ctx.equipment.send_station_command(ctx.job.to_station,
                                                  "delivered"):
            ctx.log(f"WARNING: destination {ctx.job.to_station} did not accept "
                    f"the 'delivered' notification")

        ctx.log("job complete")


class Failed(State):
    name = "FAILED"

    def on_enter(self, ctx):
        """Cancel at the ACS on the way in.

        Without this, a timed-out job leaves a robot still driving toward a
        destination nobody is waiting for.
        """
        reason = ctx.job.failure_reason or "unknown"
        ctx.acs.cancel_job(ctx.job.job_id)
        ctx.log(f"FAILED: {reason}")


def build_job_fsm(on_change=None):
    """Construct one state machine for one job.

    Each job gets its own instance — states are shared and stateless, all
    per-job data lives in the context.
    """
    idle = Idle()
    assigned = Assigned()
    running = Running()
    done = Done()
    failed = Failed()

    transitions = [
        # ASSIGNED can fail immediately if the ACS refuses the job.
        Transition("t_reject", assigned, failed,
                   lambda c: c.last_acs_result is TransportResult.REJECTED),

        # First attempt goes immediately; retries are spaced by the backoff so a
        # queued job does not re-ask a busy ACS on every single tick. When a
        # Dispatcher is running, it also has to say yes.
        Transition("t1", idle, assigned, lambda c: _may_dispatch(c)),

        # A busy fleet sends the job back to IDLE to wait its turn. This is the
        # queue: the job keeps its identity and history, it simply has not
        # started yet. Distinct from REJECTED, which is fatal.
        Transition("t_busy", assigned, idle,
                   lambda c: c.last_acs_result is TransportResult.BUSY),

        Transition("t2", assigned, running,
                   lambda c: c.last_acs_result is TransportResult.ACCEPTED),

        # Failure and timeout are checked BEFORE success — see module docstring.
        Transition("t4", running, failed,
                   lambda c: _acs_failed(c)),

        Transition("t5", running, failed,
                   lambda c: _timed_out(c)),

        Transition("t3", running, done,
                   lambda c: c.last_acs_result is TransportResult.ARRIVED),

        Transition("t6", failed, idle,
                   lambda c: getattr(c, "operator_retry", False)),
    ]

    return StateMachine(start=idle, transitions=transitions, on_change=on_change)


def _may_dispatch(ctx):
    """t1's guard: is this job allowed to go and ask the ACS?

    Two conditions, and they answer different questions. The backoff answers
    "has this job waited long enough since its own last attempt". The permit
    answers "is it this job's turn at all" — a fleet-wide question that no
    single job can see, which is why a Dispatcher FSM owns it.
    """
    if ctx.dispatch_gated and not ctx.dispatch_permit:
        return False
    return ctx.backoff_elapsed()


def _acs_failed(ctx):
    if ctx.last_acs_result is TransportResult.FAILED:
        ctx.fail("ACS reported failure")
        return True
    return False


def _timed_out(ctx):
    if ctx.timed_out():
        ctx.fail(f"timeout after {ctx.time_in_state():.0f}s in RUNNING")
        return True
    return False
