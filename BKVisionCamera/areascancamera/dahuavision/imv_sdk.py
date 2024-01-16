import ctypes
import socket
import struct
from ctypes import POINTER, cast, c_ubyte, byref, sizeof, create_string_buffer
from typing import List

import cv2
import numpy as np
from BKVisionCamera import BaseProperty
from BKVisionCamera.areascancamera.dahuavision.MVSDK.IMVApi import MvCamera
from BKVisionCamera.areascancamera.dahuavision.MVSDK.IMVDefines import IMV_DeviceList, IMV_EInterfaceType, IMV_OK

from BKVisionCamera.base.property import CameraSdkInterface, CameraInfo


class ImvSdk(CameraSdkInterface):

    @staticmethod
    def createCamera(cameraInfo):
        pass

    @staticmethod
    def getDeviceList() -> List[CameraInfo]:
        sdk_ = MvCamera()
        deviceList = IMV_DeviceList()
        nRet = sdk_.IMV_EnumDevices(deviceList,IMV_EInterfaceType.interfaceTypeAll)
        if nRet != IMV_OK :
            print("enum devices fail! ret[0x%x]" % nRet)
            return []
        cameraInfoList = []

        def toStr(data, count=32):
            buffer = create_string_buffer(32)

            # 将字节数组复制到字符串缓冲区
            ctypes.memmove(buffer, data, count)

            # 将字节数据转换为字符串
            string_data = buffer.value.decode('utf-8')
            return string_data

        def nto(addr):
            return socket.inet_ntoa(struct.pack('>L', addr))

        for i in range(deviceList.nDevNum):
            pDeviceInfo = deviceList.pDevInfo[i]
            cameraInfo = CameraInfo(pDeviceInfo)

            # ('nCameraType', c_int),
            # ('nCameraReserved', c_int * 5),
            # ('cameraKey', c_char * MAX_STRING_LENTH),
            # ('cameraName', c_char * MAX_STRING_LENTH),
            # ('serialNumber', c_char * MAX_STRING_LENTH),
            # ('vendorName', c_char * MAX_STRING_LENTH),
            # ('modelName', c_char * MAX_STRING_LENTH),
            # ('manufactureInfo', c_char * MAX_STRING_LENTH),
            # ('deviceVersion', c_char * MAX_STRING_LENTH),
            # ('cameraReserved', c_char * MAX_STRING_LENTH * 5),
            # ('DeviceSpecificInfo', DeviceSpecificInfo),
            # ('nInterfaceType', c_int),
            # ('nInterfaceReserved', c_int * 5),
            # ('interfaceName', c_char * MAX_STRING_LENTH),
            # ('interfaceReserved', c_char * MAX_STRING_LENTH * 5),
            # ('InterfaceInfo', InterfaceInfo),
            cameraInfo.nCameraType = nto(pDeviceInfo.nCameraType)
            cameraInfo.cameraKey = toStr(pDeviceInfo.cameraKey)
            cameraInfo.cameraName = toStr(pDeviceInfo.cameraName)
            cameraInfo.serialNumber = toStr(pDeviceInfo.serialNumber)
            cameraInfo.vendorName = toStr(pDeviceInfo.vendorName)
            cameraInfo.modelName = toStr(pDeviceInfo.modelName)
            cameraInfo.deviceVersion = toStr(pDeviceInfo.deviceVersion)
            cameraInfo.nInterfaceType = nto(pDeviceInfo.nInterfaceType)
            cameraInfo.interfaceName = toStr(pDeviceInfo.interfaceName)

            cameraInfoList.append(cameraInfo)

    def __init__(self, property_: BaseProperty = None, camera_info: CameraInfo = None):
        super().__init__(property_, camera_info)
        self.sdk = MvCamera()

    def init(self):
        pass

    def release(self):
        pass

    def saveConfig(self, config):
        pass

    def loadConfig(self, config):
        pass


if __name__ == '__main__':
    sdk = ImvSdk()
    print(sdk.camera_info_list)
    print(sdk.camera_info)
    sdk.init()
    sdk.release()