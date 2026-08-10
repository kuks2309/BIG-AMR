#!/usr/bin/env python3
"""Seer 상태 API `1004` → `/seer/robot_pose`(PoseStamped) 발행 — **참조·검증 채널**.

# 역할 (2026-08-08 변경 — 제어 입력이 아니다)

**측위의 주인은 PC 다.** `/robot_pose` 는 PC 측위 스택(`mcl2d_ros2` → 어댑터)이 소유하고,
본 노드는 **Seer 가 연결돼 있을 때만** 그 옆에서 같은 시각의 Seer 자세를 내보내
**우리 측위를 대조**하는 데 쓴다.

    mcl2d  → /robot_pose        ← 제어가 쓰는 자세 (PC)
    이 노드 → /seer/robot_pose   ← 대조용 참조 (Seer 가 있을 때만)

근거(사용자 지시 2026-08-08):
- 「localization 은 PC 를 사용해야 합니다」
- 「Seer 측위는 … 검증자로 쓰는 게 좋겠습니다 … **seer 가 연결되어 있을 때만**」

⇒ **본 노드가 없어도 주행은 영향받지 않는다.** 비교를 못 할 뿐이다. 초판은 `/robot_pose` 를
직접 발행해 제어 체인이 Seer 에 의존했는데, 그것은 「Seer 제어를 PC 로 대체한다」는 목적과
모순이라 참조 채널로 분리했다.

# 배경 — 왜 `/robot_pose` 공백이 문제였나

`trnav_2ws_action_server` 의 `translate_forward`·`translate_reverse`·`mpc`·`mpc_reverse`
네 액션은 `trnav_2ws_core::LocalizationMonitor` 로 `/robot_pose` 를 구독하며, **그 토픽이
없으면 목표 접수 직후 `status −3` 로 abort** 한다. 에러 문구는
`TF2 map->base_link not available` 이지만 **TF 문제가 아니다** — `localization_monitor.cpp:137-150`
은 TF 를 전혀 쓰지 않고 토픽 캐시를 읽는다(문구가 실제 기전과 어긋나 있다).

그 토픽을 PC 측위가 채우는 것이 정본 구성이고, 본 노드는 그 옆의 참조다.
(`pose_topic:=/robot_pose` 로 덮어쓰면 Seer 를 유일 측위원으로 쓰는 구성도 가능하나,
그때는 노드가 의존성 경고를 남긴다.)

# 좌표계

본 저장소는 **Seer 맵을 그대로 가져다 쓴다**. smap 파서도 좌표를 미터 그대로 보관하고 원점을
이동하지 않는다(`mcl2d_map/include/mcl2d_map/smap.hpp:29-32`). 따라서 `1004` 의
`x`·`y`·`angle` 은 액션이 받는 경로와 같은 프레임이며 변환이 없다.
**단 그 동일성은 코드가 아니라 운용 상태에 달려 있다** — 그래서 맵 게이트를 둔다.

# ⚠ 폴링 주기 — 기본 10 Hz 인 이유

`References/Seer-Driver/seer_api_guide.md:28`:

    요청 간격 ≥100~200ms 권장(과빈번 시 로봇이 연결 정리) → 실효 폴링 ~5–10Hz

액션 제어 주기는 20 Hz 지만 **벤더 권장을 넘겨 폴링하면 로봇이 연결을 끊는다.**
`LocalizationMonitor` 의 신선도 임계는 `localization_timeout_sec: 0.5` 이므로 10 Hz(100 ms)
면 **5배 여유**로 충족한다. 20 Hz 로 10초 폴링이 200/200 성공한 실측이 있으나(2026-08-06),
그것은 **지속 운용 안전의 근거가 아니다** — 기본값을 권장 안쪽에 둔다.

⚠ 제어 품질 관점의 미확인 사항: 자세가 10 Hz 로 갱신되면 20 Hz 제어 루프는 같은 자세를 두 번
쓴다. 0.2 m/s 에서 100 ms = 2 cm. 실기에서 경로 추종 오차에 어떤 영향인지 **미측정**.

**더 나은 경로**: Seer Push API(포트 19301, 동시 10 연결)는 로봇이 능동 push 하여 폴링 부담이
없다. 다만 **구독 항목 설정 방법이 우리 참조에 미열람**(`seer_api_guide.md:166`)이라 사양
확보 전에는 쓸 수 없다. 확보되면 이 노드를 그쪽으로 옮기는 것이 맞다.

# 안전 — 읽기 전용

상태 포트 19204 **만** 연다. `csm.seer_client` 의 `_ALLOWED_PORTS` 가 접속 시점에 강제하며,
제어(19205)·내비(19206)·설정(19207) 포트와 명령 API 번호는 이 파일에 등장하지 않는다.
**본 노드는 로봇을 움직일 수 없다.**
"""

from __future__ import annotations

import math
import socket

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Float64

# csm 은 정식 ROS2 패키지다. 프레이밍을 복제하지 않고 재사용하는 이유는 그 모듈이
# **읽기 전용 포트 허용목록을 접속 시점에 강제**하기 때문이다 — 복제하면 그 가드도
# 복제해야 하고, 한쪽만 고쳐지는 순간 안전 성질이 갈라진다.
from csm.seer_client import SeerError, SeerStatusClient

API_INFO = 1000       # 로봇 정보 — current_map / current_map_md5 포함
API_LOCATION = 1004   # robot_status_loc_req — x(m) · y(m) · angle(rad) · confidence[0,1]
PORT_STATUS = 19204   # 상태 포트 전용


class SeerPosePublisher(Node):
    """Seer 위치를 폴링해 `/robot_pose` 로 중계한다."""

    def __init__(self) -> None:
        super().__init__("seer_pose_publisher")

        self._declare()

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        # ⚠ 기본 발행 토픽은 `/seer/robot_pose` 이지 `/robot_pose` 가 **아니다**.
        #   `/robot_pose` 는 **PC 측위**(mcl2d)가 소유한다. 이 노드를 거기에 물리면 제어 체인이
        #   Seer 에 의존하게 되어, Seer 가 빠지면 주행이 멈춘다 — 그것은 Seer 제어를 대체한다는
        #   목적과 모순이다(사용자 지시 2026-08-08: 「측위는 PC 를 사용해야 합니다」,
        #   「Seer 측위는 검증자로 … seer 가 연결되어 있을 때만」).
        #   따라서 이 노드는 **참조 채널**이다 — 없으면 비교를 못 할 뿐 주행은 영향받지 않는다.
        #   Seer 를 유일한 측위원으로 쓰는 구성(초기 브링업 등)에서만 `pose_topic:=/robot_pose`.
        self._pose_pub = self.create_publisher(PoseStamped, self._pose_topic, qos)
        self._conf_pub = self.create_publisher(Float64, "/seer/localization_confidence", qos)

        self._sock: SeerStatusClient | None = None
        self._map_ok = False
        self._fail_streak = 0
        self._last_warn_ns = 0

        self.get_logger().info(
            f"Seer {self._host}:{PORT_STATUS} · {self._rate:.1f} Hz · frame '{self._frame}' · "
            f"발행 '{self._pose_topic}' · "
            f"맵 게이트 {'ON' if self._expect_md5 else 'OFF(expected_map_md5 미설정)'}")
        if self._pose_topic == "/robot_pose":
            self.get_logger().warn(
                "pose_topic 이 '/robot_pose' 다 — 제어 체인이 **Seer 에 의존**한다. "
                "PC 측위(mcl2d)를 쓰는 구성에서는 기본값 '/seer/robot_pose' 로 둘 것.")

        self._connect()
        self._check_map()

        self.create_timer(1.0 / self._rate, self._on_pose_timer)
        if self._map_recheck > 0.0:
            self.create_timer(self._map_recheck, self._on_map_timer)

    # ------------------------------------------------------------ parameters

    def _declare(self) -> None:
        self._host = self.declare_parameter("host", "192.168.44.82").value
        # 참조 채널 기본값. `/robot_pose` 는 PC 측위(mcl2d) 소유 — 위 발행자 주석 참조.
        self._pose_topic = str(self.declare_parameter("pose_topic", "/seer/robot_pose").value)
        # 기본 10 Hz — 벤더 권장(≥100~200 ms) 안쪽. 모듈 docstring §폴링 주기 참조.
        self._rate = float(self.declare_parameter("rate_hz", 10.0).value)
        self._frame = self.declare_parameter("frame_id", "map").value
        # 빈 문자열이면 게이트 비활성(경고만). 설정하면 불일치 시 **발행하지 않는다.**
        self._expect_md5 = str(self.declare_parameter("expected_map_md5", "").value).strip()
        self._map_recheck = float(self.declare_parameter("map_recheck_sec", 5.0).value)
        # 0 이면 비활성. 초과 설정 시 confidence 미만 표본은 발행하지 않는다.
        self._min_conf = float(self.declare_parameter("min_confidence", 0.0).value)
        self._timeout = float(self.declare_parameter("timeout_sec", 0.3).value)

        if self._rate <= 0.0:
            raise ValueError("rate_hz 는 0보다 커야 한다")
        if self._rate > 10.0:
            self.get_logger().warn(
                f"rate_hz={self._rate:.1f} 는 벤더 권장(≥100 ms → ≤10 Hz)을 넘는다. "
                f"과빈번 폴링 시 로봇이 연결을 끊는다 "
                f"(References/Seer-Driver/seer_api_guide.md:28).")

    # ------------------------------------------------------------ connection

    def _connect(self) -> bool:
        """상태 포트에 접속한다. 실패는 예외가 아니라 False — 다음 주기에 재시도한다."""
        self._close()
        try:
            c = SeerStatusClient(self._host, timeout=self._timeout)
            # SeerStatusClient 는 컨텍스트 매니저로 설계돼 있다. 장수명 노드에서는
            # 직접 열고 닫는다(모듈을 고치지 않기 위해 __enter__/__exit__ 를 그대로 쓴다).
            c.__enter__()
            self._sock = c
            self.get_logger().info(f"Seer 접속 — {self._host}:{PORT_STATUS}")
            return True
        except (OSError, SeerError) as exc:
            self._sock = None
            self._warn_throttled(f"Seer 접속 실패: {exc}")
            return False

    def _close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.__exit__(None, None, None)
            except Exception:  # noqa: BLE001 — 종료 경로에서 예외를 삼킨다
                pass
            self._sock = None

    # -------------------------------------------------------------- map gate

    def _check_map(self) -> bool:
        """로드된 맵이 기대값과 같은지 확인한다.

        같은 좌표계라는 전제는 **Seer 에 같은 맵이 올라와 있을 때만** 성립한다.
        다른 맵이면 자세가 조용히 어긋나므로, 여기서 막아 **시끄러운 실패**로 바꾼다.
        """
        if self._sock is None:
            self._map_ok = False
            return False
        try:
            info = self._sock.request(API_INFO)
        except (OSError, SeerError) as exc:
            self._warn_throttled(f"맵 확인 실패: {exc}")
            self._map_ok = False
            # 같은 이유로 소켓을 버린다 — 어긋난 스트림에서는 맵 이름도 믿을 수 없고,
            # 닫지 않으면 이 경로가 영원히 같은 쓰레기를 읽는다(실기에서 관측된 형태다).
            self._close()
            return False

        name = info.get("current_map", "")
        md5 = str(info.get("current_map_md5", ""))

        if not self._expect_md5:
            if not self._map_ok:
                self.get_logger().warn(
                    f"맵 게이트 **비활성** — 로드된 맵 '{name}' (md5 {md5}). "
                    f"expected_map_md5 를 설정하면 다른 맵일 때 발행을 막는다.")
            self._map_ok = True
            return True

        if md5 == self._expect_md5:
            if not self._map_ok:
                self.get_logger().info(f"맵 일치 — '{name}' (md5 {md5})")
            self._map_ok = True
            return True

        self.get_logger().error(
            f"맵 불일치 — 발행하지 않는다. 로드됨 '{name}' md5 {md5} ≠ 기대 {self._expect_md5}. "
            f"경로 좌표계가 어긋난다.")
        self._map_ok = False
        return False

    def _on_map_timer(self) -> None:
        """운용 중 맵이 교체될 수 있으므로 주기적으로 다시 본다."""
        if self._sock is not None:
            self._check_map()

    # ------------------------------------------------------------------ poll

    def _on_pose_timer(self) -> None:
        if self._sock is None:
            if self._connect():
                self._check_map()
            return
        if not self._map_ok:
            return

        try:
            r = self._sock.request(API_LOCATION)
        except (OSError, socket.timeout, SeerError) as exc:
            self._fail_streak += 1
            self._warn_throttled(f"1004 실패({self._fail_streak}회 연속): {exc}")
            # ⚠ **한 번이라도 실패하면 소켓을 버린다.** 이 프로토콜에는 요청 ID 가 없어
            #   응답을 요청과 맞출 수단이 없다. 타임아웃 뒤 늦게 도착한 응답은 버퍼에
            #   남아 있다가 **다음 읽기에서 헤더로 해석**되고, 그때부터 스트림이 영구히
            #   어긋난다(실기 2026-08-10: `bad sync byte 0x7B`=`{`, `0x22`=`"` — JSON 본문을
            #   헤더로 읽고 있었다). 종전에는 3회 연속이어야 닫아서, 그 사이에 이미
            #   어긋난 소켓으로 계속 읽었고 **복구 경로가 없었다.**
            self._close()
            self._fail_streak = 0
            return

        self._fail_streak = 0

        ret = r.get("ret_code", 0)
        if ret:
            self._warn_throttled(f"1004 ret_code={ret} err_msg={r.get('err_msg', '')}")
            return

        try:
            x = float(r["x"])
            y = float(r["y"])
            yaw = float(r["angle"])          # 벤더 원문 v1.2.1 p.20 — 단위 rad
        except (KeyError, TypeError, ValueError) as exc:
            self._warn_throttled(f"1004 응답에 x/y/angle 이 없다: {exc}")
            return

        conf = r.get("confidence")
        if conf is not None:
            self._conf_pub.publish(Float64(data=float(conf)))
            if self._min_conf > 0.0 and float(conf) < self._min_conf:
                self._warn_throttled(
                    f"confidence {float(conf):.3f} < {self._min_conf:.3f} — 발행 보류")
                return

        msg = PoseStamped()
        # ⚠ stamp 는 **수신 시각(ROS clock)** 이다. 응답의 `create_on` 을 쓰지 않는 이유:
        #   Seer 와 본 호스트의 시계 동기가 확인되지 않았고, LocalizationMonitor 가
        #   `localization_timeout_sec: 0.5` 로 신선도를 판정하므로 시계 오프셋이 있으면
        #   정상 데이터를 stale 로 오판하거나 그 반대가 된다. 수신 시각이 보수적으로 안전하다.
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.position.z = 0.0
        msg.pose.orientation.z = math.sin(yaw / 2.0)
        msg.pose.orientation.w = math.cos(yaw / 2.0)
        self._pose_pub.publish(msg)

    # ----------------------------------------------------------------- utils

    def _warn_throttled(self, text: str, period_ns: int = 2_000_000_000) -> None:
        now = self.get_clock().now().nanoseconds
        if now - self._last_warn_ns >= period_ns:
            self._last_warn_ns = now
            self.get_logger().warn(text)

    def destroy_node(self) -> bool:
        self._close()
        return super().destroy_node()


def main(argv=None) -> int:
    rclpy.init(args=argv)
    node = None
    try:
        node = SeerPosePublisher()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
