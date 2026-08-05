"""demo - run the CSM against a fake factory, so you can watch it work.

No hardware, no ACS, no CATL protocol. Two mock stations produce work, a mock
ACS carries it, and the job FSM drives each job through its lifecycle while
printing every transition.

    ros2 run csm demo
    python3 -m csm.demo --jobs 5 --fail-one

This is the whole point of building behind adapters: the CSM is complete
and demonstrable today, while the two interfaces it depends on are still
unknown.
"""

import argparse

from .adapters.base import StationStatus, TaskType
from .adapters.mock import ManualClock, MockAcs, MockEquipment
from .main_cycle import MainCycle

STATIONS = ["ASRS", "1A01", "1T01", "1L01"]
FEEDS = {"1A01": "ASRS", "1T01": "1A01", "1L01": "1T01"}


def main():
    parser = argparse.ArgumentParser(description="CSM demo (mock factory)")
    parser.add_argument("--jobs", type=int, default=3,
                        help="how many batches the factory produces")
    parser.add_argument("--fail-one", action="store_true",
                        help="make one job fail at the ACS")
    parser.add_argument("--timeout-one", action="store_true",
                        help="make one job hang, so t5 (timeout) fires")
    parser.add_argument("--job-timeout", type=float, default=60.0,
                        help="seconds a job may spend in one state")
    args = parser.parse_args()

    # A manual clock keeps the demo instant and identical every run — the
    # 60-second timeout is exercised without waiting 60 seconds.
    clock = ManualClock()
    equipment = MockEquipment(STATIONS, clock, process_seconds=3.0)
    acs = MockAcs(clock, travel_seconds=6.0)

    cycle = MainCycle(equipment, acs, clock=clock,
                      logger=lambda m: print(f"  {m}"),
                      job_timeout_s=args.job_timeout)
    cycle.source_for = lambda sid: FEEDS.get(sid, "ASRS")

    print("=" * 68)
    print("CSM demo — mock factory, no hardware")
    print("=" * 68)

    produced = 0
    tick = 0
    while produced < args.jobs or cycle.active:
        tick += 1

        # The factory finishes a batch every few ticks.
        if produced < args.jobs and tick % 3 == 1:
            callers = list(FEEDS)
            station = callers[produced % len(callers)]
            # Work starts with a CALL, not with material appearing. Keep the
            # supply stocked so the call can be served.
            for sid in STATIONS:
                equipment.force_status(sid, StationStatus.FINISHED)
            equipment.raise_call(station, TaskType.LOAD, source="PDA")
            produced += 1
            print(f"\n[tick {tick:>3}] {station} called for material (PDA)")

            if args.fail_one and produced == 2:
                acs.fail_next = True
                print("           (this one will be rejected by the ACS)")

        cycle.tick()

        # Freeze one job so its timeout transition fires.
        if args.timeout_one and produced == 1 and cycle.active:
            job_id = cycle.active[0][0].job_id
            acs.never_arrives(job_id)
            args.timeout_one = False
            print(f"           ({job_id} will hang — watch t5 fire)")

        clock.advance(2.0)

        if tick > 400:
            print("safety stop: demo ran too long")
            break

    print("\n" + "=" * 68)
    print(f"finished {len(cycle.finished)} jobs in {tick} ticks\n")
    for job in cycle.finished:
        path = " -> ".join(name for _, _, name in job.history)
        line = f"  {job.job_id}  {job.state_name:<7} {job.from_station} -> {job.to_station}"
        print(line)
        print(f"             {path}")
        if job.failure_reason:
            print(f"             reason: {job.failure_reason}")
    print("=" * 68)


if __name__ == "__main__":
    main()
