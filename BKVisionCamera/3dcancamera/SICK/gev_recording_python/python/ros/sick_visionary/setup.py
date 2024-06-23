# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

from os.path import join
from glob import glob
from setuptools import setup, find_packages

package_name = 'sick_visionary'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(),
    install_requires=['setuptools', 'numpy', 'opencv-python'],
    zip_safe=True,
    maintainer='xsowolk',
    maintainer_email='kai.wolf@extern.sick.de',
    description='SICK Visionary-B Two ROS node',
    license='Unlicense',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'sick_visionary = sick_visionary.visionary_publisher:main'
        ]
    }
)