"""ChargingTask — "which robot needs charging, and may it go now?"

THE DECISION IS CSM'S. The ACS team said so directly in the 2026-08-14 meeting:
"CSM will give the command to ACS to charge" (verified, transcript line 1357).
The ACS drives the robot to the charger; choosing WHO goes and WHEN is ours,
because it is a scheduling decision and scheduling is what this layer owns.

⚠ WHAT THIS DOES NOT SETTLE. The same schema note records that the ACS may also
charge on its own initiative, and nothing has confirmed whether it does. If it
does, two systems are making the same decision and they will disagree. That is
a question for the customer, not something to code around — so this task issues
its command and does not assume it is the only one.

WHY A ROBOT IS NOT SENT THE MOMENT IT DIPS

A charging robot is a robot not working, and this line has one per leg. Sending
one away mid-shift because it crossed a threshold costs a whole leg's
throughput. So it is asked for only when the robot is IDLE — a robot carrying
a roll finishes the job first. The floor of LOW_BATTERY exists for the case
where that is not enough.
"""

from ...adapters.base import AcsOrder, AcsTask, TaskKind
from ..fsm_task import FsmTask

#: Percent below which an idle robot is sent to charge.
#:
#: ⚠ NOT A MEASURED NUMBER. Nobody has given us the fleet's real capacity,
#: consumption or the charge curve, and the handbook is explicit that CSM is
#: "not required to understand battery chemistry". This is the level at which
#: sending an idle robot away costs least, and it is a parameter for exactly
#: that reason.
LOW_BATTERY = 30.0

#: How full is full enough. Charging to 100 takes disproportionately long on
#: most chemistries, and a robot at 90 is a working robot.
CHARGE_TO = 90.0

#: Below this a robot goes even if it is holding a job, because a robot that
#: stops mid-aisle blocks the aisle for everyone.
CRITICAL_BATTERY = 12.0

DEFAULT_PERIOD_S = 5.0


class ChargingTask(FsmTask):
    """Watches the fleet's charge and asks the ACS to top one up."""

    name = "charging"

    def __init__(self, store, wakes=None, name=None, period=None,
                 low_battery=None, charge_to=None, critical_battery=None):
        """
        The three thresholds are INSTANCE attributes, not the module constants
        they default to. None of the three is a measured number — we have not
        been given the fleet's capacity, consumption or charge curve — and the
        module comments already say they are parameters for that reason. This
        is what makes them actually adjustable: a simulator watching a charge
        cycle, or a site whose robots turn out to behave differently, changes
        them here rather than editing a constant and rebuilding.
        """
        super().__init__(name=name, period=period or DEFAULT_PERIOD_S)
        self.low_battery = LOW_BATTERY if low_battery is None else float(low_battery)
        self.charge_to = CHARGE_TO if charge_to is None else float(charge_to)
        self.critical_battery = (CRITICAL_BATTERY if critical_battery is None
                                 else float(critical_battery))
        if self.critical_battery > self.low_battery:
            # Critical above low would make every low robot critical, and a
            # critical robot PREEMPTS the job it is holding. The whole fleet
            # would abandon its work at the first sign of a flat battery.
            raise ValueError(
                f"critical_battery ({self.critical_battery}) must not be above "
                f"low_battery ({self.low_battery})")
        if self.charge_to <= self.low_battery:
            # Charging to at or below the level that sent it would have the
            # robot leave the charger still low and turn straight back round.
            raise ValueError(
                f"charge_to ({self.charge_to}) must be above "
                f"low_battery ({self.low_battery})")
        self.store = store
        self.wakes = list(wakes or [])
        self.charge_orders = 0
        #: Robots we have already asked for, so a slow trip to the charger is
        #: not read as "still low, ask again" every five seconds.
        self._asked = set()

    async def step(self):
        acs = self.store.acs
        if not hasattr(acs, "fleet_status"):
            return
        for robot in acs.fleet_status() or []:
            self._consider(robot)

    def _consider(self, robot):
        name = robot.get("name")
        battery = robot.get("battery")
        if name is None or battery is None:
            return                      # an ACS that cannot report charge

        # Already charging, or already asked and on its way.
        if robot.get("charging_to") is not None:
            self._asked.discard(name)
            return
        if name in self._asked:
            return
        # A robot that cannot move cannot drive to a charger either. Asking
        # would produce an order nobody can execute.
        if not robot.get("responsive", True):
            return

        critical = battery <= self.critical_battery
        if battery > self.low_battery:
            return
        if robot.get("busy") and not critical:
            return                      # finish the job first

        self._request(name, battery, critical)

    def _request(self, name, battery, critical):
        from ... import plant

        charger = plant.charger_for(name)
        if charger is None:
            # A leg with no charger is a real state — say so once rather than
            # asking again every cycle for something that cannot happen.
            self._asked.add(name)
            self.store.logger(f"[{name}] battery {battery:.0f}% and its leg "
                              f"has no charger")
            return

        order = AcsOrder(
            id=f"charge_{name}_{int(battery)}",
            tasks=[
                AcsTask(kind=TaskKind.MOVE, target=f"charger:{name}"),
                AcsTask(kind=TaskKind.CHARGE, chargeTo=int(self.charge_to)),
            ],
            # A robot about to stop in an aisle outranks material movement.
            priority=100 if critical else 1,
            requester="CSM",
            requesterDetail="charging",
        )
        response = self.store.acs.create_order(order)
        if response.ok:
            self._asked.add(name)
            self.charge_orders += 1
            self.store.logger(
                f"[{name}] battery {battery:.0f}% — sent to charge"
                f"{' (CRITICAL)' if critical else ''}")
            for task in self.wakes:
                task.notify()
        else:
            self.store.logger(f"[{name}] charge order refused: "
                              f"{response.message}")
