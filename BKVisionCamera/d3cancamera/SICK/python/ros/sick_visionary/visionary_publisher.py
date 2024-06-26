# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

from argparse import ArgumentParser, RawDescriptionHelpFormatter as rdhf
from harvesters import __version__ as harvesters_version
from harvesters.core import Harvester
from logging import basicConfig, info, INFO, error
from sys import exit, version
from rclpy import init, shutdown
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.executors import MultiThreadedExecutor
from rclpy.time import Time
from rclpy.clock import ClockType
from rclpy.qos import QoSProfile, QoSHistoryPolicy, QoSDurabilityPolicy
from tf2_ros import StaticTransformBroadcaster
from logging import info, error
import numpy as np
from os import path
import platform
from sensor_msgs.msg import Image, PointCloud2, PointField
from geometry_msgs.msg import TransformStamped, Vector3, Quaternion
from genicam.gentl import DEVICE_ACCESS_STATUS_LIST
from pathlib import Path
from time import sleep, time

# The following routines are copied from gev_recording/lib/utils.py so that we can make this
# a standalone Python package, includable in a larger project without internal dependencies.


def get_cti_dir_name():
    """Helper to get cti file directory name corresponding with the platform the script is running on"""
    if platform.system() == "Windows":
        return "windows_x64"
    if platform.system() == "Linux" and platform.machine() == "x86_64":
        return "linux_x64"
    if platform.system() == "Linux" and platform.machine() == "aarch64":
        return "linux_aarch64"

    # Not one of our recognized platforms, cti file not available
    raise RuntimeError("GenTL Producer not available on this platform")


def get_cti_path():
    """Helper to get cti file path corresponding with the platform the script is running on """
    # The directory with this script is located expected to contain "cti/" subdirectory further
    # containing one subdirectory for each platform supported by the SICK GenTL Producer for GigE Vision.
    # The actual filename of the GenTL Producer binary is always the same (SICKGigEVisionTL.cti).
    script_dir = Path(__file__).resolve().parent.parent.parent.parent
    resource_dir = script_dir / "common" / "lib" / "cti" / get_cti_dir_name()
    info(f"Using resource directory: {resource_dir}")
    return path.join(resource_dir, "SICKGigEVisionTL.cti")


def init_harvester():
    try:
        h = Harvester()
        h.add_file(get_cti_path(), check_existence=True, check_validity=True)
        info("CTI driver loaded...")
        h.update()
        info(f"Device discovery done, received {len(h.device_info_list)} answers")
        return h
    except Exception as err:
        error(f"No devices found: {err}")
        exit(1)


def cv2_to_imgmsg(cv_image, encoding='bgr8'):
    img_msg = Image()
    img_msg.height = cv_image.shape[0]
    img_msg.width = cv_image.shape[1]
    img_msg.encoding = encoding
    img_msg.is_bigendian = 0
    img_msg.data = cv_image.tobytes()
    img_msg.step = len(img_msg.data) // img_msg.height
    return img_msg


def enforce_ip_address(device_info):
    """Enforce temporary IP address to the camera with IP subnet mismatch (until reboot)"""
    info(f"Try enforcing suitable IP address to unreachable device: {device_info.display_name}")
    itf_node_map = device_info.parent.node_map
    device_id = device_info.id_
    for idx in range(itf_node_map.DeviceSelector.max + 1):
        if device_id == itf_node_map.DeviceID.value:
            itf_node_map.GevDeviceProposeIP.execute()
            proposed_ip = itf_node_map.GevDeviceForceIPAddress.to_string()
            proposed_subnet = itf_node_map.GevDeviceForceSubnetMask.to_string()
            info(f"IP address is {proposed_ip}/{proposed_subnet}, forcing into the device")
            itf_node_map.GevDeviceForceIP.execute()
            while not itf_node_map.GevDeviceForceIP.is_done():
                sleep(1)
            info("\tForcing IP address completed")


def get_rotation_mat(tilt_angle):
    tilt_rad = np.radians(tilt_angle)
    return np.array([
        [1, 0, 0, 0],
        [0, np.cos(tilt_rad), -np.sin(tilt_rad), 0],
        [0, np.sin(tilt_rad), np.cos(tilt_rad), 0],
        [0, 0, 0, 1]
    ])


def get_translation_mat(x, y, z):
    return np.array([
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1]
    ])


def get_transformation_mat(tilt_angle, x, y, z):
    rot_mat = get_rotation_mat(tilt_angle)
    trans_mat = get_translation_mat(x, y, z)
    return np.dot(trans_mat, rot_mat)


class VisionaryBTwoPublisher(Node):
    """Publisher for 2D/3D camera data"""

    def __init__(self, camera_serial, fps):
        super().__init__('Visionary_B_Two')
        self.tf_broadcaster = StaticTransformBroadcaster(self)
        transforms = list()
        transforms.append(self.static_transform('camera_frame'))
        transforms.append(self.static_transform('depth_frame'))
        transforms.append(self.static_transform('pointcloud_frame'))
        self.tf_broadcaster.sendTransform(transforms)

        self.imacq = None
        self.nm = None

        # Init IMU and make them user-adjustable from cmdline
        self.declare_parameter('tilt_angle', 0.0) # in degrees
        self.declare_parameter('mounting_height', 0.0) # in meters
        self.declare_parameter('x_trans', 0.0) # in meters
        self.declare_parameter('y_trans', 0.0) # in meters

        self.colormap = None
        self.depthmap = None
        self.pointcloud = None
        self.frame_ts = None

        self.start_time = time()
        self.startup_device(camera_serial)

        qos_profile = QoSProfile(
            # New data will be stored on free slots up to 'depth' value
            history=QoSHistoryPolicy.RMW_QOS_POLICY_HISTORY_KEEP_LAST,
            # Keep the last 'n' images and reject older ones
            depth=3,
            # Connection may be dropped in case of failure or disconnect
            durability=QoSDurabilityPolicy.RMW_QOS_POLICY_DURABILITY_VOLATILE
        )

        self.rgb_img_publisher = self.create_publisher(msg_type=Image,
                                                       topic='sick_visionary_rgb',
                                                       qos_profile=qos_profile)
        self.depth_img_publisher = self.create_publisher(msg_type=Image,
                                                         topic='sick_visionary_depth',
                                                         qos_profile=qos_profile)
        self.pointcloud_publisher = self.create_publisher(msg_type=PointCloud2,
                                                          topic='sick_visionary_pointcloud',
                                                          qos_profile=qos_profile)

        self.timer = self.create_timer(1. / fps, self.publish_callback)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.destroy_node()

    def publish_callback(self):
        self.prepare_camera()

        info("Publishing messages: (%.1f FPS)" % (1.0 / (time() - self.start_time)))
        self.start_time = time()
        if self.colormap is not None:
            info("\tcamera_frame")
            msg = cv2_to_imgmsg(self.colormap)
            msg.header.frame_id = 'camera_frame'
            msg.header.stamp = self.frame_ts.to_msg()
            self.rgb_img_publisher.publish(msg)
        if self.depthmap is not None:
            info("\tdepth_frame")
            msg = cv2_to_imgmsg(self.depthmap, 'mono8')
            msg.header.frame_id = 'depth_frame'
            msg.header.stamp = self.frame_ts.to_msg()
            self.depth_img_publisher.publish(msg)
        if self.pointcloud is not None:
            info("\tpointcloud_frame")
            pointcloud_msg = self.pointcloud
            pointcloud_msg.header.frame_id = 'pointcloud_frame'
            pointcloud_msg.header.stamp = self.frame_ts.to_msg()
            self.pointcloud_publisher.publish(pointcloud_msg)

    def static_transform(self, frame_id):
        tf_stamped = TransformStamped()
        tf_stamped.header.stamp = self.get_clock().now().to_msg()
        tf_stamped.header.frame_id = 'map'
        tf_stamped.child_frame_id = frame_id
        tf_stamped.transform.translation = Vector3(x=0., y=0., z=0.)
        tf_stamped.transform.rotation = Quaternion(x=0.0, y=0.0, z=0.0, w=1.0)
        return tf_stamped

    def startup_device(self, camera_serial):
        try:
            self.harvester = init_harvester()
            devices = self.harvester.device_info_list
            if len(devices) == 0:
                error("No GigE Vision devices discovered")
                exit(1)

            info(f"Discovered {len(devices)} device(s), trying to setup {camera_serial}:")
            device = next(filter(lambda d: d.serial_number == str(camera_serial), devices), None)
            if device is None:
                error(f"Device with serial {camera_serial} not found")
                exit(1)

            info(f"\t{device.display_name}")
            if device.access_status == DEVICE_ACCESS_STATUS_LIST.DEVICE_ACCESS_STATUS_NOACCESS:
                enforce_ip_address(device)
                self.harvester.update()

            if device.access_status != DEVICE_ACCESS_STATUS_LIST.DEVICE_ACCESS_STATUS_READWRITE:
                error("Discovered camera is not ready for readwrite")
                exit(1)

            self.imacq = self.harvester.create(search_key={'serial_number': str(camera_serial)})
            info(f"Connected to camera S/N {camera_serial}")
            self.imacq.num_buffers = 10 # improves stability
            self.imacq.stop()

            self.nm = self.imacq.remote_device.node_map
            self.nm.ComponentSelector.value = 'Range'
            self.nm.ComponentEnable.value = True
            self.nm.ComponentSelector.value = 'Intensity'
            self.nm.ComponentEnable.value = True
            self.nm.ChunkModeActive.value = True
            self.nm.GevSCPD.value = 100000 # packet delay, in ns
            self.nm.ExposureAuto.value = 'Continuous'
            self.nm.ExposureAutoFrameRateMin.value = 10
            self.nm.MultiSlopeMode.value = 'PresetAggressive'
            self.nm.Scan3dDataFilterSelector.value = 'ValidationFilter'
            self.nm.Scan3dDataFilterEnable.value = 1
            self.nm.Scan3dDepthValidationFilterLevel.value = -9
            self.imacq.start()

        except Exception as err:
            error(f"Exception: {err}")
            self.stop_camera()
            exit(1)

    def prepare_camera(self):
        if self.imacq is None:
            return
        with self.imacq.fetch(timeout=1.0) as buffer:
            self.frame_ts = Time(nanoseconds=buffer.timestamp_ns, clock_type=ClockType.ROS_TIME)
            for c in buffer.payload.components:
                if c.data_format == 'BGR8':
                    self.colormap = np.array(c.data).reshape(c.height, c.width, 3)
                elif c.data_format == 'Coord3D_C16' and self.colormap is not None:
                    range_map = c.data.reshape(c.height, c.width)
                    range_factor = np.amax(range_map) // 2**8
                    self.depthmap = (range_map // range_factor).astype(np.uint8)
                    rgb = self.colormap[:,:,2] * 256**2 + self.colormap[:,:,1] * 256 + self.colormap[:,:,0]

                    col, row = np.meshgrid(np.arange(c.width), np.arange(c.height))
                    focal_length = self.nm.ChunkScan3dFocalLength.value
                    aspect_ratio = self.nm.ChunkScan3dAspectRatio.value
                    princ_point_u = self.nm.ChunkScan3dPrincipalPointU.value
                    princ_point_v = self.nm.ChunkScan3dPrincipalPointV.value
                    scale_c = self.nm.ChunkScan3dCoordinateScale.value
                    offset_c = self.nm.ChunkScan3dCoordinateOffset.value

                    xp = (col - princ_point_u) / focal_length
                    yp = (row - princ_point_v) / (focal_length * aspect_ratio)
                    scale_c = self.depthmap * scale_c + offset_c

                    xc = xp * scale_c
                    yc = yp * scale_c
                    zc = scale_c

                    self.pointcloud = PointCloud2()
                    self.pointcloud.fields = [
                        PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
                        PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
                        PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
                        PointField(name='rgb', offset=12, datatype=PointField.UINT32, count=1)
                    ]

                    self.pointcloud.point_step = 16 # 4 * 4
                    self.pointcloud.height = xc.shape[0]
                    self.pointcloud.width = xc.shape[1]
                    self.pointcloud.row_step = self.pointcloud.point_step * self.pointcloud.width
                    self.pointcloud.is_bigendian = False
                    self.pointcloud.is_dense = True
                    dt = np.dtype([('x', np.float32), ('y', np.float32), ('z', np.float32),
                                   ('rgb', np.uint32)])
                    points = np.array(list(zip(xc.ravel(), yc.ravel(), zc.ravel(), rgb.ravel())),
                                      dtype=dt)
                    self.pointcloud._data = points.tobytes()

    def stop_camera(self):
        info("Teardown: Cleanup all objects")
        self.harvester.reset()
        self.harvester = None
        if self.imacq != None:
            self.imacq.stop()
            self.imacq.destroy()
            self.imacq = None


def main(args=None):
    if not version.startswith(('3.8.', '3.10.')):
        error(f"Python 3.8./3.10. is required. But this is: {version}")
        return 1
    elif not harvesters_version == '1.4.0':
        error(f"Harvesters 1.4.0 is required. But this is: {harvesters_version}")
        return 1

    init(args=None)
    with VisionaryBTwoPublisher(args.serial, args.fps) as camera:
        # Four threads are a sensible default with no further improvement on performance
        executor = MultiThreadedExecutor(num_threads=4)
        executor.add_node(camera)
        executor.spin()
    shutdown()
    return 0


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__, formatter_class=rdhf)
    parser.add_argument("-s", "--serial", help="Camera serial", type=int, default=22990047)
    parser.add_argument("-f", "--fps", help="Number of frames per second", type=int, default=20)
    log_fmt = "[%(levelname)s] [%(created).9f] [Visionary_B_Two]: %(message)s"
    basicConfig(format=log_fmt, level=INFO)
    exit(main(parser.parse_args()))
