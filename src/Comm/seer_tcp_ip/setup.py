from setuptools import setup

package_name = "seer_tcp_ip"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="kuks2309",
    maintainer_email="gabekim883@gmail.com",
    description="Seer(SRC) Robokit TCP/IP API 클라이언트 (전송·포트정책·편호 바인딩)",
    license="Proprietary",
    tests_require=["pytest"],
    # 노드 없음 — 라이브러리 전용 패키지. broker 노드는 다음 단계(ADR 2026-08-07 §Decision 3).
    entry_points={"console_scripts": []},
)
