"""상주 자원 샘플러 — 관측만 한다. 어떤 것도 제어하지 않는다.

**ROS 무의존이 요건이다** (ADR 2026-07-28 §Decision 2): ROS 가 죽었거나 부팅에 실패한 순간이
자원 로그를 가장 보고 싶은 시점인데, ROS 노드 안에 넣으면 정확히 그때 같이 죽는다. 본 모듈과
`sysfs`·`ringlog`·`thresholds` 는 `rclpy` 를 import 하지 않으며, 그 불변식은
`test/test_no_rclpy_import.py` 가 검사한다.

**개입 금지**: 온도가 높든 팬이 멈췄든 본 프로그램은 기록·경보만 한다. 자동 감속·안전정지는
별도 ADR 대상이다(검증 안 된 지령으로 실장비를 손상시킨 이력 —
`docs/claude-mistake/2026-07-27-002`).

사용:
    python3 -m system_health.sampler --once
    python3 -m system_health.sampler --interval 5 --out-dir /var/log/amr-health
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

from . import sysfs
from .ringlog import RingLog, RingLogWriteError
from .thresholds import (PROVISIONAL_KEYS, Finding, Thresholds, evaluate,
                         worst_level)

DEFAULT_INTERVAL_S = 5.0
DEFAULT_MAX_TOTAL_MB = 512.0
DEFAULT_MAX_AGE_DAYS = 14.0
DEFAULT_TOP_RSS = 5
# `/proc` 전체 순회는 다른 수집보다 무거우므로 매 주기마다 하지 않는다.
# 기본 12 주기 × 5 s = 1 분마다 1회.
DEFAULT_PROC_SCAN_EVERY = 12
# `--once` 에서 CPU 사용률을 내려면 스냅샷 2장이 필요하다. 그 사이 간격.
ONCE_BASELINE_DELAY_S = 1.0
# 정지 신호에 빠르게 반응하기 위한 대기 분할 단위(초).
_SLEEP_CHUNK_S = 0.2

#: 정지 요청 플래그.
#: **누가 바꾸나**: `_on_stop_signal` (SIGTERM/SIGINT 핸들러) 단독 writer.
#: **누가 읽나**: `run()` 메인 루프 단독 reader.
#: 단일 writer + bool 대입(원자적)이라 lock 을 두지 않는다 —
#: `docs/claude_guideline/coding/domains/concurrency-coding.md` §1 참조.
_stop_requested = False


def _on_stop_signal(signum: int, frame: Any) -> None:  # noqa: ARG001 - 신호 핸들러 규약
    """SIGTERM/SIGINT 수신 시 정지 플래그만 세운다.

    핸들러 안에서는 I/O·긴 작업을 하지 않는다 — 재진입 안전을 위해 플래그만 바꾸고, 실제
    정리는 메인 루프가 한다.
    """
    global _stop_requested
    _stop_requested = True


def is_stop_requested() -> bool:
    """정지 플래그. 테스트에서 상태를 확인할 수 있게 함수로 노출한다."""
    return _stop_requested


def reset_stop_flag() -> None:
    """정지 플래그를 내린다. 테스트가 상태를 격리하기 위해 쓴다."""
    global _stop_requested
    _stop_requested = False


@dataclass(frozen=True)
class SampleState:
    """차분·비교가 필요한 항목의 직전 값 묶음.

    CPU 사용률·스왑 활동량·CAN 에러율은 전부 **누적 카운터의 차분**이라 이전 표본이 있어야 한다.
    프로세스 PID 는 차분이 아니라 **비교** 대상이다(바뀌었으면 재시작).
    따로 들고 다니면 경과 시간 기준이 어긋날 수 있으므로 한 묶음으로 만든다.
    """

    stamp: float
    cpu: sysfs.CpuSnapshot | None
    swap: sysfs.SwapCounters | None
    can: dict[str, sysfs.CanInterface] = field(default_factory=dict)
    #: 감시 대상 프로세스의 직전 PID 집합. `/proc` 순회를 한 표본에서만 갱신된다.
    pids: dict[str, tuple[int, ...]] = field(default_factory=dict)


def collect(
    prev: SampleState | None,
    *,
    disk_paths: Sequence[str],
    proc_scan: bool,
    top_rss: int,
    fan_daemon_name: str,
    expected_processes: Sequence[str] = (),
    now: float | None = None,
) -> tuple[dict[str, Any], SampleState]:
    """한 시점의 자원 상태를 모아 record 로 만든다.

    CPU 사용률·스왑 활동량은 누적값의 **차분**이라 첫 호출에서는 낼 수 없다. `prev` 가
    None 이면 그 항목들을 넣지 않는다(0 으로 채우면 "한가함"으로 오독된다).

    Args:
        prev: 직전 표본 상태. 없으면 차분 항목 생략.
        disk_paths: 감시할 파일시스템 경로들. 읽기 실패한 경로는 `error` 를 담아 남긴다.
        proc_scan: 이번 주기에 `/proc` 전체 순회를 할지.
        top_rss: 순회 시 남길 RSS 상위 개수.
        fan_daemon_name: 생존을 확인할 팬 제어 데몬 이름.
        expected_processes: 살아 있어야 하는 프로세스 이름들(`/proc` comm, 15자 제한).
            **비어 있으면 프로세스 생존·재시작을 판정하지 않는다** — 감시기가 "무엇이 정상인지"를
            스스로 정하지 않는다(ADR 2026-08-01 §Decision 2).
        now: epoch 초. None 이면 현재 시각(테스트 주입용).
    Returns:
        (record, 이번 표본 상태). 상태는 다음 호출에 그대로 넘긴다.
    """
    stamp = time.time() if now is None else now
    cpu_now = sysfs.read_cpu_times()
    swap_now = sysfs.read_swap_counters()

    record: dict[str, Any] = {
        "iso_time": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(stamp)),
        "epoch_s": round(stamp, 3),
        "uptime_s": sysfs.read_uptime_s(),
        "temperatures_c": {k: round(v, 2) for k, v in sysfs.read_temperatures_c().items()},
        "cooling_states": sysfs.read_cooling_states(),
        "cpu_freqs_khz": list(sysfs.read_cpu_freqs_khz()),
    }

    if prev is not None and prev.cpu is not None and cpu_now is not None:
        usage = sysfs.cpu_usage_pct(prev.cpu, cpu_now)
        record["cpu_total_pct"] = round(usage.total_pct, 1)
        record["cpu_core_pct"] = [round(p, 1) for p in usage.per_core_pct]

    # GPU — Jetson 을 쓰는 이유가 GPU 이므로 필수 항목이다. 사용률은 순간값이라 차분이 불필요.
    gpu = sysfs.read_gpu()
    record["gpu"] = {
        "load_pct": None if gpu.load_pct is None else round(gpu.load_pct, 1),
        "freq_hz": gpu.freq_hz,
        "max_freq_hz": gpu.max_freq_hz,
    }

    # 전원 레일 — 전류는 소비 전력의 직접 지표다. 부하가 아닌데 전류가 오르면 하드웨어
    # 이상이고, 입력 전류 급변은 전원계(배터리·컨버터) 문제를 시사한다.
    rails = sysfs.read_power_rails()
    if rails:
        record["power"] = {
            r.name: {"mv": r.voltage_mv, "ma": r.current_ma, "mw": round(r.power_mw, 1)}
            for r in rails
        }

    memory = sysfs.read_memory()
    if memory is not None:
        record["memory"] = {k: round(v, 1) for k, v in asdict(memory).items()}

    # 스왑 **활동량** — 사용량이 아니라 이것이 실시간성 위험 신호다(sysfs.SwapCounters 참조).
    if prev is not None and prev.swap is not None and swap_now is not None:
        rate_in, rate_out = sysfs.swap_rate_pages_s(prev.swap, swap_now, stamp - prev.stamp)
        record["swap_rate_pages_s"] = {"in": round(rate_in, 1), "out": round(rate_out, 1)}

    disks: list[dict[str, Any]] = []
    for path in disk_paths:
        try:
            info = sysfs.read_disk(path)
        except OSError as exc:
            disks.append({"path": path, "error": str(exc)})
            continue
        disks.append(
            {
                "path": info.path,
                "total_gb": round(info.total_gb, 2),
                "free_gb": round(info.free_gb, 2),
                "used_pct": round(info.used_pct, 1),
            }
        )
    record["disks"] = disks

    fan = sysfs.read_fan()
    # rpm 은 본 하드웨어에 노드가 없어 항상 None 이다 — ADR §Decision 5. 스키마에는 남겨
    # 두어, RPM 을 읽을 수 있는 하드웨어에서 같은 코드가 그대로 동작하게 한다.
    record["fan"] = {"pwm": fan.pwm, "rpm": fan.rpm}

    load = sysfs.read_load_average()
    if load is not None:
        record["load_avg"] = [round(v, 2) for v in load]

    # CAN — 인터페이스가 없으면 항목 자체를 넣지 않는다. CAN 을 안 쓰는 운영도 정상이다.
    can_now = {c.name: c for c in sysfs.read_can_interfaces()}
    if can_now:
        elapsed = stamp - prev.stamp if prev is not None else 0.0
        rows = []
        for name, cur in sorted(can_now.items()):
            row: dict[str, Any] = {
                "name": name,
                "up": cur.is_up,
                "rx_packets": cur.rx_packets,
                "tx_packets": cur.tx_packets,
                "errors_total": cur.total_errors,
            }
            before = (prev.can if prev is not None else {}).get(name)
            if before is not None:
                # 누계가 아니라 증가율로 판정한다(ADR §Decision 3).
                row["error_rate_s"] = round(sysfs.can_error_rate(before, cur, elapsed), 2)
            rows.append(row)
        record["can"] = rows

    # DDS 세그먼트 — 기록만. 정상 개수를 모르므로 판정하지 않는다(ADR §Decision 4).
    record["dds_segments"] = sysfs.count_dds_segments()

    pids_now: dict[str, tuple[int, ...]] = (
        dict(prev.pids) if prev is not None else {}
    )
    if proc_scan:
        scan = sysfs.scan_processes(top_n=top_rss)
        record["process_count"] = scan.count
        record["top_rss"] = [
            {"pid": p.pid, "name": p.name, "rss_mb": round(p.rss_mb, 1)} for p in scan.top_rss
        ]
        record["fan_daemon_alive"] = fan_daemon_name in scan.names

        if expected_processes:
            watch = {n: scan.pids_by_name.get(n, ()) for n in expected_processes}
            missing = sorted(n for n, p in watch.items() if not p)
            # PID 가 바뀐 것 = 죽었다 살아난 것. 생존 검사만으로는 조용한 crash-loop 를 못 잡는다.
            restarted = sorted(
                n for n, p in watch.items()
                if p and n in pids_now and pids_now[n] and set(p) != set(pids_now[n])
            )
            record["process_watch"] = {
                "expected": list(expected_processes),
                "missing": missing,
                "restarted": restarted,
                "pids": {n: list(p) for n, p in watch.items()},
            }
            pids_now = {n: p for n, p in watch.items() if p}

    return record, SampleState(stamp=stamp, cpu=cpu_now, swap=swap_now,
                               can=can_now, pids=pids_now)


def _format_findings(findings: tuple[Finding, ...]) -> str:
    """경보를 사람이 읽을 한 줄들로."""
    return "\n".join(f"  [{f.level.name}] {f.message}" for f in findings)


def _sleep_until(deadline: float) -> None:
    """정지 요청에 빠르게 반응하며 `deadline`(epoch 초)까지 대기한다."""
    while not _stop_requested:
        remaining = deadline - time.time()
        if remaining <= 0:
            return
        time.sleep(min(_SLEEP_CHUNK_S, remaining))


def _load_threshold_overrides(path: str | None) -> dict[str, Any]:
    """JSON 파일에서 임계값 덮어쓰기를 읽는다. 경로가 없으면 빈 dict.

    Raises:
        SystemExit: 파일을 읽을 수 없거나 JSON 이 아니거나 객체가 아닐 때. 임계값을 바꿨다고
            믿는데 실제로는 기본값인 상태가 가장 위험하므로 조용히 넘어가지 않는다.
    """
    if path is None:
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"임계값 파일을 읽을 수 없다 ({path}): {exc}") from exc
    if not isinstance(loaded, dict):
        raise SystemExit(f"임계값 파일은 JSON 객체여야 한다 ({path})")
    return loaded


def _write_thresholds(path: str, th: Thresholds) -> int:
    """현재 임계값을 사람이 편집할 수 있는 JSON 으로 저장한다.

    임계값은 우리가 정하는 값이므로(ADR §Decision 4) 사용자가 파일로 고정할 수 있어야 한다.
    파일에는 값뿐 아니라 **어느 항목이 아직 잠정치인지**(`_provisional`)를 함께 적는다 —
    편집하는 사람이 파일만 보고 근거 상태를 알 수 있어야 하기 때문이다. `_` 로 시작하는 키는
    다시 읽을 때 주석으로 무시되므로 왕복해도 깨지지 않는다.

    Args:
        path: 저장할 파일 경로. 상위 디렉토리는 만든다.
        th: 저장할 임계값.
    Returns:
        종료 코드. 성공 0.
    Raises:
        SystemExit: 저장 실패 시. 저장됐다고 믿는데 안 된 상태를 만들지 않는다.
    """
    payload: dict[str, Any] = {
        "_설명": "AMR 자원 감시 임계값. 값을 고쳐 저장하면 다음 기동부터 적용된다.",
        "_provisional": sorted(PROVISIONAL_KEYS),
        "_provisional_설명": "위 항목은 램프 시험 전 잠정치다 — 실측 후 확정할 것.",
    }
    payload.update(th.to_mapping())
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise SystemExit(f"임계값을 저장할 수 없다 ({path}): {exc}") from exc
    print(f"임계값 저장: {path}", file=sys.stderr)
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """명령행 인자 해석."""
    parser = argparse.ArgumentParser(
        prog="system_health.sampler",
        description="AMR 본체 PC 자원 감시 샘플러 (관측 전용 — 아무것도 제어하지 않는다)",
    )
    parser.add_argument(
        "--interval", type=float, default=DEFAULT_INTERVAL_S, help="표본 주기(초)"
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="JSONL 로그 디렉토리. 생략하면 stdout 으로만 낸다(systemd 는 journald 가 받는다)",
    )
    parser.add_argument(
        "--disk",
        action="append",
        dest="disk_paths",
        default=None,
        help="감시할 파일시스템 경로(반복 지정 가능). 기본 '/'",
    )
    parser.add_argument(
        "--max-total-mb", type=float, default=DEFAULT_MAX_TOTAL_MB, help="로그 총량 상한(MB)"
    )
    parser.add_argument(
        "--max-age-days", type=float, default=DEFAULT_MAX_AGE_DAYS, help="로그 보존 기간(일)"
    )
    parser.add_argument(
        "--proc-scan-every",
        type=int,
        default=DEFAULT_PROC_SCAN_EVERY,
        help="몇 주기마다 /proc 전체를 훑을지 (상위 RSS·팬 데몬 생존 확인)",
    )
    parser.add_argument(
        "--top-rss", type=int, default=DEFAULT_TOP_RSS, help="RSS 상위 몇 개를 남길지"
    )
    parser.add_argument("--thresholds", default=None, help="임계값 덮어쓰기 JSON 파일")
    parser.add_argument(
        "--write-thresholds",
        metavar="PATH",
        default=None,
        help="현재 임계값을 JSON 으로 저장하고 종료. 사용자가 그 파일을 고쳐 --thresholds 로 되먹인다",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help=f"1회만 표본을 내고 종료(CPU 사용률을 위해 {ONCE_BASELINE_DELAY_S}초 기준선 선행)",
    )
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    """샘플 루프. 정지 신호를 받을 때까지 돈다.

    Args:
        args: `_parse_args` 결과.
    Returns:
        프로세스 종료 코드. 정상 종료 0, 로그를 한 번도 못 쓴 채 끝나면 1.
    """
    thresholds = Thresholds.from_mapping(_load_threshold_overrides(args.thresholds))
    if args.write_thresholds:
        # 저장만 하고 끝낸다 — 샘플 루프를 돌리지 않는다.
        return _write_thresholds(args.write_thresholds, thresholds)

    disk_paths = args.disk_paths or ["/"]
    ring = RingLog(
        args.out_dir,
        max_total_mb=args.max_total_mb,
        max_age_days=args.max_age_days,
    ) if args.out_dir else None

    signal.signal(signal.SIGTERM, _on_stop_signal)
    signal.signal(signal.SIGINT, _on_stop_signal)

    # CPU 사용률은 두 스냅샷의 차분이므로 **의미 있는 구간**이 필요하다.
    #
    # 상주 모드에서는 기준선을 따로 읽지 않는다 — 첫 표본 자신이 기준선이 되고 CPU% 는 둘째
    # 표본부터 나온다. 기준선을 읽고 곧바로 표본을 뜨면 구간이 사실상 0 이라 CPU% 가 쓰레기
    # 값이 된다: 그 마이크로초 창에서 우연히 jiffy 가 튄 코어만 100% 로 보이고 집계도 100% 가
    # 되어 **오탐 ERROR** 를 낸다(2026-07-28 성능시험 실측 — 유휴 상태의 첫 표본이
    # total=100% / 코어별 [100,0,100,100,0,0,0,0] 를 보고했다. 8코어 중 3개만 바빴는데 100%).
    #
    # `--once` 는 표본이 하나뿐이라 그럴 수 없으므로 기준선을 읽고 실제로 기다린다.
    prev: SampleState | None = None
    if args.once:
        prev = SampleState(stamp=time.time(), cpu=sysfs.read_cpu_times(),
                           swap=sysfs.read_swap_counters())
        time.sleep(ONCE_BASELINE_DELAY_S)

    cycle = 0
    log_write_failed = False
    consecutive_write_failures = 0
    wrote_anything = False

    while not _stop_requested:
        proc_scan = args.proc_scan_every > 0 and cycle % args.proc_scan_every == 0
        record, prev = collect(
            prev,
            disk_paths=disk_paths,
            proc_scan=proc_scan,
            top_rss=args.top_rss,
            fan_daemon_name=thresholds.fan_daemon_name,
            expected_processes=thresholds.expected_processes,
        )

        # 직전 주기의 기록 실패를 이번 판정에 반영한다 — 기록 실패 자체가 최고 심각도 사건이다.
        record["log_write_failed"] = log_write_failed
        findings = evaluate(record, thresholds)
        record["level"] = worst_level(findings).name
        record["findings"] = [
            {"key": f.key, "level": f.level.name, "value": f.value, "message": f.message}
            for f in findings
        ]

        line = json.dumps(record, ensure_ascii=False, default=str)
        if ring is None:
            print(line, flush=True)
            wrote_anything = True
        else:
            try:
                ring.write(record)
                wrote_anything = True
                if log_write_failed:
                    print("로그 기록 복구됨", file=sys.stderr, flush=True)
                log_write_failed = False
                consecutive_write_failures = 0
            except RingLogWriteError as exc:
                log_write_failed = True
                consecutive_write_failures += 1
                # 실패를 삼키지 않는다. 루프는 계속 돈다 — 디스크가 다시 비면 복구되어야 한다.
                print(
                    f"[ERROR] {exc} (연속 {consecutive_write_failures}회)",
                    file=sys.stderr,
                    flush=True,
                )
                print(line, file=sys.stderr, flush=True)

        if findings:
            print(
                f"[{record['level']}] {record['iso_time']}\n{_format_findings(findings)}",
                file=sys.stderr,
                flush=True,
            )

        cycle += 1
        if args.once:
            break
        _sleep_until(time.time() + args.interval)

    return 0 if wrote_anything else 1


def main(argv: Sequence[str] | None = None) -> int:
    """진입점.

    Args:
        argv: 인자 목록. None 이면 `sys.argv[1:]`.
    Returns:
        프로세스 종료 코드.
    """
    return run(_parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
