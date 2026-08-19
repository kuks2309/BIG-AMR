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

    def __init__(self, store, wakes=None, name=None, period=None):
        super().__init__(name=name, period=period or DEFAULT_PERIOD_S)
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

        critical = battery <= CRITICAL_BATTERY
        if battery > LOW_BATTERY:
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
                AcsTask(kind=TaskKind.CHARGE, chargeTo=int(CHARGE_TO)),
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
