# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

from genicam.genapi import NodeMap, is_available
from logging import warning
import numpy as np


def apply_param(nodeMapObj, paramName, paramValue):
    print("设置参数"+paramName+"为"+str(paramValue))
    """Helper function to apply paramName/paramValue pairs to a given node_map (from Harvesters ImageAcquirer).
    It is expected, that paramValues have types like they were read via toml.
    """
    if not isinstance(nodeMapObj, NodeMap):
        raise TypeError(f"nodeMapObj argument must have type 'NodeMap' but is: {type(nodeMapObj)}")
    if not isinstance(paramName, str):
        raise TypeError(f"paramName argument must have type 'str' but is: {type(paramName)}")
    if not isinstance(paramValue, (str, int, bool, float)):
        raise TypeError(f"paramValue argument supported types 'str, int, bool' but is: {type(paramValue)}")

    if isinstance(paramValue, str):
        command = "nodeMapObj.{}.value = '{}'".format(paramName, paramValue)
    elif isinstance(paramValue, (float)):
        # The device XML of Visionaries work with float32, passing pythons native
        # float64 here would lead to float comparison errors
        command = "nodeMapObj.{}.value = {}".format(paramName, np.float32(paramValue))
    elif isinstance(paramValue, (int, bool)):
        command = "nodeMapObj.{}.value = {}".format(paramName, paramValue)
    else:
        warning(f"Failed to apply param: {paramName} = {paramValue}")
    try:
        exec(command)
    except Exception as err:
        raise AttributeError(f"Failed to apply node/value {paramName} = {paramValue}") from err


def set_components(nodeMapObj, selectedComponents):
    """Helper function enable only the components from the list selectedComponents, disable anything else
  """
    # if not isinstance(nodeMapObj, NodeMap):
    #     raise TypeError(f"nodeMapObj argument must have type 'NodeMap' but is: {type(nodeMapObj)}")
    # if not isinstance(selectedComponents, list):
    #     raise TypeError(f"selectedComponents argument must have list-type but is: {type(selectedComponents)}")
    # if len(selectedComponents) < 1:
    #     raise RuntimeError(f"selectedComponents argument must have min length of 1 but has {len(selectedComponents)}")
    for component in selectedComponents:
        # if not isinstance(component, str):
        #     raise TypeError(f"All components in selectedComponents must be of type str but found: {type(component)}")
        if not is_available(nodeMapObj.ComponentSelector.get_entry_by_name(component)):
            raise RuntimeError(f"Component \'{component}\' not available on this device")

    selectedComponents = set(selectedComponents)
    for ele in nodeMapObj.ComponentSelector.entries:
        print(ele)
        if is_available(ele):
          print(nodeMapObj.ComponentEnable.value)
          nodeMapObj.ComponentSelector.value = ele.symbolic
          if ele.symbolic in selectedComponents:
              if not nodeMapObj.ComponentEnable.value:
                  nodeMapObj.ComponentEnable.value = True
