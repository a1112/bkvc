from base.property import CaptureBase


class HikCamera(CaptureBase):
    def __init__(self, ip, port, username, password, channel=1):
        super().__init__(ip, port, username, password)
        self.channel = channel
        self._init_camera()

    def _init_camera(self):
        self._hik = MvSdk()
        self._hik.NET_DVR_Init()
        self._hik.NET_DVR_SetLogToFile(3, b"logs", 0, 1)
        self._hik.NET_DVR_SetConnectTime(2000, 1)
        self._hik.NET_DVR_SetReconnect(10000, 1)
        self._hik.NET_DVR_SetRecvTimeOut(5000)
        self._hik.NET_DVR_SetExceptionCallBack_V30(
            0, None, self._exception_callback, None
        )
        self._hik.NET_DVR_SetDVRMessageCallBack_V30(
            self._alarm_callback, None
        )
        self._login_id = self._hik.NET_DVR_Login_V30(
            self.ip,
            self.port,
            self.username.encode("utf-8"),
            self.password.encode("utf-8"),
            None,
        )
        if self._login_id < 0:
            raise CameraException("Login failed")
        self._hik.NET_DVR_SetupAlarmChan_V41(
            self._login_id, None, None, 0, None, None
        )

    def _exception_callback(self, code, _):
        print(f"Exception code: {code}")

    def _alarm_callback(self, command, alarm_info, _, __):
        print(f"Alarm code: {command}, alarm info: {alarm_info}")

    def capture(self):
        pass

    def capture_with_callback(self, callback):
        pass

    def release(self):
        pass

    def release_with_callback(self, callback):
        pass