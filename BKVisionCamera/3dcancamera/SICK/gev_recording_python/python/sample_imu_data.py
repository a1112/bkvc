###############################################################################################
# sample_imu_data.py: sample script demonstrating how to access IMU data from SICK 
# Visionary cameras with GigE Vision interface over Python.
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
# - This file assumes you are already familiar with: tutorial_harvesters.py
# - This script demonstrate capturing one frame and extract the IMU data

from harvesters.core import Harvester
from genicam.gentl import DEVICE_ACCESS_STATUS_LIST
# Other imports required in the sample script
import sys
import platform
import os
import time
from lib.IMU import IMUParser
from lib.utils import init_harvester

###############################################################################################
# Main example code
###############################################################################################
def main():
  # If you run in any issues communicating with the camera, please revisit tutorial_harvesters.py
  # and make sure you can run it with out issues

  try:
    # ---------------------------------------------
    # | Initialization and locating of the device |
    # ---------------------------------------------
    h = init_harvester()
    if len(h.device_info_list) == 0:
      sys.exit("No GigE Vision devices discovered in this system")
    print("Discovered {} device(s), going to use the first entry in the test:".format(len(h.device_info_list)))
    for device_info in h.device_info_list:
      print("\t{}".format(device_info.display_name))
    # Expected, that the first device on idx 0 is the camera we want to use, adjust this if needed
    if h.device_info_list[0].access_status == DEVICE_ACCESS_STATUS_LIST.DEVICE_ACCESS_STATUS_NOACCESS:
      sys.exit("No access to this device possible. Please check/review the ip settings of this device and retry.")

    # ----------------------------------
    # | Configuration and capture data |
    # ----------------------------------
    with h.create() as ia:
      nm = ia.remote_device.node_map
      #  usually useful to increase the default number of buffers Harvester
      ia.num_buffers = 10

      # Enable basic IMU data component
      nm.ComponentSelector.value = 'ImuBasic'
      nm.ComponentEnable.value = True

      # after capturing one frame, the imu data samples will be appended to this list
      imu_data = []
      
      ia.start()
      with ia.fetch(timeout=2.0) as buffer:
        print("Acquired frame ID {} with timestamp {} ns".format(
            buffer.frame_id, buffer.timestamp_ns))
        # Unfortunately, current version of Harvester does not support component type identification, therefore we have to "recognize them"
        # (the component) through the pixel format of their data: ImuBasic is delivered as 'Mono8' component
        for i, cmp in enumerate(buffer.payload.components):
          if cmp.data_format == 'Mono8':
            # ImuBasic contains max. the last 100 IMU data samples. For higher frame rates, there
            # could be less samples delivered. Depending on the actual frame-to-frame time, the 
            # number of delivered IMU data samples might also vary for each frame!
            num_of_samples = cmp.delivered_image_height
            print("\tExpected number of IMU data samples: {}".format(num_of_samples))
            
            # Parse IMU data samples one-by-one from the component
            parser = IMUParser(cmp.data.tobytes())
            while True:
              current_imu_data_sample = parser.getNext()
              if current_imu_data_sample == None:
                break
              imu_data.append(current_imu_data_sample)
            print("\tExtracted IMU data samples from the buffer: {}".format(len(imu_data)))
      ia.stop()
      
      # -----------------------------------------------
      # | Printing the IMU data samples in CSV format |
      # -----------------------------------------------
      print('"id", "timestamp", "acc_x", "acc_y", "acc_z", "ang_x", "ang_y", "ang_z"')
      for i, sample in enumerate(imu_data):
        print("{:3d}, {}, {:9.6f}, {:9.6f}, {:9.6f}, {:9.6f}, {:9.6f}, {:9.6f} ".format(i, sample.timestamp,
          sample.acceleration[0], sample.acceleration[1], sample.acceleration[2],
          sample.angular_velocity[0], sample.angular_velocity[1], sample.angular_velocity[2])     
        )

  finally:
    h.reset()

  # Report success
  return 0

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


