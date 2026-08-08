"""테스트 부트스트랩 — 패키지 루트를 `sys.path` 에 넣는다.

이유: 이 테스트들은 **설치·소싱 없이도** 돌아야 한다. 안전 게이트(±90° 클램프·NaN 거부·
bit15 신뢰 판정)를 고정하는 회귀이므로, `colcon build` 나 `source install/setup.bash` 를
전제하면 그 전 단계(작성 직후·pre-commit·다른 워크스페이스)에서 검증이 끊긴다.

저장소 선례는 각 테스트 파일 상단에서 3줄을 반복하는 방식이지만
(`src/Actuators/motor_control/test/test_protocol.py:5-8`), 여기서는 `conftest.py` 한 곳에
모은다 — 같은 일을 파일마다 반복하지 않는다.

이 파일이 있으면 아래 세 가지가 모두 동작한다:
  python3 -m pytest src/Comm/CAN/can_relay/test -q      # 저장소 루트, 미소싱
  cd src/Comm/CAN/can_relay && python3 -m pytest test   # 패키지 디렉터리
  source install/setup.bash && python3 -m pytest ...    # 설치 환경
"""
import os
import sys

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from can_relay import protocol as P                            # noqa: E402
from can_relay.link import MockLink                            # noqa: E402

_SDO_UPLOAD_CMD = {1: 0x4F, 2: 0x4B, 4: 0x43}


def sdo_response(node: int, index: int, value: int, size: int = 4, sub: int = 0):
    """SDO upload 응답 1장. 각 시험의 `feed()` 와 같은 바이트 배치다."""
    data = (bytes([_SDO_UPLOAD_CMD[size], index & 0xFF, index >> 8, sub])
            + (value & 0xFFFFFFFF).to_bytes(4, "little")[:size])
    return (0x580 + node, data + b"\x00" * (8 - len(data)), 2)


class FeedingLink(MockLink):
    """폴에 **매번** 응답하는 대역.

    `MockLink.inbox` 는 한 번 소비되면 비므로, 여러 주기에 걸쳐 상태를 보는 판정
    (조향 0° 정착 대기 등)을 시험할 수 없다 — 첫 `_drain()` 뒤로는 피드백이 만료되고
    「피드백 없음」으로 떨어진다. 실기 드라이브는 폴이 올 때마다 답하므로 이쪽이 실기에 가깝다.

    `positions[node] = (position_counts, statusword)` 를 세워 두면 `recv()` 마다 재공급한다.
    """

    STATUSWORD_STEER_IDLE = 0x9450   # 실측 조향 정지 상태워드(bit15·12·10·6·4)

    def __init__(self):
        super().__init__()
        self.positions: dict = {}

    def hold(self, node: int, position: int, statusword: int = STATUSWORD_STEER_IDLE):
        self.positions[int(node)] = (int(position), int(statusword))

    def recv(self):
        for n, (pos, sw) in self.positions.items():
            self.inbox.append(sdo_response(n, P.OBJ_POSITION_ACTUAL, pos))
            self.inbox.append(sdo_response(n, P.OBJ_STATUSWORD, sw, size=2))
        return super().recv()
