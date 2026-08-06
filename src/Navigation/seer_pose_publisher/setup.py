from glob import glob

from setuptools import setup

package_name = "seer_pose_publisher"

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
    maintainer_email="drko@knj-robotics.com",
    description="Seer 상태 API 1004 → /robot_pose (읽기 전용)",
    license="Proprietary",
    entry_points={
        "console_scripts": [
            "seer_pose_publisher_node = seer_pose_publisher.pose_node:main",
        ],
    },
)
