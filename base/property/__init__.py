from abc import ABC, abstractmethod


class CameraSdkInterface(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def enumDevices(self):
        ...


class CaptureBase:
    def __init__(self, ip, port, username, password):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password

    def capture(self):
        raise NotImplementedError

    def capture_with_callback(self, callback):
        raise NotImplementedError

    def release(self):
        raise NotImplementedError

    def release_with_callback(self, callback):
        raise NotImplementedError