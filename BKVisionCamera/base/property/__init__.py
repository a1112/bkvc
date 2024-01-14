from abc import ABC, abstractmethod


class CameraInfo:
    _info_ = {}

    def __init__(self, devInfo):
        self.devInfo = devInfo

    def __setattr__(self, key, value):
        self._info_[key] = value
        print(key, value)

    def __eq__(self, other):
        other: CameraInfo
        return self._info_["macAddress"] == other._info_["macAddress"]


class CameraSdkInterface(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def init(self):
        ...

    @abstractmethod
    def release(self):
        ...

    @staticmethod
    def getDeviceList():
        ...

    @abstractmethod
    def saveConfig(self, config):
        ...

    @abstractmethod
    def loadConfig(self, config):
        ...


class CaptureInterFace(ABC):

    @abstractmethod
    def loadSdk(self):
        ...


class CaptureBase(CaptureInterFace):
    def __init__(self):
        self.sdk = self.loadSdk()

    @abstractmethod
    def loadSdk(self):
        ...

    def capture(self):
        raise NotImplementedError

    def capture_with_callback(self, callback):
        raise NotImplementedError

    def release(self):
        raise NotImplementedError

    def release_with_callback(self, callback):
        raise NotImplementedError
