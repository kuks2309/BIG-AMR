#!/usr/bin/env python3
"""CAN relay 보드 이름 읽기/쓰기 (펌웨어 0xed/0xee/0xef, 플래시 섹터 4 — 앱 재플래시에도 보존).

사용:
  python3 board_name.py                 # 읽기
  python3 board_name.py set <name>      # 쓰기 후 재확인
이름은 영문·숫자·하이픈·밑줄, 31자 이내.
쓰기는 펌웨어가 SILENT idle 에서만 커밋한다 — safety_mode 0 · 핸드오버 시퀀서 IDLE · pc_authority 0
(usb_comms.h `board_name_commit`). 이 도구는 같은 세 조건을 0xd2/0xec 로 먼저 확인해 사유를 알려준다.
"""
import os, re, sys, time
PF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panda-firmware")
sys.path.insert(0, PF)
from python import Panda  # noqa: E402

REQ_GET, REQ_STAGE, REQ_COMMIT, COMMIT_KEY, NAME_LEN = 0xED, 0xEE, 0xEF, 0x5AA5, 32
REQ_HO_STATUS = 0xEC   # 핸드오버 시퀀서 상태 6 B: [state, source, result, pending_silent, ticks, pc_authority]


def get_name(p: Panda) -> str:
    raw = bytes(p._handle.controlRead(Panda.REQUEST_IN, REQ_GET, 0, 0, NAME_LEN))
    return raw.split(b"\0", 1)[0].decode("ascii", "replace")


def ho_status(p: Panda):
    """0xec → (state, pc_authority). 빈 응답(0xec 핸들러 없음)이면 None = 현행 펌웨어가 아니다."""
    r = bytes(p._handle.controlRead(Panda.REQUEST_IN, REQ_HO_STATUS, 0, 0, 6))
    return (r[0], r[5]) if len(r) >= 6 else None


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
            ho = ho_status(p)
            if ho is None:
                sys.exit("거부: 0xec 응답 없음 — 현행 펌웨어가 아니다. flash_dfu_direct.py 로 먼저 플래시할 것")
            if ho != (0, 0):
                sys.exit(f"거부: 핸드오버 시퀀서 state={ho[0]}·pc_authority={ho[1]} — "
                         "펌웨어는 시퀀서 IDLE·권한 없음일 때만 커밋한다(반환 완료를 기다릴 것)")
            ok = set_name(p, name)
            time.sleep(0.2)
            back = get_name(p)
            print(f"commit={'OK' if ok else 'FAIL'} readback='{back}' version={p.get_version()}")
            sys.exit(0 if (ok and back == name) else 2)
        ho = ho_status(p)
        ho_txt = "없음 — 현행 펌웨어 아님, 플래시 필요" if ho is None else f"state={ho[0]} pc_authority={ho[1]}"
        print(f"board_name='{get_name(p)}' handover(0xec)={ho_txt}")
    finally:
        p.close()


if __name__ == "__main__":
    main()
