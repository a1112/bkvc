class CameraInfo:
    _info_ = {}

    def __init__(self, dev_info):
        self._devInfo_ = dev_info
        self.mac = ""
        self.ip = ""
        self.name = ""
        self.cameraName = ""
        self.serialNumber = ""
        self.sn = ""

    def __setattr__(self, key, value):
        print(key+" : "+str(value))
        super().__setattr__(key, value)

    def __eq__(self, other):
        other: CameraInfo
        return self.mac == other.mac or self.ip == other.ip