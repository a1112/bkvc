###############################################################################################
# ip_config.py: Script to configure temporary and/or persistent IP address of a device
#
# Designed for use with Python 3.x and harvesters 1.4.0 (please use exactly this version, since 
# Harvesters API might be slightly changing between versions (pip install harvesters==1.4.0).
#
# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense
#
###############################################################################################

# Intended as a tool to configure IP settings of a GigE Vision camera.
#
# The temporary settings ("force" actions) are needed in situations when the current IP address 
# of the device does not match the subnet of the network card of the host system communicating with the camera.
# In such case the GigE Vision "force IP" mechanism can be used to bring the camera into the correct
# subnet. Can be used only if the camera is not open by any application.
# The assigned temporary address will be lost on next power cycle.
#
# The persistent settings ("persistent" actions), the requested configuration is stored in the non-volatile
# memory of the device, remembering the settings across power cycles and applying them during the IP configuration
# procedure opon each subsequent camera boot or cable re-connect. To be able to apply the persistent settings,
# it is necessary to establish connection to the camera - therefore, if the camera is currently misconfigured
# with a wrong subnet, suitable temporary settings need to be forced first (using a "force" action of this script).

from harvesters.core import Harvester
import harvesters
from genicam.gentl import DEVICE_ACCESS_STATUS_LIST
import argparse
import sys
import platform
import os
import time
import ipaddress

def getH():
    validate_setup()
    with Harvester() as h:
        cti = get_cti_path()
        h.add_file(cti, check_existence=True, check_validity=True)
        h.update()
        return h
# Main script code
def main():
  # Parse the arguments
  args = parse_arguments()

  # All of the actions require access to Harvester using the SICK GenTL Producer with freshly discovered device list
  with Harvester() as h:
    cti = get_cti_path()
    h.add_file(cti, check_existence=True, check_validity=True)
    h.update()

    # Distribute the work based on the selected action
    if args.action == "list":
      list_devices(h)
    elif args.action == "force_ip":
      force_ip(h, device_sn=args.device_sn, automatic=False, ip=args.ip, subnet=args.subnet, gateway=args.gateway)
    elif args.action == "force_auto":
      force_ip(h, device_sn=args.device_sn, automatic=True)
    elif args.action == "force_restart":
      force_ip(h, device_sn=args.device_sn, automatic=False, ip="0.0.0.0", subnet="0.0.0.0", gateway="0.0.0.0")
    elif args.action == "persistent_ip":
      persist_settings(h, device_sn=args.device_sn, persistent_ip=True, dhcp=False, ip=args.ip, subnet=args.subnet, gateway=args.gateway)
    elif args.action == "persistent_current":
      persist_settings(h, device_sn=args.device_sn, persistent_ip=True, dhcp=False, ip=None)
    elif args.action == "persistent_dhcp":
      persist_settings(h, device_sn=args.device_sn, persistent_ip=False, dhcp=True)
    elif args.action == "persistent_lla":
      persist_settings(h, device_sn=args.device_sn, persistent_ip=False, dhcp=False)
    else:
      sys.exit("ERROR: unexpected script action requested")

# Helper defininig the script command line interface and parsing the arguments, returning result to the caller
def parse_arguments():
  parser = argparse.ArgumentParser(description="Script to GigE Vision device IP configuration (current and/or persistent IP settings)")

  # Split the user interface using (madatory) subparsers representing the individual supported actions
  subparsers = parser.add_subparsers(dest="action", help="Actions supported by the script (each with own specific arguments and help text)", required=True)

  # Some groups of parameters are shared among different actions/subparsers - instead of complex argparse constructs
  # with "parent-parsers" which seem to be potentially problematic, let's add them explicitly to each subparser using nested functions
  def add_device_select_args(subparser):
    subparser.add_argument("-d", "--device_sn", required=True, help="Serial number of the device to configure")
  def add_ip_address_args(subparser):
    subparser.add_argument("-i", "--ip", required=True, help="Desired IP address")
    subparser.add_argument("-s", "--subnet", required=True, help="Desired subnet mask")
    subparser.add_argument("-g", "--gateway", default="0.0.0.0", help="Desired default gateway (zero if not provided)")

  # The individual subparsers corresponding to supported actions follow, including their argument definitions
  # ... the list option does not require additional arguments
  list_parser = subparsers.add_parser("list", description="Lists all devices currently visible in the system")

  # ... the force_ip option requires argument(s) for device selection and IP specification
  force_ip_parser = subparsers.add_parser("force_ip", description="Forces the specified temporary IP/subnet settings to the selected device (which must not be in use during the operation)")
  add_device_select_args(force_ip_parser)
  add_ip_address_args(force_ip_parser)

  # ... the force_auto option requires argument(s) for device selection
  force_auto_parser = subparsers.add_parser("force_auto", description="Forces a suitable automatic temporary IP/subnet settings to the selected device (which must not be in use during the operation)")
  add_device_select_args(force_auto_parser)

  # ... the force_restart option requires argument(s) for device selection
  force_restart_parser = subparsers.add_parser("force_restart", description="Forces restart of the IP configuration procedure of the selected device based on its current persistent IP configuration (the device must not be in use during the operation)")
  add_device_select_args(force_restart_parser)

  # ... the persistent_ip option requires argument(s) for device selection and IP specification
  persistent_ip_parser = subparsers.add_parser("persistent_ip", description="Configures the selected device to use the specified IP/subnet settings upon following boot procedures (the device must be in ready-to-open state)")
  add_device_select_args(persistent_ip_parser)
  add_ip_address_args(persistent_ip_parser)

  # ... the persistent_current option requires argument(s) for device selection
  persistent_current_parser = subparsers.add_parser("persistent_current", description="Configures the selected device to use its current IP/subnet settings upon following boot procedures (the device must be in ready-to-open state)")
  add_device_select_args(persistent_current_parser)

  # ... the persistent_dhcp option requires argument(s) for device selection
  persistent_dhcp_parser = subparsers.add_parser("persistent_dhcp", description="Configures the selected device to use DHCP protocol (with LLA fallback) to obtain IP/subnet settings upon following boot procedures (the device must be in ready-to-open state)")
  add_device_select_args(persistent_dhcp_parser)

  # ... the persistent_lla option requires argument(s) for device selection
  persistent_lla_parser = subparsers.add_parser("persistent_lla", description="Configures the selected device to use LLA protocol to obtain IP/subnet settings upon following boot procedures (the device must be in ready-to-open state)")
  add_device_select_args(persistent_lla_parser)

  # Return the parsed results to the caller
  return parser.parse_args()

# Helper to list information about currently discovered cameras
def list_devices(h):
  print("Listing currently discovered devices, device count: {}".format(len(h.device_info_list)))

  for device_info in h.device_info_list:
    # The elementary infos are available directly from the GenTL DeviceInfo object
    print(device_info.display_name)
    print("\tVendor: {}".format(device_info.vendor))
    print("\tModel: {}".format(device_info.model))
    print("\tSerial number: {} (identifies the device in other actions of this script)".format(device_info.serial_number))
    print("\tGenTL device ID: {}".format(device_info.id_))
    
    # The GigE Vision specific information has to be queried from the GenTL Producer itself,
    # identify the current device in the nodemap of the interface which discovered the device
    itf_node_map = device_info.parent.node_map
    for i in range(itf_node_map.DeviceSelector.max + 1):
      itf_node_map.DeviceSelector.value = i
      if device_info.id_ == itf_node_map.DeviceID.value:
        # This is our device, print the GigE Vision specific infos and break ot of the loop
        print("\tMAC address: {}".format(itf_node_map.GevDeviceMACAddress.to_string()))
        print("\tIP address: {}".format(itf_node_map.GevDeviceIPAddress.to_string()))
        print("\tSubnet mask: {}".format(itf_node_map.GevDeviceSubnetMask.to_string()))
        print("\tDefault gateway: {}".format(itf_node_map.GevDeviceGateway.to_string()))
        print("\tDiscovered on interface: {}/{}".format(itf_node_map.GevInterfaceSubnetIPAddress.to_string(), itf_node_map.GevInterfaceSubnetMask.to_string()))
        break

    # If the device is accessible, try to open it and print also the persistent IP settings overview
    if device_info.access_status == DEVICE_ACCESS_STATUS_LIST.DEVICE_ACCESS_STATUS_READWRITE:
      try:
        with h.create(device_info) as ia:
          # Assuming we are working with a Visionary device, having the features for persistent IP configuration in its nodemap
          nm = ia.remote_device.node_map
          print("\tEnabled IP configuration protocols: persistent IP - {}, DHCP - {}, LLA - always True".format(nm.GevCurrentIPConfigurationPersistentIP.value, nm.GevCurrentIPConfigurationDHCP.value))
          if nm.GevCurrentIPConfigurationPersistentIP.value:
            print("\tPersistent IP address/subnet/gateway: {}/{}/{}".format(nm.GevPersistentIPAddress.to_string(), nm.GevPersistentSubnetMask.to_string(), nm.GevPersistentDefaultGateway.to_string()))
      except Exception:
        print("(failed to query the persistent IP settings of the device")
    else:
      print("\t(persistent IP settings can only be reported for fully accessible devices)")

    # Finally identify the current access status and report it including additional hints
    def get_access_status_info(access_status):
      if access_status == DEVICE_ACCESS_STATUS_LIST.DEVICE_ACCESS_STATUS_READWRITE:
        return "READWRITE: full access, the device is ready to connect and configure persistent IP settings"
      elif access_status == DEVICE_ACCESS_STATUS_LIST.DEVICE_ACCESS_STATUS_OPEN_READWRITE:
        return "OPEN_READWRITE: already open by this instance, unexpected"
      elif access_status == DEVICE_ACCESS_STATUS_LIST.DEVICE_ACCESS_STATUS_BUSY:
        return "BUSY: already open by another application/host, currently not accessible"
      elif access_status == DEVICE_ACCESS_STATUS_LIST.DEVICE_ACCESS_STATUS_NOACCESS:
        return "NOACCESS: misconfigured (wrong subnet), suitable temporary IP address has to be forced to be able to control the device"
      else:
        return "UNKNOWN/unexpected: unexpected access status reported"
    print("\tAccess status: {}".format(get_access_status_info(device_info.access_status)))

# Helper to force temporary IP configuration into the device
def force_ip(h, device_sn, automatic, ip=None, subnet=None, gateway=None):
  print("Forcing temporary IP configuraton to the device with serial number:: {}".format(device_sn))

  for device_info in h.device_info_list:
    if device_info.serial_number == device_sn:
      # Found the desired device, break out and continue after the loop to avoid deep nesting
      break
  else:
    sys.exit("The required device (serial number {}) was not found".format(device_sn))

  # The force IP requests will be ignored by the device if it is currently open by some other applicaton.
  # Let's first verify it is not the case (BUSY access mode), otherwise report the problem clearly
  # rather than observing strange failures later.
  if device_info.access_status == DEVICE_ACCESS_STATUS_LIST.DEVICE_ACCESS_STATUS_BUSY:
    sys.exit("The required device is currently open by another application (having BUSY access status), the force IP requests would be ignored.")

  # Here device_info points to the desired device.
  # To be able to force new IP configuraton to using the GenTL Producer, we need to identify the device
  # in the nodemap of the interface which discovered it
  itf_node_map = device_info.parent.node_map
  # If there are possibly multiple devices discovered, navigate first to our device through the DeviceSelector feature
  for i in range(itf_node_map.DeviceSelector.max + 1):
    itf_node_map.DeviceSelector.value = i
    if device_info.id_ == itf_node_map.DeviceID.value:
      # This is our device, break out and continue after the loop to avoid deep nesting
      break
  else:
    sys.exit("Failed to identify the device within GenTL Producer nodemap (unexpected failure)")

  # Here our device is selected in interface nodemap DeviceSelector, prepare the ForceIP parameters
  # depending if automatic (GenTL Producer proposed) or explicit mode is used
  if automatic:
    itf_node_map.GevDeviceProposeIP.execute()
  else:
    # IP and subnet parameters are mandatory in non-automatic mode
    validate_ip_settings(ip, subnet, gateway, zero_ip_valid=True)
    itf_node_map.GevDeviceForceIPAddress.from_string(ip)
    itf_node_map.GevDeviceForceSubnetMask.from_string(subnet)
    # The gateway is optional (zero used as default fallback)
    if gateway is None:
      itf_node_map.GevDeviceForceGateway.value = 0
    else:
      itf_node_map.GevDeviceForceGateway.from_string(gateway)

  # The desired configuration is written now (either way) and ready to be applied
  # Prococol-wise the special case with IP==0 is the same as a "regular" FORCEIP, but the operation which happens 
  # on device side is different, therefore considering this when giving script feedback to the user
  ip_restart_request = itf_node_map.GevDeviceForceIPAddress.value == 0
  if ip_restart_request:
    print("Going to force the device to restart its IP configuration procedure")
  else:
    print("Going to force following temporary configuration:")
    print("\tIP address: {}".format(itf_node_map.GevDeviceForceIPAddress.to_string()))
    print("\tSubnet mask: {}".format(itf_node_map.GevDeviceForceSubnetMask.to_string()))
    print("\tDefault gateway: {}".format(itf_node_map.GevDeviceForceGateway.to_string()))

  # Workaround: some versions of the GenTL Producer suffered a bug, treating the default force-ip procedure timeout
  # with wrong units - reporting the default value and limits in milliseconds instead of microseconds, resulting
  # in too short wait time when checking the device response and evaluating the operation success.
  # Until we are sure that all users have fixed version of the producer, let's override the timeout with value of 3s,
  # sufficient for Visionary implementation (set the value without range check due to the same problem with limits).
  itf_node_map.GevDeviceForceIPTimeout.set_value(3000000, False);

  # The actual command, followed again by mode specific info to the user
  itf_node_map.GevDeviceForceIP.execute()
  if ip_restart_request:
    # In the IP-restart case we cannot rely on the feedback/acknowledge - let the user to discover again later
    print("The operation can take several seconds, please discover the devices again after a moment (list command)")
  else:
    # The "force IP" command may take a while, therefore we need to wait for its completion
    while not itf_node_map.GevDeviceForceIP.is_done():
      time.sleep(1)
    if not itf_node_map.GevDeviceLastForceIPSuccess.value:
      print("The operation status not reported as successful (might still be OK if configuring the device to foreign network)")
    print("The temporary IP configuration procedure finished, you can list the devices again")

def persist_settings(h, device_sn, persistent_ip, dhcp, ip=None, subnet=None, gateway=None):
  print("Writing persistent IP configuraton to the device with serial number:: {}".format(device_sn))

  # To write the settings, we have to open the device, let's first verify we have READWRITE access
  # to it for better error reporting than if we just observe the connection fail
  for device_info in h.device_info_list:
    if device_info.serial_number == device_sn:
      # Our device, check the required access mode
      if device_info.access_status != DEVICE_ACCESS_STATUS_LIST.DEVICE_ACCESS_STATUS_READWRITE:
        sys.exit("The required device does not currently have READWRITE access status and cannot thus be configured (device list comman can provide further details")
      break
  else:
    sys.exit("The required device (serial number {}) was not found".format(device_sn))

  # Seems the device is ready to open and configure - get access to it over the specified serial number
  with h.create({'serial_number': device_sn, 'access_status': DEVICE_ACCESS_STATUS_LIST.DEVICE_ACCESS_STATUS_READWRITE}) as ia:
    # Assuming we are working with a Visionary device, the features for persistent IP configuration should be present
    # in the "remote device" nodemap (except of early firmware versions). 
    # When using the script with non-SICK devices, it might not always be the case...
    nm = ia.remote_device.node_map
    # First configure the protocol flags deciding how the device should be configured at startup
    nm.GevCurrentIPConfigurationPersistentIP.value = persistent_ip
    nm.GevCurrentIPConfigurationDHCP.value = dhcp
    # If the persistent IP protocol is enabled, write also its parameters (otherwise they will not be used)
    if persistent_ip:
      # Just note that argument ip==None by convention means the current active camera settings should be used
      if (ip is not None) and (subnet is not None):
        validate_ip_settings(ip, subnet, gateway, zero_ip_valid=False)
        nm.GevPersistentIPAddress.from_string(ip)
        nm.GevPersistentSubnetMask.from_string(subnet)
        # The gateway is optional (zero used as default fallback)
        if gateway is None:
          nm.GevPersistentDefaultGateway.value = 0
        else:
          nm.GevPersistentDefaultGateway.from_string(gateway)
      else:
        nm.GevPersistentIPAddress.value = nm.GevCurrentIPAddress.value 
        nm.GevPersistentSubnetMask.value = nm.GevCurrentSubnetMask.value
        nm.GevPersistentDefaultGateway.value = nm.GevCurrentDefaultGateway.value
    print("Wrote following persistent IP configuration settings:")
    print("\tPersistent IP protocol active: {}".format(nm.GevCurrentIPConfigurationPersistentIP.value))
    print("\tDHCP protocol active: {}".format(nm.GevCurrentIPConfigurationDHCP.value))
    print("\tLLA protocol active: always active")
    if persistent_ip:
      print("\tPersistent IP address: {}".format(nm.GevPersistentIPAddress.to_string()))
      print("\tPersistent subnet mask: {}".format(nm.GevPersistentSubnetMask.to_string()))
      print("\tPersistent default gateway: {}".format(nm.GevPersistentDefaultGateway.to_string()))

# Helper to validate the IP/subnet/gateway strings passed from the user to help catch obvious
# mistakes/typos early and prefer failing early with helpful message
def validate_ip_settings(ip, subnet, gateway, zero_ip_valid):
  # IP address must be always specified, let's just instantiate it and observe any error
  try:
    ipv4_ip = ipaddress.IPv4Address(ip)
  except ValueError:
    sys.exit("Please revise input parameters - this is not a valid IP address: {}".format(ip))

  # The same with subnet mask
  try:
    ipv4_subnet = ipaddress.IPv4Address(subnet)
  except ValueError:
    sys.exit("Please revise input parameters - this is not a valid subnet mask address: {}".format(subnet))

  # Gateway is optional, but once specified, it needs to be valid
  if gateway is not None:
    # Start with elementary verification same as for the other two strings
    try:
      ipv4_gateway = ipaddress.IPv4Address(gateway)
    except ValueError:
      sys.exit("Please revise input parameters - this is not a valid gateway address: {}".format(gateway))

  # Try to instantiate the interface address from it ("ip/subnet" format) - this will validate the combination
  # and in particular whether the subnet mask string is usable as subnet mask
  try:
    interface_string = "{}/{}".format(ip, subnet)
    ipv4_interface = ipaddress.IPv4Interface(interface_string)
  except ValueError:
    sys.exit("Please revise input parameters - this is not a valid IP/subnet combination: {}".format(interface_string))

  # In specific scenario (force IP), zero IP address is a valid input
  if int(ipv4_ip) == 0:
    if zero_ip_valid:
      # Valid use of zero IP, no further tests required in this case
      return
    else:
      sys.exit("Please revise input parameters - zero is not a valid IP address in given context: {}".format(ip))

  # With exception of the special-zero-value above, the IP address should never be network or broadcast address
  # in its subnet
  ipv4_network = ipv4_interface.network
  if ipv4_ip == ipv4_network.broadcast_address:
    sys.exit("Please revise input parameters - the IP address {} is a broadcast address given the specified subnet mask {}".format(ip, subnet))
  if ipv4_ip == ipv4_network.network_address:
    sys.exit("Please revise input parameters - the IP address {} is a network address given the specified subnet mask {}".format(ip, subnet))

  # Additional tests if non-zero gateway was specified
  if gateway is not None and int(ipv4_gateway) != 0:
    # Verify that it belongs to the same network as the IP address itself
    if not ipv4_gateway in ipv4_network:
        sys.exit("Please revise input parameters - the gateway address {} does not belong to network {}".format(gateway, interface_string))
    
    # Refuse also the network/broadcast addresses same as for the IP above
    if ipv4_gateway == ipv4_network.broadcast_address:
      sys.exit("Please revise input parameters - the gateway address {} is a broadcast address given the specified subnet mask {}".format(gateway, subnet))
    if ipv4_gateway == ipv4_network.network_address:
      sys.exit("Please revise input parameters - the gateway address {} is a network address given the specified subnet mask {}".format(gateway, subnet))


# Helper to get cti file path corresponding with the platform the script is running on
def get_cti_path():
  CTI_FILENAME = "SICKGigEVisionTL.cti"
  cti_platform_dir_name = get_cti_dir_name()

  if getattr(sys, 'frozen', False):
    # Running inside a PyInstaller bundle
    script_dir = sys._MEIPASS
  else:
    # Running in normal Python environment
    pyfile_dir = os.path.dirname(os.path.realpath(__file__))
    script_dir = os.path.dirname(pyfile_dir)

  return os.path.join(script_dir, "common", "lib", "cti", cti_platform_dir_name, CTI_FILENAME)

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

# Prerequisite/version checks, exit in case of a mismatch...
def validate_setup():
  # The script assumes an exact Harvesters package version.
  # Because Harvesters is currently under active development, switching to different version might require
  # changes to this script.
  HARVESTERS_VER = '1.4.0'
  if harvesters.__version__ != HARVESTERS_VER:
    sys.exit("Exact required Harvesters version for this script is {}, your version is {}".format(HARVESTERS_VER, harvesters.__version__))

# Script entry point
if __name__ == '__main__':
  # Catch any remaining exceptions which might be possibly related to the GenICam feature access (e.g. with an invalid input)
  try:
    sys.exit(main())
  except Exception as err: # (sys.exit() itself will raise BaseException and will not interfere with this handler)
    print("ERROR: an exception was raised while executing the script, please revise the input parameter correctness ({})".format(err))
    # (to further debug the exception, re-raising it here might help to get its context if desired: uncomment following line)
    # raise
#