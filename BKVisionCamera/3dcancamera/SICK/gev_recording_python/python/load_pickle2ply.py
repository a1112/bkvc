#!/usr/bin/env python3
# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

"""Convert Python pickle files to PLY format"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter as rdhf
from lib.IMU import IMUParser
from lib.intrinsics import extract_intrinsics
from lib.pickle_harvester import Reader
from logging import basicConfig, info, INFO
from multiprocessing import Pool, cpu_count
import numpy as np
from os import listdir
from os.path import isdir, join
from sys import exit
from pathlib import Path
from lib.utils import *


def write_ply(filename, points, colors):
    header = [
        'ply\n', 'format binary_little_endian 1.0\n',
        'element vertex %d\n' % np.prod(points.shape[:2]),
        *["property float %s\n" % c for c in "xyz"],
        *["property uchar %s\n" % c for c in ("red", "green", "blue")],
        'end_header\n']
    
    vtypes = np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('red', 'u1'), ('green', 'u1'), ('blue', 'u1')])
    vertices = np.empty(np.prod(points.shape[:2]), dtype=vtypes)
    vertices['x'], vertices['y'], vertices['z'] = points.reshape(-1, 3).T
    vertices['red'], vertices['green'], vertices['blue'] = colors.reshape(-1, 3).T

    with open(filename, 'wb') as f:
        info("Writing %s" % filename)
        f.write("".join(header).encode('utf-8'))
        vertices.tofile(f)


def generate_pointcloud(k, col, row, depth, trans_matrix=None):
    xp = (col - k.princ_pt_u) / k.foc_len
    yp = (row - k.princ_pt_v) / (k.foc_len * k.aspect_r)

    scaled_c = depth * k.scale_c + k.offset_c
    
    xc = xp * scaled_c
    yc = yp * scaled_c
    zc = scaled_c
    points = np.stack([xc, yc, zc], axis=-1)

    if trans_matrix is None:
        return points

    points_flat = points.reshape(-1, 3)
    points_hom = np.hstack((points_flat, np.ones((points_flat.shape[0], 1))))
    return np.dot(trans_matrix, points_hom.T).T[:, :3].reshape(points.shape)


def process_frame(frame, trans_matrix, outfile):
    data_formats = [d['data_format'] for d in frame['maps']]
    if not set(['Coord3D_C16', 'BGR8']).issubset(data_formats):
        raise RuntimeError("Could not find Intensity + Range in the pickle file")

    col, row, depth = extract_depth(data_map(frame['maps'], 'Coord3D_C16'))
    rgb = extract_color(data_map(frame['maps'], 'BGR8'))
    intrinsics = extract_intrinsics(frame)
    pointcloud = generate_pointcloud(intrinsics, col, row, depth, trans_matrix)

    write_ply(outfile, pointcloud, rgb)


def export(pickle_file, skip, convert, pose, outfile_ply):
    trans_matrix = pose.get_transform_matrix()
    with Reader(pickle_file) as reader:
        # info(f"Number of frames available: {len(reader)}")
        frames = reader.get_frames(skip, convert)
        with Pool(cpu_count()) as pool:
            pool.starmap(process_frame, [(frame, trans_matrix, outfile_ply % idx) for idx, frame in enumerate(frames)])


def main(args):
    pose = Pose()
    pose.set_orientation([args.rotation_x, args.rotation_y, args.rotation_z])
    pose.set_position([args.translation_x, args.translation_y, args.translation_z])
    pose.refresh()
    if isdir(args.pickle_file):
        for pickle_file in listdir(args.pickle_file):
            if pickle_file.lower().endswith(".pickle"):
                outfile_ply = join(args.pickle_file, Path(pickle_file).stem + "_%d.ply")
                export(join(args.pickle_file, pickle_file), args.skip, args.convert, pose, outfile_ply)
    else:
        outfile_ply = Path(args.pickle_file).stem + "_%d.ply"
        export(args.pickle_file, args.skip, args.convert, pose, outfile_ply)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__, formatter_class=rdhf)
    parser.add_argument("--pickle_file",default="2024-06-23_19-49-13_SICK AG Ranger3-40 (SICKGigEVisionTL_DEV_000677433d49)_22110085.pickle", help="(pickle) input file or folder")
    parser.add_argument("-s", "--skip", help="Number of frames to be skipped at beginning of file", default=0, type=int)
    parser.add_argument("-c", "--convert", help="Number of frames to be converted", default=0, type=int)

    parser.add_argument("-rx", "--rotation_x", help="Translation of the camera along the X-axis (in degrees)", type=float, default=0.0)
    parser.add_argument("-ry", "--rotation_y", help="Translation of the camera along the Y-axis (in degrees)", type=float, default=0.0)
    parser.add_argument("-rz", "--rotation_z", help="Translation of the camera along the Z-axis (in degrees)", type=float, default=0.0)
    parser.add_argument("-tx", "--translation_x", help="Rotation of the camera around the X-axis (in mm)", type=float, default=0.0)
    parser.add_argument("-ty", "--translation_y", help="Rotation of the camera around the Y-axis  (in mm)", type=float, default=0.0)
    parser.add_argument("-tz", "--translation_z", help="Rotation of the camera around the Z-axis  (in mm)", type=float, default=0.0)

    basicConfig(format="%(levelname)s: %(message)s", level=INFO)
    exit(main(parser.parse_args()))