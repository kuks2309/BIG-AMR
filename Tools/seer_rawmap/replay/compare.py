#!/usr/bin/env python3
"""Compare two replay outputs: the original-``.so`` oracle vs. our ``slam_karto_core`` port.

Both sides emit the same contract (see ``README.md``): one ``ours_out.jsonl`` /
``oracle_out.jsonl`` whose lines are ``{"type":"scan",...}`` records followed by a
single ``{"type":"summary",...}`` line.

What it reports:
    * per-scan ``added`` agreement, and the **first index where the two diverge**
      (that index is where root-cause tracing starts);
    * ``corrected`` pose deltas — position [m] and heading [rad] — max / mean /
      percentiles, over the scans both sides added;
    * ``num_scans`` / ``num_points`` / ``bbox`` (``num_rssi`` 는 정의가 달라 참고 출력만);
    * ``points_sha256`` equality, i.e. whether the clouds are bit-identical;
    * optionally, the first differing line of the two point-cloud files.

Exit codes:
    0 — the two outputs agree within the tolerances
    1 — they differ
    2 — usage / IO / format error

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Dict, List, Optional, Sequence, Tuple

#: Position delta at or below this is treated as agreement [m].  One micrometre is
#: far below any physical meaning and far above double round-off on metre-scale
#: coordinates, so it separates "same result" from "actually different".
DEFAULT_POS_TOL_M = 1e-6

#: Heading delta at or below this is treated as agreement [rad].
DEFAULT_YAW_TOL_RAD = 1e-6

#: Bounding-box delta at or below this is treated as agreement [m].
DEFAULT_BBOX_TOL_M = 1e-6

#: Percentiles reported for the pose-delta distribution [%].
REPORT_PERCENTILES = (50.0, 90.0, 99.0, 100.0)

#: Number of leading mismatching scan indices to list.
MAX_LISTED_MISMATCHES = 10

EXIT_SAME = 0
EXIT_DIFFERENT = 1
EXIT_ERROR = 2


def wrap_angle(a: float) -> float:
    """Wrap an angle to ``[-pi, pi]``.

    Args:
        a: Angle [rad].

    Returns:
        Equivalent angle in ``[-pi, pi]`` [rad].
    """
    return math.atan2(math.sin(a), math.cos(a))


def load_output(path: str) -> Tuple[List[Dict], Dict]:
    """Load a replay output file.

    Args:
        path: Path to ``*_out.jsonl``.

    Returns:
        ``(scan_records, summary_record)``.

    Raises:
        ValueError: Malformed content (bad JSON, unknown ``type``, missing or
            duplicated summary).
        OSError: The file cannot be read.
    """
    scans: List[Dict] = []
    summary: Optional[Dict] = None
    with open(path, "r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: JSON 파싱 실패: {exc}") from exc
            kind = rec.get("type")
            if kind == "scan":
                if summary is not None:
                    raise ValueError(f"{path}:{lineno}: summary 뒤에 scan 이 나왔다")
                scans.append(rec)
            elif kind == "summary":
                if summary is not None:
                    raise ValueError(f"{path}:{lineno}: summary 가 두 번 나왔다")
                summary = rec
            else:
                raise ValueError(f"{path}:{lineno}: 알 수 없는 type {kind!r}")
    if summary is None:
        raise ValueError(f"{path}: summary 줄이 없다")
    return scans, summary


def percentile(values: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile of an already-sorted-or-not sequence.

    Args:
        values: Sample values (non-empty).
        pct: Percentile in ``[0, 100]``.

    Returns:
        The sample at the nearest rank.
    """
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    rank = max(1, math.ceil(pct / 100.0 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def compare_scans(
    a_scans: List[Dict],
    b_scans: List[Dict],
    pos_tol: float,
    yaw_tol: float,
) -> Tuple[bool, Optional[int]]:
    """Compare the per-scan records and print the findings.

    Args:
        a_scans: Scan records from side A (oracle).
        b_scans: Scan records from side B (ours).
        pos_tol: Position agreement tolerance [m].
        yaw_tol: Heading agreement tolerance [rad].

    Returns:
        ``(same, first_divergence_index)`` — ``first_divergence_index`` is the
        0-based ``idx`` where the two first disagree, or ``None`` if they agree.
    """
    same = True
    print("== 스캔 대조 ==")
    if len(a_scans) != len(b_scans):
        same = False
        print(f"  [DIFF] 스캔 줄 수: A={len(a_scans)} B={len(b_scans)}")
    else:
        print(f"  [OK]   스캔 줄 수 {len(a_scans)}")

    n = min(len(a_scans), len(b_scans))
    added_mismatch: List[int] = []
    id_mismatch: List[int] = []
    pos_deltas: List[float] = []
    yaw_deltas: List[float] = []
    first_divergence: Optional[int] = None

    for i in range(n):
        a = a_scans[i]
        b = b_scans[i]
        idx = a.get("idx", i)
        if a.get("idx") != b.get("idx"):
            same = False
            print(f"  [DIFF] {i}번째 줄의 idx 가 다르다: A={a.get('idx')} B={b.get('idx')}")
            if first_divergence is None:
                first_divergence = i
            break

        diverged_here = False
        if bool(a.get("added")) != bool(b.get("added")):
            added_mismatch.append(idx)
            diverged_here = True
        elif a.get("unique_id") != b.get("unique_id"):
            id_mismatch.append(idx)
            diverged_here = True

        ap = a.get("corrected") or [0.0, 0.0, 0.0]
        bp = b.get("corrected") or [0.0, 0.0, 0.0]
        dpos = math.hypot(ap[0] - bp[0], ap[1] - bp[1])
        dyaw = abs(wrap_angle(ap[2] - bp[2]))
        pos_deltas.append(dpos)
        yaw_deltas.append(dyaw)
        if dpos > pos_tol or dyaw > yaw_tol:
            diverged_here = True

        if diverged_here and first_divergence is None:
            first_divergence = idx

    if added_mismatch:
        same = False
        head = added_mismatch[:MAX_LISTED_MISMATCHES]
        print(
            f"  [DIFF] added 불일치 {len(added_mismatch)}건 — 앞 {len(head)}개 idx: {head}"
        )
    else:
        print(f"  [OK]   added 전부 일치 ({n}개)")

    if id_mismatch:
        same = False
        head = id_mismatch[:MAX_LISTED_MISMATCHES]
        print(f"  [DIFF] unique_id 불일치 {len(id_mismatch)}건 — 앞 {len(head)}개 idx: {head}")
    else:
        print("  [OK]   unique_id 전부 일치")

    if pos_deltas:
        max_pos = max(pos_deltas)
        max_yaw = max(yaw_deltas)
        mean_pos = sum(pos_deltas) / len(pos_deltas)
        mean_yaw = sum(yaw_deltas) / len(yaw_deltas)
        ok = max_pos <= pos_tol and max_yaw <= yaw_tol
        if not ok:
            same = False
        tag = "OK  " if ok else "DIFF"
        print(f"  [{tag}] corrected 위치차 [m]  max={max_pos:.17g} mean={mean_pos:.17g}")
        print(f"  [{tag}] corrected 방위차 [rad] max={max_yaw:.17g} mean={mean_yaw:.17g}")
        print("         위치차 분포 [m]:  " + "  ".join(
            f"p{p:g}={percentile(pos_deltas, p):.6g}" for p in REPORT_PERCENTILES))
        print("         방위차 분포 [rad]: " + "  ".join(
            f"p{p:g}={percentile(yaw_deltas, p):.6g}" for p in REPORT_PERCENTILES))

    if first_divergence is not None:
        print(f"  ▶ 최초 분기 스캔 idx = {first_divergence}  ← 원인 추적은 여기서 시작한다")
    return same, first_divergence


def compare_summary(a: Dict, b: Dict, bbox_tol: float) -> bool:
    """Compare the two summary records and print the findings.

    Args:
        a: Summary from side A (oracle).
        b: Summary from side B (ours).
        bbox_tol: Bounding-box agreement tolerance [m].

    Returns:
        True when the summaries agree.
    """
    same = True
    print("== summary 대조 ==")
    for key in ("num_scans", "num_points"):
        av = a.get(key)
        bv = b.get(key)
        if av != bv:
            same = False
            delta = (bv - av) if isinstance(av, int) and isinstance(bv, int) else "n/a"
            print(f"  [DIFF] {key}: A={av} B={bv} (B-A={delta})")
        else:
            print(f"  [OK]   {key}={av}")

    # `num_rssi` 는 **판정에서 제외한다** — 두 도구가 세는 대상이 다르다(결함이 아니다).
    #   오라클: 필터 통과한 점마다 이진화 rssi 값(100.0/0.0)을 하나씩 기록 → 항상 num_points 와 같다.
    #   우리  : `MapResult::rssi_pos_list` = 임계 초과 빔의 **반사판 점만**.
    # 같은 이름의 서로 다른 양이라 자동 판정 대상이 아니다. 값은 참고로만 출력한다.
    a_rssi, b_rssi = a.get("num_rssi"), b.get("num_rssi")
    note = ""
    if isinstance(a_rssi, int) and a_rssi == a.get("num_points"):
        note = "  ← 오라클은 점당 1개(=num_points), 우리는 반사판 점만. 정의 차이지 결함 아님"
    print(f"  [정보] num_rssi: A={a_rssi} B={b_rssi}{note}")

    abox = a.get("bbox") or []
    bbox = b.get("bbox") or []
    if len(abox) != 4 or len(bbox) != 4:
        same = False
        print(f"  [DIFF] bbox 길이가 4가 아니다: A={abox} B={bbox}")
    else:
        names = ("min_x", "min_y", "max_x", "max_y")
        worst = max(abs(abox[i] - bbox[i]) for i in range(4))
        if worst > bbox_tol:
            same = False
            for i, nm in enumerate(names):
                print(f"  [DIFF] bbox.{nm} [m]: A={abox[i]:.17g} B={bbox[i]:.17g} "
                      f"d={abox[i] - bbox[i]:.17g}")
        else:
            print(f"  [OK]   bbox 일치 (최대차 {worst:.3g} m)")

    asha = a.get("points_sha256")
    bsha = b.get("points_sha256")
    if asha == bsha:
        print(f"  [OK]   points_sha256 일치 — 점군 비트 동일 ({asha})")
    else:
        same = False
        print(f"  [DIFF] points_sha256 불일치\n         A={asha}\n         B={bsha}")
    return same


def compare_points(path_a: str, path_b: str) -> bool:
    """Find the first differing line of two point-cloud files.

    Args:
        path_a: Side A ``*_points.jsonl``.
        path_b: Side B ``*_points.jsonl``.

    Returns:
        True when the files are byte-identical line-for-line.
    """
    print("== 점군 파일 대조 ==")
    same = True
    with open(path_a, "r", encoding="utf-8") as fa, open(path_b, "r", encoding="utf-8") as fb:
        lineno = 0
        while True:
            la = fa.readline()
            lb = fb.readline()
            if not la and not lb:
                break
            lineno += 1
            if la != lb:
                same = False
                print(f"  [DIFF] 최초 상이 줄 {lineno} (1-based)")
                print(f"         A: {la.rstrip() if la else '<EOF>'}")
                print(f"         B: {lb.rstrip() if lb else '<EOF>'}")
                break
    if same:
        print(f"  [OK]   두 점군 파일이 완전히 같다")
    return same


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point.

    Args:
        argv: Argument vector without the program name.

    Returns:
        Process exit code (see module docstring).
    """
    parser = argparse.ArgumentParser(
        description="오라클 출력과 우리 재생 출력을 대조한다.",
    )
    parser.add_argument("oracle", help="oracle_out.jsonl (기준, A)")
    parser.add_argument("ours", help="ours_out.jsonl (대조 대상, B)")
    parser.add_argument("--oracle-points", help="oracle_points.jsonl (선택)")
    parser.add_argument("--ours-points", help="ours_points.jsonl (선택)")
    parser.add_argument("--pos-tol", type=float, default=DEFAULT_POS_TOL_M,
                        help=f"위치 허용차 [m] (기본 {DEFAULT_POS_TOL_M})")
    parser.add_argument("--yaw-tol", type=float, default=DEFAULT_YAW_TOL_RAD,
                        help=f"방위 허용차 [rad] (기본 {DEFAULT_YAW_TOL_RAD})")
    parser.add_argument("--bbox-tol", type=float, default=DEFAULT_BBOX_TOL_M,
                        help=f"bbox 허용차 [m] (기본 {DEFAULT_BBOX_TOL_M})")
    args = parser.parse_args(argv)

    try:
        a_scans, a_summary = load_output(args.oracle)
        b_scans, b_summary = load_output(args.ours)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    print(f"A (기준)   : {args.oracle}")
    print(f"B (대조)   : {args.ours}")
    print()
    scans_same, _ = compare_scans(a_scans, b_scans, args.pos_tol, args.yaw_tol)
    print()
    summary_same = compare_summary(a_summary, b_summary, args.bbox_tol)

    points_same = True
    if args.oracle_points and args.ours_points:
        for p in (args.oracle_points, args.ours_points):
            if not os.path.exists(p):
                print(f"error: 점군 파일이 없다: {p}", file=sys.stderr)
                return EXIT_ERROR
        print()
        points_same = compare_points(args.oracle_points, args.ours_points)

    print()
    if scans_same and summary_same and points_same:
        print("결과: 차이 없음")
        return EXIT_SAME
    print("결과: 차이 있음")
    return EXIT_DIFFERENT


if __name__ == "__main__":
    sys.exit(main())
