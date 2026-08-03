#!/usr/bin/env python3
"""판다 실기 신원 조회 — 지금 장치에 올라간 이미지가 무엇인지 **장치에 묻는다**.

## 왜 있는가

`docs/claude-mistake/2026-07-28-011_device-state-claimed-from-staging-file.md`:
배포 스테이징 파일의 md5 만 보고 「실기에 플래시된 적 없다」고 단정했다가 실기 조회에서 정반대로 뒤집혔다.
⇒ **파일을 보고 장치를 말하지 않는다.** 장치 서명(`0xd3`+`0xd4`)을 읽어 저장소 후보와 대조한다.

또 2026-08-03 적대적 검증 F6: 그때 쓴 1회용 스크립트가 스크래치패드에 있어 **소실**됐고
`§3` 의 수치가 재현 불가가 됐다. 그래서 이 도구는 **저장소에 둔다.**

## 무엇을 대조하는가

`Panda.get_signature()` 는 플래시에 저장된 **128 B RSA 서명**을 돌려준다
(`panda/python/__init__.py:437-440`, 펌웨어 `board/usb_comms.h:227-243`).
서명은 이미지 SHA-1 다이제스트로 결정되며(`crypto/sign.py:26-38`), 부트스텁이 부팅 시
`RSA_verify` 를 통과해야 앱으로 점프하므로(`board/bootstub.c:45-62`)
**서명 일치 = 구동 중 이미지가 그 파일과 같다**로 볼 수 있다.

⚠ 범위: 구속력은 md5 가 아니라 **SHA-1** 이다. 또 이미지 첫 4 B(길이 워드)는 해시 범위 밖이다.
   md5 는 **저장소 파일의 속성**으로만 병기한다(장치에서 md5 를 낼 수단은 없다).

## 안전

**읽기 전용**이다 — `0xd3`/`0xd4`(서명) · `0xd6`(버전) · health · `0xc3`(per-bus CAN health) ·
`0xeb`(호밍 상태 폴)만 호출한다. `0xe8`/`0xe9`/`0xea` 는 **호출하지 않는다**(제어권·호밍 미개입).

사용:
  python3 orin_panda_identity.py
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from panda import Panda  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CANDIDATE_GLOBS = [
    "Tools/Can_Relay/panda-firmware/board/obj/panda.bin.signed",
    "Tools/Can_Relay/fw_backups/panda.bin.signed.*",
    "Tools/docking_field_kit/panda.bin.signed",
]
HOME_STATE = {0: "IDLE", 1: "ENABLE", 2: "SET_SPEED", 3: "START", 4: "WAIT",
              5: "DONE", 6: "ERR_TIMEOUT", 7: "ERR_ABORT", 8: "RESTORE",
              9: "GOZERO", 10: "ERR_GOZERO", 11: "GOZERO_W"}
LEC = {0: "No Error", 1: "Stuff", 2: "Form", 3: "Ack", 4: "Bit recessive",
       5: "Bit dominant", 6: "CRC", 7: "(sw)"}


def candidates() -> list[str]:
    out = []
    for g in CANDIDATE_GLOBS:
        out.extend(sorted(glob.glob(os.path.join(REPO, g))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", default=None, help="이 파일과 일치해야 한다(불일치 시 exit 1)")
    args = ap.parse_args()

    p = Panda()
    print("=== 장치 신원 ===", flush=True)
    try:
        print(f"  serial   : {p.get_serial()}", flush=True)
    except Exception as exc:
        print(f"  serial   : (조회 실패: {exc})", flush=True)
    ver = p.get_version()
    sig = p.get_signature()
    print(f"  version  : {ver}", flush=True)
    print(f"  signature: {sig.hex()[:32]}… ({len(sig)} B)", flush=True)
    print(f"  판독 시각 : {time.strftime('%Y-%m-%d %H:%M:%S')}  ← 시변 상태이므로 시각을 함께 인용할 것",
          flush=True)

    print("\n=== 저장소 후보와 서명 대조 ===", flush=True)
    matched = []
    for path in candidates():
        try:
            fw_sig = Panda.get_signature_from_firmware(path)
        except Exception as exc:
            print(f"  [오류] {os.path.relpath(path, REPO)}: {exc}", flush=True)
            continue
        blob = open(path, "rb").read()
        hit = (fw_sig == sig)
        if hit:
            matched.append(path)
        print(f"  [{'★일치' if hit else '  ―  '}] {os.path.relpath(path, REPO)}", flush=True)
        print(f"            {len(blob):,} B · md5 {hashlib.md5(blob).hexdigest()}", flush=True)

    print()
    if matched:
        for m in matched:
            print(f"  ⇒ 실기 탑재 = {os.path.relpath(m, REPO)}", flush=True)
    else:
        print("  ⇒ ★ 후보 어느 것과도 불일치 — **백업되지 않은 빌드가 올라가 있다**", flush=True)

    print("\n=== health ===", flush=True)
    h = p.health()
    for k in ("safety_mode", "controls_allowed", "car_harness_status",
              "heartbeat_lost", "uptime", "can_rx_errs", "can_fwd_errs", "faults"):
        if k in h:
            print(f"  {k:20s}: {h[k]}", flush=True)
    # can_send_errs 는 이름과 달리 **USB rx 큐 push 실패** 카운터다
    # (board/drivers/bxcan.h:118,194 · can_common.h:222). 버스 TX 오류가 아니다.
    if "can_send_errs" in h:
        print(f"  {'can_send_errs':20s}: {h['can_send_errs']:,}"
              f"  ← USB rx 큐 push 실패(호스트가 안 비움). **버스 오류 아님**", flush=True)

    print("\n=== per-bus CAN health (bxCAN ESR) ===", flush=True)
    for bus in (0, 1, 2):
        try:
            c = p.can_health(bus)
            print(f"  bus{bus}: bus_off={c['bus_off']} err_passive={c['error_passive']} "
                  f"TEC={c['transmit_error_cnt']} REC={c['receive_error_cnt']} "
                  f"LEC={c['last_error_code']}({LEC.get(c['last_error_code'], '?')})", flush=True)
        except Exception as exc:
            print(f"  bus{bus}: 조회 실패 {exc}", flush=True)
    print("  ⚠ ESR 은 순간·감쇠값이다. SILENT 에서 TEC=0 은 자명하므로 「버스 정상」의 근거로 과신 금지.",
          flush=True)

    print("\n=== 호밍 시퀀서 (0xeb, 읽기 전용) ===", flush=True)
    try:
        r = p._handle.controlRead(Panda.REQUEST_IN, 0xeb, 0, 0, 8)
        if len(r) == 8:
            st = r[0]
            print(f"  state={st} ({HOME_STATE.get(st, '?')})  done={r[1]:#04b} "
                  f"seen_active={r[2]:#04b} elapsed={r[3] | (r[4] << 8)}s "
                  f"DI3={r[5]:#04x} DI4={r[6]:#04x} reached={r[7]:#04b}", flush=True)
            print("  ⇒ 8B 정상 응답 = 호밍 시퀀서 탑재됨", flush=True)
        else:
            print(f"  ⚠ 응답 {len(r)}B (기대 8B) — 시퀀서 미탑재 가능", flush=True)
    except Exception as exc:
        print(f"  ⚠ 0xeb 실패: {exc} — 시퀀서 미탑재 가능", flush=True)

    p.close()

    if args.expect:
        want = os.path.abspath(args.expect)
        ok = any(os.path.abspath(m) == want for m in matched)
        print(f"\n--expect 대조: {os.path.relpath(want, REPO)} → {'★일치' if ok else '⚠ 불일치'}",
              flush=True)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
