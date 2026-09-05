#!/usr/bin/env python3
"""4e002c(force-pin 함정보드) 안전 재flash: app->DFU->DFU직접 program->reset->검증.
통상경로(Panda().flash, bootstub 가둠)·recover(재-가둠 위험) 모두 회피.
2026-09-01 검증된 step3b(erase+program+reset)+step4(서명대조)만 사용.
"""
import sys, os, time, hashlib
PF = "/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/Can_Relay/panda-firmware"
sys.path.insert(0, PF)
from python import Panda
from python.dfu import PandaDFU
from python.config import APP_ADDRESS_FX, BLOCK_SIZE_FX

APP = os.path.join(PF, "board", "obj", "panda.bin.signed")
app = open(APP, "rb").read()
print(f"[img] {APP}")
print(f"[img] len={len(app):,}B md5={hashlib.md5(app).hexdigest()}")
if len(app) > 49152:
    sys.exit(f"[abort] {len(app)}B > 49,152B 앱영역 초과")

print(f"[pre] normals={Panda.list()} dfus={PandaDFU.list()}")
if not Panda.list():
    sys.exit("[abort] app 판다 미연결 — 이미 DFU/bootstub 이면 이 스크립트로 진행 말고 알릴 것")

p = Panda()
print(f"[cur] serial={Panda.list()[0]} version={p.get_version()} bootstub={p.bootstub} sm={p.health().get('safety_mode')}")

print("[A] reset(enter_bootloader=True) → DFU 진입 ...")
p.reset(enter_bootloader=True)
try: p.close()
except Exception: pass
time.sleep(3)

t = time.time()
while time.time() - t < 15 and not PandaDFU.list():
    time.sleep(0.5)
ds = PandaDFU.list()
print(f"[B] dfus={ds} normals={Panda.list()}")
if not ds:
    sys.exit("[abort] DFU 미열거 — 보드 상태 불명, 물리 확인 필요(전원/버튼)")

d = PandaDFU(ds[0])
d.clear_status()
for a in (0x8004000, 0x8008000, 0x800C000):
    print(f"[C] erase {a:#x}"); d.erase(a)
print(f"[C] program @ {APP_ADDRESS_FX:#x} ({len(app):,}B)")
d.program(APP_ADDRESS_FX, app, BLOCK_SIZE_FX)
print("[C] reset ...")
d.reset()
time.sleep(3)

t = time.time()
while time.time() - t < 20 and not Panda.list():
    time.sleep(0.5)
if not Panda.list():
    print(f"[D] app 판다 미열거. dfus={PandaDFU.list()} — 부팅 실패/함정 가능")
    sys.exit(2)
p = Panda()
ver = p.get_version()
sig_dev = p.get_signature()
sig_file = Panda.get_signature_from_firmware(APP)
h = p.health()
try:   # 펌웨어 0xed 보드 이름(섹터 4) — 위 erase 범위(섹터 1~3) 밖이라 재플래시 전과 같아야 한다
    name = bytes(p._handle.controlRead(Panda.REQUEST_IN, 0xED, 0, 0, 32)).split(b"\0", 1)[0].decode("ascii", "replace")
except Exception:
    name = ""
try:   # 펌웨어 0xec 핸드오버 시퀀서 상태 6 B — 현행 펌웨어의 표지. 빈 응답이면 그 이전 이미지(운용하지 않음)
    ho = bytes(p._handle.controlRead(Panda.REQUEST_IN, 0xEC, 0, 0, 6))
    ho = (ho[0], ho[5]) if len(ho) >= 6 else None
except Exception:
    ho = None
print(f"[D] device version : {ver}")
print(f"[D] sig device==file: {sig_dev == sig_file}")
print(f"[D] safety_mode={h.get('safety_mode')} hw_type={bytes(p.get_type()).hex()} serial={p.get_usb_serial()}")
print(f"[D] board_name='{name}'  (미기록이면 빈값)")
print(f"[D] handover(0xec) : {'없음 — 현행 펌웨어 아님' if ho is None else f'state={ho[0]} pc_authority={ho[1]}'}")
p.close()
ok = (sig_dev == sig_file) and (ho is not None)
print("=== RESULT:", "OK flash+서명+현행펌웨어 검증 통과" if ok else "MISMATCH 재확인", "===")
sys.exit(0 if ok else 3)
