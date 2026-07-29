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
