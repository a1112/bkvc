#!/usr/bin/env python3
# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

"""Recorder for multiple (Visionary) GigE cameras"""

from argparse import Action, ArgumentParser, RawDescriptionHelpFormatter as rdhf
from logging import basicConfig, info, INFO, error
from os import environ as env
from lib.utils import *
from lib.pickle_harvester import Writer
from sys import exit
from time import time


DEVICE_ACCESS_STATUS_READWRITE = 1 # GenICam/GenTL dfinition

class ListArgs(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        args = list(map(int, values.split(',')))
        if len(args) != 3:
            raise ArgumentTypeError("Must define 3 comma-separated values: "
                                    "<start>,<end>,<step>")
        args = range(args[0], args[1]+1, args[2])
        if args.start > args.stop:
            raise AttributeError("<start> must be smaller than <end>")
        setattr(namespace, self.dest, args)


def select_devices(device_list, config):
  serials = config['cameras']['serial']
  device_ids = list()
  info("Available cameras:")
  for idx, device in enumerate(device_list):
    acc_stat = device.access_status
    if acc_stat == DEVICE_ACCESS_STATUS_READWRITE and device.serial_number in serials:
        device_ids.append(idx)
        info(f"  {device.display_name} ({device.serial_number})")
  return device_ids
  

def setup_camera_objects(harvester, device_ids):
    cameras = list()
    info("Cameras to be used")
    for idx in device_ids:
        device = harvester.device_info_list[idx]
        info(f"  {device.display_name} ({device.serial_number})")
        cameras.append(setup_camera_object(harvester, idx))
    return cameras


def main(args):
    harvester = None
    cameras = None
    try:
        config = parse_config(args.config)
        if 'env' in config:
          for key, value in config['env'].items():
            env[key] = str(value)
        harvester = init_harvester()
        device_ids = select_devices(harvester.device_info_list, config)
        cameras = setup_camera_objects(harvester, device_ids)
        print(cameras)
        for cam in cameras:
          try:
            config_camera(cam, config)
          except Exception as err:
            print("Error while configuring the camera, please double check correctness of the config file ({})".format(err))
            raise

        info("Open storage files")
        for cam in cameras:
          record_ident = cam['name']
          if args.auto_bracket:
              record_ident += "_AutoBracket"
          cam['writer'] = Writer(cam['name'])
        if len(cameras) < 1:
          raise RuntimeError("No cameras in the list - please double check whether the config file contains valid serial numbers identifying the cameras to use")

        t_start = time()
        args.num_frames = 10
        maybe_capture_secs(cameras, config, t_start, args.duration)
        maybe_capture_num_frames(cameras, config, args.num_frames)
        maybe_capture_auto_bracket(cameras, args.auto_bracket)
        elapsed = time() - t_start
        
        for cam in cameras:
            info(f"{cam['name']} received {cam['frameCount']} frames ({cam['frameCount']/elapsed:.1f} Hz), recorded {cam['recordedCount']} frames")
            cam['writer'] = None
            cam['nm'] = None
            cam['ia'].stop()
    except:
        raise
    finally:
        if cameras:
            for cam in cameras:
                cam['ia'].destroy()
        if harvester:
            harvester.reset()


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__, formatter_class=rdhf)
    parser.add_argument('-c', '--config',default="sample.cfg",
                        help='Defines which configuration file to be used')
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-a', '--auto_bracket', required=False, action=ListArgs,
                       help='Run Auto Bracket: <start>,<end>,<step> [us] increasing the exposure time. '
                       'Example: "-a 100,4000,50" from 100us up to 4000us with 50us steps')
    group.add_argument('-d', '--duration', type=float, required=False,
                       help='Duration of the recording [s]. '
                       'Example: "-d 2.5" record for 2.5 seconds')
    group.add_argument('-n', '--num_frames', type=int, required=False,
                       help='Number of frames to being recorded. '
                       'Example: "-n 100" will record exactly 100 frames')
    basicConfig(format="%(levelname)s: %(message)s", level=INFO)
    # Catch any remaining exceptions which might be possibly related to the GenICam feature access (e.g. with an invalid input)
    try:
      exit(main(parser.parse_args()))
    except Exception as err: # (sys.exit() itself will raise BaseException and will not interfere with this handler)
      raise
      print("ERROR: an exception was raised while executing the script: {}".format(err))
      # (to further debug the exception, re-raising it here might help to get its context if desired: uncomment following line)
      # raise
