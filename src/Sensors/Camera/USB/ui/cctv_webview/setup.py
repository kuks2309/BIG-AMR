from glob import glob

from setuptools import setup

package_name = "cctv_webview"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Ford_CATL_AMR",
    maintainer_email="kukwonko@gmail.com",
    description="압축 카메라 토픽(JPEG)을 디코드 없이 브라우저로 흘리는 CCTV 웹 뷰어",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "cctv_webview = cctv_webview.app:main",
        ],
    },
)
