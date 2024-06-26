import struct
import numpy
from dataclasses import dataclass

@dataclass
class IMUData:
    """
    Values of imu data sample

    ...

    Attributes
    ----------
    acceleration : np.array [dtype=float64, length 3]
        Acceleration [m/s^2] for X/Y/Z axis
    angular_velocity : np.array [dtype=float64, length 3]
        Angular velocity [rad/s] for X/Y/Z axis
    magnetic_field : np.array [dtype=float64, length 3]
        Magnetic field [T] for X/Y/Z axis
    orientation : np.array [dtype=float64, length 4]
        Orientation estimate as quaternion (4-element vector) with norm 1
    timestamp : int
        Timestamp in nano seconds
    """
    acceleration: numpy.array
    angular_velocity: numpy.array
    magnetic_field: numpy.array
    orientation: numpy.array
    timestamp: int


class IMUParser():
    """
    A class to extract imu data samples from a buffer

    ...

    Attributes
    ----------
    buffer : bytearray
        Actual values will be extracted with struct.unpack_from(..)

    Methods
    -------
    getNext():
        Returns next imu data sample object of type 'IMUData'
        or 'None' if no bytes are left
    """
    def __init__(self, buffer):
        vec3_format_string = "<ddd"
        self.vec3_parser = struct.Struct(vec3_format_string)
        self.vec3_size = struct.calcsize(vec3_format_string)
        vec4_format_string = "<dddd"
        self.vec4_parser = struct.Struct(vec4_format_string)
        self.vec4_size = struct.calcsize(vec4_format_string)
        timestamp_format_string = "<Q"
        self.timestamp_parser = struct.Struct(timestamp_format_string)
        self.timestamp_size = struct.calcsize(timestamp_format_string)
        self.buffer = buffer
        self.offset = 0

    def getNext(self):
        imu_data = None
        if self.offset < len(self.buffer):
            acceleration = numpy.array(
                self.vec3_parser.unpack_from(self.buffer, self.offset))
            self.offset += self.vec3_size
            angular_velocity = numpy.array(
                self.vec3_parser.unpack_from(self.buffer, self.offset))
            self.offset += self.vec3_size
            magnetic_field = numpy.array(
                self.vec3_parser.unpack_from(self.buffer, self.offset))
            self.offset += self.vec3_size
            orientation = numpy.array(
                self.vec4_parser.unpack_from(self.buffer, self.offset))
            self.offset += self.vec4_size
            timestamp = self.timestamp_parser.unpack_from(
                self.buffer, self.offset)[0]
            self.offset += self.timestamp_size
            imu_data = IMUData(acceleration, angular_velocity,
                               magnetic_field, orientation, timestamp)
        return imu_data

  
  
  
  