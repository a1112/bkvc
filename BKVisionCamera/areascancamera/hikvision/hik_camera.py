from BKVisionCamera.areascancamera.hikvision.hik_sdk import MvSdk
from BKVisionCamera.base.property import CaptureBase


class HikCamera(CaptureBase):
    def __init__(self):
        super().__init__()
        self.sdk: MvSdk

    def loadSdk(self):
        return MvSdk()

    def init(self):
        self.sdk.MVInitLib()
