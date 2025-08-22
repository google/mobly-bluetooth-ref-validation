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

"""Controller configurations for the BES controller module."""

from __future__ import annotations

from collections.abc import Sequence
import dataclasses
import logging
import sys
from typing import Any, Dict, List, Optional

import dacite

from testing.mobly.platforms.bluetooth.lib import utils

# Error messages used in this module.
_DEVICE_EMPTY_CONFIG_MSG = 'Configuration is empty, abort!'
_CONFIG_MISSING_REQUIRED_KEY_MSG = 'Missing required key in config'
_CONFIG_INVALID_VALUE_MSG = 'Invalid value in config'
_INVALID_BLUETOOTH_ADDRESS_MSG = 'Invalid Bluetooth address'


class ConfigError(Exception):
  """The BES controller configs encounter error."""


def from_dicts(configs: Sequence[dict[str, Any]]) -> List[DeviceConfig]:
  """Create DeviceConfig objects from a list of dict configs.

  Args:
    configs: A list of dicts each representing the configuration of one
      Bluetooth reference device.

  Returns:
    A list of DeviceConfig.

  Raises:
    errors.ConfigError: Invalid controller config is given.
  """
  device_configs = []
  if not configs:
    raise ConfigError(_DEVICE_EMPTY_CONFIG_MSG)

  for config in configs:
    logging.debug('Parsing BES config: %s', config)
    device_configs.append(DeviceConfig.from_dict(config))

  return device_configs


@dataclasses.dataclass
class DeviceConfig:
  """Provides configs and default values for BesDevice.

  Attributes:
    serial_port: The serial port of the BES dev board connected to the Mobly
      host or the Raspberry Pi.
    bluetooth_address: The Bluetooth MAC address of the BES dev board connected
      to the Mobly host or the Raspberry Pi.
    shell_mode: Whether to use Linux shell to send command to the board.
    enable_hard_reset: Whether to try to hard reset the board when fail to init.
      Hard reset is enabled only on Linux.
    dimensions: The field for user to pass MH dimensions or custom configs of
      the BES device.
  """

  # BES configs.
  serial_port: str
  bluetooth_address: str
  shell_mode: bool = False
  enable_hard_reset: bool = False

  # MH dimensions of this testbed. The dimensions can then be used to filter
  # devices in the test. Dimensions can also be set in local testbeds.
  #
  # Example testbed:
  #   ```config.yaml
  #   BesDevice:
  #   - serial_port: '/dev/ttyUSB0'
  #     bluetooth_address: '11:22:33:44:55:66'
  #     dimensions:
  #       mode: 'headset'
  #   ```
  dimensions: Dict[str, Any] = dataclasses.field(default_factory=dict)

  def __post_init__(self):
    if not utils.is_valid_address(self.bluetooth_address):
      raise ConfigError(
          f'{_INVALID_BLUETOOTH_ADDRESS_MSG}: {self.bluetooth_address}'
      )
    if sys.platform not in ('linux', 'linux2'):
      self.shell_mode = False
      self.enable_hard_reset = False

  def get(self, key: str, default_value: Any = None) -> Any:
    """Gets the value of the key in device config or its dimensions.

    This method first tries to get the value of the key from DeviceConfig
    attributes. If the key is not in the attributes, it will try to get the
    value from `dimensions` dict.

    Args:
      key: The key to find.
      default_value: The value to return if cannot find target key.

    Returns:
      The value of the key if the key is in DeviceConfig attributes or
      dimensions. Otherwise, returns `default_value`.
    """
    if hasattr(self, key):
      return getattr(self, key)
    if key in self.dimensions:
      return self.dimensions[key]
    return default_value

  @classmethod
  def from_dict(cls, config: dict[str, Any]) -> DeviceConfig:
    """Parses controller configs from Mobly runner to DeviceConfig.

    Args:
      config: A dictionary of string parameters.

    Returns:
      DeviceConfig data class.

    Raises:
      ConfigError: Invalid controller config is given.
    """
    def _bool_converter(value: Any) -> bool:
      """Converts the input data to a boolean if it is string."""
      if isinstance(value, bool):
        return value
      if isinstance(value, str) and value.lower() == 'true':
        return True
      if isinstance(value, str) and value.lower() == 'false':
        return False
      raise ValueError(f'Invalid value for bool: {value}')

    type_converters = {
        # Integer converter: any integer value in string
        # simply cast it to integer.
        int: int,
        bool: _bool_converter,
    }
    try:
      config = dacite.from_dict(
          data_class=DeviceConfig,
          data=config,
          config=dacite.Config(type_hooks=type_converters))
    except dacite.exceptions.MissingValueError as err:
      raise ConfigError(
          f'{_CONFIG_MISSING_REQUIRED_KEY_MSG}: {config}') from err
    except ValueError as err:
      raise ConfigError(
          f'{_CONFIG_INVALID_VALUE_MSG}: {config}') from err

    return config
