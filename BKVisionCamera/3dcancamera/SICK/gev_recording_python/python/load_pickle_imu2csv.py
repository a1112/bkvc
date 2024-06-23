#!/usr/bin/env python3
# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

"""Covert IMU data which is stored in a pickle file to a csv table"""
from sys import exit
from os.path import join
from logging import basicConfig, info, DEBUG
from lib.pickle_harvester import Reader
from argparse import ArgumentParser, RawDescriptionHelpFormatter as rdhf
import csv
from lib.IMU import IMUParser


def main(args):
    with Reader(args.pickle) as reader:
        with open(args.output, newline='', mode="w") as csv_file:
            imu_writer = csv.writer(csv_file, delimiter=' ',
                                    quotechar='|', quoting=csv.QUOTE_MINIMAL)
            imu_writer.writerow(
                ["accX", "accY", "accZ", "angX", "angY", "angZ"])
            for frame in reader:
                for m in frame['maps']:
                    data_type = m['data_format']
                    if data_type == 'Mono8':
                        parser = IMUParser(m["data"].tobytes())
                        while True:
                            imu_data = parser.getNext()
                            if imu_data == None:
                                break
                            imu_writer.writerow([imu_data.acceleration[0], imu_data.acceleration[1], imu_data.acceleration[2],
                                                 imu_data.angular_velocity[0], imu_data.angular_velocity[1], imu_data.angular_velocity[2]])


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__, formatter_class=rdhf)
    parser.add_argument("-p", "--pickle", help="(pickle) input file", default=join('data',
                        '2023_01_25_SICK_Visionary_AP.pickle'))
    parser.add_argument(
        "-o", "--output", help="(CSV) output file", default='imudata.csv')
    basicConfig(format="%(levelname)s: %(message)s", level=DEBUG)
    exit(main(parser.parse_args()))
