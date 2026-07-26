from setuptools import setup

package_name = "seer_lidar_tf"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/seer_lidar_tf.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Big-AMR",
    maintainer_email="kukwonko@gmail.com",
    description="Read SEER SRC lidar install_info and publish base_footprint -> scan_* static TF.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "seer_lidar_tf_node = seer_lidar_tf.seer_lidar_tf_node:main",
        ],
    },
)
