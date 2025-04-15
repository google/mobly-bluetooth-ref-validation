# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Example Mobly controller module."""

from __future__ import annotations

from collections.abc import Sequence
import datetime
import enum
import logging
import os
import pathlib
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Union

import dacite
from mobly import logger as mobly_logger
from mobly import runtime_test_info
from mobly import signals
from mobly import utils as mobly_utils

from testing.mobly.platforms.bluetooth import example_device_config
from testing.mobly.platforms.bluetooth import bluetooth_reference_device_base


# This is used in the config file located in the test lab's home directory.
MOBLY_CONTROLLER_CONFIG_NAME = 'BtBoardDevice'

# Error messages used in this module.
_DEVICE_CONFIG_ERROR_MSG = (
    'Failed to parse device configs when creating devices: '
)

class DeviceError(signals.ControllerError):
  """Raised for errors related to the BtBoardDevice controller module."""


def create(configs: Sequence[dict[str, Any]]) -> List[BtBoardDevice]:
  """Creates BtBoardDevice controller objects.

  Mobly uses this to instantiate BtBoardDevice controller objects from configs.
  The configs come from Mobly configs that look like:

    ```config.yaml
    TestBeds:
    - Name: SampleTestBed
      Controllers:
        BtBoardDevice:
        - serial_port: '/dev/ttyUSB0'
          bluetooth_address: '11:22:33:44:55:66'
    ```

  Each config should have required key-value pair 'serial_port' and
  'bluetooth_address'.

  Args:
    configs: a list of dicts, each representing a configuration for a device.

  Returns:
    A list of BtBoardDevice objects.

  Raises:
    errors.BtReferenceError: Invalid controller configs are given.
  """
  try:
    device_configs = example_device_config.from_dicts(configs)
  except Exception as e:
    raise DeviceError(_DEVICE_CONFIG_ERROR_MSG, e) from e

  devices = []
  for config in device_configs:
    logging.debug(
        'Creating device %s on serial port %s',
        config.bluetooth_address,
        config.serial_port,
    )
    devices.append(BtBoardDevice(config))

  return devices


def destroy(devices: Sequence[BtBoardDevice]) -> None:
  """Destroys BtBoardDevice objects.

  Mobly uses this to destroy BtBoardDevice objects created by `create`.

  Args:
    devices: list of BtBoardDevice.
  """
  for device in devices:
    try:
      device.destroy()
    except Exception:  # pylint: disable=broad-except
      logging.exception('Failed to clean up device properly: %s', repr(device))


def get_info(devices: Sequence[BtBoardDevice]) -> Sequence[dict[str, Any]]:
  """Gets info from the BtBoardDevice objects used in a test run.

  Args:
    devices: A list of BtBoardDevice objects.

  Returns:
    list of dict, each representing info for input devices.
  """
  return [dict() for d in devices]


class BtBoardDevice(bluetooth_reference_device_base.BluetoothReferenceDeviceBase):
  """Example Mobly controller for a Bluetooth dev board device.

  NOTE: This class must implement all abstract methods in base class
  `bluetooth_reference_device_base.BluetoothReferenceDeviceBase` to be
  instantiated. Otherwise a `TypeError` will be raised.

  Attributes:
    bluetooth_address: The unique BRE/DR address (classic Bluetooth address)
      of the device.
    config: The configurations for the device.
    debug_tag: A string that represents this device in the debug info.
    log_path: The local path on the host to save logs in the test.
    log: A logger adapted from root logger with an added prefix
      '[BtBoardDevice|<bluetooth_address>] 'specific to a test device.
  """

  bluetooth_address: str

  _debug_tag: str

  def __init__(self, config: example_device_config.DeviceConfig) -> None:
    self.config = config
    self.bluetooth_address = self.config.bluetooth_address

    # logging.log_path only exists when this is used in a Mobly test run.
    log_path_base = getattr(logging, 'log_path', '/tmp/logs')
    device_log_directory_name = mobly_logger.sanitize_filename(
        f'BtBoardDevice_{config.bluetooth_address}'
    )
    self._debug_tag = config.bluetooth_address
    self.log_path = os.path.join(log_path_base, device_log_directory_name)
    mobly_utils.create_dir(self.log_path)
    self.log = mobly_logger.PrefixLoggerAdapter(
        logging.getLogger(),
        {
            mobly_logger.PrefixLoggerAdapter.EXTRA_KEY_LOG_PREFIX: (
                f'[BtBoardDevice|{self.debug_tag}]'
            )
        },
    )

  @property
  def debug_tag(self) -> str:
    """A string that represents this device in the debug info.

    This will be used as part of the prefix of debugging messages emitted by
    this device object, like log lines and the message of DeviceError. Default
    value is the Bluetooth address of the board.
    """
    return self._debug_tag

  @debug_tag.setter
  def debug_tag(self, tag: str) -> None:
    """Sets the debug tag."""
    self.log.set_log_prefix(f'[BtBoardDevice|{tag}]')
    self.log.debug('Logging debug tag set to "%s"', tag)
    self._debug_tag = tag

  def __repr__(self) -> str:
    return f'<BtBoardDevice|{self.debug_tag}>'

  def __del__(self) -> None:
    self.destroy()

  def destroy(self) -> None:
    """Tears BtBoardDevice object down."""
