"""demo - run the Mini MES against a fake factory, so you can watch it work.

No hardware, no ACS, no CATL protocol. Two mock stations produce work, a mock
ACS carries it, and the job FSM drives each job through its lifecycle while
printing every transition.

    ros2 run mini_mes demo
    python3 -m mini_mes.demo --jobs 5 --fail-one

This is the whole point of building behind adapters: the Mini MES is complete
and demonstrable today, while the two interfaces it depends on are still
unknown.
"""

import argparse

from .adapters.base import StationStatus
from .adapters.mock import ManualClock, MockAcs, MockEquipment
from .main_cycle import MainCycle

STATIONS = ["station_3", "station_5", "station_9"]


def main():
    parser = argparse.ArgumentParser(description="Mini MES demo (mock factory)")
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
    cycle.on_station_finished = lambda sid: cycle.create_job(sid, "station_9")

    print("=" * 68)
    print("Mini MES demo — mock factory, no hardware")
    print("=" * 68)

    produced = 0
    tick = 0
    while produced < args.jobs or cycle.active:
        tick += 1

        # The factory finishes a batch every few ticks.
        if produced < args.jobs and tick % 3 == 1:
            station = STATIONS[produced % len(STATIONS)]
            equipment.force_status(station, StationStatus.FINISHED)
            produced += 1
            print(f"\n[tick {tick:>3}] {station} finished a batch")

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
