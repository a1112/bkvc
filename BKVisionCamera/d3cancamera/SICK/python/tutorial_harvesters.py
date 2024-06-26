###############################################################################################
# tutorial_harvesters.py: tutorial script demonstrating how to access SICK Visionary cameras
# with GigE Vision interface over Python.
#
# Designed for use with Python 3.x and harvesters 1.4.0 (please use exactly this version, since 
# Harvesters API might be slightly changing between versions (pip install harvesters==1.4.0).
# For use on the aarch64 platform, the genicam module's arm64 preview must be installed manually
# in the moment, see: https://github.com/genicam/harvesters/issues/254#issuecomment-1133200274
# Note that the example was primarily tested with Python 3.8 - refer to Harvesters documentation
# for eventual other limitations imposed by Harvesters itself
#
# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense
#
###############################################################################################


# Quick Overview:
# - Visionary cameras provide standard GigE Vision interface - users relying on GigE Vision compliant
#   receiver software can use them out of the box
# - For users without direct access to a GigE Vision receiver, SICK provides a GigE Vision receiver
#   implementation which exposes its functionality over a standard GenICam GenTL API
# - The receiver is delivered together with this sample script as a standard GenTL Producer file (*.cti),
#   one binary for every supported platform
# - The GenTL Producer can be accessed either directly using GenICam GenTL API (https://genicam.org/)
#   or indirectly through another tool supporting that API
# - Harvesters (https://github.com/genicam/harvesters) is one such option, wrapping the GenTL API into
#   a simple to use Python library - refer to its documentation (https://harvesters.readthedocs.io/en/latest/)
#   for further details beyond this tutorial
# - Check also brief overview of the system in InterfacingGev.pdf

# The most important import to reach Harvester functionality:
from harvesters.core import Harvester
# Needed just to verify version of the harvesters package:
import harvesters
# Some Harvester properties correspond to actual GenTL constants, in that case importing
# corresponding parts of GenTL Python wrappers might be required
from genicam.gentl import DEVICE_ACCESS_STATUS_LIST
# The acquired data are delivered as numpy arrays by Harvester
import numpy
# Other imports required in the sample script
import sys
import platform
import os
import time
from PIL import Image
from plyfile import PlyData, PlyElement

###############################################################################################
# Main example code
###############################################################################################
def main():
  # Perform setup prerequisite checks, will exit the script in case of a problem
  validate_setup()

  # Note: some Harvester functions can raise exceptions. We do not particularly care about them
  # in this example to keep it straightforward, assuming that it is OK to let the script die
  # in case of a problem. In a real world application this would be different.

  # Instantiate the Harvester object which will give us access to the cameras
  # Using the with statement helps to avoid any cleanup problems, otherwise the object would have
  # to be properly reset on all code paths when it's no more used (refer to Harvesters docu).
  with Harvester() as h:
    # Determine the GenTL Producer file Harvester should use to talk to the camera and add it to Harvester.
    # This file is SICK's implementation of a GigE Vision protocol, providing standard GenTL API
    cti = get_cti_path()
    print("Going to use GenTL Producer file {}".format(cti))

    # Pass given GenTL Producer file to Harvester (asking for basic validity checks to detect issues early),
    # it will be used to discover and communicate with the cameras
    h.add_file(cti, check_existence=True, check_validity=True)

    # Let Harvester discover the camera(s) connected to the system, updating the device list.
    # At this point the camera must be running and connected to the system running the script
    h.update()

    # Stop the script if no devices were found, otherwise print their overview
    if len(h.device_info_list) == 0:
      sys.exit("No GigE Vision devices discovered in this system")
    print("Discovered {} device(s), going to use the first entry in the test:".format(len(h.device_info_list)))
    for device_info in h.device_info_list:
      print("\t{}".format(device_info.display_name))

    # Before trying to open, we can check the access status of the (first discovered) device.
    # If the status is "NOACCESS", most likely a wrong IP address (not matching the subnet of the network card
    # it is connected to).
    # We can demonstrate how a suitable IP address can be "forced" into the device, however, configuring
    # the device to boot into expected IP subnet is recommended instead.
    if h.device_info_list[0].access_status == DEVICE_ACCESS_STATUS_LIST.DEVICE_ACCESS_STATUS_NOACCESS:
      force_suitable_ip_address(h.device_info_list[0])
      # Update the device list again to notify Harvester about the new state
      # (refer to Harvester docu to learn about all side effects of the update call)
      h.update()

    # If the access status is still not "READWRITE" (meaning it is ready to open), stop the script.
    # This can happen because of multiple reasons, including that it is already open by another application
    # and is beyond the scope of this example.
    # (Also beyond this example's scope is the situation of multiple cameras connected to the system and discovered
    # by Harvester always in different order - in such cases identifying the cameras by MAC or serial number
    # would be better than simply taking the first seen one as in this script).
    if len(h.device_info_list) == 0 or h.device_info_list[0].access_status != DEVICE_ACCESS_STATUS_LIST.DEVICE_ACCESS_STATUS_READWRITE:
      sys.exit("The discovered camera is not ready to open")

    # Create the Harvester's ImageAcquirer which will establish connection to the camera and allow configuring it
    # and acquire images. Without parameters, create() will connect to the first discovered camera. In multiple camera setups,
    # the actual camera to open can be selected by its serial number or other parameters - see Harvesters documentation.
    # Same comments apply about use of the with statement as with the Harvester object itself (if not used, the ImageAcquirer
    # should be explicitly destroyed when no more used)
    with h.create() as ia:
      # It is possible to get important information about the used GenICam GenTL Producer (a.k.a. cti driver) from the
      # system node map. here we just print the most important one, check the harvesters doc for more details.
      print("Version of GenTL producer driver: {} ({})".format(ia.system.node_map.TLVersion.to_string(), ia.system.node_map.TLVendorName.to_string()))
      # Now we can get access to the "remote device" (which in GenICam GenTL vocabulary means the actual device connected
      # to the host system) and its "node map" (GenICam map of feature nodes defining user interface of the device).
      # We can use features in this node map to configure the device properties.
      # For details about individual available parameters and their relationships, refer to the camera feature documentation
      # delivered together with this package.
      nm = ia.remote_device.node_map
      # Enable both acquired image components (Range data and RGB intensity data) to be delivered with the stream
      nm.ComponentSelector.value = 'Range'
      nm.ComponentEnable.value = True
      nm.ComponentSelector.value = 'Intensity'
      nm.ComponentEnable.value = True
      # The basic IMU data is not needed/used in this sample. Hence, we can disable this component.
      nm.ComponentSelector.value = 'ImuBasic'
      nm.ComponentEnable.value = False
      # Ensure the "chunk data" is switched on (chunk data is again a GenICam term for metadata transferred in the stream),
      # for the Visionary devices it especially carries the camera intrinsic parameters required to build the point cloud
      nm.ChunkModeActive.value = True
      # For purpose of this test, set a lower frame rate and insert an "inter-packet delay" to slow the stream and make
      # this example reliable in all setups - note that to reach good results (mainly no lost packets) with full-speed stream,
      # the receiver should be running on a well performing and optimized system. Most importantly the network card should
      # be configured to allow receiving larger packets ("jumbo frames"). Find more info in the camera documentation.
      # Note also that with small negotiated packet size (implying many packets required to transfer each frame) and following
      # (relatively large) inter-packet delay, the camera might be producing frames faster then their packets can be sent out,
      # resulting in dropped blocks on camera side.
      # Please note also that to be able to reliably configure frame rate, we are first switching the auto-exposure
      # feature "off" (frame rate feature would not be available otherwise). This is an example of a feature
      # dependency to be considered (mentioned in camera features documentation). Because the camera keeps its
      # configuration across multiple connections, one should keep in mind that when freshly connected, the camera
      # is in the state where it was left during the previous session.
      nm.ExposureAuto.value = 'Off'
      nm.AcquisitionFrameRate.value = 5.0 # (in Hz)
      nm.GevSCPD.value = 100000 # (packet delay, in ns)

      # Refer to the camera documentation to learn about other parameters, such as ExposureAuto, MultiSlopeMode (HDR...)
      # or Scan3dDataFilterSelector (ValidationFilter) which can have significant impact on the output quality, 
      # but depend on the actual scene and conditions.
      # Assuming that this tutorial is usually executed in developer's "office conditions" (indoor, low light levels),
      # we attempt below to set few more parameters, trying to achive reasonable output quality in such conditions.
      # It should be understood, however, that this selection is senstitive to actual environment and you might need
      # to adjust them if the output is not good enough.
      # In particular, we disable auto-exposure (already done above), set long enough exposure time and apply stronges 
      # possible validation filter level to get rid of unwanted noise.
      nm.ExposureTime.value = 25000
      nm.Scan3dDataFilterSelector.value = 'ValidationFilter'
      nm.Scan3dDataFilterEnable.value = True
      nm.Scan3dDepthValidationFilterLevel.value = -3

      # The GenTL Producer will attempt to negotiate with the camera highest possible packet size supported by all the involved
      # network components. If the negotiated packet size is not bigger than the standard 1500B, likely the above mentioned
      # jumbo frame support was not enabled on the network card or the camera is connected through a switch without jumbo frame support.
      # For the purpose of this tests, let's just issue a warning, for real world use this should be addressed properly.
      if nm.GevSCPSPacketSize.value <= 1500:
        print("BEWARE: failed to negotiate larger packet size (>1500B), enable jumbo frame support on the network card for optimal performance")

      # Finally, before starting acquisition, it is usually useful to increase the default number of buffers Harvester will use
      # for acquisition - this can help overcome possible temporary hiccups in the buffer processing on Harvester/application side
      ia.num_buffers = 10 

      # Now we can start the acquisition. Note that during active acquisition many of the camera parameters will be locked
      # (not writable).
      ia.start()

      # To demonstrate the acquistion loop, let's just fetch few buffers in a loop. Refer again to Harvester documentation
      # when more details are needed about the acquisition control. 
      IMAGES_TO_ACQUIRE = 20
      print("Going to acquire {} frames".format(IMAGES_TO_ACQUIRE))
      for _ in range(IMAGES_TO_ACQUIRE):
        # When using the with statement as demonstrated below, Harvester will automatically requeue the buffer for further acquisition 
        # as soon as its processing is finished. The optional timeout will raise an exception if there's a problem with the acquisition
        # and the buffer reception takes longer than expected (the exception is not handled in the lines below...).
        with ia.fetch(timeout=2.0) as buffer:
          # Print the acquired frame ID. Skipped IDs signal any kind of acquisition problem: dropped frame(s) (due to corrupted/lost packets),
          # queue overflow on camera side (cannot send all required packets possibly due to too long packet delay) or queue "underflow"
          # in the receiver side. Most of these cases usually signal performance problems on the receiver and/or its network stack.
          print("\tAcquired frame ID {} with timestamp {} ns".format(buffer.frame_id, buffer.timestamp_ns))
          # (Actual buffer contents processing demonstrated in the second acquisition round below...)

      # First simple acquisition loop test is finished, stop the acquisition
      ia.stop()

      # In case of suspecting acquisition performance issues, we can print some statistics, which are provided by the GenTL Producer itself.
      # These are accessible through another "node map" - one provided by the producer's data stream module.
      stream_nm = ia.data_streams[0].node_map
      print("Selected stream statistics")
      print("\tNumber of blocks skipped (for any reason, camera or receiver side): {}".format(stream_nm.GevStreamSkippedBlockCount.value))
      print("\tNumber of discarded blocks (typically because they arrived corrupted with too big packet loss): {}".format(stream_nm.GevStreamDiscardedBlockCount.value))
      print("\tNumber of blocks that were delivered, but were missing some data packets: {}".format(stream_nm.GevStreamIncompleteBlockCount.value))
      print("\tNumber of blocks discarded by the acquisition if no acquisition buffers were free to fill at the moment: {}".format(stream_nm.GevStreamEngineUnderrunCount.value))
      print("\tNumber of all stream packets seen by the acquisition engine: {}".format(stream_nm.GevStreamSeenPacketCount.value))
      print("\tNumber of all packets detected as lost by the engine: {}".format(stream_nm.GevStreamLostPacketCount.value))
      print("\tNumber of all packets in successfully delivered frames: {}".format(stream_nm.GevStreamDeliveredPacketCount.value))
      print("\tNumber of packet resend request commands issued by the acquisition engine: {}".format(stream_nm.GevStreamResendCommandCount.value))
      print("\tNumber of all packets requested in those resend request commands: {}".format(stream_nm.GevStreamResendPacketCount.value))
      print("\tNumber of resend-requested packets which were marked as no more available by the camera: {}".format(stream_nm.GevStreamUnavailablePacketCount.value))

      # Here the acquisition is stopped and we could have chance to reconfigure again any camera parameters that are locked during acquisition.
      # Instead, we simply start the acquisition again and acquire just a single buffer to demonstrate how to query and process its contents.
      ia.start()
      with ia.fetch(timeout=2.0) as buffer:
        print("Acquired one more frame to demonstrate buffer contents processing")
        # The acquired buffer will contain one or more "components". Because we have enabled "Range" and "Intensity" components when
        # configuring the device above, those two should always be delivered.
        # Unfortunately, current version of Harvester does not support component type identification, therefore we have to "recognize them"
        # through the pixel format of their data.
        cmp_range = None
        cmp_intensity = None
        print("The buffer contains following {} components:".format(len(buffer.payload.components)))
        for i, cmp in enumerate(buffer.payload.components):
          print("\t#{}: size {}x{}, format {}".format(i, cmp.width, cmp.height, cmp.data_format))
          # Identify and remember the range & intensity components based on their pixel format as indicated above
          # The Visionary-B by default uses BGR8 format for intensity, Coord3D_C16 for range data
          if cmp.data_format == 'BGR8':
              cmp_intensity = cmp
              print("\t\t(identified as intensity)")
          elif cmp.data_format == 'Coord3D_C16':
              cmp_range = cmp
              print("\t\t(identified as range)")

        # We expect both components must be successfully located in the buffer
        if not (cmp_range and cmp_intensity):
          sys.exit("Failed to locate both Range and Intensity components in the acquired buffer")

        # Besides accessing the actual acquired data of range and intensity components, to compute the point cloud
        # real world coordinates, we'll need the corresponding parameters (camera intrinsics) to compute it.
        # These are delivered, as usual in GigE Vision & GenICam world, within the stream "per buffer" metadata,
        # called "chunk data" in GenICam. Note that we have enabled delivery of the chunk data during the device
        # configuration above. GenICam standard provides means to access the chunk data through the same "node map"
        # as the device configuration features - and Harvester ensures that the metadata (if delivered with the buffer)
        # are connected to the node map while you are working with a Harvester's acquired buffer.
        # Note that the Visionary device intrinsics will stay the same for all buffers during the acquisition session,
        # but it is in general good practice to read the chunk data per buffer, because for other chunk parameters
        # or other device types they might actually change frame by frame.
        # Note that attempt to read the chunk data features when no buffer is fetched or when the chunk data was not
        # delivered will fail.

        # Read the important cameara intrinsics
        # (Refer to GenICam SFNC standard and PointCloudGeneration.pdf for detailed explanations)
        focal_length =  nm.ChunkScan3dFocalLength.value
        aspect_ratio = nm.ChunkScan3dAspectRatio.value
        princ_point_u = nm.ChunkScan3dPrincipalPointU.value
        princ_point_v = nm.ChunkScan3dPrincipalPointV.value
        # Read also the scale/offset to be applied on the "coordinate C" (acquired range value)
        nm.ChunkScan3dCoordinateSelector.value = 'CoordinateC'
        coord_c_scale = nm.ChunkScan3dCoordinateScale.value
        coord_c_offset = nm.ChunkScan3dCoordinateOffset.value
        # Read information about the range value used to flag an invalid pixel (carrying no useful measurement)
        invalid_flag_used = nm.ChunkScan3dInvalidDataFlag.value
        invalid_flag_value = nm.ChunkScan3dInvalidDataValue.value
        # For completeness, read also the 3D output mode defining the algorithm to build point cloud from the acquired
        # range ("depth") data - although we know that Visionary devices always use the "ProjectedC" mode as described in
        # PointCloudGeneration.pdf and illustrated in the example code below
        output_mode = nm.ChunkScan3dOutputMode.value
        # Print the values
        print("Received stream meta data ('chunk data') values:")
        print("\tOutput mode: {}".format(output_mode))
        print("\tFocal length (in pixels): {}".format(focal_length))
        print("\tAspect ratio: {}".format(aspect_ratio))
        print("\tPrincipal point [U,V]: [{}, {}]".format(princ_point_u, princ_point_v))
        print("\tCoordinate C (range) scale: {}".format(coord_c_scale))
        print("\tCoordinate C (range) offset: {}".format(coord_c_offset))
        print("\tInvalid data flag used: {}".format(invalid_flag_used))
        print("\tInvalid data flag value: {}".format(invalid_flag_value))

        # Let's store the two acquired components as images to the disk to demonstrate Harvester data access.
        # Harvester provides the acquired data as 1-dimensional numpy arrays. It recognizes the delivered pixel formats
        # and thus correctly determines the array dtype (single element data type). The number of elements in the array
        # is width*height*num_channels (num_channels is 3 for example in RGB image).
        # Further details as well as Harvester utilities related to pixel format processing is beyond scope of this example,
        # refer to Harvester documentation. We'll keep it simple here, relying on our knowledge of the pixel format
        # used by the camera for each component type.

        # The intensity component is known to be delivered in BGR8 format: 3 B-G-R channels, uint8 dtype.
        # Let's reshape the array as image.
        intensity_arr_bgr = cmp_intensity.data.reshape(cmp_intensity.height, cmp_intensity.width, 3)
        # Reverse the channels to get RGB format
        # (Depending on wheter further use of the data requires/benefits from a contiguous array, copy() might be needed or not
        # in the following line)
        intensity_arr_rgb = intensity_arr_bgr[...,::-1].copy()
        # And finally store it to disk (live stream visualization beyond scope of this example)
        intensity_image = Image.fromarray(intensity_arr_rgb, mode="RGB")
        intensity_image.save("intensity.png")

        # The range component is known to be delivered in Coord3D_C16 format: 1 channel, uint16 dtype.
        # Let's reshape the array as image.
        range_arr_uint16 = cmp_range.data.reshape(cmp_range.height, cmp_range.width)
        # Depending on the field of view, the actual measured range values can be rather small for the 16-bit range,
        # let's roughly scale them to full range and convert to uint8 dtype before saving (for human eye friendliness).
        # Note that this modified image is not intended for further processing, the only goal is to make it easily viewable.
        max_range_val = numpy.amax(range_arr_uint16)
        uint8_range_factor = max_range_val // 255 + 1
        range_arr_uint8 = (range_arr_uint16 // uint8_range_factor).astype(numpy.uint8)
        # And store it again to the disk
        range_image = Image.fromarray(range_arr_uint8, mode="L")
        range_image.save("range.png")

        # Finally, let's also demonstrate, how a point cloud with all three world coordinates could be computed from the acquired
        # range data. The algorithm is described in PointCloudGeneration.pdf and mostly relies on principles & intrinsic parameters
        # in GenICam SFNC standard - only the new ChunkScan3dOutputMode "ProjectedC" is currently still in ratification process.
        # The following lines aim just to demonstrate that algorithm in code - depending on your actual needs or use of the data
        # you might wish to adjust it for your needs. Other examples delivered with the camera might also demonstrate other tasks,
        # such as recording the acquired data for later reuse.

        # At this point we have the "range" and "intensity" data organized as multidimensional arrays organized same as the sensor
        # pixel grid (WxH): see range_arr_uint16 for "range", intensity_arr_bgr/rgb for "intensity" above.
        # To compute X/Y point cloud coordinates, we need column/row indices of each pixel - organized similar way.
        col, row = numpy.meshgrid(numpy.arange(cmp_range.width), numpy.arange(cmp_range.height))
        # The X/Y coordinate per-pixel multiplicators
        # (Note: these can be also precomputed just once within the acquisition loop, relying on the fact that the intrinsic
        # parameters will not change during the acquisition)
        xp = (col - princ_point_u) / focal_length
        yp = (row - princ_point_v) / (focal_length * aspect_ratio)
        # The actual coordinate values xc/yc/zc for each pixel are all computed from the measured range (depth) values
        # The distance units used by Visionary are millimeters (could also be "formally" queried from ChunkScan3dDistanceUnit)
        scaled_c = range_arr_uint16 * coord_c_scale + coord_c_offset
        xc = xp * scaled_c
        yc = yp * scaled_c
        zc = scaled_c
        # Remember that not all pixels might carry a valid measurement - the invalid ones might be marked using the corresponding
        # invalid data flag. The actual use and value of the flag was read together with the intrinsics from chunk data above.
        # Current version of the Visionary cameras always switch use of the flag ON (True) and the flag value is fixed at 0.
        # Zero delivered range pixels therefore denote invalid pixels - let's filter them out of the coordinate arrays.
        # The following lines to create the "filtered" xcf/ycf/zcf arrays anyway rely on the generically retrieved invalid
        # value parameters
        xcf = xc[not(invalid_flag_used) or range_arr_uint16 != invalid_flag_value]
        ycf = yc[not(invalid_flag_used) or range_arr_uint16 != invalid_flag_value]
        zcf = zc[not(invalid_flag_used) or range_arr_uint16 != invalid_flag_value]
        # If we were going to use the color component as point cloud overlay, you might need to filter it similarly
        bgrf = intensity_arr_bgr[not(invalid_flag_used) or range_arr_uint16 != invalid_flag_value]
        # Let's just print trivial statistics about the computed point cloud
        # and store the point cloud to a PLY file format for possible inspection
        print("Number of valid points: {}".format(zcf.size))
        # (note that after filtering above, bgrf is 2D array, where second dimension carries the BGR channels per-point)
        bgrf_channels = numpy.transpose(bgrf)
        rf = bgrf_channels[2]
        gf = bgrf_channels[1]
        bf = bgrf_channels[0]
        store_ply_file("pointcloud.ply", xcf, ycf, zcf, rf, gf, bf)

      # Stop the acquisition once finished processing the buffer
      ia.stop()

  # Report success
  return 0

###############################################################################################
# Helper functions
###############################################################################################

# Prerequisite/version checks, exit in case of a mismatch...
def validate_setup():
  # The example assumes a minimal Python version and an exact Harvesters package version.
  # Because Harvesters is currently under active development, switching to different version might require
  # changes to this script. Note also that Harvesters itself might imply additional restrictions
  # on supported Python version - please consult Harvesters documentation if required.
  MIN_PYTHON_VER = (3, 6)
  if sys.version_info < MIN_PYTHON_VER:
    sys.exit("Minimal required Python version for this script is {}.{}, your version is {}".format(*MIN_PYTHON_VER, sys.version))
  HARVESTERS_VER = '1.4.0'
  if harvesters.__version__ != HARVESTERS_VER:
    sys.exit("Exact required Harvesters version for this script is {}, your version is {}".format(HARVESTERS_VER, harvesters.__version__))

# Helper to get cti file path corresponding with the platform the script is running on
def get_cti_path():
  # The "python" directory with the example scripts (including this one) is expected to be a sibling of a "common" directory (shared
  # with other languages). The common directory among others contains "lib/cti" subdirectory further containing one subdirectory
  # for each platform supported by the SICK GenTL Producer for GigE Vision.
  # The actual filename of the GenTL Producer binary is always the same (SICKGigEVisionTL.cti).
  cti_platform_dir_name = get_cti_dir_name()
  script_dir = os.path.dirname(os.path.realpath(__file__))
  script_parent = os.path.dirname(script_dir)
  CTI_FILENAME = "SICKGigEVisionTL.cti"
  return os.path.join(script_parent, "common", "lib", "cti", cti_platform_dir_name, CTI_FILENAME)

# Helper to get cti file directory name corresponding with the platform the script is running on
def get_cti_dir_name():
  if platform.system() == "Windows":
    return "windows_x64"
  if platform.system() == "Linux" and platform.machine() == "x86_64":
    return "linux_x64"
  if platform.system() == "Linux" and platform.machine() == "aarch64":
    return "linux_aarch64"

  # Not one of our recognized platforms, cti file not available
  sys.exit("GenTL Producer not available on this platform")

# Helper to force a suitable IP address to the camera/device which is currently not accessible due to IP subnet mismatch
def force_suitable_ip_address(device_info):
  print("Attempting to force suitable IP address into the (currently unreachable) device {}".format(device_info.display_name))
  # The SICK GenTL Producer allows to propose and force a suitable temporary IP address to the device
  # through features of the GenTL "interface module", where the device was discovered (ie. device's parent module).
  itf_node_map = device_info.parent.node_map
  # If there are possibly multiple devices discovered, navigate first to our device through the DeviceSelector feature
  device_id = device_info.id_
  for i in range(itf_node_map.DeviceSelector.max + 1):
    itf_node_map.DeviceSelector.value = i
    # Check if the DeviceID corresponding to currently selected device in the nodemap is the device we are going to adjust
    if device_id == itf_node_map.DeviceID.value:
      # This is our device, execute the GevDeviceProposeIP command that will search for a suitable IP address
      itf_node_map.GevDeviceProposeIP.execute()
      # The proposed IP & subnet mask will be filled in the corresponding features used for the actual "force" command
      proposed_ip = itf_node_map.GevDeviceForceIPAddress.to_string()
      proposed_subnet = itf_node_map.GevDeviceForceSubnetMask.to_string()
      print("\tThe proposed IP address is {}, subnet mask {}, forcing it into the device".format(proposed_ip, proposed_subnet))
      # Finally invoke the "force" command that will attempt to use the proposed IP
      # IMPORTANT: the forced IP address is just a temporary one and will be lost after the next device power cycle
      itf_node_map.GevDeviceForceIP.execute()
      # The "force IP" command may take a while, therefore we need to wait for its completion
      while not itf_node_map.GevDeviceForceIP.is_done():
        time.sleep(1)
      print("\tThe force-ip procedure completed")

# Helper to write the point cloud to a PLY file using the plyfile package, assuming vertices (per-point/pixel) only
# are stored, containing coordinate and RGB color information
def store_ply_file(file, x, y, z, r, g, b):
  # The input arrays are expected to be the same length
  if not(x.size == y.size == z.size == r.size == g.size == b.size):
    print("\tFailed to store the point cloud to PLY file - the input arrays have different size")
    return

  # Copy the individual input arrays into the structure expected by PlyData (study plyfile package docu for more advanced use)
  num_vertices = x.size
  vertices = numpy.empty(num_vertices, dtype=[('x', 'f4'), ('y', 'f4'), ('z', 'f4'), ('red', 'u1'), ('green', 'u1'), ('blue', 'u1')])
  vertices['x'] = x.astype('f4')
  vertices['y'] = y.astype('f4')
  vertices['z'] = z.astype('f4')
  vertices['red'] = r.astype('u1')
  vertices['green'] = g.astype('u1')
  vertices['blue'] = b.astype('u1')

  # Write the output
  ply = PlyData([PlyElement.describe(vertices, 'vertex')], text=False)
  ply.write(file)

###############################################################################################
# Tutorial code invocation
###############################################################################################
if __name__ == '__main__':
  # Specific exception handling skipped in this example to keep the code simple, real application should add exception
  # handling close to the possible exception source depending on the actual application logic
  try:
    sys.exit(main())
  except Exception: # (sys.exit() itself will raise BaseException and will not interfere with this handler)
    print("#############")
    print("ERROR: an exception was raised within the example code. Re-raising to display context, this example does not provide specific exception handling.")
    print("#############")
    raise


