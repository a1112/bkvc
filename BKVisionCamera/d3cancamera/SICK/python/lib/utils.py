# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

import cv2
import harvesters
from PIL import Image
if list(map(int, cv2.__version__.split('.')))[0] > 3:
    from cv2 import cvtColor, COLOR_BAYER_RG2RGB_EA as BayerPattern
else:
    from cv2 import cvtColor, COLOR_BayerRGGB2BGR_EA as BayerPattern
import numpy as np
from toml import loads
from harvesters.core import Harvester
from .gev_helper import apply_param, set_components
from os import path
import platform
from time import time
from logging import info, error

DEVICE_ACCESS_STATUS_READWRITE = 1 # GenICam/GenTL dfinition
FETCH_TIMEOUT = 3.0                # relaxed, better stability for bad network bandwidth


def data_map(maps, data_format):
    return next(filter(lambda x: x['data_format'] == data_format, maps))


def extract_depth(coord3d_data):
    width = coord3d_data['width']
    height = coord3d_data['height']
    col, row = np.meshgrid(np.arange(width), np.arange(height))
    depth = coord3d_data['data'].reshape(height, width)
    return col, row, depth


def extract_color(bgr8_data):
    width = bgr8_data['width']
    height = bgr8_data['height']
    bgr = bgr8_data['data'].reshape(height, width, 3)
    return bgr[..., ::-1].copy()


def extract_bayer(bayer_data):
    width = bayer_data['width']
    height = bayer_data['height']
    bayer = bayer_data['data'].reshape(height, width)
    return cvtColor(bayer, BayerPattern)


def parse_config(config_file):
    with open(config_file, 'rb') as infile:
        file_bytes = infile.read()
        config = loads(file_bytes.decode('utf-8'))
        return config


def get_cti_path():
    """Helper to get cti file path corresponding with the platform the script is running on """
    # The directory with this script (python/lib) is located next to a parallel directory (common/lib) 
    # with support files shared among languages. That common location among others contains 
    # a "cti" subdirectory further containing one subdirectory for each platform supported by the 
    # SICK GenTL Producer for GigE Vision.
    # The actual filename of the GenTL Producer binary is always the same (SICKGigEVisionTL.cti).
    cti_platform_dir_name = get_cti_dir_name()
    script_dir = path.dirname(path.realpath(__file__))
    package_root = path.dirname(path.dirname(script_dir))
    CTI_FILENAME = "SICKGigEVisionTL.cti"
    return path.join(package_root, "common", "lib", "cti", cti_platform_dir_name, CTI_FILENAME)


def get_cti_dir_name():
    """Helper to get cti file directory name corresponding with the platform the script is running on"""
    if platform.system() == "Windows":
        return "windows_x64"
    if platform.system() == "Linux" and platform.machine() == "x86_64":
        return "linux_x64"
    if platform.system() == "Linux" and platform.machine() == "aarch64":
        return "linux_aarch64"

    # Not one of our recognized platforms, cti file not available
    raise RuntimeError("GenTL Producer not available on this platform")


def init_harvester():
    try:
        h = Harvester()
        cti = get_cti_path()
        h.add_file(cti, check_existence=True, check_validity=True)
        info("CTI driver loaded...")
        h.update()
        info(f"Device discovery done, received {len(h.device_info_list)} answers")
        return h
    except Exception as err:
        error(f"No devices found: {err}")
        exit(1)


def setup_camera_object(harvester, device_idx):
    ia = harvester.create(device_idx)
    ia.num_buffers = 10
    ia.stop()
    device = harvester.device_info_list[device_idx]
    camera = {
        'name': f"{device.display_name}_{device.serial_number}",
        'ia': ia,
        'nm': ia.remote_device.node_map,
        'writer': None,  # init later after params config
        'frameCount': 0,
        'recordedCount': 0,
    }
    return camera


def select_device(device_list, config):
    for idx, device in enumerate(device_list):
        acc_stat = device.access_status
        if device.serial_number == config['cameras']['serial'][0]:
            if acc_stat == DEVICE_ACCESS_STATUS_READWRITE:
                info(f"Found camera: {device.display_name} ({device.serial_number})")
                return idx
    return None


def config_camera(camera, config):
    for name, val in config['gev_params'].items():
        apply_param(camera['nm'], name, val)
    print(camera['nm'])
    if 'ComponentList' in config['gev_config']:
        set_components(camera['nm'], config['gev_config']['ComponentList'])
    info(f"Applied configuration for camera: {camera['name']}")


def doFetch(camera, config):
    with camera['ia'].fetch(timeout=FETCH_TIMEOUT) as buffer:
      buffer:harvesters.core.Buffer

      for index,component in enumerate(buffer.payload.components):
        print(component.data_format)
        print(len(buffer.payload.components))
        data = component.data
        print(component)
        print(data)
        data = data.reshape((data.shape[0]//2560),2560)
        cv2.namedWindow("frame"+str(index), cv2.WINDOW_NORMAL)
        cv2.imshow("frame"+str(index), data)
      if cv2.waitKey(1) & 0xFF == ord('q'):
        return
      camera['frameCount'] += 1
      if camera['frameCount'] % config['cameras']['recordingRate'] == 0:
          camera['recordedCount'] += 1
          camera['writer'].store(buffer, camera['nm'])




def maybe_capture_secs(cameras, config, t_start, duration):
    if not duration:
        return

    if len(cameras) == 1:
      info(f"Capture frames for {duration} seconds")
      cam = cameras[0]
      cam['ia'].start()
      while time() < (t_start + duration):
        doFetch(cam, config)
      cam['ia'].stop()
    else:
      # cameras list==0 handled outside/before this function
      info(f"Capture frames (round-robin for multiple cameras) for {duration} seconds")
      while time() < (t_start + duration):
          for cam in cameras:
              cam['ia'].start()
              doFetch(cam, config)
              cam['ia'].stop()


def maybe_capture_num_frames(cameras, config, num_frames):
    if not num_frames:
        return
    if len(cameras) == 1:
      info(f"Capture {num_frames} frames")
      cam = cameras[0]
      cam['ia'].start()

      while cam['recordedCount'] < num_frames:
        print(cam['recordedCount'])
        print(num_frames)
        doFetch(cam, config)
      cam['ia'].stop()

    else:
      # cameras list==0 handled outside/before this function
      while cameras[0]['recordedCount'] < num_frames:
          for cam in cameras:
              cam['ia'].start()
              doFetch(cam, config)
              cam['ia'].stop()


def maybe_capture_auto_bracket(cameras, auto_bracket):
    if not auto_bracket:
        return
    info(f"Capture frames for: {auto_bracket.start}..{auto_bracket.stop-1} with steps of {auto_bracket.step} us")
    for exp_time in auto_bracket:
        for cam in cameras:
            apply_param(cam['nm'], 'ExposureTime', exp_time)
            cam['ia'].start()
            with cam['ia'].fetch(timeout=FETCH_TIMEOUT) as buffer:
                cam['frameCount'] += 1
                cam['recordedCount'] += 1
                cam['writer'].store(buffer, cam['nm'])
            cam['ia'].stop()


class Pose:
    """
    Pose configuration
    Contains the camera-to-world matrix and both rotation and position vectors;
    the Pose class ensures that the camera-to-world matrix is always calculated
    from rotation and position vectors in the correct way (Euler XZY), suitable
    to be used with data from Visionary cameras
    """
    def __init__(self):
        """ X/Y/Z translation for camera 2 world transformation"""
        self.position = np.zeros(3, dtype=np.float64)
        """ a/b/c rotation [deg] for camera 2 world transformation"""
        self.orientation = np.zeros(3, dtype=np.float64)
        self.transform_matrix = np.identity(4, dtype=np.float64)

    def get_position(self):
        """returns the current position as offset for X, Y, Z axis"""
        return self.position

    def set_position(self, new_position):
        """set the position as offset for X, Y, Z axis"""
        self.position = np.array(new_position, dtype=np.float64)

    def get_orientation(self):
        """returns the current orientation as rotation around X, Y, Z axis in degrees"""
        return self.orientation

    def set_orientation(self, new_orientation):
        """set position as rotation around X, Y, Z axis in degrees"""
        self.orientation = np.array(new_orientation, dtype=np.float64)

    def get_transform_matrix(self):
        """returns the current transform3d matrix"""
        return self.transform_matrix

    def refresh(self):
        """recalculate the transform3d matrix with the current position and orientation"""
        a, b, c = np.deg2rad(self.orientation)
        m_rot = self._create_from_euler_xyz(a, b, c)
        m_trans = np.hstack((m_rot, self.get_position().reshape(3, 1)))
        m_trans = np.vstack((m_trans, [0, 0, 0, 1]))
        self.transform_matrix = m_trans

    def __init_cs(self, angle):
        """returns sin, cos for a given angle in radians"""
        s = np.sin(angle)
        c = np.cos(angle)
        return s, c

    def _create_rot_3dx(self, angle):
        """creates 3D rotation matrix around x axis"""
        s, c = self.__init_cs(angle)
        m = np.array(
            [[1, 0, 0],
             [0, c, -s],
             [0, s, c]], dtype=np.float64)
        return m

    def _create_rot_3dy(self, angle):
        """creates 3D rotation matrix around y axis"""
        s, c = self.__init_cs(angle)
        m = np.array(
            [[c, 0, s],
             [0, 1, 0],
             [-s, 0, c]], dtype=np.float64)
        return m

    def _create_rot_3dz(self, angle):
        """creates 3D rotation matrix around y axis"""
        s, c = self.__init_cs(angle)
        m = np.array(
            [[c, -s, 0],
             [s, c, 0],
             [0, 0, 1]], dtype=np.float64)
        return m

    def _create_from_euler_xyz(self, x_angle_deg, y_angle_deg, z_angle_deg):
        """creates 3D rotation matrix for angles around the axis X, Y, Z"""
        m_rot_x = self._create_rot_3dx(x_angle_deg)
        m_rot_y = self._create_rot_3dy(y_angle_deg)
        m_rot_z = self._create_rot_3dz(z_angle_deg)
        return m_rot_x @ m_rot_y @ m_rot_z
