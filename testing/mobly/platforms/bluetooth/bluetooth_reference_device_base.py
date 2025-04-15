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

"""The base class for Bluetooth reference devices."""

import abc
import dataclasses
import datetime
from typing import Any, Dict, List, Optional

from mobly import runtime_test_info

from testing.mobly.platforms.bluetooth.lib import utils


@dataclasses.dataclass
class BluetoothInfo:
  """The basic information of a Bluetooth device.

  Attributes:
    bluetooth_address: The classic Bluetooth address of the device, in BD_ADDR
      format and upper case.
    ble_address: The BLE address of the device, in BD_ADDR format and upper
      case.
    bluetooth_name: The classic Bluetooth name of device.
    ble_name: The BLE name of the device.
  """

  bluetooth_address: str
  ble_address: str
  bluetooth_name: str
  ble_name: str

  def __post_init__(self):
    # Ensure the address is in BD_ADDR format and in upper case.
    self.bluetooth_address = utils.lsb_addr_to_bd_addr(
        self.bluetooth_address
    ).upper()
    self.ble_address = utils.lsb_addr_to_bd_addr(self.ble_address).upper()


class BluetoothReferenceDeviceBase(metaclass=abc.ABCMeta):
  """Common interface for Mobly to interact with Bluetooth reference devices."""

  def destroy(self) -> None:
    """Tears the instance down."""

  def get_info(self) -> dict[str, str]:
    """Gets the information of the device."""
    return {}

  @abc.abstractmethod
  def reboot(self) -> None:
    """Soft reboots the device.

    This method powers off and then powers on the device. The paired devices
    will be preserved. If the device is powered off, this method just powers on
    the device.
    """

  @abc.abstractmethod
  def factory_reset(self) -> None:
    """Factory resets the device.

    This method deletes all of the paired devices, restores the device to its
    original state, and reboots the device.
    """

  @abc.abstractmethod
  def power_on(self) -> None:
    """Soft powers on the device."""

  @abc.abstractmethod
  def power_off(self) -> None:
    """Soft powers off the device."""

  @abc.abstractmethod
  def get_device_info(self) -> BluetoothInfo:
    """Gets the general information of the device.

    Returns:
      A BluetoothInfo object that contains the classic Bluetooth and BLE address
      and name information of the device.
    """

  @abc.abstractmethod
  def set_address(self, address: str) -> None:
    """Sets the Bluetooth MAC address of the device.

    Args:
      address: The new Bluetooth address to be set on the device.
    """

  @abc.abstractmethod
  def set_name(self, bluetooth_name: str, ble_name: str) -> None:
    """Sets the classic Bluetooth name and BLE name of the device.

    Args:
      bluetooth_name: The new classic Bluetooth name of the device.
      ble_name: The new BLE name of the device.
    """

  @abc.abstractmethod
  def get_fast_pair_support(self) -> bool:
    """Checks if the device supports Google Fast Pair."""

  @abc.abstractmethod
  def enable_fast_pair(self) -> None:
    """Enables Google Fast Pair on the device."""

  @abc.abstractmethod
  def disable_fast_pair(self) -> None:
    """Disables Google Fast Pair on the device."""

  @abc.abstractmethod
  def get_fp_params(self) -> tuple[str, str]:
    """Gets the Fast Pair parameters of the device.

    Returns:
      A tuple of Google Fast Pair model ID (format 0xXXXXXX) and Google Fast
      Pair anti-spoofing key (base64, uncompressed).
    """

  @abc.abstractmethod
  def set_fp_params(self, model_id: str, private_key: str) -> None:
    """Sets the Fast Pair parameters of the device.

    Args:
      model_id: Google Fast Pair model ID (format XXXXXX or 0xXXXXXX).
      private_key: Google Fast Pair anti-spoofing key (base64, uncompressed).
    """

  @abc.abstractmethod
  def get_sass_support(self) -> bool:
    """Checks if the device supports Fast Pair Audio Switch (SASS) feature."""

  @abc.abstractmethod
  def enable_sass(self) -> None:
    """Enables Fast Pair Audio Switch (SASS) feature on the device."""

  @abc.abstractmethod
  def disable_sass(self) -> None:
    """Disables Fast Pair Audio Switch (SASS) feature on the device."""

  def get_device_type(self) -> str:
    """Gets the Bluetooth reference device type.

    Different device types support different interactions. The default device
    type is "audio device". Other device support will be added in the future,
    such as "keyboard" and "mouse".

    Returns:
      The Bluetooth reference device type.
    """
    return 'audio device'

  def set_device_type(self, device_type: str) -> None:
    """Sets the Bluetooth reference device type.

    If the current type is not the target type, this method will change the
    type of the device, clears all of the paired devices, and reboots the
    device. Otherwise, this method will do nothing.

    Changing device type also changes the supported interactions.

    Args:
      device_type: The target device type.
    """

  @abc.abstractmethod
  def get_lea_support(self) -> bool:
    """Checks if the device supports LE Audio."""

  @abc.abstractmethod
  def enable_lea(self) -> None:
    """Enables LE Audio on the device."""

  @abc.abstractmethod
  def disable_lea(self) -> None:
    """Disables LE Audio on the device."""

  @abc.abstractmethod
  def set_single_point(self) -> None:
    """Sets the device to single point mode."""

  @abc.abstractmethod
  def set_multi_point(self) -> None:
    """Sets the device to multi point mode."""

  @abc.abstractmethod
  def start_pairing_mode(
      self, timeout: datetime.timedelta | None = None
  ) -> None:
    """Puts the devboard into pairing mode.

    The device will be able to be discovered and paired. If the device is
    currently in pairing mode, this method will refresh the timeout to exit
    pairing mode.

    Args:
      timeout: The optional timeout to stop pairing mode. The device will exit
        the pairing mode after this timeout has elapsed. If None, the device
        will keep staying in pairing mode.
    """

  @abc.abstractmethod
  def stop_pairing_mode(self) -> None:
    """Exits the pairing mode.

    The device will not be able to be discovered and paired. If the device is
    currently not in pairing mode, this method will do nothing.
    """

  @abc.abstractmethod
  def connect(self, address: str) -> None:
    """Connects the device to the given address.

    The given address should be paired. If the given address is currently
    disconnected, this method will connect the device to the given address.
    Otherwise, this method will do nothing.

    Args:
      address: The target classic Bluetooth address to connect to.

    Raises:
      ValueError: If the given address is invalid.
    """

  @abc.abstractmethod
  def disconnect(self, address: str) -> None:
    """Disconnects from a given address.

    The given address should be paired. If the given address is currently
    connected, this method will disconnect the device from the given address.
    Otherwise, this method will do nothing.

    Args:
      address: The target classic Bluetooth address to disconnect from.

    Raises:
      ValueError: If the given address is invalid.
    """

  @abc.abstractmethod
  def clear_paired_devices(self) -> None:
    """Clears all of the paired devices.

    This method disconnects and unpairs all the paired devices.
    """

  @abc.abstractmethod
  def enable_tws(self) -> None:
    """Enables the TWS mode.

    Under the TWS mode, we can control and stream the output of the
    secondary board that represents the secondary ear in the TWS headphones.
    Primary board and secondary board will work together as one pair of
    headphones.
    """

  @abc.abstractmethod
  def disable_tws(self) -> None:
    """Disables the TWS mode.

    This method will put the device into the non-TWS mode, where we use only one
    board to represent a non-TWS device, sush as speaker, headset, etc.
    """

  @abc.abstractmethod
  def get_component_number(self) -> int:
    """Gets the number of components of the device.

    Component number refers to the device number in the CSIP
    (https://www.bluetooth.com/specifications/specs/csip-1-0-1/) Coordinated
    Set.

    If 1, the device has a single component. It shows 1 address on Android after
    pairing.
    If 2, the device has two components, one CSIP Set Coordinator (primary
    earbud), one CSIP Set Member (secondary earbud). And shows 2 addresses on
    Android after pairing.

    Returns:
      The number of components of the device.
    """

  @abc.abstractmethod
  def set_component_number(self, number: int) -> None:
    """Sets the number of components of the device.

    Component number refers to the device number in the CSIP
    (https://www.bluetooth.com/specifications/specs/csip-1-0-1/) Coordinated
    Set.

    Args:
      number: The target number of components.
    """

  @abc.abstractmethod
  def pair_tws(self) -> None:
    """Pairs two devices to create a pair of TWS earpods."""

  @abc.abstractmethod
  def get_in_box_state(self) -> bool:
    """Gets if the TWS earpods are in the box."""

  @abc.abstractmethod
  def set_in_box_state(self, in_box: bool) -> None:
    """Sets the box state of the TWS earpods."""

  @abc.abstractmethod
  def get_on_head_state(self) -> bool:
    """Gets if the TWS earpods are on head."""

  @abc.abstractmethod
  def set_on_head_state(self, on_head: bool) -> None:
    """Sets the on head status of the TWS earpods."""

  @abc.abstractmethod
  def open_box(self) -> None:
    """Opens the charging box."""

  @abc.abstractmethod
  def fetch_out(self) -> None:
    """Fetches the TWS earpods out of the charging box."""

  @abc.abstractmethod
  def wear_up(self) -> None:
    """Puts the TWS earpods on head."""

  @abc.abstractmethod
  def wear_down(self) -> None:
    """Takes the TWS earpods off head."""

  @abc.abstractmethod
  def put_in(self) -> None:
    """Puts the TWS earpods into the charging box."""

  @abc.abstractmethod
  def close_box(self) -> None:
    """Closes the charging box."""

  @abc.abstractmethod
  def set_battery_level(self, level: int | list[int]) -> None:
    """Sets the fake battery level of the device.

    Args:
      level: The fake battery level of the device, in the range of 0-100.
        `level=80` represents that the battery is 80% full. If the device is a
        TWS device, the level is a list of 3 integers representing the battery
        leve of [left bud, case, right bud] respectively.

    Raises:
      ValueError: If the given battery level is not in the valid range.
    """

  @abc.abstractmethod
  def get_battery_level(self) -> int | list[int]:
    """Gets the fake battery level of the device.

    Returns:
      The fake battery level of the device, in the range of 0-100.
      `level=80` represents that the battery is 80% full. If the device is a
      TWS device, the level is a list of 3 integers representing the battery
      level of [left bud, case, right bud] respectively.
    """

  @abc.abstractmethod
  def get_paired_devices(self) -> list[dict[str, str]]:
    """Gets the list of paired devices information.

    Returns:
      A list of dicts containing the paired device name and address. The keys in
      the result dict are aligned with the Android `btGetPairedDevices` result.
      Example:
      [
        {'Name': 'Phone A', 'Address': '00:11:22:33:44:55'},
        {'Name': 'Phone B', 'Address': '66:77:88:99:AA:BB'},
      ]
    """

  @abc.abstractmethod
  def media_play(self) -> None:
    """Plays the media stream."""

  @abc.abstractmethod
  def media_pause(self) -> None:
    """Pauses the media stream."""

  @abc.abstractmethod
  def media_next(self) -> None:
    """Jumps to the next media track."""

  @abc.abstractmethod
  def media_prev(self) -> None:
    """Jumps to the previous media track."""

  @abc.abstractmethod
  def volume_up(self, level: int = 1) -> None:
    """Increases the device volume.

    This method simulates a press on the `Vol+` button. Each simulated press on
    the button will increase the volume by `level` unit.

    Args:
      level: The number of volume levels to increase.
    """

  @abc.abstractmethod
  def volume_down(self, level: int = 1) -> None:
    """Increases the device volume.

    This method simulates a press on the `Vol-` button. Each simulated press on
    the button will decrease the volume by `level` unit.

    Args:
      level: The number of volume levels to decrease.
    """

  @abc.abstractmethod
  def set_volume(self, level: int) -> None:
    """Sets the volume of the device to a given level.

    Args:
      level: The target volume level, in the range of [0, 127].
    """

  @abc.abstractmethod
  def get_volume(self) -> int:
    """Gets the volume of the device.

    Returns:
      The volume level of the device.
    """

  @abc.abstractmethod
  def call_accept(self) -> None:
    """Accepts a phone call."""

  @abc.abstractmethod
  def call_decline(self) -> None:
    """Declines a phone call or hangs up on a current phone call."""

  @abc.abstractmethod
  def call_hold(self) -> None:
    """Holds the current call."""

  @abc.abstractmethod
  def call_redial(self) -> None:
    """Redials the last phone call."""

  @abc.abstractmethod
  def get_anc_support(self) -> bool:
    """Checks if the device supports Active Noise Cancellation (ANC)."""

  @abc.abstractmethod
  def enable_anc(self) -> None:
    """Enables Active Noise Cancellation (ANC) on the device."""

  @abc.abstractmethod
  def disable_anc(self) -> None:
    """Disables Active Noise Cancellation (ANC) on the device."""

  @abc.abstractmethod
  def get_anc_mode(self) -> str:
    """Gets the ANC mode of the device."""

  @abc.abstractmethod
  def set_anc_mode(self, mode: str) -> None:
    """Sets the ANC mode of the device."""

  @abc.abstractmethod
  def get_spatial_audio_support(self) -> bool:
    """Checks if the device supports Spatial Audio."""

  @abc.abstractmethod
  def enable_spatial_audio(self) -> None:
    """Enables Spatial Audio on the device."""

  @abc.abstractmethod
  def disable_spatial_audio(self) -> None:
    """Disables Spatial Audio on the device."""

  def create_output_excerpts(
      self, test_info: runtime_test_info.RuntimeTestInfo
  ) -> list[Any]:
    """Creates excerpts for specified logs and returns the excerpt paths.

    Args:
      test_info: `self.current_test_info` in a Mobly test.

    Returns:
      The list of absolute paths to excerpt files.
    """
    del test_info  # Unused
    return []