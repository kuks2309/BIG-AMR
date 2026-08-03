"""Runtime scaffolding for the Mini MES: a supervisor and independent FSMs.

See ARCHITECTURE.md §5 — the design is a core loop that owns lifecycle only,
holding a list of state machines that each wake on an event.
"""

from .fsm_task import FsmTask
from .job_store import JobRecord, JobStore
from .mes_app import MesApp, build_mes
from .supervisor import Supervisor
from .tasks import DispatcherTask, EquipmentMonitorTask, JobTrackerTask

__all__ = [
    "FsmTask", "Supervisor",
    "JobStore", "JobRecord",
    "EquipmentMonitorTask", "DispatcherTask", "JobTrackerTask",
    "MesApp", "build_mes",
]
