import ctypes
import socket
import struct
from ctypes import POINTER, cast, c_ubyte, byref, sizeof, create_string_buffer
from typing import List

import cv2
import numpy as np

from BKVisionCamera.areascancamera.hikvision.MvImport.CameraParams_const import MV_GIGE_DEVICE, MV_USB_DEVICE, \
    MV_ACCESS_Exclusive, MV_CAMERALINK_DEVICE
from BKVisionCamera.areascancamera.hikvision.MvImport.CameraParams_header import MV_CC_DEVICE_INFO_LIST, \
    MV_CC_DEVICE_INFO, MV_TRIGGER_MODE_OFF, MV_FRAME_OUT_INFO_EX, MVCC_ENUMVALUE, MVCC_INTVALUE, MV_GIGE_DEVICE_INFO
from BKVisionCamera.areascancamera.hikvision.MvImport.MvCameraControl_class import MvCamera
from BKVisionCamera.base.property import CameraInfo, CameraSdkInterface, BaseProperty


class MvSdk(CameraSdkInterface):

    def __init__(self, property_: BaseProperty = None, camera_info: CameraInfo = None):
        super().__init__(property_, camera_info)
        self.cam = MvCamera()

    def saveConfig(self, config):
        pass

    def loadConfig(self, config):
        pass

    @staticmethod
    def _getCameraInfo_(camera_):

        stDevList = MV_CC_DEVICE_INFO_LIST()
        ret = camera_.MV_CC_EnumDevices(MV_GIGE_DEVICE | MV_USB_DEVICE | MV_CAMERALINK_DEVICE | MV_CAMERALINK_DEVICE
                                        , stDevList)
        if ret != 0:
            raise Exception("枚举设备失败")
        res = []
        for i in range(0, stDevList.nDeviceNum):
            camera_info = MvSdk.createCamera(stDevList.pDeviceInfo[i])
            res.append(camera_info)
        return res

    @staticmethod
    def createCamera(stDeviceInfo):
        stDeviceInfo = cast(stDeviceInfo, POINTER(MV_CC_DEVICE_INFO)).contents
        camera_info = CameraInfo(stDeviceInfo)
        camera_info.majorVer = stDeviceInfo.nMajorVer
        camera_info.minorVer = stDeviceInfo.nMinorVer
        mac_high = stDeviceInfo.nMacAddrHigh
        mac_low = stDeviceInfo.nMacAddrLow
        mac_address = f"{mac_high:08X}{mac_low:08X}"
        macAddress = ':'.join(mac_address[i:i + 2] for i in range(0, len(mac_address), 2))
        camera_info.macAddress = macAddress

        def toStr(data, count=32):
            buffer = create_string_buffer(32)

            # 将字节数组复制到字符串缓冲区
            ctypes.memmove(buffer, data, count)

            # 将字节数据转换为字符串
            string_data = buffer.value.decode('utf-8')
            return string_data

        def nto(addr):
            return socket.inet_ntoa(struct.pack('>L', addr))

        # stDeviceInfo.SpecialInfo.stGigEInfo: MV_GIGE_DEVICE_INFO
        camera_info.ipCfgOption = nto(stDeviceInfo.SpecialInfo.stGigEInfo.nIpCfgOption)
        camera_info.ipCfgCurrent = nto(stDeviceInfo.SpecialInfo.stGigEInfo.nIpCfgCurrent)
        camera_info.ip = nto(stDeviceInfo.SpecialInfo.stGigEInfo.nCurrentIp)
        camera_info.subNetMask = nto(stDeviceInfo.SpecialInfo.stGigEInfo.nCurrentSubNetMask)
        camera_info.defultGateWay = nto(stDeviceInfo.SpecialInfo.stGigEInfo.nDefultGateWay)
        camera_info.manufacturerName = toStr(stDeviceInfo.SpecialInfo.stGigEInfo.chManufacturerName)
        camera_info.modelName = toStr(stDeviceInfo.SpecialInfo.stGigEInfo.chModelName)
        camera_info.deviceVersion = toStr(stDeviceInfo.SpecialInfo.stGigEInfo.chDeviceVersion)
        camera_info.manufacturerSpecificInfo = toStr(stDeviceInfo.SpecialInfo.stGigEInfo.chManufacturerSpecificInfo)
        camera_info.serialNumber = toStr(stDeviceInfo.SpecialInfo.stGigEInfo.chSerialNumber)
        camera_info.userDefinedName = toStr(stDeviceInfo.SpecialInfo.stGigEInfo.chUserDefinedName)
        camera_info.netExport = nto(stDeviceInfo.SpecialInfo.stGigEInfo.nNetExport)
        return camera_info

    @staticmethod
    def getDeviceList() -> List[CameraInfo]:
        cam_ = MvCamera()
        return MvSdk._getCameraInfo_(cam_)

    def _enumDevices_(self):
        # 创建相机实例
        stDevList = MV_CC_DEVICE_INFO_LIST()
        ret = self.cam.MV_CC_EnumDevices(MV_GIGE_DEVICE | MV_USB_DEVICE | MV_CAMERALINK_DEVICE | MV_CAMERALINK_DEVICE
                                         , stDevList)
        return stDevList, ret

    def init(self):
        stDevList, ret = self._enumDevices_()
        index = -1
        for i in range(stDevList.nDeviceNum):
            if self.camera_info == MvSdk.createCamera(stDevList.pDeviceInfo[i]):
                index = i
                break
        print(index)
        stDevInfo = cast(stDevList.pDeviceInfo[index], POINTER(MV_CC_DEVICE_INFO)).contents
        # 选择第一台相机并创建句柄
        ret = self.cam.MV_CC_CreateHandle(stDevInfo)
        if ret != 0:
            raise Exception("创建句柄失败")
        return ret

    def open(self):
        # 打开设备
        self._open()
        self.startGrabbing()

    def _open(self):
        # 打开设备
        ret = self.cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
        if ret != 0:
            print(ret)
            raise Exception("打开设备失败")
        self.triggerMode = MV_TRIGGER_MODE_OFF
        # 开始取流

    @property
    def triggerMode(self):
        stEnumValue = MVCC_ENUMVALUE()
        ret = self.cam.MV_CC_GetEnumValue("TriggerMode", stEnumValue)
        if ret != 0:
            raise Exception("获取触发模式失败")
        return stEnumValue.nCurValue

    @triggerMode.setter
    def triggerMode(self, value=MV_TRIGGER_MODE_OFF):
        self.cam.MV_CC_SetEnumValue("TriggerMode", value)

    @property
    def exposureTime(self):
        stParam = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("ExposureTime", stParam)
        if ret != 0:
            raise Exception("获取曝光时间失败")
        return stParam.nCurValue

    @exposureTime.setter
    def exposureTime(self, value):
        self.cam.MV_CC_SetIntValue("ExposureTime", value)

    @property
    def gain(self):
        stParam = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("Gain", stParam)
        if ret != 0:
            raise Exception("获取增益失败")
        return stParam.nCurValue

    @gain.setter
    def gain(self, value):
        self.cam.MV_CC_SetIntValue("Gain", value)

    @property
    def gamma(self):
        stParam = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("Gamma", stParam)
        if ret != 0:
            raise Exception("获取Gamma失败")
        return stParam.nCurValue

    @gamma.setter
    def gamma(self, value):
        self.cam.MV_CC_SetIntValue("Gamma", value)

    @property
    def balanceRatioRed(self):
        stParam = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("BalanceRatioRed", stParam)
        if ret != 0:
            raise Exception("获取BalanceRatioRed失败")
        return stParam.nCurValue

    @balanceRatioRed.setter
    def balanceRatioRed(self, value):
        self.cam.MV_CC_SetIntValue("BalanceRatioRed", value)

    @property
    def balanceRatioGreen(self):
        stParam = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("BalanceRatioGreen", stParam)
        if ret != 0:
            raise Exception("获取BalanceRatioGreen失败")
        return stParam.nCurValue

    @balanceRatioGreen.setter
    def balanceRatioGreen(self, value):
        self.cam.MV_CC_SetIntValue("BalanceRatioGreen", value)

    @property
    def balanceRatioBlue(self):
        stParam = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("BalanceRatioBlue", stParam)
        if ret != 0:
            raise Exception("获取BalanceRatioBlue失败")
        return stParam.nCurValue

    @balanceRatioBlue.setter
    def balanceRatioBlue(self, value):
        self.cam.MV_CC_SetIntValue("BalanceRatioBlue", value)

    @property
    def balanceWhiteAuto(self):
        stEnumValue = MVCC_ENUMVALUE()
        ret = self.cam.MV_CC_GetEnumValue("BalanceWhiteAuto", stEnumValue)
        if ret != 0:
            raise Exception("获取BalanceWhiteAuto失败")
        return stEnumValue.nCurValue

    @balanceWhiteAuto.setter
    def balanceWhiteAuto(self, value):
        self.cam.MV_CC_SetEnumValue("BalanceWhiteAuto", value)

    @property
    def balanceRatioSelector(self):
        stEnumValue = MVCC_ENUMVALUE()
        ret = self.cam.MV_CC_GetEnumValue("BalanceRatioSelector", stEnumValue)
        if ret != 0:
            raise Exception("获取BalanceRatioSelector失败")
        return stEnumValue.nCurValue

    @balanceRatioSelector.setter
    def balanceRatioSelector(self, value):
        self.cam.MV_CC_SetEnumValue("BalanceRatioSelector", value)

    @property
    def balanceWhiteAutoOnce(self):
        stEnumValue = MVCC_ENUMVALUE()
        ret = self.cam.MV_CC_GetEnumValue("BalanceWhiteAutoOnce", stEnumValue)
        if ret != 0:
            raise Exception("获取BalanceWhiteAutoOnce失败")
        return stEnumValue.nCurValue

    @balanceWhiteAutoOnce.setter
    def balanceWhiteAutoOnce(self, value):
        self.cam.MV_CC_SetEnumValue("BalanceWhiteAutoOnce", value)

    @property
    def balanceRatio(self):
        stParam = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("BalanceRatio", stParam)
        if ret != 0:
            raise Exception("获取BalanceRatio失败")
        return stParam.nCurValue

    @balanceRatio.setter
    def balanceRatio(self, value):
        self.cam.MV_CC_SetIntValue("BalanceRatio", value)

    @property
    def payloadSize(self):
        stCap = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("PayloadSize", stCap)
        if ret != 0:
            raise Exception("获取相机能力失败")
        return stCap.nCurValue

    @property
    def width(self):
        stParam = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("Width", stParam)
        if ret != 0:
            raise Exception("获取图像宽度失败")
        return stParam.nCurValue

    @property
    def height(self):
        stParam = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("Height", stParam)
        if ret != 0:
            raise Exception("获取图像高度失败")
        return stParam.nCurValue

    @property
    def pixelFormat(self):
        stEnumValue = MVCC_ENUMVALUE()
        ret = self.cam.MV_CC_GetEnumValue("PixelFormat", stEnumValue)
        if ret != 0:
            raise Exception("获取像素格式失败")
        return stEnumValue.nCurValue

    @pixelFormat.setter
    def pixelFormat(self, value):
        self.cam.MV_CC_SetEnumValue("PixelFormat", value)

    @property
    def reverseX(self):
        stParam = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("ReverseX", stParam)
        if ret != 0:
            raise Exception("获取ReverseX失败")
        return stParam.nCurValue

    @reverseX.setter
    def reverseX(self, value):
        self.cam.MV_CC_SetIntValue("ReverseX", value)

    @property
    def reverseY(self):
        stParam = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("ReverseY", stParam)
        if ret != 0:
            raise Exception("获取ReverseY失败")
        return stParam.nCurValue

    @reverseY.setter
    def reverseY(self, value):
        self.cam.MV_CC_SetIntValue("ReverseY", value)

    @property
    def binningX(self):
        stParam = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("BinningX", stParam)
        if ret != 0:
            raise Exception("获取BinningX失败")
        return stParam.nCurValue

    @binningX.setter
    def binningX(self, value):
        self.cam.MV_CC_SetIntValue("BinningX", value)

    @property
    def binningY(self):
        stParam = MVCC_INTVALUE()
        ret = self.cam.MV_CC_GetIntValue("BinningY", stParam)
        if ret != 0:
            raise Exception("获取BinningY失败")
        return stParam.nCurValue

    @binningY.setter
    def binningY(self, value):
        self.cam.MV_CC_SetIntValue("BinningY", value)

    def startGrabbing(self):
        # 开始取流
        ret = self.cam.MV_CC_StartGrabbing()
        if ret != 0:
            print(ret)
            raise Exception("开始取流失败")

    def getOneFrame(self, pData, stOutFrame):
        ret = self.cam.MV_CC_GetOneFrameTimeout(byref(pData), sizeof(pData), stOutFrame, 1000)
        if ret != 0:
            raise Exception("采集图像失败")

    def getOneFrameTimeout(self, pData, stOutFrame, timeout=1000):
        ret = self.cam.MV_CC_GetOneFrameTimeout(byref(pData), sizeof(pData), stOutFrame, timeout)
        if ret != 0:
            raise Exception("采集图像失败")
        return ret

    def stopGrabbing(self):
        # 停止取流
        ret = self.cam.MV_CC_StopGrabbing()
        if ret != 0:
            raise Exception("停止取流失败")
        return ret

    def closeDevice(self):
        # 关闭设备
        ret = self.cam.MV_CC_CloseDevice()
        if ret != 0:
            raise Exception("关闭设备失败")
        return ret

    def destroyHandle(self):
        # 销毁句柄
        ret = self.cam.MV_CC_DestroyHandle()
        if ret != 0:
            raise Exception("销毁句柄失败")
        return ret

    def release(self):
        # 停止取流
        self.stopGrabbing()
        # 关闭设备
        self.closeDevice()
        # 销毁句柄
        self.destroyHandle()

    def getFrame(self):
        stOutFrame = MV_FRAME_OUT_INFO_EX()
        pData = (c_ubyte * self.width * self.height)()  # 假设最大分辨率为2048x2048
        ret = self.cam.MV_CC_GetOneFrameTimeout(byref(pData), sizeof(pData), stOutFrame, 1000)
        if ret != 0:
            raise Exception("采集图像失败")
        # 数据处理，这里仅将其转换为NumPy数组并显示
        frame_data = np.frombuffer(pData, count=int(stOutFrame.nWidth * stOutFrame.nHeight), dtype=np.uint8)
        frame_data = frame_data.reshape((stOutFrame.nHeight, stOutFrame.nWidth))
        if ret != 0:
            raise Exception("采集图像失败")

        return frame_data


if __name__ == '__main__':
    cam = MvSdk(camera_info=MvSdk.getDeviceList()[0])
    cam.init()
    cam.open()
    while True:
        frame = cam.getFrame()
        cv2.imshow("frame", frame)
        cv2.waitKey(1)
