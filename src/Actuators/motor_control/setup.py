from glob import glob

from setuptools import setup

package_name = "motor_control"

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
    maintainer="amap",
    maintainer_email="kukwonko@gmail.com",
    description="Tongyi 4-axis AMR CAN motor driver (SDO polling master, module-set abstraction)",
    license="Proprietary",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "motor_control_node = motor_control.driver_node:main",
        ],
    },
)
