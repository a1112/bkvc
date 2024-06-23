#!/usr/bin/env python3
# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

"""Shows image and IMU data"""
from sys import exit
from os.path import join
from matplotlib import pyplot as plt
from lib.pickle_harvester import Reader
from lib.IMU import IMUParser
from lib.Player import Player
from argparse import ArgumentParser, RawDescriptionHelpFormatter as rdhf
from lib.utils import data_map, extract_color, extract_depth


class ReaderWrapper():
    def __init__(self, reader):
        self.reader = reader
        self.pos = 0
        self.length = self.reader._get_number_of_frames()
        self.frame = self._parseFrame(self.reader.get_next_frame())

    def _parseFrame(self, frame):
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
                _, _, depth = extract_depth(data_map(frame['maps'], data_type))
                frame_object["depth"] = depth
            elif data_type == 'BGR8':
                rgb = extract_color(data_map(frame['maps'], data_type))
                frame_object["rgb"] = rgb
        return frame_object

    def __getitem__(self, key):
        if key > self.length:
            return None
        if key == self.pos:
            return self.frame
        data = None
        if key < self.pos:
            self.reader._rewind_to_start_of_frames()
            data = self.reader.get_next_frame()
            self.pos = 0
        while self.pos < key:
            data = self.reader.get_next_frame()
            self.pos += 1
        self.frame = self._parseFrame(data)
        return self.frame

    def __len__(self):
        return self.length


def main(args):
    max_acc = -1000
    min_acc = 1000
    max_ang = -1000
    min_ang = 1000
    with Reader(args.pickle) as reader:
        for frame in reader:
            for m in frame['maps']:
                data_type = m['data_format']
                if data_type == 'Mono8':
                    parser = IMUParser(m["data"].tobytes())
                    while True:
                        imu_data = parser.getNext()
                        if imu_data == None:
                            break
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

        pa = Player(min_acc, max_acc, min_ang, max_ang, ReaderWrapper(reader))
        plt.show()

if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__, formatter_class=rdhf)
    parser.add_argument("-p", "--pickle", help="(pickle) input file", default=join('data',
                        '2023_01_25_SICK_Visionary_AP.pickle'))
    #basicConfig(format="%(levelname)s: %(message)s", level=DEBUG)
    exit(main(parser.parse_args()))
