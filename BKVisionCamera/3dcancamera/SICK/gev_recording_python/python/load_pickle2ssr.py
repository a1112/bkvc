#!/usr/bin/env python3
# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

"""Convert Python pickle files to SSR format"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter as rdhf
from lib import pickle_harvester as ph, ssr_helper as ssrh
from lib.intrinsics import extract_intrinsics
from logging import basicConfig, info, INFO, error
from struct import pack
from sys import exit
from os import getcwd, listdir, makedirs, remove
from os.path import basename, getsize, isdir, join
from PIL.Image import fromarray, new
from lib.utils import *
from zipfile import ZipFile, ZIP_DEFLATED

TWO_GB = 1 << 31
FOUR_GB = 1 << 32


def create_xml_values(k, width, height, num_frames):
    mapset = ssrh.distanceTemplate.format(
        MIN_DISTANCE=1, MAX_DISTANCE=15000,
        DTYPE_DISTANCE="uint16") + "\n" + ssrh.intensityTemplate.format(
        MIN_INTENISTY=1, MAX_INTENSITY=4294967295, DTYPE_INTENISTY="uint32")
    return {
        "FX": k.foc_len,
        "FY": k.foc_len * k.aspect_r,
        "CX": k.princ_pt_u,
        "CY": k.princ_pt_v,
        "K1": 0.0,
        "K2": 0.0,
        "P1": 0.0,
        "P2": 0.0,
        "K3": 0.0,
        "PixelSizeX": 1.0,
        "PixelSizeY": 1.0,
        "PixelSizeZ": 1.0,
        "MAPSET": mapset,
        "WIDTH": width,
        "HEIGHT": height,
        "NUM_FRAMES": num_frames
    }


def create_ssr_file(pickle_file, output_name, output_dir=getcwd()):
    reader = ph.Reader(pickle_file)
    num_frames = len(reader)
    info("Number of frames available: %d" % num_frames)
    data_bin_path = join(output_dir, "data.bin")

    with open(data_bin_path, "wb") as file:
        for frame_number, frame in enumerate(reader.get_all_frames(), 1):
            data_formats = [d['data_format'] for d in frame['maps']]
            if not set(['Coord3D_C16', 'BGR8']).issubset(data_formats):
                raise RuntimeError(
                    "Could not find Intensity + Range in the pickle file")

            coord3d_data = data_map(frame['maps'], 'Coord3D_C16')
            width, height = coord3d_data['width'], coord3d_data['height']
            # We assume intrinsics are equal for all frames
            if frame_number == 1:
                intrinsics = extract_intrinsics(frame)
            _, _, depth = extract_depth(coord3d_data)
            rgb = extract_color(data_map(frame['maps'], 'BGR8'))
            img_z = fromarray(depth)
            img_rgb = fromarray(rgb, mode="RGB")
            # 'L' 8-bit pixels, black and white
            alpha_channel = new('L', img_rgb.size, 255)
            img_rgb.putalpha(alpha_channel)
            # width * height * (2(Z-Map)+4(RGB Map)) + 16 (header) + 8 (footer)
            frame_size = width * height * 6 + 16 + 8

            file.write(pack("<I", frame_size))  # FrameLength
            file.write(b"\x8D\x5E\x67\x01\xC0\x09\xF2\x03")  # Timestamp
            file.write(b"\x02\x00")  # Version
            file.write(pack("<I", frame_number))  # Framenumber
            file.write(b"\x03")  # Dataquality
            file.write(b"\x01")  # device status
            file.write(img_z.tobytes())
            file.write(img_rgb.tobytes())
            file.write(b"\x00\x00\x00\x00")  # CRC
            file.write(pack("<I", frame_size))  # FrameLength2
    reader = None

    xml_values = create_xml_values(intrinsics, width, height, num_frames)
    xml = ssrh.baseXML.format(**xml_values)

    main_xml_path = join(output_dir, "main.xml")
    with open(main_xml_path, "w") as file:
        file.write(xml)

    # Pad file if data.bin or resulting ssr filesize is between 2GB and 4GB
    total_filesize = getsize(main_xml_path) + getsize(data_bin_path)
    if total_filesize >= TWO_GB and total_filesize < FOUR_GB:
        with open(join(output_dir, "data.bin"), "ab") as file:
            file.write(b'\0'*(FOUR_GB - total_filesize))

    # Set compresslevel to 0 to speed up execution or to 1 to get save ~50% of disc space
    with ZipFile(join(output_dir, output_name), 'w', compression=ZIP_DEFLATED, compresslevel=0) as myzip:
        myzip.write(main_xml_path, arcname="main.xml")
        myzip.write(data_bin_path, arcname="data/data.bin")

    # Cleanup
    remove(main_xml_path)
    remove(data_bin_path)


def main(args):
    if isdir(args.pickle_file):
        if args.output:
            error("Cannot use folder for pickle files with -o/--output")
            return 1
        for pfile in listdir(args.pickle_file):
            if pfile.endswith('.pickle'):
                output_dir = join(args.pickle_file)
                makedirs(output_dir, exist_ok=True)
                create_ssr_file(join(args.pickle_file, pfile),
                                pfile + ".ssr", output_dir)
    else:
        output_name = args.output if args.output else basename(
            args.pickle_file) + ".ssr"
        create_ssr_file(args.pickle_file, output_name)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__, formatter_class=rdhf)
    parser.add_argument('pickle_file', help='(pickle) input file or folder')
    parser.add_argument('-o', '--output', help='Output filename for SSR')
    basicConfig(format="%(levelname)s: %(message)s", level=INFO)
    exit(main(parser.parse_args()))
