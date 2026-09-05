#!/usr/bin/env python3
"""하드웨어 없이 `board_name.py`·`flash_new_board.py` 의 USB 요청/응답 해석을 펌웨어 계약대로 검증한다.

펌웨어 계약(`panda-firmware/board/usb_comms.h`):
  0xed IN  → 이름 바이트(resp_len = 이름 길이, 미기록 0)
  0xee OUT → wValue = 짝수 바이트 인덱스(0..30), wIndex = lo | hi<<8
  0xef IN  → wValue = 0x5AA5 일 때 커밋, resp[0] = 1 성공 / 0 거부(형식 위반·SILENT 아님·시퀀서 진행·pc_authority)
  0xec IN  → 6 B [state, source, result, pending_silent, ticks, pc_authority]; 핸들러 없는 이미지(현행 펌웨어 아님)는 빈 응답
  0xd6 IN  → 버전 문자열, 보드 이름이 있으면 '#<name>' 접미

실행: python3 Tools/Can_Relay/tests/test_board_name_flash_tools.py   (exit 0 = 전부 PASS)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # Tools/Can_Relay
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "panda-firmware"))
from python import Panda            # noqa: E402
import board_name                   # noqa: E402
import flash_new_board              # noqa: E402


class FakeHandle:
    """usb_comms.h 의 보드 이름·0xec 핸들러를 파이썬으로 옮긴 모의 장치."""

    def __init__(self, name=b"", has_ec=True, ho=(0, 0, 0, 0, 0, 0), silent=True):
        self.flash = name
        self.stage = bytearray(32)
        self.has_ec = has_ec
        self.ho = ho
        self.silent = silent
        self.writes = []

    def controlRead(self, rt, req, val, idx, ln):
        if req == 0xED:
            return bytes(self.flash)                        # resp_len = 이름 길이
        if req == 0xEC:
            return bytes(self.ho) if self.has_ec else b""   # 0xec 핸들러 없는 이미지: NO HANDLER → 빈 응답
        if req == 0xEF:
            ok = ((val == 0x5AA5) and self._stage_valid() and self.silent
                  and self.ho[0] == 0 and self.ho[5] == 0)
            if ok:
                self.flash = bytes(self.stage).split(b"\0", 1)[0]
            return bytes([1 if ok else 0])
        raise AssertionError(f"unexpected read {req:#x}")

    def controlWrite(self, rt, req, val, idx, data):
        assert req == 0xEE, hex(req)
        self.writes.append((val, idx))
        if val + 1 < 32:
            self.stage[val] = idx & 0xFF
            self.stage[val + 1] = (idx >> 8) & 0xFF

    def _stage_valid(self):                                 # board_name_stage_valid 이식
        ended = False
        n = 0
        for c in self.stage:
            if c == 0:
                ended = True
                continue
            if ended:
                return False
            if not (chr(c).isalnum() or c in (0x5F, 0x2D)):
                return False
            n += 1
        return 1 <= n <= 31


class FakePanda:
    REQUEST_IN = Panda.REQUEST_IN
    REQUEST_OUT = Panda.REQUEST_OUT

    def __init__(self, h):
        self._handle = h


class Boom:
    def controlRead(self, *a):
        raise OSError("pipe")


def main() -> int:
    fails = 0

    def check(cond, msg):
        nonlocal fails
        print(("PASS " if cond else "FAIL ") + msg)
        if not cond:
            fails += 1

    # 1) 읽기
    check(board_name.get_name(FakePanda(FakeHandle(b""))) == "", "get_name 미기록 → ''")
    check(board_name.get_name(FakePanda(FakeHandle(b"trworks-t3-1"))) == "trworks-t3-1", "get_name 기록 → 이름")

    # 2) 스테이징이 0xee 계약(짝수 idx 16회, 2 B 씩, NUL 패딩)대로인지
    h = FakeHandle()
    ok = board_name.set_name(FakePanda(h), "trworks-t3-1")
    check(ok and h.flash == b"trworks-t3-1", "set_name 커밋 OK·플래시 = 이름")
    check([w[0] for w in h.writes] == list(range(0, 32, 2)), "0xee wValue = 0,2,…,30 (16회)")
    check(bytes(h.stage) == b"trworks-t3-1".ljust(32, b"\0"), "스테이징 32 B = 이름 + NUL 패딩")

    # 3) 형식 검사는 도구가 펌웨어보다 먼저 거른다
    try:
        board_name.set_name(FakePanda(FakeHandle()), "bad name!")
        check(False, "형식 위반 ValueError")
    except ValueError:
        check(True, "형식 위반 ValueError")

    # 4) 0xec 해석
    check(board_name.ho_status(FakePanda(FakeHandle(ho=(1, 1, 0, 1, 3, 1)))) == (1, 1), "ho_status RESTORE·auth → (1,1)")
    check(board_name.ho_status(FakePanda(FakeHandle(ho=(0, 0, 1, 0, 0, 0)))) == (0, 0), "ho_status IDLE → (0,0)")
    check(board_name.ho_status(FakePanda(FakeHandle(has_ec=False))) is None, "ho_status 0xec 없음(현행 펌웨어 아님) → None")

    # 5) 펌웨어 커밋 가드 재현 — 시퀀서 진행·권한 중 커밋은 0
    check(board_name.set_name(FakePanda(FakeHandle(ho=(1, 1, 0, 1, 3, 1))), "x") is False, "시퀀서 진행 중 커밋 → 펌웨어 거부(0)")

    # 6) 플래시 도구의 이름 판독(예외 흡수)
    check(flash_new_board.read_board_name(FakePanda(FakeHandle(b"4e002c-x"))) == "4e002c-x", "read_board_name 기록 → 이름")
    check(flash_new_board.read_board_name(FakePanda(Boom())) == "", "read_board_name 예외 → ''")
    check(flash_new_board.read_ho_status(FakePanda(FakeHandle(ho=(0, 0, 1, 0, 0, 0)))) == (0, 0), "read_ho_status 현행 펌웨어 → (0,0)")
    check(flash_new_board.read_ho_status(FakePanda(FakeHandle(has_ec=False))) is None, "read_ho_status 0xec 없음 → None(플래시 verify 실패 조건)")
    check(flash_new_board.read_ho_status(FakePanda(Boom())) is None, "read_ho_status 예외 → None")

    # 7) 버전 대조 — '#name' 접미 제거 후 사이드카와 등호 (flash_new_board.py verify 식과 동일)
    want = "DEV-8dcca835-DEBUG"
    check("DEV-8dcca835-DEBUG#trworks-t3-1".strip().split('#', 1)[0] == want, "버전 접미 제거 대조 일치")
    check("DEV-8dcca835-DEBUG".split('#', 1)[0] == want, "접미 없는 버전도 일치")

    print("\nRESULT:", "ALL PASS" if fails == 0 else f"{fails} FAIL")
    return fails


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
