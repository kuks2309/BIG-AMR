#!/usr/bin/env python3
"""CAN relay 시험 GUI — Tools 독립 런처 (colcon/ROS2 소싱 불요, `python3` 즉시 실행).

근거: 2026-08-06 사용자 지시 「Tools 폴더에 can relay gui 도 이식해서 주행 설정에 맞도록」.
UI 실체는 `src/Comm/CAN/can_relay/can_relay/ui/`(1벌 UI + 백엔드 2종,
`docs/adr/2026-08-04-amr-test-gui-swappable-backend.md`) 이며 **여기서는 복제하지 않는다** —
sys.path 만 열어 같은 코드를 실행한다(사본 이중화 금지, CLAUDE.md §UI 는 패키지 아래 종속).

- 기본 `--backend both` (gui_node 기본값 그대로): ROS2 미소싱 환경이면 ros2 백엔드 생성이
  실패하고 direct(판다 직결) 탭만 뜬다 — gui_node 의 「한쪽이 없어도 나머지는 띄운다」 동작.
- 주행 설정 정본: `src/Comm/CAN/can_relay/config/machine/foil_a082.yaml`
  (steer_home_counts · steer_counts_per_deg · drive_units_per_mmps · drive_max_units ·
  steer_limit_deg — backend_direct `_load_steer_home`/`_load_drive_scale` 이 로드).
- panda 라이브러리는 backend_direct 가 `Tools/docking_field_kit/panda` 를 자체 경로 주입한다.

사용:
    python3 Tools/can_relay_gui/can_relay_gui.py                  # 기본(both, 기체 foil_a082)
    python3 Tools/can_relay_gui/can_relay_gui.py --backend direct # 판다 직결만
    python3 Tools/can_relay_gui/can_relay_gui.py --machine lgit_moma_qd   # QD 기체 설정
"""
from __future__ import annotations

import argparse
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     os.pardir, os.pardir))
_PKG = os.path.join(_REPO, "src", "Comm", "CAN", "can_relay")

if not os.path.isdir(os.path.join(_PKG, "can_relay", "ui")):
    raise SystemExit(f"can_relay 패키지를 찾지 못했습니다: {_PKG}")

sys.path.insert(0, _PKG)

# --machine 은 backend_direct 가 import 시점에 읽는 env 로 전달한다 (기체별 정본 YAML 선택).
_ap = argparse.ArgumentParser(add_help=False)
_ap.add_argument("--machine", default=None,
                 help="config/machine/<이름>.yaml 선택 (기본 foil_a082)")
_known, _rest = _ap.parse_known_args()
if _known.machine:
    os.environ["CAN_RELAY_MACHINE"] = _known.machine
sys.argv = [sys.argv[0]] + _rest

from can_relay.ui.gui_node import main  # noqa: E402  (sys.path·env 주입 후 import)

if __name__ == "__main__":
    raise SystemExit(main())
