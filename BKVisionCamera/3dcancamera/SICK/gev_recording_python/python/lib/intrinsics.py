# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

from dataclasses import dataclass
from logging import warning

@dataclass
class Intrinsics:
    scale_c: float
    offset_c: float
    princ_pt_u: float
    princ_pt_v: float
    foc_len: float
    aspect_r: float


def extract_intrinsics(frame):
    chunk = ['FocalLength', 'AspectRatio', 'PrincipalPointU', 'PrincipalPointV', 'CoordinateScaleC', 'CoordinateOffsetC']
    k = Intrinsics(1.0, 0.0, 516.90, 290.54, 216.31, 1.0)
    if not set(chunk).issubset(frame.keys()):
        warning("Using default parameters for camera intrinsics")
        return k
    
    k.scale_c = frame['CoordinateScaleC']
    k.offset_c = frame['CoordinateOffsetC']
    k.princ_pt_u = frame['PrincipalPointU']
    k.princ_pt_v = frame['PrincipalPointV']
    k.foc_len = frame['FocalLength']
    k.aspect_r = frame['AspectRatio']
    return k