#!/usr/bin/env python3
# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

"""Stream connected Visionary camera via ROS2 node"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter as rdhf
from harvesters import __version__ as harvesters_version
from logging import basicConfig, info, INFO, error
from sys import exit, version
from rclpy import init, spin, shutdown
from sick_visionary.sick_visionary.visionary_publisher import VisionaryBTwoPublisher


def main(args):
    if not version.startswith(('3.8.', '3.10.')):
        error(f"Python 3.8./3.10. is required. But this is: {version}")
        return 1
    elif not harvesters_version == '1.4.0':
        error(f"Harvesters 1.4.0 is required. But this is: {harvesters_version}")
        return 1

    init(args=None)
    with VisionaryBTwoPublisher(args.serial, args.fps) as camera:
        spin(camera)
    shutdown()
    return 0


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__, formatter_class=rdhf)
    parser.add_argument("-s", "--serial", help="Camera serial", type=int, default=22990047)
    parser.add_argument("-f", "--fps", help="Number of frames per second", type=int, default=20)
    log_fmt = "[%(levelname)s] [%(created).9f] [Visionary_B_Two]: %(message)s"
    basicConfig(format=log_fmt, level=INFO)
    exit(main(parser.parse_args()))
