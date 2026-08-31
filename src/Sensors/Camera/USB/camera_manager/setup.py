from setuptools import find_packages, setup

package_name = "camera_manager"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="drko",
    maintainer_email="drko@knj-robotics.com",
    description="카메라 관리 모드 — 프레임 생존 감시·자동 복구·camctl CLI",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "manager_node = camera_manager.manager_node:main",
            "camctl = camera_manager.cli:main",
        ],
    },
)
