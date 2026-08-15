from glob import glob

from setuptools import setup

package_name = "can_relay"

setup(
    name=package_name,
    version="0.1.0",
    # UI 는 독립 패키지를 만들지 않고 대상 패키지 아래 `ui/` 로 둔다
    # (저장소 규약 — README §디렉토리 배치, ADR 2026-08-03-amr-test-gui-ros2-port).
    packages=[package_name, package_name + ".ui"],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
        # 장비별 캘리브레이션 — 기체마다 한 장. 설치 안 하면 launch 가 못 찾는다.
        ("share/" + package_name + "/config/machine", glob("config/machine/*.yaml")),
        # systemd 유닛 템플릿. install_service.sh 는 소스 트리에서 읽지만, 설치본에도
        # 두어야 배포된 워크스페이스만 가진 장비에서 유닛 내용을 확인할 수 있다.
        ("share/" + package_name + "/systemd", glob("systemd/*.service")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="kuks2309",
    maintainer_email="gabekim883@gmail.com",
    description="판다 CAN 릴레이 경유 Tongyi 4축 모터 구동 ROS2 드라이버",
    license="Proprietary",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "can_relay_node = can_relay.driver_node:main",
            "home_and_zero = can_relay.home_and_zero:main",
            "can_relay_gui = can_relay.ui.gui_node:main",
            "relay_supervisor = can_relay.supervisor:main",
        ],
    },
)
