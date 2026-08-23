from glob import glob

from setuptools import setup

package_name = "telegram_notifier"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        # 유닛은 glob 으로 싣는다. 파일명을 열거하면 새 유닛이 조용히 빠진다.
        ("share/" + package_name + "/systemd", glob("systemd/*.service")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="kuks",
    maintainer_email="kukwonko@gmail.com",
    description="can_relay /diagnostics 경보를 텔레그램으로 전송하는 감시 노드",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "telegram_notifier = telegram_notifier.notifier_node:main",
        ],
    },
)
