import ctypes
import socket
import struct
from ctypes import POINTER, cast, c_ubyte, byref, sizeof, create_string_buffer
from typing import List
import copy
import cv2
import harvesters
import csv
from  pathlib import Path

from harvesters.core import Component2DImage
from harvesters.util.pfnc import Coord3D_C16

from .python.lib import apply_param, set_components
from .python.lib.utils import init_harvester, DEVICE_ACCESS_STATUS_READWRITE, setup_camera_object, FETCH_TIMEOUT

from BKVisionCamera.base.property import CameraSdkInterface, CameraInfo

harvester = init_harvester()


def select_devices(device_list, config):
    serials = config['cameras']['serial']
    device_ids = list()
    for idx, device in enumerate(device_list):
        acc_stat = device.access_status
        if acc_stat == DEVICE_ACCESS_STATUS_READWRITE and device.serial_number in serials:
            device_ids.append(idx)
    return device_ids


def setup_camera_objects(harvester, device_ids):
    cameras = list()
    for idx in device_ids:
        device = harvester.device_info_list[idx]
        cameras.append(setup_camera_object(harvester, idx))
    return cameras


def setup_camera_object_by_index(harvester, device_idx):
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


class SickSdk(CameraSdkInterface):

    def __init__(self, property_=None, camera_info: CameraInfo = None):
        super().__init__(property_, camera_info)
        self.camera = None

    def init(self):
        pass

    def release(self):
        print("release")
        self.camera['ia'].stop()
        self.camera['ia'].destroy()

    @staticmethod
    def createCamera(cameraInfo):
        device_idx = 0
        device = harvester.device_info_list[device_idx]
        ia = harvester.create(device_idx)
        ia.num_buffers = 10
        ia.stop()
        return {
            'name': f"{device.display_name}_{device.serial_number}",
            'ia': ia,
            'nm': ia.remote_device.node_map,
            'writer': None,  # init later after params config
            'frameCount': 0,
            'recordedCount': 0,
        }

    @staticmethod
    def getDeviceList() -> List[CameraInfo]:
        return [SickSdk._getCameraInfo_(device) for device in harvester.device_info_list]

    @staticmethod
    def _getCameraInfo_(camera_):
        camera_info = CameraInfo(camera_)
        camera_info.serial_number = camera_.serial_number
        camera_info.mac = camera_.serial_number
        camera_info.ip = "????"
        camera_info.model = camera_.model
        camera_info.vendor = camera_.vendor
        camera_info.access_status = camera_.access_status
        camera_info.device_id = camera_.display_name
        camera_info.sn=camera_.serial_number
        return camera_info

    def saveConfig(self, config):
        if self.property.configFile:
            pass

    def loadConfig(self, config):

        # 设置参数AcquisitionFrameRate为5
        # 设置参数ExposureTime为1
        # 设置参数GevSCPD为0
        # 设置参数ChunkModeActive为True
        apply_param(self.camera['nm'], "AcquisitionFrameRate", 5)
        apply_param(self.camera['nm'], "ExposureTime", 1)
        apply_param(self.camera['nm'], "GevSCPD", 0)
        apply_param(self.camera['nm'], "ChunkModeActive", True)
        set_components(self.camera['nm'], [ 'Intensity' ])
        return
        configFile = config
        if Path(configFile).exists():
            csv_reader = csv.reader(open(configFile, 'r', encoding='utf-8'))
            for row in csv_reader:
                if len(row) < 2:
                    continue
                name, val = row
                if "#" in name:
                    continue
                try:
                    apply_param(self.camera['nm'], name, val)
                except Exception as e:
                    print(f"Failed to set {name} to {val} ({e})")
            # if 'ComponentList' in config['gev_config']:
            #     set_components(self.camera['nm'], config['gev_config']['ComponentList'])
    def open(self):
        self.camera = self.createCamera(self.camera_info)
        # self.loadConfig(self.property.configFile)
        # self.setExposureTime(1)
        self.camera['ia'].start()

    def getFrame(self):
        with self.camera['ia'].fetch(timeout=FETCH_TIMEOUT) as buffer:
            buffer: harvesters.core.Buffer
            dataList = []
            # for index, component in enumerate(buffer.payload.components):
            #     data = component.data
            #     data = data.reshape((data.shape[0] // 2560), 2560)
            #     dataList.append(data)
            # return dataList
            yield buffer
            # for index, component in enumerate(buffer.payload.components):
            #     print(component.data_format)
            #     print(len(buffer.payload.components))
            #     data = component.data
            #     print(component)
            #     print(data)
            #     Coord3D_C16
            #     Component2DImage
            #     data = data.reshape((data.shape[0] // 2560), 2560)
            #     dataList.append(component)
            # yield dataList
                # cv2.namedWindow("frame" + str(index), cv2.WINDOW_NORMAL)
                # cv2.imshow("frame" + str(index), data)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     return
            # camera['frameCount'] += 1
    def setExposureTime(self, exposureTime):
        apply_param(self.camera['nm'], "ExposureTime", exposureTime)