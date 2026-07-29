from setuptools import setup

package_name = "dataset_collector"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/collect.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="kuks",
    maintainer_email="kukwonko@gmail.com",
    description="Orbbec 카메라 토픽에서 학습용 정지영상을 수집하는 노드",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "collector = dataset_collector.collector_node:main",
        ],
    },
)
