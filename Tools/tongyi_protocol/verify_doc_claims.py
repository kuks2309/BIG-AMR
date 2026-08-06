#!/usr/bin/env python3
"""통합 정본 문서의 **인쇄 수치와 인용 좌표**를 원자료·매뉴얼과 대조한다. 불일치가 있으면 exit 1.

⚠⚠ **이 도구가 보증하지 않는 것을 먼저 읽어라.**
    검사 대상은 (a) 문서에 인쇄된 숫자가 원자료에서 재계산되는가 (b) 인용한 쪽에 그 문구가 실재하는가
    (c) 「V7.0 에 없다」류 **부재 주장이 참인가** — 이 셋뿐이다.
    **결론·해석·방향·안전 문구는 검사하지 않는다.** 2026-08-06 감사에서 숫자를 그대로 둔 채 서술만
    23곳 뒤집은 사본(little-endian→big-endian, 「주변 확보 필수」→「불필요」 등)이 그대로 통과했다.
    ⇒ **이 도구의 통과를 문서 신뢰의 근거로 인용하지 말 것.**

사용:
    python3 Tools/tongyi_protocol/verify_doc_claims.py
    python3 Tools/tongyi_protocol/verify_doc_claims.py --verbose
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/tongyi_can_protocol/2026-08-05.md"
CAP = ROOT / "Log/homing_capture_220350.jsonl"
CAP_NOMOVE = [ROOT / "Log/seer_homing_260803_100813.jsonl",
              ROOT / "Log/home_experiment_260803_095815.jsonl"]
CAP_DIAG = ROOT / "Log/homing_diag_260803_141949.json"
CAP_DIAG_CAN = ROOT / "Log/homing_diag_260803_141949_can.jsonl"
DRIVE = ROOT / "Log/field_2026-08-04/ros2_drive_trace_151700.csv"
MAN_V70 = ROOT / "References/Tongyi-Motor-Controller/manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.txt"
MAN_V79 = ROOT / "References/Tongyi-Motor-Controller/manuals/IxL-II_Servo_Driver_Handbook_V7.9_2025-07-25.txt"
EDS_OLD = ROOT / "References/Tongyi-Motor-Controller/canopen/EDS_extracted/Servo_Driver_20200805.eds"
EDS_NEW = ROOT / "References/Tongyi-Motor-Controller/canopen/EDS_extracted_20240423/Servo_Driver_20240423(3).eds"
CAPTURE_TOOL = ROOT / "Tools/docking_field_kit/orin_homing_capture.py"
SWEEP_TOOL = ROOT / "Tools/docking_field_kit/orin_steer_sweep_1005.py"

FAILS: list[str] = []
PASSES: list[str] = []
DOC_TEXT = DOC.read_text(encoding="utf-8") if DOC.exists() else ""


def check(label: str, ok: bool, detail: str = "") -> None:
    (PASSES if ok else FAILS).append(label + (f" — {detail}" if detail else ""))


def near(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def claim(label: str, *needles: str) -> None:
    """문서가 그 문자열을 싣고 있는가. ⚠ 존재만 본다 — 다중 등장 시 하나가 틀려도 통과."""
    missing = [n for n in needles if n not in DOC_TEXT]
    check(label, not missing, "문서에 없음: " + " / ".join(missing) if missing else "")


def doc_values(label: str, pattern: str, expected: set[str]) -> None:
    """문서에서 pattern 의 1번 캡처를 **전부** 뽑아 기대 집합과 정확히 일치하는지 본다."""
    got = {m.group(1) for m in re.finditer(pattern, DOC_TEXT)}
    check(label, got == expected,
          f"문서값 {sorted(got)} ≠ 기대 {sorted(expected)} (초과 {sorted(got-expected)} · 누락 {sorted(expected-got)})")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s)


# ══ 캡처 디코드 ═══════════════════════════════════════════════════════════
WRITE_CMD = {0x2F: 1, 0x2B: 2, 0x27: 3, 0x23: 4}
RESP_SIZE = {0x4F: 1, 0x4B: 2, 0x47: 3, 0x43: 4}


def _iter(path):
    with open(path, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if "id" not in r or not r.get("d"):
                continue
            try:
                yield r.get("t"), r["id"], bytes.fromhex(r["d"])
            except ValueError:
                continue


def _sval(data, size):
    return struct.unpack("<i", data[:4])[0] if size == 4 else int.from_bytes(data[:size], "little")


def load(path):
    c = dict(kinds=Counter(), nodes=Counter(), guard=defaultdict(Counter), dlc=Counter(),
             writes=defaultdict(list), reads=defaultdict(list), resps=defaultdict(list),
             aborts=Counter(), frames=0, t0=None, t1=None)
    for t, cid, d in _iter(path):
        c["frames"] += 1
        c["dlc"][len(d)] += 1
        c["t0"] = t if c["t0"] is None else min(c["t0"], t)
        c["t1"] = t if c["t1"] is None else max(c["t1"], t)
        if 0x600 < cid <= 0x67F:
            c["kinds"]["rx"] += 1
            c["nodes"][cid - 0x600] += 1
            if len(d) >= 8:
                n, idx, sub, cmd = cid - 0x600, d[1] | (d[2] << 8), d[3], d[0]
                if cmd in WRITE_CMD:
                    c["writes"][(n, idx, sub)].append((t, _sval(d[4:8], WRITE_CMD[cmd])))
                elif cmd == 0x40:
                    c["reads"][(n, idx, sub)].append(t)
        elif 0x580 < cid <= 0x5FF:
            c["kinds"]["tx"] += 1
            if len(d) >= 8:
                n, idx, sub, cmd = cid - 0x580, d[1] | (d[2] << 8), d[3], d[0]
                if cmd in RESP_SIZE:
                    c["resps"][(n, idx, sub)].append((t, _sval(d[4:8], RESP_SIZE[cmd])))
                elif cmd == 0x80:
                    c["aborts"][(n, idx, sub, struct.unpack("<I", d[4:8])[0])] += 1
        elif 0x700 <= cid <= 0x77F:
            c["kinds"]["guard"] += 1
            c["guard"][cid - 0x700][d.hex()] += 1
        elif cid in (0x000, 0x080) or 0x080 < cid <= 0x0FF or 0x180 <= cid <= 0x57F:
            c["kinds"]["other"] += 1
    c["dur"] = c["t1"] - c["t0"]
    return c


# ══ 비트 스터핑 포함 버스 부하 ════════════════════════════════════════════
def _crc15(bits):
    crc = 0
    for b in bits:
        inv = b ^ ((crc >> 14) & 1)
        crc = (crc << 1) & 0x7FFF
        if inv:
            crc ^= 0x4599
    return crc


def _frame_bits(cid, data):
    b = [0] + [(cid >> i) & 1 for i in range(10, -1, -1)] + [0, 0, 0]
    b += [(len(data) >> i) & 1 for i in range(3, -1, -1)]
    for by in data:
        b += [(by >> i) & 1 for i in range(7, -1, -1)]
    crc = _crc15(b)
    return b + [(crc >> i) & 1 for i in range(14, -1, -1)]


def _stuffed(b):
    n, run = len(b), 1
    for i in range(1, len(b)):
        if b[i] == b[i - 1]:
            run += 1
            if run == 5:
                n += 1
                run = 1
        else:
            run = 1
    return n


def bus_load():
    """구간별 (프레임, 길이, fps, 실부하%) 와 스터핑 오버헤드."""
    seg = {"A": (0, 5.15), "B": (5.15, 17.80), "C": (17.80, 1e9), "ALL": (0, 1e9)}
    acc = {k: [0, 0, None, None] for k in seg}
    raw_total = stuffed_total = 0
    for t, cid, d in _iter(CAP):
        bits = _frame_bits(cid, d)
        tail = 1 + 2 + 7 + 3                       # CRC델리미터+ACK+EOF+IFS (스터핑 대상 아님)
        raw_total += len(bits) + tail
        total = _stuffed(bits) + tail
        stuffed_total += total
        for k, (lo, hi) in seg.items():
            if lo <= t < hi:
                a = acc[k]
                a[0] += total
                a[1] += 1
                a[2] = t if a[2] is None else min(a[2], t)
                a[3] = t if a[3] is None else max(a[3], t)
    out = {}
    for k, (bits, n, t0, t1) in acc.items():
        dur = t1 - t0
        out[k] = (n, dur, n / dur, bits / dur / 250000 * 100)
    return out, (stuffed_total / raw_total - 1) * 100


# ══ [실측] 검증 ═══════════════════════════════════════════════════════════
def verify_capture(c):
    dur, f = c["dur"], c["frames"]
    doc_values("§전체 「N 프레임」 표기 전량", r"([\d,]+) 프레임", {f"{f:,}"})
    check("§4-2 구간 179.97 s", near(dur, 179.966, 0.005), f"{dur:.3f}")
    check("§4-2 전체 fps 1,409", round(f / dur) == 1409, f"{f/dur:.0f}")

    check("§2-2 SDO 요청 121,721", c["kinds"]["rx"] == 121721, str(c["kinds"]["rx"]))
    check("§2-2 SDO 응답 118,333", c["kinds"]["tx"] == 118333, str(c["kinds"]["tx"]))
    check("§2-2 Guard 13,456", c["kinds"]["guard"] == 13456, str(c["kinds"]["guard"]))
    check("§2-2 NMT/EMCY/PDO 0건", c["kinds"]["other"] == 0, str(c["kinds"]["other"]))
    check("§2-2 노드 1·2·3·4 뿐", sorted(c["nodes"]) == [1, 2, 3, 4], str(sorted(c["nodes"])))
    claim("§2-2 표기", "121,721", "118,333", "13,456", "3,388건 적다")
    check("§1 DLC 8=240,054 · 1=13,456", c["dlc"][8] == 240054 and c["dlc"][1] == 13456,
          f"8→{c['dlc'][8]} 1→{c['dlc'][1]}")
    claim("§1 DLC 표기", "240,054", "13,456")

    # ── §2-3 두절 ──
    req = Counter(); resp = Counter(); grd = Counter()
    for t, cid, d in _iter(CAP):
        seg = "A" if t < 5.15 else ("B" if t < 17.80 else "C")
        if 0x600 < cid <= 0x67F: req[seg] += 1
        elif 0x580 < cid <= 0x5FF: resp[seg] += 1
        elif 0x700 <= cid <= 0x77F: grd[seg] += 1
    want = {"A": (4359, 4360, 481), "B": (3399, 10, 3), "C": (113963, 113963, 12972)}
    for s, (wq, wr, wg) in want.items():
        check(f"§2-3 구간 {s} 요청/응답/guard = {wq:,}/{wr:,}/{wg:,}",
              (req[s], resp[s], grd[s]) == (wq, wr, wg), f"{req[s]}/{resp[s]}/{grd[s]}")
    check("§2-3 두절 무응답 3,389", req["B"] - resp["B"] == 3389, str(req["B"] - resp["B"]))
    check("§2-3 A·C 무응답 0", req["A"] - resp["A"] <= 0 and req["C"] == resp["C"], "")
    claim("§2-3 표기", "12.65 s", "3,389", "12.65 s 전노드 두절")

    # ── §4-2 버스 부하 ──
    loads, overhead = bus_load()
    for k, want_pct, want_fps in (("A", 85.4, 1798), ("B", 13.4, 270), ("C", 70.5, 1485), ("ALL", 66.9, 1409)):
        n, d_, fps, pct = loads[k]
        check(f"§4-2 부하 {k} = {want_pct} %", near(pct, want_pct, 0.05), f"{pct:.1f}")
        check(f"§4-2 fps {k} = {want_fps}", round(fps) == want_fps, f"{fps:.0f}")
    check("§4-2 스터핑 오버헤드 +9.98 %", near(overhead, 9.98, 0.01), f"{overhead:.2f}")
    claim("§4-2 부하 표기", "85.4 %", "13.4 %", "66.9 %", "27,386,074", "30,118,076")
    # 다중 등장 사각 메우기 — 같은 값이 여러 곳에 나오므로 **전량**을 뽑아 대조한다.
    doc_values("§전체 굵은 백분율 전량(정상구간 부하)", r"\*\*(\d+\.\d) %\*\*", {"70.5"})
    doc_values("§전체 스터핑 오버헤드 전량", r"\*\*\+(\d+\.\d+) %\*\*", {"9.98"})
    doc_values("§4-2 부하표 fps 열 전량", r"\| ([\d,]+) \| [\d.]+ %", {"1,798", "270", "1,409"})
    doc_values("§전체 굵은 1바이트 hex 전량(DI 값)", r"\*\*`(0x[0-9A-Fa-f]{2})`\*\*", {"0x03", "0x09"})
    doc_values("§전체 3,3xx 계열 전량(guard·요청·무응답)", r"(3,3\d\d)", {"3,364", "3,388", "3,389", "3,399"})

    # ── §4-2 지연 (읽기 / 쓰기 ack 분리) ──
    def latency(kind):
        lat = []
        acks = defaultdict(list)
        if kind == "ack":
            for t, cid, d in _iter(CAP):
                if 0x580 < cid <= 0x5FF and len(d) >= 8 and d[0] == 0x60:
                    acks[(cid - 0x580, d[1] | (d[2] << 8), d[3])].append(t)
            targets = acks
        else:
            targets = c["resps"]
        for key, rs in targets.items():
            qs = sorted(c["reads"].get(key, []) + [t for t, _ in c["writes"].get(key, [])])
            i = 0
            for item in rs:
                t = item if kind == "ack" else item[0]
                while i + 1 < len(qs) and qs[i + 1] <= t:
                    i += 1
                if i < len(qs) and qs[i] <= t:
                    lat.append(t - qs[i])
        lat.sort()
        return lat

    lr = latency("read")
    check("§4-2 읽기 지연 n=80,175", len(lr) == 80175, str(len(lr)))
    for name, got, want in zip(("평균", "중앙", "p95", "p99", "최대"),
                               (sum(lr) / len(lr) * 1000, lr[len(lr) // 2] * 1000,
                                lr[int(len(lr) * .95)] * 1000, lr[int(len(lr) * .99)] * 1000, lr[-1] * 1000),
                               (0.980, 0.900, 2.300, 5.700, 26.500)):
        check(f"§4-2 읽기 지연 {name} {want:.3f} ms", near(got, want, 0.0005), f"{got:.3f}")
    la = latency("ack")
    check("§4-2 쓰기 ack 평균 1.224 ms", near(sum(la) / len(la) * 1000, 1.224, 0.002),
          f"{sum(la)/len(la)*1000:.3f} (n={len(la)})")
    check("§4-2 쓰기 ack 최대 26.000 ms", near(la[-1] * 1000, 26.000, 0.001), f"{la[-1]*1000:.3f}")
    claim("§4-2 지연 표기", "0.980 ms", "1.224 ms", "26.500", "26.000", "n = 80,175", "n = 38,158")

    check("§4-3 주 캡처 abort 0건", sum(c["aborts"].values()) == 0, str(sum(c["aborts"].values())))

    # ── §10-1 폴링 ──
    want = {(1, 0x6064): 18560, (2, 0x6064): 18368, (3, 0x6064): 18071, (4, 0x6064): 18070,
            (1, 0x6041): 420, (2, 0x6041): 420, (3, 0x6041): 1975, (4, 0x6041): 1971}
    for (n, idx), v in want.items():
        got = len(c["reads"].get((n, idx, 0), []))
        check(f"§10-1 n{n} 0x{idx:04X} {v:,}회", got == v, str(got))
    check("§10-1 0x603F·0x6078·0x6000:01 = 421/노드",
          all(len(c["reads"].get((n, i, 1 if i == 0x6000 else 0), [])) == 421
              for n in (1, 2, 3, 4) for i in (0x603F, 0x6078, 0x6000)), "")
    check("§10-1 n3 0x6064 응답 16,811", len(c["resps"][(3, 0x6064, 0)]) == 16811,
          str(len(c["resps"][(3, 0x6064, 0)])))
    claim("§10-1 표기", "18,560", "18,368", "18,071", "18,070", "1,975", "1,971", "16,811건")

    # ── §6-4 Controlword ──
    cw1 = c["writes"][(1, 0x6040, 0)]
    check("§6-4 구동 0x6040 106회 전부 0x86", len(cw1) == 106 and all(v == 0x86 for _, v in cw1), str(len(cw1)))
    in_gap = sum(1 for t, _ in cw1 if 5.15 <= t < 17.80)
    check("§6-4 구동 0x86 중 105회가 두절 구간", in_gap == 105, str(in_gap))
    span = cw1[-1][0] - cw1[0][0]
    check("§6-4 구동 0x86 평균 간격 119.4 ms", near(span / (len(cw1) - 1) * 1000, 119.4, 0.05),
          f"{span/(len(cw1)-1)*1000:.1f}")
    for n in (3, 4):
        cw = Counter(v for _, v in c["writes"][(n, 0x6040, 0)])
        check(f"§6-4 조향 n{n} 0x3F 6,464 · 0x86 2", cw[0x3F] == 6464 and cw[0x86] == 2, str(dict(cw)))
        check(f"§6-4 n{n} 0x800F 0회", 0x800F not in cw, "")
    check("§10-2 구동 0x60FF 6,360회 전부 0",
          len(c["writes"][(1, 0x60FF, 0)]) == 6360 and all(v == 0 for _, v in c["writes"][(1, 0x60FF, 0)]), "")
    pre = [t for t, _ in c["writes"][(1, 0x60FF, 0)] if t < 18]
    gaps = [b - a for a, b in zip(pre, pre[1:])]
    check("§10-2 구동 0x60FF 최대 간격 12,549 ms", near(max(gaps) * 1000, 12549, 1), f"{max(gaps)*1000:.0f}")
    claim("§6-4·§10-2 표기", "106회", "105회(99 %)", "6,464회", "6,360", "12,549 ms", "119.4 ms")

    # ── §10-3 0x607A 분포·런 ──
    for n, hi, lo in ((3, 7882020, 7871815), (4, 7859062, 7840086)):
        xs = c["writes"][(n, 0x607A, 0)]
        dist = Counter(v for _, v in xs)
        check(f"§10-3 n{n} {hi:,}×6,319 / {lo:,}×145", dist[hi] == 6319 and dist[lo] == 145, str(dict(dist)))
        runs, prev = [], None
        for t, v in xs:
            if v != prev:
                runs.append([v, t, t, 1]); prev = v
            else:
                runs[-1][2] = t; runs[-1][3] += 1
        check(f"§10-3 n{n} 런 4개", len(runs) == 4, str([(r[0], r[3]) for r in runs]))
        check(f"§10-3 n{n} 마지막 런 6,072회", runs[-1][3] == 6072, str(runs[-1][3]))
    doc_values("§10-3 「N (백분율 %)」 전량", r"([\d,]+) \(\d+\.\d %\)", {"6,319", "145"})
    doc_values("§전체 7자리 조향 counts 전량", r"(7,8\d\d,\d\d\d)",
               {"7,882,020", "7,871,815", "7,859,062", "7,840,086",
                "7,882,001", "7,882,008", "7,859,065", "7,859,058",
                "7,872,820", "7,881,981"})

    # ── §9-2 타임라인 (인쇄 문자열 대조) ──
    tl = {}
    for n in (3, 4):
        chain, prev = [], None
        for t, v in c["resps"][(n, 0x6041, 0)]:
            v &= 0xFFFF
            if v != prev:
                chain.append((t, v)); prev = v
        tl[n] = chain
        check(f"§6-4 n{n} Statusword 전이 6단계", len(chain) == 6,
              " → ".join(f"0x{v:04X}@{t:.3f}" for t, v in chain))
    for n in (1, 2):
        vals = {v & 0xFFFF for _, v in c["resps"][(n, 0x6041, 0)]}
        check(f"§6-4 구동 n{n} 0x8050 고정", vals == {0x8050}, str([hex(v) for v in vals]))

    t3 = lambda x: f"{x:.3f}"
    di = {n: c["resps"][(n, 0x6000, 1)] for n in (3, 4)}
    cw86 = {n: [t for t, v in c["writes"][(n, 0x6040, 0)] if v == 0x86] for n in (3, 4)}
    zero0 = {n: next(t for t, v in c["resps"][(n, 0x6064, 0)] if v == 0) for n in (3, 4)}
    di_set = {n: next(t for t, v in di[n] if v == 9) for n in (3, 4)}
    di_clr = {n: next(t for t, v in di[n] if v == 1 and t > di_set[n]) for n in (3, 4)}
    rows = [
        ("0x86 1회차", f"{t3(cw86[3][0])} / {t3(cw86[4][0])}"),
        ("0x6099", f"{t3(c['writes'][(3,0x6099,0)][0][0])} / {t3(c['writes'][(4,0x6099,0)][0][0])}"),
        ("0x60FB:04", f"{t3(c['writes'][(3,0x60FB,4)][0][0])} / {t3(c['writes'][(4,0x60FB,4)][0][0])}"),
        ("0x6064→0", f"{t3(zero0[3])} / {t3(zero0[4])}"),
        ("bit15 1→0", f"{t3(tl[3][1][0])} / {t3(tl[4][1][0])}"),
        ("DI 물림", f"{t3(di_set[3])} / {t3(di_set[4])}"),
        ("bit15 0→1", f"{t3(tl[3][3][0])} / {t3(tl[4][3][0])}"),
        ("0x86 2회차", f"{t3(cw86[3][1])} / {t3(cw86[4][1])}"),
        ("0x607A 재개", f"{t3(next(t for t,_ in c['writes'][(3,0x607A,0)] if t>49))} / "
                        f"{t3(next(t for t,_ in c['writes'][(4,0x607A,0)] if t>49))}"),
        ("DI 해제", f"{t3(di_clr[3])} / {t3(di_clr[4])}"),
        ("목표 도달", f"{t3(tl[3][-1][0])} / {t3(tl[4][-1][0])}"),
    ]
    for label, s in rows:
        check(f"§9-2 타임라인 「{label}」 = {s}", s in DOC_TEXT, "문서에 이 시각 조합 없음")

    for n, want_dur in ((3, 31.154), (4, 31.074)):
        st = c["writes"][(n, 0x60FB, 4)][0][0]
        done = tl[n][3][0]
        check(f"§9-2 n{n} 개시→완료 {want_dur} s", near(done - st, want_dur, 0.001), f"{done-st:.3f}")
    check("§9-2 탐색 29.100 s", near(di_set[3] - c["writes"][(3, 0x60FB, 4)][0][0], 29.100, 0.002), "")

    # ── §9-3 동결 vs bit15 ──
    for n in (3, 4):
        zeros = [t for t, v in c["resps"][(n, 0x6064, 0)] if v == 0]
        check(f"§9-2 n{n} 0x6064=0 표본 3,115", len(zeros) == 3115, str(len(zeros)))
        check(f"§9-3 n{n} 동결 종료 49.178", near(zeros[-1], 49.178, 0.001), f"{zeros[-1]:.3f}")
        b15_end = tl[n][3][0]
        lag = (zeros[-1] - b15_end) * 1000
        check(f"§9-3 n{n} 동결이 bit15 보다 늦게 풀림", lag > 0, f"{lag:.0f} ms")
    claim("§9-3 지연 표기", "98~179 ms", "49.178")

    # ── §9-3 궤적 ──
    for want_t, want_v in ((49.747, 623699), (50.487, 2939853), (51.231, 5374613),
                           (52.339, 7872820), (52.715, 7881981)):
        got = [v for t, v in c["resps"][(3, 0x6064, 0)] if near(t, want_t, 0.0006)]
        check(f"§9-3 궤적 t={want_t} → {want_v:,}", bool(got) and got[0] == want_v, str(got))

    # ── §8 폴트 ──
    for n in (1, 2, 3, 4):
        vals = Counter(v for _, v in c["resps"][(n, 0x603F, 0)])
        check(f"§8 n{n} 0x603F 421표본 전부 0", vals == {0: 421}, str(dict(vals)))

    # ── §3-4 guard ──
    for n in (1, 2, 3, 4):
        tot = sum(c["guard"][n].values())
        check(f"§3-4 node{n} guard 3,364건", tot == 3364, str(tot))
    check("§3-4 guard 0xFF 1,683 / 0x7F 1,681",
          c["guard"][1]["ff"] == 1683 and c["guard"][1]["7f"] == 1681, str(dict(c["guard"][1])))

    # ── §7-3 DI ──
    for n in (3, 4):
        vals = Counter(v for _, v in c["resps"][(n, 0x6000, 1)])
        check(f"§7-3 조향 n{n} DI {{1:414, 9:6}}", dict(vals) == {1: 414, 9: 6}, str(dict(vals)))
    for n in (1, 2):
        vals = {v for _, v in c["resps"][(n, 0x6000, 1)]}
        check(f"§7-3 구동 n{n} DI 전 구간 0x01", vals == {1}, str(vals))


def verify_cross_captures():
    """§7-3·§9-4 — 다른 캡처가 주장을 반증하지 않는지 확인한다."""
    for p in CAP_NOMOVE:
        di3 = Counter(); sw = Counter(); pos = Counter(); rst = []
        for t, cid, d in _iter(p):
            if len(d) < 8:
                continue
            idx = d[1] | (d[2] << 8)
            if 0x600 < cid <= 0x67F and d[0] == 0x2F and idx == 0x60FB and d[3] == 4:
                rst.append((cid - 0x600, d[4]))
            if cid == 0x583 and d[0] == 0x4F and idx == 0x6000 and d[3] == 1:
                di3[d[4]] += 1
            if cid in (0x583, 0x584) and d[0] == 0x4B and idx == 0x6041:
                sw[int.from_bytes(d[4:6], "little")] += 1
            if cid in (0x583, 0x584) and d[0] == 0x43 and idx == 0x6064:
                pos[struct.unpack("<i", d[4:8])[0]] += 1
        name = p.name
        check(f"§9-4 {name}: 0x60FB:04=1 기록됨", any(v == 1 for _, v in rst), str(rst))
        check(f"§9-4 {name}: statusword 0x9450 무전이", set(sw) == {0x9450}, str([hex(v) for v in sw]))
        check(f"§9-4 {name}: 0x6064 전량 0", set(pos) == {0}, str(list(pos)[:3]))
        check(f"§7-3 {name}: n3 DI = 0x03", set(di3) == {3}, str(dict(di3)))
    claim("§9-4 표기", "20,654 표본", "24,431 표본", "516 표본", "1,575 표본")
    claim("§7-3 다른 캡처 DI 표기", "258 표본", "787 표본")
    doc_values("§7-3 다른 캡처 DI 값 전량", r"n3 가 \*\*`(0x\d\d)`\*\*", {"0x03"})
    doc_values("§12 #8 실측 유휴값 전량", r"실측 유휴값 `0x01`·`(0x\d\d)`", {"0x03"})
    doc_values("§9-1 0x609A 리드백 전량", r"`0x609A` Homing acceleration \| (\d+)", {"100"})

    # §9-1 드라이브 리드백
    d = json.loads(CAP_DIAG.read_text())
    nodes = d.get("nodes", {})
    for n in ("3", "4"):
        check(f"§9-1 node{n} 0x6098 = 1", nodes.get(n, {}).get("6098.0") == 1, str(nodes.get(n, {}).get("6098.0")))
        check(f"§9-1 node{n} 0x609A = 100", nodes.get(n, {}).get("609A.0") == 100, "")
        check(f"§9-1 node{n} 0x607C = 0", nodes.get(n, {}).get("607C.0") == 0, "")

    # §4-3 abort
    ab = Counter()
    for t, cid, dd in _iter(CAP_DIAG_CAN):
        if 0x580 < cid <= 0x5FF and len(dd) >= 8 and dd[0] == 0x80:
            ab[(dd[1] | (dd[2] << 8), struct.unpack("<I", dd[4:8])[0])] += 1
    check("§4-3 diag 캡처 abort 10건", sum(ab.values()) == 10, str(sum(ab.values())))
    check("§4-3 abort 인덱스 0x20F1~0x20F5 · code 0x06020000",
          {k[0] for k in ab} == {0x20F1, 0x20F2, 0x20F3, 0x20F4, 0x20F5} and {k[1] for k in ab} == {0x06020000},
          str(sorted(ab)))
    claim("§4-3 표기", "abort 10건", "`0x20F1`~`0x20F5`", "`0x06020000`")


def verify_drive():
    rows = list(csv.DictReader(open(DRIVE)))
    segs, cur = [], None
    for r in rows:
        if cur is None or r["phase"] != cur[0]:
            segs.append([r["phase"], []]); cur = segs[-1]
        cur[1].append(r)
    got = {}
    for ph, rs in segs:
        tail = rs[len(rs) // 2:]
        got[ph] = (sum(float(x["n1_vel"]) for x in tail) / len(tail),
                   sum(float(x["n2_vel"]) for x in tail) / len(tail))
    for ph, (w1, w2) in (("fwd", (-1259.4, -1265.9)), ("bwd", (1220.8, 1230.6))):
        check(f"§11-2 {ph} n1={w1}", near(got[ph][0], w1, 0.05), f"{got[ph][0]:.1f}")
        check(f"§11-2 {ph} n2={w2}", near(got[ph][1], w2, 0.05), f"{got[ph][1]:.1f}")
    check("§11-2 기대 1,222.3 units", near(50 * 24.447, 1222.3, 0.05), "")
    claim("§11-2 표기", "1,259.4", "1,265.9", "1,220.8", "1,230.6", "1,222.3")


def verify_scale_is_config():
    """§11-1 — counts/° 가 [설정] 이고 순환임을 문서가 밝히는지, 그 근거가 실재하는지."""
    check("§11-1 등급이 [설정] 로 표기됨", "[설정] ⚠ **[실측] 이 아니다**" in DOC_TEXT, "")
    check("§11-1 순환 경고 존재", "순환이었다 — 인용 금지" in DOC_TEXT, "")
    check("§11-1 유도식 표기", "16,384 × 4(체배) × 315 / 360 = 57,344" in DOC_TEXT, "")
    check("§11-1 산술 57,344", 16384 * 4 * 315 / 360 == 57344, "")
    check("§11-1 315 검산", near(57344 * 360 / 65536, 315.0, 1e-9), "")
    for f in ("frontsteer1.png", "frontsteer2.png"):
        check(f"§11-1 1차 source {f} 실재", (ROOT / "References/motor_configuration" / f).exists(), "")
    if SWEEP_TOOL.exists():
        src = SWEEP_TOOL.read_text(errors="replace")
        check("§11-1 스윕 도구가 deg × CPD 로 지령(순환 근거)",
              "HOME_0DEG[node] + deg * CPD" in src, "")
    check("§0-4 DLC 0 필터 근거 실재",
          CAPTURE_TOOL.exists() and "if bus != MOTOR_BUS or not dat:" in CAPTURE_TOOL.read_text(errors="replace"), "")
    check("§0-4 250 kbps 근거 실재",
          CAPTURE_TOOL.exists() and "CAN_KBPS = 250" in CAPTURE_TOOL.read_text(errors="replace"), "")


# ══ [규격] 검증 ═══════════════════════════════════════════════════════════
def page_index(path: Path, footer_marker: str):
    lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    marks = [(i, int(l.strip())) for i, l in enumerate(lines)
             if re.fullmatch(r"\d{1,3}", l.strip()) and i + 1 < len(lines) and footer_marker in lines[i + 1]]
    pages, start = {}, 0
    for i, pg in marks:
        pages[pg] = re.sub(r"\s+", " ", " ".join(lines[start:i + 1]))
        start = i + 1
    return pages


# (판본, 페이지, 원문 문구, 라벨)
SPEC_CLAIMS = [
    ("V7.0", 33, "USRC_DI5", "§9-1 DI5 Home 원점 신호"),
    ("V7.0", 33, "USRC_DI8", "§9-1 DI8 호밍 기동"),
    ("V7.0", 116, "SelfSofRst.uwRstMode", "§9-1 Modbus 파라미터 표"),
    ("V7.0", 116, "exceeds more than 120S", "§9-1 120 s 제한"),
    ("V7.0", 117, "Start homing: Write SelfSofRst.uwRstStart", "§9-1 Home 1 절차"),
    ("V7.0", 133, "default baud rate of the driver is", "§1 공장 기본 500 kbps"),
    ("V7.0", 135, "can_Para_CHANGED.BAUDRATE", "§1 보드레이트 Modbus 0x4670"),
    ("V7.0", 137, "Position of CANopen Identifier and Data in CAN frame", "§1 11-bit ID + 8-byte"),
    ("V7.0", 138, "up to 127 slave", "§1 최대 슬레이브 127"),
    ("V7.0", 138, "always contain 8 bytes", "§4-1 DLC 항상 8"),
    ("V7.0", 138, "must have an answer", "§4-1 요청에 반드시 응답"),
    ("V7.0", 139, "Error_Code", "§4-1 abort 구조표"),
    ("V7.0", 141, "6.3 Bus Management NMT Message", "§3-1 NMT"),
    ("V7.0", 142, "6.4.1 Heartbeat", "§3-2 Heartbeat"),
    ("V7.0", 143, "without powering off the motor", "§3-3 V7.0 모터 전원 유지 문구"),
    ("V7.0", 144, "the trigger bit. Each node", "§3-3 토글 비트"),
    ("V7.0", 145, "6.5 Device Flag Message", "부록 §6.5"),
    ("V7.0", 149, "6.6.1 Controlword", "§6-1 Controlword"),
    ("V7.0", 150, "Reset Home is the motor homing", "§6-1 bit15"),
    ("V7.0", 150, "6.6.2 Statusword", "§6-2 Statusword"),
    ("V7.0", 151, "Bit8", "§6-2 bit8 Reserve"),
    ("V7.0", 152, "6.6.3 Modes of Operation", "§6-3 운전 모드"),
    ("V7.0", 152, "Max slippage error", "§6-2 bit12-13 세부"),
    ("V7.0", 153, "6.6.4 Error Code", "§8 폴트"),
    ("V7.0", 154, "Motor overheating", "§12 #4 V7.0 상세표 뒤바뀜"),
    ("V7.0", 156, "6.7.1 SDO Reading", "§4-1 SDO 읽기"),
    ("V7.0", 156, "6.7.2 SDO Writing", "§4-1 SDO 쓰기"),
    ("V7.0", 157, "little-endian mode", "§1 little-endian"),
    ("V7.0", 157, "Master 60A", "§4-1 예제"),
    ("V7.0", 158, "6.8 PDO Communication", "§5 NMT Start 필요"),
    ("V7.0", 160, "meets the standard CANOPEN 301/402", "§1 CiA301/402"),
    ("V7.0", 161, "SDO address: 0x67FF", "§12 #5 RPDO3 오기"),
    ("V7.0", 162, "TPDO4", "§5 TPDO2~4 매핑"),
    ("V7.0", 171, "0-Home off, 1-37", "§12 #2 §6.9 범위"),
    ("V7.0", 190, "6.17 Dynamic Configuration of PDO Mapping", "§12-1 §6.17 은 신설 아님"),
    ("V7.0", 194, "0x800F", "§6-1 지령값 사전"),
    ("V7.0", 194, "Battery alarm", "§12 #3 Appendix I bit14"),
    ("V7.0", 195, "Position_actual_Angle_value", "§7-2·§11-1 0x6064 정의"),
    ("V7.0", 196, "1-35Reset mode", "§12 #2 Appendix I 범위"),
    ("V7.0", 197, "Read Input 1h to 8h State", "§7-3 0x6000:01"),
    ("V7.0", 197, "Transmission Type, initial value is 255", "§5 전송타입 255"),
    ("V7.0", 198, "Inhibit Time, 0-No Inhibit Time, Unit: 100us", "§5 inhibit 단위"),
    ("V7.0", 198, "MotoTemp", "§7-2 0x2301"),
    ("V7.0", 205, "can_Para_CHANGED.BAUDRATE", "§1 Appendix II 재수록"),
    ("7.9", 45, "USRC_DI5", "§9-1 [7.9] DI5"),
    ("7.9", 46, "USRC_DI8", "§9-1 [7.9] DI8"),
    ("7.9", 61, "USRC_DI5", "§9-1 [7.9] §2.9 단자표"),
    ("7.9", 108, "回零操作", "부록 [7.9] §4.6"),
    ("7.9", 120, "0x4670", "§1 [7.9] 보드레이트"),
    ("7.9", 122, "6.2 CANopen 通信简介", "부록 [7.9] §6.2"),
    ("7.9", 125, "6.3 总线管理 NMT 报文", "부록 [7.9] §6.3"),
    ("7.9", 126, "驱动报警（通讯超时）", "§3-3 통신 타임아웃 알람"),
    ("7.9", 132, "6.6.1 控制字", "부록 [7.9] Controlword"),
    ("7.9", 133, "6.6.2 状态字", "§12 #3 [7.9] Statusword"),
    ("7.9", 134, "Home attend", "§12 #10 [7.9] Home attend 철자"),
    ("7.9", 135, "0x603F（0x0020）", "§8 [7.9] 폴트 요약표"),
    ("7.9", 135, "6.6.3 模式控制", "부록 [7.9] 운전 모드"),
    ("7.9", 136, "驱动器内部温度过高", "§8 [7.9] 폴트 상세표(해소 근거)"),
    ("7.9", 137, "通讯超时", "§8 [7.9] 0x8005 상세 신설"),
    ("7.9", 138, "6.7 SDO 通信", "부록 [7.9] SDO"),
    ("7.9", 141, "6.8.3 驱动器默认 PDO 映射", "부록 [7.9] PDO 매핑"),
    ("7.9", 142, "SDO 地址：0x67FF", "§12 #5 [7.9] 잔존"),
    ("7.9", 149, "1-37 回零模式", "§12 #2 [7.9] §6.9"),
    ("7.9", 164, "6.17 用 EasyDRIVE", "부록 [7.9] §6.17"),
    ("7.9", 166, "回零操作为上升沿", "§6-1 상승 에지"),
    ("7.9", 166, "Bit14:Battery alarm", "§12 #3 [7.9] bit14"),
    ("7.9", 167, "Motor_rate_ current", "§12 #6 0x6075"),
    ("7.9", 167, "电机绝对位置反馈", "§12-1 0x6064 서술"),
    ("7.9", 167, "立即速度模式", "§12-1 0x6061 -3"),
    ("7.9", 168, "1-35 复位模式", "§12 #2 [7.9] Appendix I"),
    ("7.9", 168, "Read Input 1h to 8h State", "§12 #8 0x6000:01"),
    ("7.9", 170, "附录二：MODBUS", "부록 [7.9] Appendix II"),
]

# 「그 판에 **없다**」는 주장 — (판본, 있으면 안 되는 문구, 라벨)
ABSENT_CLAIMS = [
    ("V7.0", "回零操作为上升沿", "§12-1 상승 에지는 V7.0 에 없음"),
    ("V7.0", "Start home operation (", "§12-1 V7.0 0x800F 에 에지 단서 없음"),
    ("V7.0", "立即速度模式", "§12-1 0x6061 -3 은 V7.0 에 없음"),
    ("V7.0", "通讯超时", "§12-1 0x8005 상세는 V7.0 에 없음"),
    ("7.9", "0xBF", "§12 #8 7.9 는 0xBF 기본값 문구 삭제"),
    ("V7.0", "6502", "§12-2 0x6502 는 V7.0 매뉴얼에 없음"),
    ("7.9", "6502", "§12-2 0x6502 는 7.9 매뉴얼에도 없음"),
]


def verify_spec():
    src = {}
    if MAN_V70.exists():
        src["V7.0"] = page_index(MAN_V70, "Handbook V5.6")
    if MAN_V79.exists():
        src["7.9"] = page_index(MAN_V79, "WWW.TYZDH.COM.CN")
    full = {"V7.0": MAN_V70.read_text(errors="replace") if MAN_V70.exists() else "",
            "7.9": MAN_V79.read_text(errors="replace") if MAN_V79.exists() else ""}

    for edition, page, needle, label in SPEC_CLAIMS:
        if edition not in src:
            check(f"[{edition}] {label}", False, "매뉴얼 텍스트 없음")
            continue
        n = norm(needle)
        found = sorted(pg for pg, body in src[edition].items() if n in body)
        check(f"[{edition} p{page}] {label}", page in found, f"실제 페이지 {found}")

    for edition, needle, label in ABSENT_CLAIMS:
        present = norm(needle) in norm(full[edition])
        check(f"[{edition} 부재] {label}", not present, "그 판에 실재한다 — 부재 주장이 거짓")

    # 문서가 인용한 page 번호가 전부 검증표에 덮이는가
    # 한 줄에 두 판본 쪽수가 함께 오므로, `page N` 바로 앞의 가장 가까운 판본 마커로 귀속한다.
    cited = {"V7.0": set(), "7.9": set()}
    for line in DOC_TEXT.splitlines():
        for m in re.finditer(r"page (\d{1,3})", line):
            before = line[:m.start()]
            i79, i70 = before.rfind("[7.9]"), max(before.rfind("V7.0"), before.rfind("[규격]"))
            cited["7.9" if i79 > i70 else "V7.0"].add(int(m.group(1)))
    for e in ("V7.0", "7.9"):
        covered = {p for ed, p, _, _ in SPEC_CLAIMS if ed == e}
        miss = cited[e] - covered
        check(f"§전체 {e} 인용 페이지가 검증표에 덮임", not miss, f"미검증 {sorted(miss)}")


def verify_eds():
    def parse(p):
        d, cur = {}, None
        for l in open(p, encoding="utf-8", errors="replace"):
            l = l.strip()
            if l.startswith("[") and l.endswith("]"):
                cur = l[1:-1].upper(); d[cur] = {}; continue
            if cur and "=" in l:
                k, v = l.split("=", 1); d[cur][k.strip().upper()] = v.strip()
        return d
    o, n = parse(EDS_OLD), parse(EDS_NEW)
    check("§0-1 구판 EDS V4.32", o["DEVICEINFO"]["PRODUCTNAME"].endswith("V4.32"), "")
    check("§0-1 신판 EDS V4.44", n["DEVICEINFO"]["PRODUCTNAME"].endswith("V4.44"), "")
    check("§12-2 VendorName 변경",
          o["DEVICEINFO"]["VENDORNAME"] == "TONGYI Electric Ltd." and n["DEVICEINFO"]["VENDORNAME"] == "TONGYI Ltd.", "")
    idx = lambda d: {k for k in d if re.fullmatch(r"[0-9A-F]{4}", k)}
    check("§12-2 신설 인덱스", sorted(idx(n) - idx(o)) ==
          ["2300", "2301", "2400", "2401", "2402", "2403", "2404", "2405", "2406", "2407",
           "2408", "2409", "240A", "240B", "240C", "240D", "240E", "240F", "2FFF", "6502"], "")
    check("§12-2 삭제 인덱스", sorted(idx(o) - idx(n)) ==
          ["2000", "201A", "2074", "2075", "20F1", "20F2", "20F3", "20F4", "20F5", "2133", "213D"], "")
    check("§12-2 0x6502 기본값 0x0000006F", n["6502"]["DEFAULTVALUE"].lower() == "0x0000006f", "")

    # CiA402 모션 오브젝트 무변경
    motion = ["603F", "6040", "6041", "6060", "6061", "6064", "606C", "6071", "6078", "607A",
              "6081", "6083", "6084", "6098", "6099", "607C", "609A", "60FF", "6000", "60FB",
              "100C", "100D", "1017"]
    keys = ("PARAMETERNAME", "DATATYPE", "ACCESSTYPE", "DEFAULTVALUE", "PDOMAPPING")
    changed = [f"{s}.{k}" for i in motion
               for s in sorted({s for s in set(o) | set(n) if s.split("SUB")[0] == i})
               for k in keys if o.get(s, {}).get(k) != n.get(s, {}).get(k)]
    check("§12-2 CiA402 모션 오브젝트 무변경", not changed, str(changed))

    # ⚠ 통신·매핑 파라미터는 **바뀌었다** — 문서가 그 사실을 싣고 있는가
    comm = [f"1{x}" for x in ("600", "601", "602", "603", "800", "801", "802", "803",
                              "A00", "A01", "A02", "A03")]
    diffs = {f"{s}.{k}": (o.get(s, {}).get(k), n.get(s, {}).get(k))
             for i in comm
             for s in sorted({s for s in set(o) | set(n) if s.split("SUB")[0] == i.upper()})
             for k in keys if o.get(s, {}).get(k) != n.get(s, {}).get(k)}
    check("§12-2 통신·매핑 DefaultValue 18건 변경", len(diffs) == 18, f"{len(diffs)}건: {sorted(diffs)}")
    check("§12-2 TPDO2 에 0x2300/0x2301 매핑 추가",
          n.get("1A01SUB2", {}).get("DEFAULTVALUE", "").lower() == "0x23000010"
          and n.get("1A01SUB3", {}).get("DEFAULTVALUE", "").lower() == "0x23010010", "")
    claim("§12-2 표기", "`0x23000010`", "`0x23010010`", "DefaultValue 18건 변경")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    if not DOC.exists():
        print(f"문서 없음: {DOC}")
        return 2
    print(f"검토 대상: {DOC.relative_to(ROOT)}  ({len(DOC_TEXT.splitlines())}줄)\n")

    verify_capture(load(CAP))
    verify_cross_captures()
    verify_drive()
    verify_scale_is_config()
    verify_spec()
    verify_eds()

    if a.verbose:
        for p in PASSES:
            print(f"  ✓ {p}")
    print(f"\n통과 {len(PASSES)} · 불일치 {len(FAILS)}")
    if FAILS:
        print("\n불일치 목록:")
        for f in FAILS:
            print(f"  ✗ {f}")
        return 1
    print("**인쇄 수치·인용 좌표·부재 주장**이 원자료·매뉴얼과 일치한다.")
    print("⚠ 서술·해석·방향·안전 문구는 이 도구의 검사 대상이 아니다 — 문서 §0-3 참조.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
