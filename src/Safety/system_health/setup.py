from setuptools import setup

package_name = "system_health"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (
            "share/" + package_name + "/systemd",
            ["systemd/amr-health-sampler.service"],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="kuks",
    maintainer_email="kukwonko@gmail.com",
    description="AMR 본체 PC 자원 감시 샘플러 (관측 전용, Phase 1 은 ROS 무의존)",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "health_sampler = system_health.sampler:main",
        ],
    },
)
