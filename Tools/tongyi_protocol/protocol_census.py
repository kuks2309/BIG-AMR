#!/usr/bin/env python3
"""Tongyi 서보 CANopen — 실측 캡처에서 프로토콜 사실을 재계산한다.

`docs/tongyi_can_protocol/2026-08-05.md` 의 **[실측] 등급 수치는 전부 이 도구의 출력**이다.
문서를 근거로 문서를 고치지 않기 위해, 인용하려는 수치가 있으면 먼저 여기서 다시 센다.

사용:
    python3 Tools/tongyi_protocol/protocol_census.py Log/homing_capture_220350.jsonl
    python3 Tools/tongyi_protocol/protocol_census.py --steer Log/steer_two_phase_260803_131305.jsonl
    python3 Tools/tongyi_protocol/protocol_census.py --drive Log/field_2026-08-04/ros2_drive_trace_151700.csv

입력 형식
    CAN 캡처(.jsonl)  : {"t": <초>, "id": <CAN ID 10진>, "d": "<데이터 hex>"} 한 줄에 하나
    조향 스윕(.jsonl) : {"deg_cmd": <지령각>, "can": {"3": <counts>, "4": <counts>}, ...}
    구동 트레이스(.csv): t_mono,phase,cmd,n1_vel,n2_vel,n1_pos,n2_pos  (cmd 단위 mm/s)

프레임 해석 근거는 제조사 문서다 — SDO 명령어 바이트·응답 크기는
[IxLII/IxLs/IxH Servo Driver Handbook V7.0 §6.7.1-6.7.2, printed page 156]
(References/Tongyi-Motor-Controller/manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf).
"""
from __future__ import annotations

import argparse
import csv
import json
import struct
import sys
from collections import Counter, defaultdict

# Handbook §6.7.2 page 156 — 쓰기 명령어 바이트 → 유효 데이터 바이트 수
WRITE_CMD = {0x2F: 1, 0x2B: 2, 0x27: 3, 0x23: 4}
# Handbook §6.7.1 page 156 — 읽기 응답 명령어 바이트 → 유효 데이터 바이트 수
RESP_SIZE = {0x4F: 1, 0x4B: 2, 0x47: 3, 0x43: 4}
READ_REQ = 0x40
WRITE_ACK = 0x60
ABORT = 0x80

SDO_TX, SDO_RX, GUARD = 0x580, 0x600, 0x700


def _load(path):
    """캡처 한 줄씩 (t, can_id, data) 로 흘린다."""
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "id" not in r or "d" not in r:
                continue
            yield r.get("t"), r["id"], bytes.fromhex(r["d"]) if r["d"] else b""


def _signed(data, size):
    if size == 4:
        return struct.unpack("<i", data[:4])[0]
    return int.from_bytes(data[:size], "little")


def census(path):
    kinds = Counter()
    other = Counter()
    guard_data = defaultdict(Counter)
    guard_n = Counter()
    writes = defaultdict(list)      # (node, index, sub) -> [(t, value)]
    reads = defaultdict(list)       # (node, index, sub) -> [t]
    resps = defaultdict(list)       # (node, index, sub) -> [(t, value)]
    aborts = Counter()
    dlc = Counter()
    bits = frames = 0
    t0 = t1 = None

    for t, cid, d in _load(path):
        frames += 1
        dlc[len(d)] += 1
        # 표준 11-bit 데이터 프레임 비트수(스터핑 제외):
        # SOF1+ID11+RTR1+IDE1+r0_1+DLC4+데이터8L+CRC15+CRCdel1+ACK2+EOF7+IFS3
        bits += 1 + 11 + 1 + 1 + 1 + 4 + 8 * len(d) + 15 + 1 + 2 + 7 + 3
        if t is not None:
            t0 = t if t0 is None else min(t0, t)
            t1 = t if t1 is None else max(t1, t)

        if SDO_RX < cid <= SDO_RX + 0x7F:
            kinds["SDO 요청 (0x600+N)"] += 1
            if len(d) >= 8:
                n, idx, sub, cmd = cid - SDO_RX, d[1] | (d[2] << 8), d[3], d[0]
                if cmd in WRITE_CMD:
                    writes[(n, idx, sub)].append((t, _signed(d[4:8], WRITE_CMD[cmd])))
                elif cmd == READ_REQ:
                    reads[(n, idx, sub)].append(t)
        elif SDO_TX < cid <= SDO_TX + 0x7F:
            kinds["SDO 응답 (0x580+N)"] += 1
            if len(d) >= 8:
                n, idx, sub, cmd = cid - SDO_TX, d[1] | (d[2] << 8), d[3], d[0]
                if cmd in RESP_SIZE:
                    resps[(n, idx, sub)].append((t, _signed(d[4:8], RESP_SIZE[cmd])))
                elif cmd == ABORT:
                    aborts[(n, idx, sub, struct.unpack("<I", d[4:8])[0])] += 1
        elif GUARD <= cid <= GUARD + 0x7F:
            kinds["Guard/Heartbeat (0x700+N)"] += 1
            guard_n[cid - GUARD] += 1
            if d:
                guard_data[cid - GUARD][d.hex()] += 1
        elif cid == 0x000:
            kinds["NMT (0x000)"] += 1
        elif cid == 0x080:
            kinds["SYNC (0x080)"] += 1
        elif 0x080 < cid <= 0x0FF:
            kinds["EMCY (0x080+N)"] += 1
        elif 0x180 <= cid <= 0x57F:
            kinds["PDO 대역 (0x180~0x57F)"] += 1
            other[hex(cid)] += 1
        else:
            other[hex(cid)] += 1

    dur = (t1 - t0) if t0 is not None else 0.0
    print(f"\n파일 {path}")
    print(f"프레임 {frames:,} · 구간 {dur:.3f} s · 평균 {frames/dur:.0f} fps · DLC {dict(sorted(dlc.items()))}")

    print("\n[1] 프레임 종류")
    for k, v in kinds.most_common():
        print(f"    {k:28s} {v:8,}")
    for k in ("NMT (0x000)", "SYNC (0x080)", "EMCY (0x080+N)", "PDO 대역 (0x180~0x57F)"):
        if k not in kinds:
            print(f"    {k:28s} {0:8,}   ← 미관측")
    if other:
        print(f"    분류 밖 ID: {dict(other.most_common(8))}")

    print("\n[2] 버스 부하 (250 kbps 기준)")
    print(f"    스터핑 제외 {bits/dur/1000:6.1f} kbit/s = {bits/dur/250000*100:.1f} %")
    print(f"    스터핑 +20 % 가정 {bits*1.2/dur/1000:6.1f} kbit/s = {bits*1.2/dur/250000*100:.1f} %")

    print("\n[3] Guard 프레임 (0x700+N)")
    for n in sorted(guard_n):
        vals = dict(guard_data[n].most_common(4))
        print(f"    node{n}: {guard_n[n]:,}건 ({guard_n[n]/dur:.1f} Hz) 값 {vals}")

    print("\n[4] SDO 쓰기 — (node, index:sub) → 값 분포")
    for key in sorted(writes):
        n, idx, sub = key
        xs = writes[key]
        c = Counter(v for _, v in xs)
        print(f"    n{n} 0x{idx:04X}:{sub:02X}  총 {len(xs):6,}")
        for v, cnt in c.most_common(4):
            ts = [t for t, vv in xs if vv == v]
            print(f"          값 {v:>12,} ×{cnt:6,}  (t={ts[0]:.3f}~{ts[-1]:.3f})")

    print("\n[5] SDO 읽기 요청 — 폴링율")
    for key in sorted(reads):
        n, idx, sub = key
        cnt = len(reads[key])
        print(f"    n{n} 0x{idx:04X}:{sub:02X}  {cnt:7,}회  {cnt/dur:6.1f} Hz")

    print("\n[6] SDO Abort")
    if aborts:
        for (n, idx, sub, code), cnt in aborts.most_common():
            print(f"    n{n} 0x{idx:04X}:{sub:02X} abort=0x{code:08X} ×{cnt}")
    else:
        print("    0건")

    # ── SDO 왕복 지연: 응답 직전의 같은 (node,index,sub) 요청과 짝지어 잰다 ──
    lat, unmatched = [], 0
    for key, rs in resps.items():
        qs = reads.get(key, []) + [t for t, _ in writes.get(key, [])]
        qs.sort()
        i = 0
        for t, _ in rs:
            while i + 1 < len(qs) and qs[i + 1] <= t:
                i += 1
            if i < len(qs) and qs[i] <= t:
                lat.append(t - qs[i])
            else:
                unmatched += 1
    if lat:
        lat.sort()
        m = len(lat)
        print(f"\n[7] SDO 왕복 지연  n={m:,} (미매칭 {unmatched})")
        print(f"    평균 {sum(lat)/m*1000:.3f} ms · 중앙 {lat[m//2]*1000:.3f} · "
              f"p95 {lat[int(m*0.95)]*1000:.3f} · p99 {lat[int(m*0.99)]*1000:.3f} · 최대 {lat[-1]*1000:.3f}")

    print("\n[8] 호밍 타임라인")
    for key in sorted(writes):
        n, idx, sub = key
        if (idx, sub) in ((0x60FB, 4), (0x6099, 0)):
            for t, v in writes[key]:
                print(f"    n{n} 0x{idx:04X}:{sub:02X} = {v} write @ t={t:.4f}")
    for n in sorted({k[0] for k in resps}):
        sw = resps.get((n, 0x6041, 0), [])
        if sw:
            chain, prev = [], None
            for t, v in sw:
                v &= 0xFFFF
                if v != prev:
                    chain.append((t, v))
                    prev = v
            print(f"    n{n} 0x6041 전이: " + " → ".join(f"0x{v:04X}@{t:.3f}" for t, v in chain))
        di = resps.get((n, 0x6000, 1), [])
        if di:
            chain, prev = [], None
            for t, v in di:
                if v != prev:
                    chain.append((t, v))
                    prev = v
            print(f"    n{n} 0x6000:01 전이: " + " → ".join(f"0x{v:02X}@{t:.3f}" for t, v in chain))
        pos = resps.get((n, 0x6064, 0), [])
        if pos:
            z = [t for t, v in pos if v == 0]
            nz = [(t, v) for t, v in pos if v != 0]
            zs = f"값=0 {len(z):,}표본 (t={z[0]:.4f}~{z[-1]:.4f})" if z else "값=0 없음"
            print(f"    n{n} 0x6064 {len(pos):,}표본 · {zs}")
            if nz:
                tail = Counter(v for t, v in nz if t > pos[-1][0] * 0.4)
                print(f"          최초 비영 {nz[0][1]:,}@{nz[0][0]:.3f} · 후반 정착값 {dict(tail.most_common(3))}")


def steer_scale(path):
    """조향 지령각 → 0x6064 counts 최소제곱 기울기 = counts/°."""
    rows = [json.loads(l) for l in open(path) if l.strip()]
    groups = defaultdict(list)
    for r in rows:
        if "deg_cmd" in r and isinstance(r.get("can"), dict):
            groups[r.get("phase")].append((r["deg_cmd"], r["can"]))
    print(f"\n파일 {path}")
    for ph, pts in groups.items():
        for node in sorted({k for _, c in pts for k in c}):
            xs = [d for d, c in pts if node in c]
            ys = [c[node] for d, c in pts if node in c]
            if len(xs) < 3 or len(set(xs)) < 2:
                continue
            n = len(xs)
            mx, my = sum(xs) / n, sum(ys) / n
            sxx = sum((x - mx) ** 2 for x in xs)
            slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
            icept = my - slope * mx
            res = max(abs(y - (slope * x + icept)) for x, y in zip(xs, ys))
            print(f"    phase={ph} node{node}: n={n} 기울기 {slope:+,.3f} counts/° · "
                  f"절편 {icept:,.1f} c · 최대잔차 {res:.1f} c · 지령 {min(xs)}~{max(xs)}°")


def drive_track(path):
    """구동 속도 지령(mm/s) ↔ 0x606C 피드백(0.1 r/min) 추종 확인.

    구간 후반 50 % 만 평균해 가감속 램프를 뺀다.
    """
    UNITS_PER_MMPS = 24.447   # 기체 config 환산값 — 제조사 spec 아님
    rows = list(csv.DictReader(open(path)))
    segs, cur = [], None
    for r in rows:
        if cur is None or r["phase"] != cur[0]:
            segs.append([r["phase"], []])
            cur = segs[-1]
        cur[1].append(r)
    print(f"\n파일 {path}")
    for ph, rs in segs:
        tail = rs[len(rs) // 2:]
        try:
            cmd = float(tail[0].get("cmd", "") or "nan")
        except ValueError:
            cmd = float("nan")
        try:
            v1 = [float(x["n1_vel"]) for x in tail]
            v2 = [float(x["n2_vel"]) for x in tail]
        except (ValueError, KeyError):
            continue
        a1, a2 = sum(v1) / len(v1), sum(v2) / len(v2)
        line = (f"    phase={ph:8s} {float(rs[-1]['t_mono'])-float(rs[0]['t_mono']):5.1f}s "
                f"cmd={cmd:7.1f} mm/s → 0x606C n1={a1:9.1f} n2={a2:9.1f} (0.1 r/min)")
        if cmd == cmd and cmd:
            exp = abs(cmd) * UNITS_PER_MMPS
            line += f" · 기대 {exp:.1f} → n1 {abs(a1)/exp:.3f}× n2 {abs(a2)/exp:.3f}×"
        print(line)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", default="Log/homing_capture_220350.jsonl")
    ap.add_argument("--steer", metavar="JSONL", help="조향 스윕 캡처에서 counts/° 를 잰다")
    ap.add_argument("--drive", metavar="CSV", help="구동 트레이스에서 속도 추종을 잰다")
    a = ap.parse_args()
    if a.steer:
        steer_scale(a.steer)
    elif a.drive:
        drive_track(a.drive)
    else:
        census(a.path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
