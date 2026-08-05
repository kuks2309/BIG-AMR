#!/usr/bin/env python3
"""판다 도킹 릴레이 펌웨어 플래시 (필드 킷 자립형).

킷 폴더의 panda/ 라이브러리 + panda.bin.signed 를 사용해 연결된 판다에 우리 펌웨어를 플래시.
실행: python3 flash_panda.py

- 플래시 전/후 버전을 출력하고 DEV-26524538-DEBUG 확인.
- 실패 시(부트스텁 갇힘) 복구: python3 flash_panda.py --recover

⚠⚠ 정정 2026-07-27 — 동봉 바이너리는 구버전이다 (원 문장은 위에 그대로 남김).
  동봉 `panda.bin.signed` 는 2026-07-23 20:36 빌드(47,808 B)로, 2026-07-27 펌웨어 정정이
  **포함되지 않는다**:
    (a) 부팅 기본 CAN 비트레이트 500→250 kbps
        — Tools/Can_Relay/panda-firmware/board/drivers/can_common.h:174-176 (`can_speed` 5000U→2500U)
        — docs/verified_facts/2026-07-27.md:17-43 §A-1: 500 kbps 부팅이 250 kbps 버스를 파괴해
          Seer 52106 / 52111 / 54022 를 지속 발생시켰고, 2500U 수정 후 재검증(:45-63)으로 소멸.
    (b) heartbeat 상실 시 릴레이 해제 + PC 주도권 반납
        — board/main.c:252-258 `set_intercept_relay(false); pc_authority = false;`
        — docs/verified_facts/2026-07-27.md:127-149 §A-5
    ADR: docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md
  ⇒ **이 스크립트를 그대로 실행하면 500 kbps 부팅 결함을 되돌린다.**
  최신 빌드: Tools/Can_Relay/panda-firmware/board/obj/panda.bin.signed (2026-07-27 20:30, 48,620 B)
  (바이너리 교체·값 변경은 실측 검증 후 별도 승인 사항이므로 본 정정은 서술만 한다.)
"""
import os
import sys
import time

KIT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KIT)
from panda import Panda

FW = os.path.join(KIT, "panda.bin.signed")
# ⚠ 2026-07-23 20:36 빌드(47,808 B). 2026-07-27 정정(부팅 250 kbps · heartbeat 상실 시 릴레이 해제)
#   미포함 — 상단 docstring "정정 2026-07-27" 참조.
EXPECT = "DEV-26524538-DEBUG"
# ⚠ EXPECT 는 **특정 시점의 git short hash 기반 문자열**이지 "우리 펌웨어" 일반의 식별자가 아니다.
#   버전 문자열 생성: Tools/Can_Relay/panda-firmware/board/SConscript:90-93 (git short hash 삽입).
#   `26524538` 은 2026-07-23 시점 고정값(HANDOFF-amap2.md:9 에 같은 날짜로 기록).
#   따라서 최신 소스로 재빌드하면 이 문자열은 **정상적으로 달라지며**, 불일치가 곧 오류는 아니다.


# ── 기본 펌웨어 경로 정정 (2026-08-03) ────────────────────────────────────
# 종전에는 무조건 동봉 `KIT/panda.bin.signed`(2026-07-23 구버전)를 플래시했다.
# 상단 docstring 이 「이 스크립트를 그대로 실행하면 500 kbps 부팅 결함을 되돌린다」고
# 경고해 놓고도 **코드는 그 위험한 기본값을 그대로 쓰고 있었다** — 경고문만으로는 막히지 않는다.
# ⇒ 기본값을 **저장소 현재 빌드**로 바꾸고, 동봉 구버전을 쓰려면 명시적으로 지정하게 한다.
REPO_FW = os.path.abspath(os.path.join(
    KIT, "..", "Can_Relay", "panda-firmware", "board", "obj", "panda.bin.signed"))


def pick_fw(argv) -> str:
    """`--fw PATH` 우선. 없으면 저장소 현재 빌드, 그것도 없으면 동봉본(경고 후)."""
    if "--fw" in argv:
        i = argv.index("--fw")
        if i + 1 >= len(argv):
            sys.exit("--fw 뒤에 경로가 필요하다")
        return os.path.abspath(argv[i + 1])
    if os.path.isfile(REPO_FW):
        return REPO_FW
    print("⚠ 저장소 빌드를 찾지 못해 동봉 구버전을 쓴다 — 상단 docstring 경고 참조:")
    print(f"    {FW}")
    return FW


def read_build_version(fw: str):
    """플래시 대상 이미지 옆의 `version` 사이드카를 읽는다 (없으면 None).

    `board/SConscript` 가 빌드 때마다 `obj/version`(과 `obj/gitversion.h`)을 갱신하므로,
    이 파일은 **그 이미지에 실제로 박힌 문자열**이다 — 고정 상수 EXPECT 와 달리 재빌드를 따라간다.
    동봉본처럼 사이드카가 없는 경우도 있어 None 을 정상 반환값으로 둔다(호출부가 fallback).
    """
    path = os.path.join(os.path.dirname(fw), "version")
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def main():
    if "--recover" in sys.argv:
        print("DFU 복구 시도...")
        Panda.recover()
        print("복구 완료. 다시 flash_panda.py 실행 권장.")
        return
    fw = pick_fw(sys.argv)
    if not os.path.isfile(fw):
        sys.exit(f"펌웨어 없음: {fw}")
    import hashlib
    blob = open(fw, "rb").read()
    print(f"대상 펌웨어: {fw}")
    print(f"  크기 {len(blob):,} B · md5 {hashlib.md5(blob).hexdigest()}")
    # 앱 영역은 섹터 1~3 = 49,152 B (flasher 가 그 범위만 소거한다 — panda/python/__init__.py:296-299).
    # 초과분은 미소거 섹터에 기록돼 서명 검증이 깨지고 부트스텁에 갇힌다
    # (docs/claude-mistake/2026-07-28-007_flash-without-size-limit-check.md).
    if len(blob) > 49152:
        sys.exit(f"⚠ 크기 초과: {len(blob):,} B > 49,152 B (앱 영역). 플래시하면 부트스텁에 갇힌다.")
    p = Panda()
    before = p.get_version()
    print("플래시 전 version:", before)
    print(f"펌웨어 플래시: {fw}")
    # 재연결 중 벤더 라이브러리가 traceback 을 찍는 것은 정상이다 — 미리 알린다.
    #   플래시는 장치를 재열거시키므로 첫 claimInterface(0) 가 LIBUSB_ERROR_BUSY 로 실패할 수 있다.
    #   panda/python/__init__.py:236-241 의 connect() 는 예외를 **찍고 재시도**하는 while 루프이고,
    #   :265-275 reconnect() 가 최대 15초 재시도한다 → 뒤에 "connected" 가 찍히면 성공이다.
    #   진짜 실패는 "reconnect failed" 예외로 죽는 것뿐. 벤더 라이브러리는 수정하지 않는다.
    print("  ℹ 재연결 중 'LIBUSB_ERROR_BUSY' traceback 이 보일 수 있다 — 실패가 아니라 정상 재시도다.")
    print("    뒤에 'connected' 가 찍히면 성공. 진짜 실패는 'reconnect failed' 로 죽는 경우뿐.")
    p.flash(fw)
    print("플래시 완료, 재연결...")
    time.sleep(2.5)
    p2 = Panda()
    after = p2.get_version()
    h = p2.health()
    print("플래시 후 version:", after)
    # 정정 2026-07-27 — 원 문구: "(0=SILENT/passthrough 부팅 정상)"
    #   SILENT 와 passthrough 는 같은 것이 아니고, safety_mode=0 만으로 부팅 건전성을 판정할 수 없다.
    #   · 버스 통과 여부는 safety_mode 가 아니라 **릴레이 상태**가 결정한다
    #     (docs/verified_facts/2026-07-27.md:94-109 §A-3: harness.h:91 `set_intercept_relay(false)`,
    #      bus0/bus2 동일 프레임 동일 카운트 실측. "SILENT 라 포워딩이 끊긴다"는 진단은 :111-113 에서 철회됨).
    #   · 반대로 PINMAP.md:68 은 "판다 켜진 SILENT 는 트랜시버 간섭으로 불통"이라 적어, SILENT=통과가 아님을 명시.
    #   · 부팅 건전성의 실제 변수는 **기본 CAN 비트레이트**다(verified_facts §A-1:17-43) — 이 print 는 그것을 보지 않는다.
    print("safety_mode:", h.get("safety_mode"),
          "(0 = SAFETY_SILENT: 판다 송신 없음. 버스 통과 여부는 릴레이 상태가 결정 — verified_facts §A-3."
          " 부팅 건전성은 기본 CAN 비트레이트 250 kbps 여부로 별도 확인할 것 — §A-1)")
    print("hw type:", p2.get_type())
    p2.close()
    # 정정 2026-07-27 — 원 문구: ("OK: 우리 펌웨어 적용됨" if EXPECT in str(after) else "⚠ 예상과 다름")
    #   버전 문자열 일치는 "2026-07-23 빌드가 올라갔다"는 뜻일 뿐 "최신 정정본"을 뜻하지 않는다(EXPECT 주석 참조).
    #
    # 정정 2026-08-05 — 판정 기준을 고정 EXPECT 에서 **방금 플래시한 이미지의 version 사이드카**로 옮긴다.
    #   종전에는 EXPECT(2026-07-23 고정 해시)와 다르면 "=== 버전 문자열이 EXPECT 와 다름 ===" 을 찍었는데,
    #   재빌드하면 달라지는 것이 정상이라 **성공한 플래시가 실패처럼 읽혔다**(2026-08-05 실사용에서 실제 오독 유발).
    #   이제는 `<fw 경로>/../version`(SConscript 가 빌드마다 갱신)과 대조해 일치 = 성공으로 단정한다.
    expected = read_build_version(fw)
    if expected and expected == str(after).strip():
        print(f"=== ✅ 플래시 성공 — 장치 version 이 빌드 사이드카와 일치: {expected} ===")
    elif expected:
        print(f"=== ⚠ 불일치 — 빌드 사이드카 {expected} vs 장치 {after} ===")
        print("  플래시가 실제로 반영되지 않았을 수 있다. 재시도하거나 --recover 후 다시 플래시할 것.")
    elif EXPECT in str(after):
        print("=== 플래시된 이미지 = 동봉 2026-07-23 빌드(DEV-26524538-DEBUG) ===")
        print("⚠ 이 이미지에는 2026-07-27 정정(부팅 250 kbps · heartbeat 상실 시 릴레이 해제)이 없다.")
        print("  → 부팅 기본 500 kbps 결함이 되돌아간 상태다. 최신 빌드로 다시 플래시할 것:")
        print("    Tools/Can_Relay/panda-firmware/board/obj/panda.bin.signed")
        print("    근거: docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md ·"
              " docs/verified_facts/2026-07-27.md §A-1/§A-5")
    else:
        print(f"=== version={after} (빌드 사이드카 없음 — 자동 대조 불가) ===")
        print("  EXPECT 는 2026-07-23 시점 git hash 고정값이므로 재빌드 시 달라지는 것이 정상이다.")
    # 어느 경로로 오든 비트레이트는 별도 확인 대상이다 — version 문자열은 그것을 증명하지 않는다.
    print("  ※ 부팅 기본 CAN 비트레이트 250 kbps 여부는 별도 확인할 것"
          " (verified_facts 2026-07-27 §A-1 재현 절차: 수 초 수신 후 can_rx_errs 가 0 이면 정합).")


if __name__ == "__main__":
    main()
