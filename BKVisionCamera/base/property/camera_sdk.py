from abc import ABC, abstractmethod
from typing import List

from .camera_info import CameraInfo


class CameraSdkInterface(ABC):
    def __init__(self, property_=None, camera_info: CameraInfo = None):

        self.property = property_
        if camera_info is not None:
            self.camera_info = camera_info
        else:
            self.camera_info = None
            self.camera_info_list = self.getDeviceList()
            print(self.camera_info_list)
            print(property_.selectType)
            print(property_.ip)
            for index, camera_info in enumerate(self.camera_info_list):
                print(camera_info)
                print(camera_info.ip)

                camera_info: CameraInfo
                if property_.selectType == "mac":
                    if camera_info.mac == property_.mac:
                        self.camera_info = camera_info
                        break
                elif property_.selectType == "ip":
                    if camera_info.ip == property_.ip:
                        self.camera_info = camera_info
                        break
                elif property_.selectType == "index":
                    if index == property_.index:
                        self.camera_info = camera_info
                        break
                elif property_.selectType == "sn":
                    if camera_info.sn == property_.sn:
                        self.camera_info = camera_info
                        break
                else:
                    if getattr(camera_info, property_.selectType)==getattr(property_, property_.selectType):
                        self.camera_info = camera_info
                        break

        if self.camera_info is None:
            print(self.getDeviceList())
            raise ValueError("未找到对应的相机")

    @abstractmethod
    def init(self):
        ...

    @abstractmethod
    def release(self):
        ...

    @abstractmethod
    def getFrame(self):
        ...
    @staticmethod
    @abstractmethod
    def createCamera(cameraInfo):
        ...

    @staticmethod
    @abstractmethod
    def getDeviceList() -> List[CameraInfo]:
        ...

    @abstractmethod
    def saveConfig(self, config):
        ...

    @abstractmethod
    def loadConfig(self, config):
        ...

    @property
    def width(self):
        return 0

    @property
    def height(self):
        return 0

    def setExposureTime(self, exposureTime):
        pass