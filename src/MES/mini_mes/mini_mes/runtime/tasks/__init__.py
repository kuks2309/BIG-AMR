"""The Mini MES's state machines, as independent tasks under the Supervisor.

Three of them, matching the three boxes drawn on the 2026-07-28 whiteboard:

    EquipmentMonitorTask   is material ready anywhere?      -> creates jobs
    DispatcherTask         whose turn is it to ask the ACS? -> grants permits
    JobTrackerTask         advance every job one step       -> owns the lifecycle

They share a JobStore and wake each other with notify(). None of them knows how
the others are implemented; the store is the only thing they have in common.

Why these three and not one loop. `MainCycle` does all of this sequentially and
works, but it is one failure domain: an exception anywhere stops everything, and
the poll rates are welded together even though they want to be different by two
orders of magnitude (equipment changes over seconds, a job FSM wants a few hertz,
a dispatcher only has anything to do when a queue exists). Split, each runs at
its own rate, and one crashing does not silence the others — the Supervisor
records the failure and the siblings keep going.
"""

from .equipment_monitor import EquipmentMonitorTask

__all__ = ["EquipmentMonitorTask"]
