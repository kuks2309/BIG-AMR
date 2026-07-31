"""Runtime scaffolding for the Mini MES: a supervisor and independent FSMs.

See ARCHITECTURE.md §5 — the design is a core loop that owns lifecycle only,
holding a list of state machines that each wake on an event.
"""

from .fsm_task import FsmTask
from .supervisor import Supervisor

__all__ = ["FsmTask", "Supervisor"]
