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
        if value:
            print(key+" : "+str(value))
        super().__setattr__(key, value)

    def __eq__(self, other):
        other: CameraInfo
        if self.mac:
            return self.mac == other.mac
        if self.serialNumber:
            return self.serialNumber==other.serialNumber
        return self.ip == other.ip