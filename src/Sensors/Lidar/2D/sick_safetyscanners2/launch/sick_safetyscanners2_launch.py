# ⚠ channel 은 0 이 아니라 1 이다 — 이 라이다를 Seer 컨트롤러와 공유하기 때문이다.
#
# 드라이버는 기동 시 COLA2 `changeSensorSettings()` 로 **센서 쪽 출력 채널의 목적지**를
# host_ip:host_udp_port 로 덮어쓴다(SickSafetyscanners.cpp:145). 센서의 저장 구성(Safety Designer)
# 이 채널 0 을 Seer 에게 물려 두고 있어, 우리가 채널 0 을 쓰면 Seer 의 스트림을 빼앗는다. 게다가
# 이 설정은 **우리 노드를 종료해도 센서에 그대로 남는다**(드라이버에 원복 코드 없음) — 한 번
# 빼앗으면 Seer 는 마지막 프레임에 얼어붙는다. Seer 프로그램 재시작(5004)으로도 안 돌아온다:
# Seer 는 설정을 쓰지 않고 **듣기만** 하기 때문이다. [실측 2026-08-07]
#
# 사고 시 원복 방법 — 센서 저장 구성을 CoLa 2 로 판독해 Seer 수신 주소를 확정해 뒀다
# (`Tools/sick_channel_audit/read_output_channels.py`, Index 177):
#     전방 .100 → 192.168.192.5:6060 · 후방 .101 → 192.168.192.5:6061  (둘 다 채널 0)
# 채널 0 을 실수로 덮어썼다면 이 드라이버를
#     channel:=0 host_ip:=192.168.192.5 host_udp_port:=6060(후방 6061)
# 로 한 번 띄워 되돌린다. 전원 재인가로도 저장 구성이 복귀한다.
#
# [실측] 2026-08-07, 센서 NANS3-CAAZ30AN1P02(nanoScan3, FW(firmware) R01.66):
#   채널 1 → 6070 으로 /scan 34.04 Hz 를 받는 **동시에** 채널 0 → 6060 이 204 pkt/s 로 계속 흘렀다.
#   → 이 센서는 UDP 출력 채널을 2개 이상 동시 지원한다. Seer=채널 0, 우리=채널 1 로 공존한다.
# ※ 멀티캐스트도 드라이버는 지원하지만(host_ip 가 multicast 면 interface_ip 로 그룹 가입 —
#   SickSafetyscanners.cpp:156) Seer **수신 측**을 그룹에 가입시킬 수단이 확인되지 않아 채택하지 않았다.
#
# use_persistent_config=False 이므로 플래시에는 쓰지 않는다(센서 전원 재인가 시 원복).
#
# ── 1차 source 대조 (2026-08-07) ─────────────────────────────────────────────
# ✓ 채널 번호 범위는 **0…3**(최대 4채널)이다 — `u8ChannelNumber`: "Number of the channel to be
#   configured (0 ... 3)". 따라서 channel=1 은 규격 내다.
#   [microScan3/outdoorScan3/nanoScan3 — Data output via UDP and TCP/IP, 8022708/1W29,
#    Table 73 §6.3.2.2, page 62](../../../../../References/sick/nanoscan3/technical_information_data_output_udp_tcpip_en_im0083701.pdf)
#   ※ 단 "The number of available data output channels depends on the device variant"(page 9)
#     이므로 변이형별 상한은 다를 수 있다. 본 기체는 채널 0·1 동시 동작을 실측했다.
# ✓ 채널은 서로 독립이다 — "Every data output channel has independent settings."
#   [nanoScan3 I/O Operating Instructions, 8024596/1W27, page 94]
# ✓ **데이터 출력은 애초에 안전 기능이 아니다** — DANGER "Data output may only be used for general
#   monitoring and control tasks. → Do not use data output for safety-related applications."
#   [8022708/1W29, §2.1 page 6 · §4 page 9]. 운영지침도 "This data is not intended for use in
#   safety-related applications" 이며 용도로 **AGV 내비게이션 지원**을 명시한다
#   [8024596/1W27, page 94]. ⇒ 채널 추가는 비안전 데이터 경로 설정이며 OSSD 와 무관하다.
# ✓ 이 설정이 전원 재인가로 원복되는 이유도 문서에 있다 — "This configuration is not permanent,
#   i.e. the previously saved configuration will be active again after restarting the device."
#   [8022708/1W29, §6.3.2.2, page 62]. 즉 Safety Designer 저장 설정은 우리가 못 건드린다.

import importlib.util
import os

from launch import LaunchDescription
from launch.actions import OpaqueFunction
from launch_ros.actions import Node


def _guard(context, *args, **kwargs):
    """기동 전 검사 — 남이 쓰는 채널을 빼앗으려 하면 여기서 런치를 중단시킨다.

    주석·문서는 **그 파일을 보지 않는 경로로 기동하면 무력**하다는 것이 2026-08-07·08-08
    사고로 증명됐다(각각 Seer 라이다 정지). 그래서 기동 경로 자체에 기계 검사를 둔다.
    `channel_guard.py` 는 이 파일과 같은 `launch/` 에 있고 CMakeLists 가 디렉터리째 설치하므로
    어느 워크트리에서 띄우든 함께 따라온다.
    """
    path = os.path.join(os.path.dirname(__file__), "channel_guard.py")
    spec = importlib.util.spec_from_file_location("channel_guard", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for sensor_ip, channel, label in ((FRONT_IP, CHANNEL, "front"), (REAR_IP, CHANNEL, "rear")):
        mod.assert_channel_free(sensor_ip, channel, label)   # 점유 시 RuntimeError → 기동 중단
    return []


FRONT_IP = "192.168.192.100"
REAR_IP = "192.168.192.101"
CHANNEL = 1                 # ⚠ 0 으로 되돌리지 말 것 — 파일 상단 주석 참조


def generate_launch_description():
    return LaunchDescription([
        OpaqueFunction(function=_guard),
        Node(
            package="sick_safetyscanners2",
            executable="sick_safetyscanners2_node",
            name="sick_safetyscanners2_front",
            output="screen",
            emulate_tty=True,
            parameters=[
                {"frame_id": "scan_front",
                 "sensor_ip": FRONT_IP,
                 "host_ip": "192.168.192.10",
                 "interface_ip": "0.0.0.0",
                 "host_udp_port": 6060,
                 "channel": CHANNEL,     # 가드가 검사하는 값과 동일해야 한다 (상단 상수)
                 "channel_enabled": True,
                 "skip": 0,
                 "angle_start": 0.0,
                 "angle_end": 0.0,
                 "time_offset": 0.0,
                 "general_system_state": True,
                 "derived_settings": True,
                 "measurement_data": True,
                 "intrusion_data": True,
                 "application_io_data": True,
                 "use_persistent_config": False,
                 "min_intensities": 0.0}
            ],
            remappings=[('/scan', '/scan_front')]
        ),
        Node(
            package="sick_safetyscanners2",
            executable="sick_safetyscanners2_node",
            name="sick_safetyscanners2_rear",
            output="screen",
            emulate_tty=True,
            parameters=[
                {"frame_id": "scan_rear",
                 "sensor_ip": REAR_IP,
                 "host_ip": "192.168.192.10",
                 "interface_ip": "0.0.0.0",
                 "host_udp_port": 6061,
                 "channel": CHANNEL,     # 가드가 검사하는 값과 동일해야 한다 (상단 상수)
                 "channel_enabled": True,
                 "skip": 0,
                 "angle_start": 0.0,
                 "angle_end": 0.0,
                 "time_offset": 0.0,
                 "general_system_state": True,
                 "derived_settings": True,
                 "measurement_data": True,
                 "intrusion_data": True,
                 "application_io_data": True,
                 "use_persistent_config": False,
                 "min_intensities": 0.0}
            ],
            remappings=[('/scan', '/scan_rear')]
        )
    ])