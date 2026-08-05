from setuptools import find_packages, setup

package_name = 'csm'

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
    description='CSM — job planning and tracking above the ACS',
    license='Proprietary',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # The sequential driver — one thread, injected clock, everything
            # in order. The reference for what the system should do.
            'demo = csm.demo:main',
            # The same factory under the Supervisor, on real timers.
            'supervised_demo = csm.supervised_demo:main',
            'sim_node = csm.sim_node:main',
            'seer_client = csm.seer_client:main',
            'skeleton = csm.runtime.demo_skeleton:main',
        ],
    },
)
