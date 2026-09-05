#!/usr/bin/env python3
"""신규 공장(DFU) CAN relay 보드에 검증본 펌웨어를 굽는다.

`docking_field_kit/flash_panda.py` 는 이미 정상 판다(bbaa:ddcc)가 붙어 있어야만 동작한다
(공장 DFU 상태에선 `Panda()` 가 assert 로 죽는다). 이 도구는 그 공백을 메운다:

  1) DFU 상태면 bootstub 먼저 복구(정본 라이브러리 PandaDFU.recover)
  2) 보드가 정상 판다로 재열거되면 앱을 통상 경로로 flash
  3) BOOT0 스트랩으로 DFU 로 재진입하면(2026-08-23·2026-09-01 실측) 앱을 DFU 로 직접 flash
  4) 부팅 후 장치 서명(0xd3/0xd4)을 파일과 대조해 검증(rewrite-guide §각 단계 5)

이미지 = board/obj/panda.bin.signed (저장소 현재 빌드). `--fw <경로>` 로 교체 가능.
실행: python3 Tools/Can_Relay/flash_new_board.py
"""
import sys, os, time, hashlib

PF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panda-firmware")
sys.path.insert(0, PF)
from python import Panda
from python.dfu import PandaDFU
from python.config import APP_ADDRESS_FX, BLOCK_SIZE_FX


def pick_fw(argv):
    if "--fw" in argv:
        i = argv.index("--fw")
        if i + 1 >= len(argv):
            sys.exit("--fw 뒤에 경로가 필요하다")
        return os.path.abspath(argv[i + 1])
    return os.path.join(PF, "board", "obj", "panda.bin.signed")


def read_sidecar_version(fw):
    try:
        with open(os.path.join(os.path.dirname(fw), "version")) as f:
            return f.read().strip()
    except OSError:
        return None


def normals():
    try: return Panda.list()
    except Exception: return []


def dfus():
    try: return PandaDFU.list()
    except Exception: return []


def read_board_name(p):
    """펌웨어 0xed 보드 이름(플래시 섹터 4). 미기록이면 ''(USB 예외도 '')."""
    try:
        raw = bytes(p._handle.controlRead(Panda.REQUEST_IN, 0xED, 0, 0, 32))
        return raw.split(b"\0", 1)[0].decode("ascii", "replace")
    except Exception:
        return ""


def read_ho_status(p):
    """펌웨어 0xec 핸드오버 시퀀서 상태 → (state, pc_authority). 빈 응답·예외면 None = 현행 펌웨어가 아니다."""
    try:
        r = bytes(p._handle.controlRead(Panda.REQUEST_IN, 0xEC, 0, 0, 6))
        return (r[0], r[5]) if len(r) >= 6 else None
    except Exception:
        return None


def main():
    APP = pick_fw(sys.argv)
    if not os.path.isfile(APP):
        sys.exit(f"펌웨어 없음: {APP}")
    app = open(APP, "rb").read()
    print(f"[img] {APP}\n[img] len={len(app):,}B md5={hashlib.md5(app).hexdigest()}")
    if len(app) > 49152:
        sys.exit(f"[abort] app {len(app):,}B > 49,152B (앱영역 초과) — 부트스텁에 갇힌다")
    print(f"[pre] normals={normals()} dfus={dfus()}")

    # Step 1: bootstub recover (DFU 상태일 때)
    if dfus() and not normals():
        ds = dfus()[0]
        print(f"[step1] bootstub recover on DFU {ds} ...")
        PandaDFU(ds).recover()
        time.sleep(3)
        print(f"[step1] after recover: normals={normals()} dfus={dfus()}")

    # Step 2: 재열거 대기
    t = time.time()
    while time.time() - t < 12 and not normals() and not dfus():
        time.sleep(0.5)
    print(f"[step2] settle: normals={normals()} dfus={dfus()}")

    # Step 3: 앱 플래시
    if normals():
        if len(normals()) > 1:
            sys.exit(f"[abort] 정상 판다 {len(normals())}대 {normals()} — 대상 모호, 중단")
        print("[step3a] normal path: Panda().flash(app)")
        p = Panda()
        print(f"[step3a] connected: ver={p.get_version()} bootstub={p.bootstub}")
        p.flash(APP)
        p.close()
    elif dfus():
        ds = dfus()[0]
        print(f"[step3b] DFU 재진입 {ds} — 앱 DFU 직접 플래시")
        d = PandaDFU(ds)
        d.clear_status()
        for a in (0x8004000, 0x8008000, 0x800C000):
            print(f"[step3b] erase {a:#x}"); d.erase(a)
        d.program(APP_ADDRESS_FX, app, BLOCK_SIZE_FX)
        d.reset()
        time.sleep(3)
    else:
        sys.exit("[abort] bootstub recover 후 장치 없음")

    # Step 4: 검증 (장치 서명 == 파일)
    t = time.time()
    while time.time() - t < 15 and not normals():
        time.sleep(0.5)
    if not normals():
        print(f"[verify] 정상 판다 미열거. dfus={dfus()} — 부팅 실패 가능")
        sys.exit(2)
    p = Panda()
    ver = p.get_version()
    sig_dev = p.get_signature()
    sig_file = Panda.get_signature_from_firmware(APP)
    h = p.health()
    name = read_board_name(p)
    ho = read_ho_status(p)
    print(f"[verify] device version : {ver}")
    print(f"[verify] sig device==file: {sig_dev == sig_file}  (sigtail md5 {hashlib.md5(sig_dev).hexdigest()[:16]})")
    print(f"[verify] safety_mode={h.get('safety_mode')} hw_type={bytes(p.get_type()).hex()} serial={p.get_usb_serial()}")
    print(f"[verify] board_name='{name}'  (섹터 4 — 앱 erase 범위 밖이라 재플래시 전과 같아야 한다; 미기록이면 빈값)")
    print(f"[verify] handover(0xec) : {'없음 — 현행 펌웨어 아님' if ho is None else f'state={ho[0]} pc_authority={ho[1]}'}")
    p.close()
    want = read_sidecar_version(APP)
    # 펌웨어 0xd6 는 보드 이름이 기록돼 있으면 '#<name>' 을 덧붙인다 — 사이드카 대조는 접미를 뗀 버전으로 한다.
    # 0xec 응답은 현행 펌웨어(핸드오버 시퀀서 탑재)의 표지다 — 그 이전 이미지는 운용하지 않으므로 없으면 실패.
    ok = (sig_dev == sig_file) and (want is None or ver.strip().split('#', 1)[0] == want) and (ho is not None)
    print("=== RESULT:", "OK 플래시+서명+현행펌웨어 검증 통과" if ok else "MISMATCH — 재확인 필요", "===")
    print("  ※ 부팅 250 kbps 정합은 실기 버스 장착 후 별도 확인(수 초 수신·can_rx_errs=0)")
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
