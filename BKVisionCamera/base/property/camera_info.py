class CameraInfo:
    _info_ = {}

    def __init__(self, devInfo):
        self._devInfo_ = devInfo
        self.mac = ""
        self.ip = ""
        self.name = ""

    def __setattr__(self, key, value):
        print(key+" : "+str(value))
        super().__setattr__(key, value)

    def __eq__(self, other):
        other: CameraInfo
        return self.mac == other.mac or self.ip == other.ip