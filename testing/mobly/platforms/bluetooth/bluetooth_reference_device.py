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

"""The factory of Bluetooth reference device Mobly controllers.

The Bluetooth reference device are used as test peers for testing the Bluetooth
features of device under test (DUT), such as Android phones or Chromebooks.

The Bluetooth reference device can be of different types. The Mobly controller
of each device type is defined in its own module, derived from the
`BluetoothReferenceDeviceBase` class.

Use this module to instantiate Mobly controller objects of Bluetooth reference
devices. Each Mobly config passed to the factory should have required key-value
pair 'controller_name' which matches the Mobly controller name of the target
device. The other key-value pairs are passed to the device class constructor.

Example Mobly-MH test config:

```yaml
- name: SampleTestBed
  devices:
  - type: MiscTestbedSubDevice
    properties:
      controller_name: BtBoardDevice
      serial_port: "/dev/ttyUSB0"
      bluetooth_address: "11:22:33:44:55:66"
    dimensions:
      mobly_type: BluetoothReferenceDevice
```

Example Mobly-Py test config:

```yaml
TestBeds:
- Name: SampleTestBed
  Controllers:
    BluetoothReferenceDevice:
    - controller_name: BtBoardDevice
      serial_port: '/dev/ttyUSB0'
      bluetooth_address: '11:22:33:44:55:66'
    BluetoothReferenceDevice:
    - controller_name: TwsDevice
      ...
```

Example usage:

```python
# In 'setup_class'
self.ref_list = self.register_controller(bluetooth_reference_device)
```
"""

from collections.abc import Sequence
import logging
from typing import Any, TypeAlias

import immutabledict
from mobly import signals

from testing.mobly.platforms.bluetooth import bluetooth_reference_device_base
from testing.mobly.platforms.bluetooth import example_device

# The supported device class list.
# Import new device class as denpendency. Then add device class to this list 
# in the format of: `class_name.MOBLY_CONTROLLER_CONFIG_NAME: class_name`
SUPPORTED_DEVICE_CLASSES = immutabledict.immutabledict({
    example_device.MOBLY_CONTROLLER_CONFIG_NAME: example_device
})

# This is used in the config file located in the test lab's home directory.
MOBLY_CONTROLLER_CONFIG_NAME = 'BluetoothReferenceDevice'

# Error messages used in this module.
_DEVICE_EMPTY_CONFIG_MSG = 'Configuration is empty, abort!'
_CONFIG_MISSING_REQUIRED_KEY_MSG = (
    'Missing required key `controller_name` in config!'
)

BluetoothReferenceDeviceBase: TypeAlias = (
    bluetooth_reference_device_base.BluetoothReferenceDeviceBase
)


class Error(signals.ControllerError):
  """Raised for errors related to BluetoothReferenceDevice controller."""


class DeviceNotSupportedError(Exception):
  """Raised when the device class to create is not supported."""


def create(
    configs: Sequence[dict[str, Any]],
) -> list[BluetoothReferenceDeviceBase]:
  """Creates controller objects for Bluetooth reference devices.

  See the module docstring for the details of the config format and usage.

  Args:
    configs: a list of dicts, each representing a configuration for a Bluetooth
      reference device.

  Returns:
    A list of Bluetooth reference device objects.

  Raises:
    Error: If the given configuration is not valid.
    DeviceNotSupportedError: If the device class is not supported.
  """
  if not configs:
    raise Error(_DEVICE_EMPTY_CONFIG_MSG)

  devices = []
  for config in configs:
    logging.debug('Create Bluetooth reference device from config: %s', config)

    if 'controller_name' not in config:
      raise Error(_CONFIG_MISSING_REQUIRED_KEY_MSG)

    if config['controller_name'] not in SUPPORTED_DEVICE_CLASSES:
      raise DeviceNotSupportedError(
          f'Device class {config["controller_name"]} is not supported.'
      )

    try:
      devices.extend(
          SUPPORTED_DEVICE_CLASSES[config['controller_name']].create([config])
      )
    except Exception as e:  # pylint: disable=broad-except
      raise Error(
          'Failed to create Bluetooth reference device class'
          f' `{config["controller_name"]}`'
      ) from e

  return devices


def destroy(devices: Sequence[BluetoothReferenceDeviceBase]) -> None:
  """Destroys Bluetooth reference device objects.

  Args:
    devices: list of Bluetooth reference device objects.
  """
  for device in devices:
    try:
      device.destroy()
    except Exception:  # pylint: disable=broad-except
      logging.exception('Failed to clean up device properly: %s', repr(device))


def get_info(
    devices: Sequence[BluetoothReferenceDeviceBase],
) -> list[dict[str, Any]]:
  """Gets info from the Bluetooth reference device objects used in a test run.

  Args:
    devices: A list of Bluetooth reference device objects.

  Returns:
    list of dict, each representing info for input devices.
  """
  return [d.get_info() for d in devices]
