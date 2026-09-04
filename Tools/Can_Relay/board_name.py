#!/usr/bin/env python3
"""CAN relay 보드 이름 읽기/쓰기 (펌웨어 0xed/0xee/0xef, 플래시 섹터 4 — 앱 재플래시에도 보존).

사용:
  python3 board_name.py                 # 읽기
  python3 board_name.py set <name>      # 쓰기(SILENT idle 에서만 허용) 후 재확인
이름은 영문·숫자·하이픈·밑줄, 31자 이내.
"""
import os, re, sys, time
PF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panda-firmware")
sys.path.insert(0, PF)
from python import Panda  # noqa: E402

REQ_GET, REQ_STAGE, REQ_COMMIT, COMMIT_KEY, NAME_LEN = 0xED, 0xEE, 0xEF, 0x5AA5, 32


def get_name(p: Panda) -> str:
    raw = bytes(p._handle.controlRead(Panda.REQUEST_IN, REQ_GET, 0, 0, NAME_LEN))
    return raw.split(b"\0", 1)[0].decode("ascii", "replace")


def set_name(p: Panda, name: str) -> bool:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,31}", name):
        raise ValueError("이름은 영문·숫자·하이픈·밑줄 1~31자")
    buf = name.encode("ascii").ljust(NAME_LEN, b"\0")
    for i in range(0, NAME_LEN, 2):
        p._handle.controlWrite(Panda.REQUEST_OUT, REQ_STAGE, i, buf[i] | (buf[i + 1] << 8), b"")
    r = p._handle.controlRead(Panda.REQUEST_IN, REQ_COMMIT, COMMIT_KEY, 0, 1)
    return bool(r and r[0] == 1)


def main():
    p = Panda()
    try:
        h = p.health()
        print(f"serial={p.get_usb_serial()} fw={p.get_version()} safety_mode={h.get('safety_mode')}")
        if len(sys.argv) >= 3 and sys.argv[1] == "set":
            name = sys.argv[2]
            if h.get("safety_mode") != 0:
                sys.exit("거부: SILENT idle(safety_mode 0)에서만 기록할 수 있다")
            ok = set_name(p, name)
            time.sleep(0.2)
            back = get_name(p)
            print(f"commit={'OK' if ok else 'FAIL'} readback='{back}' version={p.get_version()}")
            sys.exit(0 if (ok and back == name) else 2)
        print(f"board_name='{get_name(p)}'")
    finally:
        p.close()


if __name__ == "__main__":
    main()
