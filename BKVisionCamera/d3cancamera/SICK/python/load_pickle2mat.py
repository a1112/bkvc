#!/usr/bin/env python3
# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

"""Convert Python pickle files to Matlab matrices"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter as rdhf
from lib.pickle_harvester import Reader
from os.path import join
from logging import basicConfig, info, INFO
from scipy.io import savemat
from sys import exit

def main(args):
    with Reader(args.pickle) as reader:
       info(f"Number of frames: {len(reader)}")
       frames = {f'frame_{idx:03}': frame for idx, frame in enumerate(reader)}
       savemat(args.output, frames, appendmat=True, do_compression=True)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__, formatter_class=rdhf)
    parser.add_argument("-p", "--pickle", help="(pickle) input file", default=join('data', '2023_01_25_SICK_Visionary_AP.pickle'))
    parser.add_argument("-o", "--output", help="(Matlab) output file", default='testRecord.mat')
    basicConfig(format="%(levelname)s: %(message)s", level=INFO)
    exit(main(parser.parse_args()))
