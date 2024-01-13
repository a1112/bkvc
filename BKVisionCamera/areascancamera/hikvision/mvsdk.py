from ctypes import POINTER, cast, c_ubyte, byref, sizeof

import cv2
import numpy as np

from BKVisionCamera.areascancamera.hikvision.MvImport.CameraParams_const import MV_GIGE_DEVICE, MV_USB_DEVICE, \
    MV_ACCESS_Exclusive, MV_CAMERALINK_DEVICE
from BKVisionCamera.areascancamera.hikvision.MvImport.CameraParams_header import MV_CC_DEVICE_INFO_LIST, \
    MV_CC_DEVICE_INFO, MV_TRIGGER_MODE_OFF, MV_FRAME_OUT_INFO_EX, MVCC_ENUMVALUE
from BKVisionCamera.areascancamera.hikvision.MvImport.MvCameraControl_class import MvCamera
from base.property import CameraSdkInterface


class MvSdk(CameraSdkInterface):

    def __init__(self):
        super().__init__()
        self.cam = MvCamera()

    def enumDevices(self):
        # 创建相机实例
        stDevList = MV_CC_DEVICE_INFO_LIST()
        ret = self.cam.MV_CC_EnumDevices(MV_GIGE_DEVICE | MV_USB_DEVICE | MV_CAMERALINK_DEVICE | MV_CAMERALINK_DEVICE
                                         , stDevList)
        return stDevList, ret

    def init(self, index=0):
        stDevList, ret = self.enumDevices()
        if ret != 0:
            raise Exception("枚举设备失败")
        if stDevList.nDeviceNum == 0:
            raise Exception("未找到设备")
        if index >= stDevList.nDeviceNum:
            raise Exception("设备索引超出范围")
        stDevInfo = cast(stDevList.pDeviceInfo[index], POINTER(MV_CC_DEVICE_INFO)).contents
        # 选择第一台相机并创建句柄
        ret = self.cam.MV_CC_CreateHandle(stDevInfo)
        if ret != 0:
            raise Exception("创建句柄失败")
        return stDevList, ret

    @property
    def triggerMode(self):
        stEnumValue = MVCC_ENUMVALUE()
        ret = self.cam.MV_CC_GetEnumValue("TriggerMode", stEnumValue)
        if ret != 0:
            raise Exception("获取触发模式失败")
        return stEnumValue.nCurValue

    def open(self):
        # 打开设备
        ret = self.cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
        if ret != 0:
            raise Exception("打开设备失败")
        self.triggerMode = MV_TRIGGER_MODE_OFF
        # 开始取流


    @triggerMode.setter
    def triggerMode(self, value=MV_TRIGGER_MODE_OFF):
        self.cam.MV_CC_SetEnumValue("TriggerMode", value)

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

    def close(self):
        # 停止取流
        self.stopGrabbing()
        # 关闭设备
        self.closeDevice()
        # 销毁句柄
        self.destroyHandle()


def main():
    # 开始取流
    cam = MvSdk()
    cam.init()
    cam.open()
    cam.startGrabbing()
    stOutFrame = MV_FRAME_OUT_INFO_EX()
    pData = (c_ubyte * 3072 * 2048)()  # 假设最大分辨率为2048x2048
    while True:
        print(pData)
        ret = cam.getOneFrameTimeout(pData, stOutFrame, 1000)
        print(ret)
        if ret == 0:
            print(f"成功采集一帧：宽度={stOutFrame.nWidth}，高度={stOutFrame.nHeight}")
            # 数据处理，这里仅将其转换为NumPy数组并显示
            frame_data = np.frombuffer(pData, count=int(stOutFrame.nWidth * stOutFrame.nHeight), dtype=np.uint8)
            frame_data = frame_data.reshape((stOutFrame.nHeight, stOutFrame.nWidth))
            cv2.imshow("Frame", frame_data)
            cv2.waitKey(1)



if __name__ == '__main__':
    main()
