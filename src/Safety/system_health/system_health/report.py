"""운영 결과 보고 — JSONL 로그를 읽어 판정 기준별로 요약한다. ROS 무의존.

시험 운전이 "문제 없음" 인지 사람이 눈으로 판정하려면 표본 수천 개를 볼 수 없다. 본 모듈은
그 판정에 실제로 쓰이는 항목만 뽑는다:

  ① **표본 결손** — 감시기가 죽거나 밀려서 빈 구간이 있는가. 사고 순간에 표본이 없으면
     감시기를 넣은 의미가 사라지므로 가장 먼저 본다.
  ② **주기 지터** — 목표 주기를 지키는가.
  ③ **판정 분포·경보 집계** — 무엇이 몇 번 걸렸는가(오탐 판단 근거).
  ④ **일자 회전** — 파일이 날짜별로 갈렸는가. 단위 테스트는 시각을 주입해 검증하지만
     실시간 경로는 자정을 한 번 넘겨야 확인된다.
  ⑤ **자원 추이** — 온도·CPU·메모리·디스크의 범위와 마지막 값.
  ⑥ **로그 성장률** — 표본당 바이트 → 일일 추정.

판정은 하지 않고 **수치와 근거만** 낸다 — 합격 여부는 사람이 정한다.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .cliargs import positive_float

_BYTES_PER_MB = 1 << 20
#: 표본 간격이 목표의 이 배수를 넘으면 "결손 의심" 으로 센다. 1.5 배는 한 표본을 통째로
#: 놓쳤다고 보기에 충분한 여유다(정상 지터는 0.1 % 수준 — 2026-07-28 실측).
GAP_FACTOR = 1.5


@dataclass(frozen=True)
class LogFileInfo:
    """로그 파일 하나의 요약."""

    path: Path
    records: int
    bytes: int


def list_log_paths(log_dir: str | Path, prefix: str = "health") -> list[Path]:
    """로그 파일 **경로만** 날짜순으로 돌려준다 — 내용을 읽지 않는다.

    `load_files` 는 표본 수를 세려고 파일을 통째로 읽으므로, 꼬리만 필요한 경로에서 쓰면
    안 된다(그러면 `tail_records` 의 의미가 사라진다).
    """
    directory = Path(log_dir)
    if not directory.is_dir():
        return []
    return sorted(directory.glob(f"{prefix}-*.jsonl"))


def log_span(log_dir: str | Path, prefix: str = "health") -> dict[str, Any]:
    """기록 구간 요약 — 파일 수·총 바이트·가장 오래된 표본 시각.

    **가장 오래된 파일의 첫 줄만** 읽는다. 화면 갱신마다 전체를 세면 로그가 커질수록
    비싸지므로, 표본 개수 대신 구간과 크기로 대신한다.
    """
    paths = list_log_paths(log_dir, prefix)
    total = 0
    for path in paths:
        try:
            total += path.stat().st_size
        except OSError:
            continue
    first_iso = None
    for path in paths:
        try:
            with path.open("r", encoding="utf-8") as handle:
                line = handle.readline()
            first_iso = json.loads(line).get("iso_time")
            break
        except (OSError, json.JSONDecodeError):
            continue
    return {"files": len(paths), "bytes": total, "first_time": first_iso}


def load_files(log_dir: str | Path, prefix: str = "health") -> list[LogFileInfo]:
    """로그 디렉토리의 파일별 표본 수·크기. 날짜 오름차순.

    Args:
        log_dir: JSONL 로그 디렉토리.
        prefix: 파일명 접두.
    Returns:
        `LogFileInfo` 목록. 디렉토리가 없으면 빈 목록.
    """
    directory = Path(log_dir)
    if not directory.is_dir():
        return []
    out: list[LogFileInfo] = []
    for path in sorted(directory.glob(f"{prefix}-*.jsonl")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        out.append(
            LogFileInfo(
                path=path,
                records=sum(1 for line in text.splitlines() if line.strip()),
                bytes=path.stat().st_size,
            )
        )
    return out


def load_records(log_dir: str | Path, prefix: str = "health") -> list[dict[str, Any]]:
    """모든 표본을 시간순으로 읽는다. 깨진 줄은 건너뛴다(부분 기록된 마지막 줄 등).

    Args:
        log_dir: JSONL 로그 디렉토리.
        prefix: 파일명 접두.
    Returns:
        표본 dict 목록.
    """
    recs: list[dict[str, Any]] = []
    for info in load_files(log_dir, prefix):
        for line in info.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    recs.sort(key=lambda r: r.get("epoch_s", 0.0))
    return recs


#: `tail_records` 가 한 파일에서 뒤에서부터 읽는 블록 크기(바이트).
_TAIL_BLOCK = 1 << 16


def tail_records(log_dir: str | Path, n: int, prefix: str = "health") -> list[dict[str, Any]]:
    """**최근 `n` 개만** 읽는다 — 전체를 파싱하지 않는다.

    `load_records` 는 디렉토리의 모든 파일을 통째로 읽으므로 화면 갱신처럼 반복 호출되는
    경로에서 쓰면 안 된다: 5초마다 수십 MB 를 파싱하게 되고 로그가 쌓일수록 악화된다
    (2026-07-29 실측 — 대시보드가 16 시간 만에 RSS 137 MB 까지 불었다. 로그 16 MB × 반복 파싱).

    파일을 **최신부터 역순**으로, 각 파일은 **뒤에서부터 블록 단위**로 읽어 필요한 만큼만 뜬다.

    Args:
        log_dir: JSONL 로그 디렉토리.
        n: 필요한 표본 수(1 이상).
        prefix: 파일명 접두.
    Returns:
        시간순(오래된 → 최신) 표본, 최대 `n` 개.
    """
    want = max(1, n)
    lines: list[str] = []
    for path in reversed(list_log_paths(log_dir, prefix)):
        try:
            with path.open("rb") as handle:
                handle.seek(0, 2)
                pos = handle.tell()
                chunk = b""
                while pos > 0 and chunk.count(b"\n") <= want:
                    step = min(_TAIL_BLOCK, pos)
                    pos -= step
                    handle.seek(pos)
                    chunk = handle.read(step) + chunk
        except OSError:
            continue
        got = [ln for ln in chunk.decode("utf-8", "ignore").splitlines() if ln.strip()]
        # 블록 경계에서 잘린 첫 줄은 버린다(파일 선두까지 읽은 경우는 온전하므로 유지).
        if pos > 0 and got:
            got = got[1:]
        lines = got[-want:] + lines
        if len(lines) >= want:
            break
    recs: list[dict[str, Any]] = []
    for line in lines[-want:]:
        try:
            recs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    recs.sort(key=lambda r: r.get("epoch_s", 0.0))
    return recs


def sample_gaps(records: Sequence[dict[str, Any]]) -> list[float]:
    """연속 표본 사이 간격(초). 표본이 2개 미만이면 빈 목록."""
    stamps = [r["epoch_s"] for r in records if "epoch_s" in r]
    return [b - a for a, b in zip(stamps, stamps[1:])]


def gap_stats(gaps: Sequence[float], interval_s: float) -> dict[str, Any]:
    """간격 통계와 결손 의심 구간.

    Args:
        gaps: `sample_gaps` 결과.
        interval_s: 목표 주기(초).
    Returns:
        평균·중앙·최소·최대·표준편차와 `gaps_over`(목표×GAP_FACTOR 초과 간격 목록),
        `missing_estimate`(놓친 것으로 추정되는 표본 수).
    """
    if not gaps:
        return {"count": 0, "gaps_over": [], "missing_estimate": 0}
    stats = {
        "count": len(gaps),
        "mean": st.mean(gaps),
        "median": st.median(gaps),
        "min": min(gaps),
        "max": max(gaps),
        "stdev": st.pstdev(gaps) if len(gaps) > 1 else 0.0,
    }
    if interval_s <= 0:
        # 목표 주기가 없으면 "결손"이 정의되지 않는다. 간격 통계는 그대로 내되 결손 판정만 뺀다 —
        # 가드가 없으면 아래 `g / interval_s` 가 ZeroDivisionError 를 내 보고서가 통째로 끊긴다.
        return {**stats, "gaps_over": [], "missing_estimate": 0}
    threshold = interval_s * GAP_FACTOR
    over = [g for g in gaps if g > threshold]
    return {
        **stats,
        "gaps_over": over,
        "missing_estimate": int(sum(round(g / interval_s) - 1 for g in over)),
    }


def level_counts(records: Sequence[dict[str, Any]]) -> dict[str, int]:
    """판정 등급별 표본 수."""
    counts: dict[str, int] = {}
    for r in records:
        key = r.get("level", "?")
        counts[key] = counts.get(key, 0) + 1
    return counts


def finding_counts(records: Sequence[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """경보 키별·등급별 발생 횟수. 오탐 판단의 1차 근거다."""
    out: dict[str, dict[str, int]] = {}
    for r in records:
        for f in r.get("findings", []) or []:
            per = out.setdefault(f.get("key", "?"), {})
            lvl = f.get("level", "?")
            per[lvl] = per.get(lvl, 0) + 1
    return out


def _series(records: Sequence[dict[str, Any]], pick) -> list[float]:
    """표본에서 값을 뽑아 None 을 걸러낸 수열."""
    out = []
    for r in records:
        try:
            v = pick(r)
        except (KeyError, TypeError, ValueError, IndexError):
            continue
        if isinstance(v, (int, float)):
            out.append(float(v))
    return out


def resource_ranges(records: Sequence[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """자원 항목별 최소·최대·마지막 값."""
    picks = {
        "최고온도(°C)": lambda r: max(r["temperatures_c"].values()),
        "CPU(%)": lambda r: r["cpu_total_pct"],
        "GPU(%)": lambda r: r["gpu"]["load_pct"],
        "GPU주파수(MHz)": lambda r: r["gpu"]["freq_hz"] / 1e6,
        "가용메모리(MB)": lambda r: r["memory"]["available_mb"],
        "스왑활동(pages/s)": lambda r: r["swap_rate_pages_s"]["in"] + r["swap_rate_pages_s"]["out"],
        "스왑누적사용(MB)": lambda r: r["memory"]["swap_used_mb"],
        "디스크여유(GB)": lambda r: r["disks"][0]["free_gb"],
        "팬PWM": lambda r: r["fan"]["pwm"],
    }
    out: dict[str, dict[str, float]] = {}
    for name, pick in picks.items():
        vals = _series(records, pick)
        if vals:
            out[name] = {"min": min(vals), "max": max(vals), "last": vals[-1]}
    return out


def filter_since(records: Sequence[dict[str, Any]], since: str | None) -> list[dict[str, Any]]:
    """`since`(ISO 문자열, 예 `2026-07-28T16:36`) 이후 표본만 남긴다.

    **왜 필요한가**: 한 로그 디렉토리에 여러 번의 실행이 누적되면, 실행 사이의 공백이
    "감시기가 죽어 있던 구간" 으로 집계된다(2026-07-28 시험 운전에서 수집률이 23.7 % 로
    보였으나 실제로는 별개 실행 사이의 공백이었다). 평가 구간을 잘라야 판정이 의미를 갖는다.

    Args:
        records: 표본 목록.
        since: ISO 시각 접두 문자열. None 이면 전체.
    Returns:
        해당 구간 표본.
    """
    if not since:
        return list(records)
    return [r for r in records if (r.get("iso_time") or "") >= since]


def format_report(log_dir: str | Path, interval_s: float, prefix: str = "health",
                  since: str | None = None, *,
                  records: Sequence[dict[str, Any]] | None = None,
                  files: Sequence[LogFileInfo] | None = None,
                  max_samples: int | None = None) -> str:
    """사람이 읽는 보고문. 판정은 하지 않고 수치만 낸다.

    Args:
        log_dir: JSONL 로그 디렉토리.
        interval_s: 목표 표본 주기(초).
        prefix: 로그 파일명 접두.
        since: ISO 시각 접두. 이후 표본만 평가한다.
        records: 이미 읽어 둔 표본. 주면 다시 읽지 않는다 — 호출자가 같은 로그를 두 번
            완독하지 않게 하려는 주입점이다(`main` 이 종료 코드 판정에 재사용한다).
        files: 이미 읽어 둔 파일 요약. 같은 이유의 주입점.
        max_samples: 읽을 표본 수 상한. 주면 `tail_records` 로 **꼬리만** 읽는다.
            반복 호출되는 경로(웹 `/api/report`)가 로그 전체를 파싱하지 않게 한다.
    Returns:
        보고문.
    """
    files = list(load_files(log_dir, prefix) if files is None else files)
    if records is None:
        all_recs = (tail_records(log_dir, max_samples, prefix) if max_samples
                    else load_records(log_dir, prefix))
    else:
        all_recs = list(records)
    capped = max_samples is not None and len(all_recs) >= max_samples
    recs = filter_since(all_recs, since)
    lines: list[str] = []
    add = lines.append

    add(f"■ 운영 결과 — {log_dir}  (목표 주기 {interval_s:g}s)")
    if capped:
        add(f"  ⚠ 최근 {max_samples}개 표본만 읽었다(상한). 전 구간이 필요하면 CLI 로 실행할 것.")
    if not recs:
        add("  표본 없음 — 감시기가 기록하지 못했다.")
        return "\n".join(lines)

    first, last = recs[0], recs[-1]
    span = last["epoch_s"] - first["epoch_s"]
    expected = int(span / interval_s) + 1 if interval_s > 0 else 0
    add(f"  구간   : {first['iso_time']} ~ {last['iso_time']}  ({span/3600:.2f} h)")
    add(f"  표본   : {len(recs)}개 / 기대 {expected}개"
        f"  (수집률 {100*len(recs)/expected:.1f} %)" if expected else "")

    g = gap_stats(sample_gaps(recs), interval_s)
    if g["count"]:
        add("① 주기 지터")
        add(f"  평균 {g['mean']:.3f}s · 중앙 {g['median']:.3f}s · 최소 {g['min']:.3f}s"
            f" · 최대 {g['max']:.3f}s · 표준편차 {g['stdev']:.3f}s")
        add(f"  결손 의심({interval_s*GAP_FACTOR:g}s 초과 간격): {len(g['gaps_over'])}건"
            f" · 놓친 표본 추정 {g['missing_estimate']}개")
        if g["gaps_over"]:
            add("  " + ", ".join(f"{x:.1f}s" for x in g["gaps_over"][:8]))

    add("② 판정 분포")
    add("  " + " · ".join(f"{k} {v}개({100*v/len(recs):.1f}%)"
                          for k, v in sorted(level_counts(recs).items())))

    fc = finding_counts(recs)
    add("③ 경보 집계")
    if fc:
        for key, per in sorted(fc.items(), key=lambda kv: -sum(kv[1].values())):
            add(f"  {key:<22} " + " · ".join(f"{l} {n}" for l, n in sorted(per.items())))
    else:
        add("  없음")

    add(f"④ 일자 회전 — 파일 {len(files)}개"
        + ("  (표본 수는 --since 로 자르지 않은 전체다)" if since else ""))
    for info in files:
        add(f"  {info.path.name}  표본 {info.records}개  {info.bytes/1024:.0f} KB")
    if len(files) < 2:
        add("  ⚠ 파일이 1개뿐 — 자정 회전 경로가 아직 실시간 검증되지 않았다.")

    add("⑤ 자원 추이 (최소 → 최대, 마지막)")
    for name, r in resource_ranges(recs).items():
        add(f"  {name:<16} {r['min']:>9.1f} → {r['max']:>9.1f}   (마지막 {r['last']:.1f})")

    # 분자(총 바이트)는 파일 전체이므로 분모도 **전 구간 표본 수**를 쓴다. `--since` 로 잘린
    # 표본 수를 분모에 넣으면 표본당 바이트가 구간을 자른 비율만큼 부풀려지고, 그 값이 그대로
    # 하루 추정 → `--max-total-mb` 근거로 쓰인다.
    total = sum(i.bytes for i in files)
    per_sample = total / len(all_recs) if all_recs else 0.0
    add("⑥ 로그 성장률" + ("  (전 구간 기준 — --since 로 자르지 않는다)" if since else ""))
    daily = f" · 하루 추정 {per_sample*86400/interval_s/_BYTES_PER_MB:.1f} MB" if interval_s > 0 else ""
    add(f"  총 {total/_BYTES_PER_MB:.2f} MB · 표본당 {per_sample:.0f} B{daily}")
    return "\n".join(lines)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="system_health.report",
        description="자원 감시 로그 요약 — 시험 운전·상주 운영 결과 확인용",
    )
    p.add_argument("log_dir", help="JSONL 로그 디렉토리 (예: Log/health)")
    p.add_argument("--interval", type=positive_float, default=5.0, help="목표 표본 주기(초, 0 초과)")
    p.add_argument("--prefix", default="health", help="로그 파일명 접두")
    p.add_argument("--since", default=None,
                   help="이 ISO 시각 이후 표본만 평가 (예: 2026-07-28T16:36). 한 폴더에 여러 "
                        "실행이 누적되면 실행 사이 공백이 결손으로 집계되므로 구간을 자른다")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """진입점.

    Returns:
        표본이 하나라도 있으면 0, 없으면 1.
    """
    args = _parse_args(argv)
    # 로그는 **한 번만** 완독한다. 보고문을 만든 뒤 종료 코드를 정하려고 다시 읽으면 같은
    # 디렉토리를 두 번 파싱하게 된다.
    recs = load_records(args.log_dir, args.prefix)
    print(format_report(args.log_dir, args.interval, args.prefix, args.since, records=recs))
    return 0 if filter_since(recs, args.since) else 1


if __name__ == "__main__":
    sys.exit(main())
