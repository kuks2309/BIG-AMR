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
print(f"[D] device version : {ver}")
print(f"[D] sig device==file: {sig_dev == sig_file}")
print(f"[D] safety_mode={h.get('safety_mode')} hw_type={bytes(p.get_type()).hex()} serial={p.get_usb_serial()}")
p.close()
ok = (sig_dev == sig_file)
print("=== RESULT:", "OK flash+서명검증 통과" if ok else "MISMATCH 재확인", "===")
sys.exit(0 if ok else 3)
