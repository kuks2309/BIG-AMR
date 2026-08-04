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
from std_msgs.msg import Bool, Float64                 # noqa: E402
from std_srvs.srv import SetBool, Trigger              # noqa: E402

from can_relay.driver_node import CanRelayNode, LATCHED_QOS   # noqa: E402
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
    """드라이버의 `~/stop` 은 요청 즉시 구동을 0 으로 만든다.

    ⚠ 2026-08-04: `RelayClient.send_drive` 는 이제 **주기 재발행**한다 — UI 가 연속 지령자여야
    드라이버 워치독(`cmd_timeout_s`=0.3 s)이라는 안전장치를 살린 채 조그가 유지된다
    (사용자 결정: 「ros2 설계는 맞고 UI 에서 계속 명령을 내는 것이 맞다」).
    따라서 여기서는 재발행이 섞이지 않도록 **생 퍼블리셔**로 한 번만 지령해 드라이버만 본다.
    UI 경로의 정지는 `test_stop_wins_over_republish` 가 따로 고정한다(유지값을 먼저 0 으로 내림).
    """
    driver, client = rig
    _engage(client)
    ns = str(client.cfg["driver_ns"]).rstrip("/")
    pub = client.create_publisher(Float64, f"{ns}/drive_mmps", 10)
    try:
        # 새 퍼블리셔는 디스커버리가 끝나야 도달한다. 연결을 **먼저 기다린 뒤 딱 한 번** 보낸다 —
        # 반복 발행하면 큐에 쌓인 지령이 `~/stop` **이후에** 도착해 정지를 덮어쓴다(2026-08-04 실측).
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and pub.get_subscription_count() < 1:
            time.sleep(0.05)
        assert pub.get_subscription_count() >= 1, "드라이버가 구독을 열지 않았다"
        # GUI 가 유휴 상태에서 조용해질 때까지 기다린다(정지 0 반복 구간 ZERO_HOLD_S).
        # 이 대기가 없으면 우리 0 이 외부 지령을 즉시 덮어써 드라이버에 도달조차 못 한다.
        from can_relay.ui.backend_ros2 import ZERO_HOLD_S
        time.sleep(ZERO_HOLD_S + 0.2)
        pub.publish(Float64(data=50.0))
        assert _wait(lambda: driver.backend.snapshot()["drive_units"] != 0), \
            "지령이 드라이버에 도달하지 않았다"

        ok, _why = client.call(client.cli_stop, Trigger.Request())
        assert ok
        assert driver.backend.snapshot()["drive_units"] == 0
    finally:
        client.destroy_publisher(pub)


def test_estop_latch_blocks_drive(rig):
    """드라이버의 `~/estop` 래치 회귀.

    ⚠ 2026-08-04: GUI 쪽 E-stop 배선(`pub_estop`·`send_estop`)은 **삭제됐다** — 원본에 E-stop 이
    없어 UI 에 버튼이 없고, 아무도 호출하지 않는 경로였다(리뷰 Medium ③·④). 그러나 **드라이버의
    `estop` 구독은 계약이므로 살아 있고**, 이 시험이 계속 고정한다. GUI 를 거치지 않고 직접
    발행한다 — 시험 대상이 드라이버이지 GUI 가 아니기 때문이다.
    """
    driver, client = rig
    _engage(client)
    pub = client.create_publisher(Bool, "/estop", LATCHED_QOS)
    pub.publish(Bool(data=True))
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


# ── 구동 지령 유지 (2026-08-04 실기에서 확정된 결함) ──────────────────────
def test_drive_command_is_republished_so_watchdog_does_not_kill_the_jog(rig):
    """`Ros2Backend` 는 구동 지령을 **주기 재발행**해야 한다.

    ⚠ 2026-08-04 실기 실측: 단발 발행이면 드라이버 워치독(`cmd_timeout_s`=0.3 s)이 만료시켜
    실속도가 −1172 까지 올라갔다가 **0.75 초경 스스로 0** 이 됐다. 같은 UI 인데
    `--backend direct` 는 유지되고 `--backend ros2` 만 꺼지면 「UI 100% 동일」이 깨진다.
    원본 `gui.py` 도 폴 루프가 매 주기 재송신한다(리뷰 High ③).
    """
    driver, client = rig
    _engage(client)
    client.send_drive(50.0)                      # **한 번만** 부른다
    assert _wait(lambda: driver.backend.snapshot()["drive_units"] != 0), "지령이 도달하지 않았다"

    # 워치독 만료보다 넉넉히 오래 기다린다 — 재발행이 있으면 지령이 살아 있어야 한다.
    #
    # ⚠ 판정은 **두 가지**를 본다. 이 rig 는 드라이버와 클라이언트를 한 실행기에 올리므로,
    #   전체 시험을 함께 돌리면 타이머가 밀려 드라이버 쪽 상태만으로는 간헐 실패가 난다
    #   (2026-08-04 실측). 그래서 **우리가 통제하는 발행 횟수**를 주 판정으로 삼고,
    #   드라이버 상태는 잠깐의 스케줄링 지연을 흡수하도록 재시도한다.
    #   재발행이 아예 없으면(원래 결함) 발행은 1건뿐이고 드라이버 상태도 0 으로 남아 둘 다 깨진다.
    ns = str(client.cfg["driver_ns"]).rstrip("/")
    seen = []
    sub = client.create_subscription(Float64, f"{ns}/drive_mmps",
                                     lambda m: seen.append(m.data), 20)
    timeout_s = driver.backend.cfg.cmd_timeout_s
    window = timeout_s * 4
    time.sleep(0.2)                       # 구독 연결
    seen.clear()
    t0 = time.monotonic()
    while time.monotonic() - t0 < window:
        time.sleep(0.05)
    client.destroy_subscription(sub)

    assert len(seen) >= 5, (
        f"{window:.1f}s 동안 구동 지령 발행이 {len(seen)}건뿐 — 재발행이 없다")
    assert all(v == 50.0 for v in seen), f"재발행 값이 지령과 다르다: {set(seen)}"
    for _ in range(20):                   # 스케줄링 지연 흡수(재발행이 있으면 곧 복구된다)
        if driver.backend.snapshot()["drive_units"] != 0:
            break
        time.sleep(0.05)
    assert driver.backend.snapshot()["drive_units"] != 0, (
        f"발행은 {len(seen)}건 있었는데 드라이버 지령이 0 이다 — 전달 경로를 확인할 것")

    client.send_drive(0.0)
    assert _wait(lambda: driver.backend.snapshot()["drive_units"] == 0)


def test_zero_is_repeated_briefly_then_goes_quiet(rig):
    """정지 0 은 **잠깐 반복**하고(유실 방지) 그 뒤에는 **조용해진다**(토픽 점유 금지).

    ⚠ 2026-08-04: 처음에는 0 도 무기한 재발행했는데, 그러면 이 GUI 가 유휴 상태에서도
    `~/drive_mmps` 를 영구 점유해 **다른 지령자의 지령을 즉시 덮어썼다** — 외부에서 넣은 50 이
    드라이버에 도달조차 못 했다(`test_drive_and_stop_through_ros` 가 이를 잡았다).
    """
    from can_relay.ui.backend_ros2 import ZERO_HOLD_S
    driver, client = rig
    _engage(client)
    ns = str(client.cfg["driver_ns"]).rstrip("/")
    got = []
    sub = client.create_subscription(Float64, f"{ns}/drive_mmps",
                                     lambda m: got.append((time.monotonic(), m.data)), 10)
    time.sleep(0.3)                       # 구독 연결
    got.clear()
    client.send_drive(0.0)
    t_cmd = time.monotonic()
    time.sleep(ZERO_HOLD_S * 0.6)
    during = len(got)
    time.sleep(ZERO_HOLD_S + 0.4)
    after = len([1 for t, _ in got if t > t_cmd + ZERO_HOLD_S + 0.1])
    client.destroy_subscription(sub)
    assert during >= 3, f"정지 0 이 반복되지 않는다(보유 구간 수신 {during}건)"
    assert all(v == 0.0 for _, v in got), got
    assert after == 0, f"보유 시간이 지나도 계속 발행한다({after}건) — 토픽을 점유한다"


def test_stop_wins_over_republish(rig):
    """정지가 재발행보다 **세다** — 유지값을 내리지 않으면 정지가 무효화된다.

    2026-08-04: 재발행 타이머를 넣자마자 `~/stop` 직후 마지막 비영 지령이 다시 나가
    구동이 되살아났다. 기존 회귀 `test_drive_and_stop_through_ros` 가 이를 잡았고,
    여기서는 **정지 후 충분히 오래** 지켜봐 되살아나지 않음을 고정한다.
    """
    from can_relay.ui.backend_ros2 import Ros2Backend
    driver, client = rig
    _engage(client)
    be = Ros2Backend.__new__(Ros2Backend)      # 노드는 rig 것을 쓴다(스핀 중)
    be.node = client
    client.send_drive(50.0)
    assert _wait(lambda: driver.backend.snapshot()["drive_units"] != 0)

    ok, _why = be.stop()
    assert ok
    t0 = time.monotonic()
    while time.monotonic() - t0 < driver.backend.cfg.cmd_timeout_s * 3:
        assert driver.backend.snapshot()["drive_units"] == 0, "정지 후 구동이 되살아났다"
        time.sleep(0.05)
