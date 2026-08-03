"""노드 동시성 회귀 — 호밍 중에도 취소·정지 서비스가 살아 있어야 한다.

## 이 파일이 존재하는 이유

`driver_node.py` 는 「진행 중 취소는 `~/home_cancel` 로 한다」고 계약을 적어 두었고,
`backend.home()` 의 docstring 도 취소 가능성을 이 경로를 쓰는 **유일한 이유**로 든다.

그런데 `~/home` 콜백은 `backend.home()` 안의 폴링 루프에서 terminal 상태나 timeout(기본 180 s)
까지 반환하지 않는다. 실행기가 단일 스레드이거나 두 서비스가 같은
MutuallyExclusiveCallbackGroup 에 있으면 **그동안 `~/home_cancel` 이 소비되지 않는다** —
문서화된 취소 수단이 정작 호밍 중에만 죽는다(2026-08-03 코드 리뷰 H1).

여기서는 그 계약을 실제 rclpy 실행기 위에서 고정한다. ROS2 미소싱 환경에서는 skip 된다
(나머지 회귀는 소싱 없이도 계속 돈다 — `conftest.py` 참조).
"""
import threading
import time

import pytest

rclpy = pytest.importorskip("rclpy", reason="ROS2 미소싱 환경 — 노드 회귀는 건너뛴다")

from rclpy.callback_groups import MutuallyExclusiveCallbackGroup  # noqa: E402
from rclpy.executors import MultiThreadedExecutor                 # noqa: E402
from std_srvs.srv import Trigger                                  # noqa: E402

from can_relay.driver_node import CanRelayNode                    # noqa: E402
from can_relay.link import MockLink                               # noqa: E402

ROS_ARGS = [
    "--ros-args",
    "-p", "link:=mock",
    "-p", "steer_home_counts:=[7871815,7840086]",
    "-p", "require_homed_for_steer:=false",
]

WAIT_S = 5.0        # 취소 응답을 기다리는 상한. 이것을 넘기면 H1 재현이다.


@pytest.fixture
def relay_node():
    """mock 링크로 기동한 노드 + 제어권 획득 상태. 종료 경로까지 책임진다."""
    rclpy.init(args=ROS_ARGS)
    node = CanRelayNode()
    node.link.open()
    node.link.acquire()
    node.backend.start()
    try:
        yield node
    finally:
        try:
            node.backend.cancel_home()       # 회귀 실패 시에도 스레드를 풀어 준다
        except Exception:
            pass
        node.backend.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def _spin(*nodes):
    """노드들을 다중 스레드 실행기에 올리고 배경에서 돌린다. (executor, thread) 반환."""
    executor = MultiThreadedExecutor(num_threads=4)
    for n in nodes:
        executor.add_node(n)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    return executor, thread


def _wait(cond, timeout=WAIT_S):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if cond():
            return True
        time.sleep(0.02)
    return False


def test_home_cancel_is_serviced_while_homing_runs(relay_node):
    """호밍이 진행 중인 동안 `~/home_cancel` 이 응답해야 한다.

    MockLink 에 WAIT(4) 상태 대본을 하나만 넣으면 terminal 이 오지 않아
    `home()` 이 timeout 까지 붙잡는다 — 실기의 호밍 진행 중과 같은 조건이다.
    """
    relay_node.link.homing_script = [MockLink.homing_state(4)]   # WAIT, terminal 아님

    client = rclpy.create_node("can_relay_test_client")
    executor, _thread = _spin(relay_node, client)
    try:
        cli_home = client.create_client(Trigger, "/can_relay_node/home")
        cli_cancel = client.create_client(Trigger, "/can_relay_node/home_cancel")
        assert cli_home.wait_for_service(timeout_sec=WAIT_S), "~/home 서비스 미노출"
        assert cli_cancel.wait_for_service(timeout_sec=WAIT_S), "~/home_cancel 서비스 미노출"

        fut_home = cli_home.call_async(Trigger.Request())
        assert _wait(lambda: relay_node.backend.snapshot()["homing"]), \
            "호밍이 시작되지 않았다 — 회귀 전제 불성립"

        fut_cancel = cli_cancel.call_async(Trigger.Request())
        got = _wait(lambda: fut_cancel.done())
        assert got, (
            f"호밍 진행 중 `~/home_cancel` 이 {WAIT_S:.0f}초 안에 응답하지 않았다 — "
            f"실행기가 `~/home` 콜백에 묶여 있다(H1). "
            f"문서화된 유일한 취소 수단이 호밍 중에만 동작하지 않는다")
        assert fut_cancel.result().success

        # 취소가 실제로 호밍을 끝냈는지까지 본다 — 응답만 오고 안 멈추면 의미가 없다.
        assert _wait(lambda: fut_home.done()), "취소 후에도 `~/home` 이 반환하지 않았다"
        assert relay_node.backend.snapshot()["homing"] is False
    finally:
        # 순서 주의 — 실행기를 먼저 내리면 막힌 콜백이 timeout(180 s)까지 붙잡는다.
        # 회귀가 깨졌을 때도 시험이 몇 초 안에 끝나야 한다.
        relay_node.backend.cancel_home()
        executor.shutdown()
        client.destroy_node()


def test_stop_service_is_serviced_while_homing_runs(relay_node):
    """정지도 마찬가지다 — 호밍 중에 `~/stop` 이 막히면 정지 수단이 사라진다."""
    relay_node.link.homing_script = [MockLink.homing_state(4)]

    client = rclpy.create_node("can_relay_test_client_stop")
    executor, _thread = _spin(relay_node, client)
    try:
        cli_home = client.create_client(Trigger, "/can_relay_node/home")
        cli_stop = client.create_client(Trigger, "/can_relay_node/stop")
        assert cli_home.wait_for_service(timeout_sec=WAIT_S)
        assert cli_stop.wait_for_service(timeout_sec=WAIT_S)

        cli_home.call_async(Trigger.Request())
        assert _wait(lambda: relay_node.backend.snapshot()["homing"])

        fut_stop = cli_stop.call_async(Trigger.Request())
        assert _wait(lambda: fut_stop.done()), (
            f"호밍 진행 중 `~/stop` 이 {WAIT_S:.0f}초 안에 응답하지 않았다(H1)")
    finally:
        relay_node.backend.cancel_home()     # 실행기 종료보다 먼저 — 위 시험과 같은 이유
        executor.shutdown()
        client.destroy_node()


def test_long_running_services_are_not_in_the_default_group(relay_node):
    """구조 고정 — 블로킹 서비스가 기본(상호배타) 그룹에 있으면 위 계약이 깨진다.

    행위 회귀만으로는 "실행기를 다중 스레드로 만들면 통과" 하는 우연한 통과가 가능하다.
    콜백 그룹 분리는 `main()` 의 실행기 선택과 무관하게 성립해야 하므로 따로 박는다.
    """
    default = relay_node.default_callback_group
    assert relay_node.srv_home.callback_group is not default, \
        "`~/home` 이 기본 콜백 그룹에 있다 — 같은 그룹의 다른 콜백이 전부 대기한다"
    assert relay_node.srv_home_cancel.callback_group is not default, \
        "`~/home_cancel` 이 기본 콜백 그룹에 있다"
    assert relay_node.srv_home.callback_group is not \
        relay_node.srv_home_cancel.callback_group, \
        "호밍과 취소가 같은 그룹이면 상호배타 그룹일 때 취소가 막힌다"
    assert isinstance(relay_node.srv_home_cancel.callback_group,
                      MutuallyExclusiveCallbackGroup), \
        "취소는 재진입이 필요 없다 — 자기 전용 상호배타 그룹이면 충분하다"
