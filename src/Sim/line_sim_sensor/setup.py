from setuptools import setup

package_name = "line_sim_sensor"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", ["config/line_sim_params.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="kuks",
    maintainer_email="kukwonko@gmail.com",
    description="SIL 가상 라인 센서 — 맵 라인 + 자세 → /line/error",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "line_sim_sensor_node = line_sim_sensor.sensor_node:main",
        ],
    },
)
