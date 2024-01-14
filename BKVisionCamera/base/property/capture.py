from abc import ABC, abstractmethod

from .camera_sdk import CameraSdkInterface


class CaptureModel(ABC):
    def __init__(self, property_):
        self.property = property_
        self.sdk = self.load()
        self.sdk:CameraSdkInterface
        self.camera_info = self.sdk.camera_info

    @abstractmethod
    def load(self):
        ...

    @abstractmethod
    def open(self):
        ...

    @abstractmethod
    def release(self):
        ...

    @abstractmethod
    def getFrame(self):
        ...

    def __enter_(self):
        ...

    def __exit__(self, exc_type, exc_val, exc_tb):
        ...
