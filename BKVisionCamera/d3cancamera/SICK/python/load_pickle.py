#!/usr/bin/env python3
# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

"""Print debug output of frames and show image data"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter as rdhf
from lib.pickle_harvester import Reader
from lib.utils import data_map, extract_bayer, extract_color, extract_depth
from matplotlib import pyplot as plt
from logging import basicConfig, info, DEBUG, WARNING, INFO
from os.path import join
from sys import exit


def display(title, img):
    plt.figure()
    plt.title(title)
    plt.imshow(img)
    plt.waitforbuttonpress()


def main(args):
    with Reader(args.pickle) as reader:
        # info(f"Number of frames: {len(reader)}")
        for frame in reader:
            # reader.debug_frame(frame)
            for m in frame['maps']:
                dtype = m['data_format']
                print(dtype)
                if dtype == 'Coord3D_C16':
                    _, _, depth = extract_depth(data_map(frame['maps'], dtype))
                    display('Range/Depth/Z', depth)
                elif dtype == 'BGR8':
                    rgb = extract_color(data_map(frame['maps'], dtype))
                    display('Intensity/Color', rgb)
                elif dtype == 'BayerRG10':
                    rgb = extract_bayer(data_map(frame['maps'], dtype))
                    display('Raw Left/Right (color, demosaiced)', rgb)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__, formatter_class=rdhf)
    parser.add_argument("-p", "--pickle", help="(pickle) input file", default= "2024-06-23_19-35-34_SICK AG Ranger3-40 (SICKGigEVisionTL_DEV_000677433d49)_22110085.pickle")
    basicConfig(format="%(levelname)s: %(message)s", level=INFO)
    exit(main(parser.parse_args()))

