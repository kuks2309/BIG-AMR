from setuptools import find_packages, setup

package_name = 'mini_mes'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='T-Robotics',
    maintainer_email='habib.usa2014@gmail.com',
    description='Mini MES — job planning and tracking above the ACS',
    license='Proprietary',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'demo = mini_mes.demo:main',
        ],
    },
)
