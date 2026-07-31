"""demo_skeleton — proof that the supervisor runs, with placeholder FSMs.

    ros2 run mini_mes skeleton
    python3 -m mini_mes.runtime.demo_skeleton --seconds 12

These two machines are NOT the real ones. Which four FSMs the Mini MES needs is
still an open question for Dr. Shim (ARCHITECTURE.md §5.3), and it decides
whether jobs carry their own state machine or become data passed between
subsystem FSMs. Until that is answered, this file exists only to demonstrate
that the structure works:

  * a supervisor holding a list and starting each machine
  * a periodic FSM that wakes on its own timer  (like an equipment poller)
  * a reactive FSM that sleeps until notified   (like a dispatcher)
  * work handed from one to the other by notify()
  * one FSM crashing without taking down the others
  * clean shutdown, with on_stop() reached in every case

Replace these two with the real machines and delete this file.
"""

import argparse
import asyncio

from .fsm_task import FsmTask
from .supervisor import Supervisor


class Producer(FsmTask):
    """Wakes on a timer and hands work on. Stands in for an equipment poller."""

    name = "producer"
    period = 1.0

    def __init__(self, consumer=None, fail_on=None):
        super().__init__()
        self.consumer = consumer
        self.fail_on = fail_on          # raise on this attempt, once
        self.produced = 0
        self.attempts = 0

    async def step(self):
        # Counted separately from self.ticks, which only advances on success —
        # testing against ticks would make this fail on every attempt for ever
        # rather than exactly once.
        self.attempts += 1
        if self.fail_on is not None and self.attempts == self.fail_on:
            raise RuntimeError("deliberate failure, to prove isolation")

        self.produced += 1
        print(f"  producer: item {self.produced} ready")
        if self.consumer:
            self.consumer.inbox.append(self.produced)
            self.consumer.notify()      # hand it over — the other FSM wakes


class Consumer(FsmTask):
    """Sleeps until notified. Stands in for a dispatcher."""

    name = "consumer"
    # No period: purely reactive. It costs nothing while idle.

    def __init__(self):
        super().__init__()
        self.inbox = []
        self.handled = 0

    async def step(self):
        while self.inbox:
            item = self.inbox.pop(0)
            self.handled += 1
            print(f"  consumer: handling item {item}")


async def _main(seconds, fail_on):
    consumer = Consumer()
    producer = Producer(consumer=consumer, fail_on=fail_on)

    sup = Supervisor(logger=lambda m: print(f"[supervisor] {m}"))
    sup.register(producer)
    sup.register(consumer)

    print("=" * 62)
    print("supervisor skeleton — placeholder FSMs, not the real ones")
    print("=" * 62)

    async def stop_later():
        await asyncio.sleep(seconds)
        print(f"\n[test] {seconds}s elapsed — requesting stop")
        sup.request_stop()

    asyncio.ensure_future(stop_later())
    # Signal handlers are skipped so this stays usable inside a test runner.
    health = await sup.run(install_signal_handlers=False)

    print("\n" + "=" * 62)
    for name, h in health.items():
        line = f"  {name:<10} {h['ticks']:>3} ticks, {h['errors']} errors"
        if h["last_error"]:
            line += f"  last: {h['last_error']}"
        print(line)
    print(f"\n  produced {producer.produced}, handled {consumer.handled}")
    if producer.errors:
        print(f"  the producer crashed {producer.errors}x and both machines")
        print("  carried on — isolation works.")
    print("=" * 62)


def main():
    ap = argparse.ArgumentParser(description="Supervisor skeleton demo")
    ap.add_argument("--seconds", type=float, default=6.0)
    ap.add_argument("--fail-on", type=int, default=2,
                    help="tick at which the producer raises (-1 to disable)")
    args = ap.parse_args()
    fail_on = None if args.fail_on < 0 else args.fail_on
    asyncio.run(_main(args.seconds, fail_on))


if __name__ == "__main__":
    main()
