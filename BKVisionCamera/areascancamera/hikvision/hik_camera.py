from BKVisionCamera.areascancamera.hikvision.hik_sdk import MvSdk
from BKVisionCamera.base import register
from BKVisionCamera.base.property.capture import CaptureModel


@register()
class HikCamera(CaptureModel):
    names = ["hikvision", "海康"]

    sdk: MvSdk

    def init(self):
        self.sdk.init()

    def open(self):
        self.sdk.open()

    def release(self):
        self.sdk.release()

    def getFrame(self):
        try:
            return self.sdk.getFrame()
        except:
            return None

    def __init__(self, property_):
        super().__init__(property_)
        self.sdk: MvSdk

    def load(self):
        return MvSdk(self.property)

    def __enter__(self):
        # 初始化或打开相机等操作
        self.init()
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 清理资源，例如关闭相机
        self.release()
