#!/usr/bin/env python3
# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

"""Shows image and IMU data (parses all data at startup)"""
from sys import exit
from os.path import join
from matplotlib import pyplot as plt
from lib.utils import data_map, extract_color, extract_depth
from lib.pickle_harvester import Reader
from argparse import ArgumentParser, RawDescriptionHelpFormatter as rdhf
from lib.IMU import IMUParser
from lib.Player import Player


def main(args):
    frame_list = []
    max_acc = -1000
    min_acc = 1000
    max_ang = -1000
    min_ang = 1000
    with Reader(args.pickle) as reader:
        for i, frame in enumerate(reader):
            frame_object = {}
            for m in frame['maps']:
                data_type = m['data_format']
                if data_type == 'Mono8':
                    parser = IMUParser(m["data"].tobytes())
                    acc_x = []
                    acc_y = []
                    acc_z = []
                    ang_x = []
                    ang_y = []
                    ang_z = []
                    while True:
                        imu_data = parser.getNext()
                        if imu_data == None:
                            break
                        acc_x.append(imu_data.acceleration[0])
                        acc_y.append(imu_data.acceleration[1])
                        acc_z.append(imu_data.acceleration[2])
                        for j in range(3):
                            if imu_data.acceleration[j] > max_acc:
                                max_acc = imu_data.acceleration[j]
                            if imu_data.acceleration[j] < min_acc:
                                min_acc = imu_data.acceleration[j]

                        for j in range(3):
                            if imu_data.angular_velocity[j] > max_ang:
                                max_ang = imu_data.angular_velocity[j]
                            if imu_data.angular_velocity[j] < min_ang:
                                min_ang = imu_data.angular_velocity[j]

                        ang_x.append(imu_data.angular_velocity[0])
                        ang_y.append(imu_data.angular_velocity[1])
                        ang_z.append(imu_data.angular_velocity[2])

                    frame_object["acc_x"] = acc_x
                    frame_object["acc_y"] = acc_y
                    frame_object["acc_z"] = acc_z
                    frame_object["ang_x"] = ang_x
                    frame_object["ang_y"] = ang_y
                    frame_object["ang_z"] = ang_z
                if data_type == 'Coord3D_C16':
                    _, _, depth = extract_depth(
                        data_map(frame['maps'], data_type))
                    frame_object["depth"] = depth
                elif data_type == 'BGR8':
                    rgb = extract_color(data_map(frame['maps'], data_type))
                    frame_object["rgb"] = rgb
            frame_list.append(frame_object)
    pa = Player(min_acc, max_acc, min_ang, max_ang, frame_list)
    plt.show()


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__, formatter_class=rdhf)
    parser.add_argument("-p", "--pickle", help="(pickle) input file", default=join('data',
                        '2023_01_25_SICK_Visionary_AP.pickle'))
    exit(main(parser.parse_args()))
