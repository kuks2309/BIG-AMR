#!/usr/bin/env python3
"""[하위호환 shim] can-relay 주도권 코디네이터 — authority.py 로 이전됨 (ADR 2026-07-28).

구 relay_authority.RelayAuthority 호출부 유지를 위한 재-export. 신규 코드는 authority 를 직접 import.
로직·결함수정(High 주도권 롤백·Medium gate_off rc)은 authority.py 에 있다.
"""
from authority import (  # noqa: F401 — 재-export
    CANGW_SCRIPT,
    KernelCangwAuthority,
    NoAuthority,
    RelayAuthority,
    _Forwarder,
    make_seer_gate_hook,
    run_cangw,
)

if __name__ == "__main__":
    print(__doc__)
    print(f"relay_cangw.sh: {CANGW_SCRIPT or '(없음)'}")
