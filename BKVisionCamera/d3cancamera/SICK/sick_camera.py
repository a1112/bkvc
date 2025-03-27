from BKVisionCamera.base import register
from BKVisionCamera.base.property.capture import CaptureModel
# from .sick_sdk import SickSdk

@register()
class SickCamera(CaptureModel):
    names = ["sick", "西克"]

    def init(self):
        self.sdk.init()

    def open(self):
        self.sdk.open()

    def release(self):
        self.sdk.release()

    def getFrame(self):
        return self.sdk.getFrame()

    def __init__(self, property_):
        super().__init__(property_)
        self.sdk: SickSdk

    def load(self):
        return SickSdk(self.property)

    def __enter__(self):
        # 初始化或打开相机等操作
        self.init()
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 清理资源，例如关闭相机
        self.release()



