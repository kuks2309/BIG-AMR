from setuptools import setup

package_name = "yolo_detector"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/detect.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="kuks",
    maintainer_email="kukwonko@gmail.com",
    description="YOLOv8 객체탐지 노드 (카메라 토픽 구독)",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "detector = yolo_detector.detector_node:main",
            "verify_live = yolo_detector.verify_live:main",
        ],
    },
)
