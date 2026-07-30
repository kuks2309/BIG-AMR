from glob import glob

from setuptools import setup

package_name = "can_relay"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
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
        ],
    },
)
