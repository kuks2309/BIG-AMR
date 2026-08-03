"""GUI 이식본의 **ROS 계약** 회귀 — 하드웨어도 화면도 없이 돈다.

여기서 고정하는 것은 「GUI 가 드라이버와 실제로 말이 통하는가」다. 화면이 뜨는 것은 판정이
아니다(ADR `docs/adr/2026-08-03-amr-test-gui-ros2-port.md` §Verification 3).

`RelayClient` 는 Qt 를 import 하지 않으므로 이 파일에서 그대로 쓸 수 있다 — 그것이 GUI 를
ROS 층과 화면 층으로 나눈 이유다.

시험 대상 경로: 제어권(`~/engage`) · 축별 조향(`~/steer_axis_deg`) · 전축 조향(`~/steer_deg`) ·
구동(`~/drive_mmps`) · 정지(`~/stop`) · 호밍(`~/home`·`~/home_cancel`) · 실측 신선도(TTL).
"""
import threading
import time

import pytest

rclpy = pytest.importorskip("rclpy", reason="ROS2 미소싱 환경 — GUI 계약 회귀는 건너뛴다")

from rclpy.executors import MultiThreadedExecutor      # noqa: E402
from sensor_msgs.msg import JointState                 # noqa: E402
from std_srvs.srv import SetBool, Trigger              # noqa: E402

from can_relay.driver_node import CanRelayNode         # noqa: E402
from can_relay.link import MockLink                    # noqa: E402
from can_relay.ui.backend_base import BackendBase       # noqa: E402
from can_relay.ui.backend_ros2 import RelayClient       # noqa: E402


class _Adapter(BackendBase):
    """`settled` 는 `BackendBase` 가 소유한다 — 시험은 **공용 구현**을 그대로 쓴다.

    (백엔드 교체 구조로 바뀌면서 옮겨졌다: ADR 2026-08-04.)
    """

    def __init__(self, client):
        self.client = client

    def meas_angle(self, node):
        return self.client.meas_angle(node)

ROS_ARGS = [
    "--ros-args",
    "-p", "link:=mock",
    "-p", "steer_home_counts:=[7871815,7840086]",
    "-p", "require_homed_for_steer:=false",
    "-p", "seer_enabled:=false",        # GUI 쪽 — 네트워크를 타지 않는다
]

WAIT_S = 5.0


def _wait(cond, timeout=WAIT_S):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if cond():
            return True
        time.sleep(0.02)
    return False


@pytest.fixture
def rig():
    """드라이버 + GUI 클라이언트를 한 실행기에 올린다. `(driver, client)` 반환."""
    rclpy.init(args=ROS_ARGS)
    driver = CanRelayNode()
    client = RelayClient()
    executor = MultiThreadedExecutor(num_threads=6)
    executor.add_node(driver)
    executor.add_node(client)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    try:
        yield driver, client
    finally:
        try:
            driver.backend.cancel_home()
        except Exception:
            pass
        driver.backend.shutdown()
        executor.shutdown()
        client.destroy_node()
        driver.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def _engage(client):
    ok, why = client.call(client.cli_engage, SetBool.Request(data=True))
    assert ok, why
    return ok


# ── 제어권 ────────────────────────────────────────────────────────────────
def test_engage_and_release_through_service(rig):
    driver, client = rig
    assert _engage(client)
    assert driver.link.engaged is True
    assert driver.backend.snapshot()["running"] is True

    ok, why = client.call(client.cli_engage, SetBool.Request(data=False))
    assert ok, why
    assert driver.link.engaged is False


def test_service_absence_is_reported_not_raised(rig):
    """드라이버가 없을 때 GUI 가 예외로 죽으면 안 된다 — 문자열로 돌려준다."""
    _driver, client = rig
    ghost = client.create_client(Trigger, "/nonexistent_node/stop")
    ok, why = client.call(ghost, Trigger.Request())
    assert ok is False and "서비스 없음" in why


# ── 조향 ──────────────────────────────────────────────────────────────────
def test_steer_axis_topic_moves_only_that_axis(rig):
    """축별 슬라이더 경로 — 이식을 위해 신설한 인터페이스가 실제로 붙는지."""
    driver, client = rig
    _engage(client)
    client.send_steer_axis(3, 10.0)
    assert _wait(lambda: set(driver.backend._steer_counts) == {3}), \
        f"축별 지령 미반영: {driver.backend._steer_counts}"
    counts_3 = driver.backend._steer_counts[3]

    client.send_steer_axis(4, -20.0)
    assert _wait(lambda: 4 in driver.backend._steer_counts)
    assert driver.backend._steer_counts[3] == counts_3, "다른 축 목표가 바뀌었다"


def test_steer_axis_out_of_range_is_clamped_not_rejected(rig):
    driver, client = rig
    _engage(client)
    client.send_steer_axis(3, 500.0)
    assert _wait(lambda: 3 in driver.backend._steer_counts)
    home = driver.backend.cfg.steer_home[3]
    limit = 90.0 * driver.backend.cfg.steer_counts_per_deg
    assert driver.backend._steer_counts[3] == int(round(home + limit))


def test_steer_axis_malformed_payload_is_rejected_with_reason(rig):
    """`[node, deg]` 가 아니면 거부 카운터가 올라가야 한다 — 조용히 버리지 않는다."""
    driver, client = rig
    _engage(client)
    before = driver._rejected
    from std_msgs.msg import Float64MultiArray
    client.pub_steer_axis.publish(Float64MultiArray(data=[3.0]))       # 길이 1
    assert _wait(lambda: driver._rejected > before), "형식 오류가 거부로 집계되지 않았다"


def test_steer_all_axes_topic(rig):
    driver, client = rig
    _engage(client)
    client.send_steer(15.0)
    assert _wait(lambda: set(driver.backend._steer_counts) == {3, 4}), \
        "전축 조향(~/steer_deg)이 두 축에 반영되지 않았다"


# ── 구동 · 정지 ───────────────────────────────────────────────────────────
def test_drive_and_stop_through_ros(rig):
    driver, client = rig
    _engage(client)
    client.send_drive(50.0)
    assert _wait(lambda: driver.backend.snapshot()["drive_units"] != 0)

    ok, _why = client.call(client.cli_stop, Trigger.Request())
    assert ok
    assert driver.backend.snapshot()["drive_units"] == 0


def test_estop_latch_blocks_drive(rig):
    driver, client = rig
    _engage(client)
    client.send_estop(True)
    assert _wait(lambda: driver.backend.snapshot()["estop"] is True)
    client.send_drive(50.0)
    time.sleep(0.2)
    assert driver.backend.snapshot()["drive_units"] == 0, "E-stop 중에 구동이 나갔다"


# ── 실측 신선도 (원본 High 의 재발 방지) ─────────────────────────────────
def test_measured_angle_expires(rig):
    """TTL 밖 실측은 없는 것으로 친다 — 원본은 이것이 없어 정지된 값으로 정착 판정했다."""
    _driver, client = rig
    client.set_parameters([rclpy.parameter.Parameter(
        "meas_ttl_s", rclpy.Parameter.Type.DOUBLE, 0.3)])
    js = JointState()
    js.name = ["steer_3", "steer_4"]
    js.position = [0.0, 0.0]
    client._on_joints(js)
    assert client.meas_angle(3) == pytest.approx(0.0)
    assert _Adapter(client).settled(0.0, 1.0, (3, 4)) is True
    time.sleep(0.4)
    assert client.meas_angle(3) is None, "만료된 실측이 살아 있다"
    assert _Adapter(client).settled(0.0, 1.0, (3, 4)) is False, \
        "만료된 값으로 정착 판정했다"


def test_settled_requires_all_axes(rig):
    """한 축만 맞으면 정착이 아니다 — crab 은 앞뒤가 같아야 성립한다."""
    _driver, client = rig
    js = JointState()
    js.name = ["steer_3"]
    js.position = [0.0]
    client._on_joints(js)
    assert _Adapter(client).settled(0.0, 1.0, (3, 4)) is False


def test_joint_states_flow_from_driver(rig):
    """드라이버 → GUI 실측 경로가 실제로 이어지는지(발행·구독 배선)."""
    driver, client = rig
    _engage(client)
    for node, pos in ((3, 7871815), (4, 7840086)):
        for idx, size in ((0x6064, 4), (0x6041, 2)):
            val = pos if idx == 0x6064 else 0x9450
            cmd = {2: 0x4B, 4: 0x43}[size]
            data = bytes([cmd, idx & 0xFF, idx >> 8, 0]) + \
                (val & 0xFFFFFFFF).to_bytes(4, "little")[:size]
            driver.link.inbox.append((0x580 + node, data + b"\x00" * (8 - len(data)), 2))
    assert _wait(lambda: client.meas_angle(3) is not None, timeout=8.0), \
        "joint_states 가 GUI 까지 도달하지 않았다"
    assert client.meas_angle(3) == pytest.approx(0.0, abs=0.01)


# ── 호밍 — 드라이버의 H1 계약(호밍 중에도 다른 콜백이 소비된다) ─────────
def test_home_and_cancel_through_ros(rig):
    """호밍 중 취소 서비스가 도달하는지 — **드라이버 계약**이다(UI 는 노출하지 않는다)."""
    driver, client = rig
    _engage(client)
    driver.link.homing_script = [MockLink.homing_state(4)]      # WAIT 유지

    result = {}

    def home_call():
        result["home"] = client.call(client.cli_home, Trigger.Request(), timeout_s=30.0)

    th = threading.Thread(target=home_call, daemon=True)
    th.start()
    assert _wait(lambda: driver.backend.snapshot()["homing"]), "호밍이 시작되지 않았다"

    # ⚠ `cli_home_cancel` 는 RelayClient 에서 뺐다 — UI 가 취소를 노출하지 않기로 했기 때문이다
    #   (ADR 2026-08-04 §Decision ②). **드라이버 서비스는 그대로 있고**, 그 계약(H1: 호밍 중에도
    #   다른 콜백이 소비된다)은 여전히 고정해야 하므로 여기서 클라이언트를 직접 만든다.
    cli_cancel = client.create_client(Trigger, "/can_relay_node/home_cancel")
    ok, why = client.call(cli_cancel, Trigger.Request())
    assert ok, f"호밍 취소가 수리되지 않았다: {why}"
    th.join(timeout=WAIT_S)
    assert "home" in result, "취소 후에도 ~/home 이 반환하지 않았다"
    assert driver.backend.snapshot()["homing"] is False
