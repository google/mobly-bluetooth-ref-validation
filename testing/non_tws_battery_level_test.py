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

"""Test Bluetooth battery level setter of reference device."""

import datetime
import logging
import time

from mobly import asserts
from mobly import test_runner
from mobly.controllers import android_device

from testing import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)
_UI_UPDATE_TIME = datetime.timedelta(seconds=60)

_BATTERY_LEVEL = 80


class NonTwsTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test battery level setter of reference device."""

  ad: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    bluetooth_utils.setup_android_device(self.ad, enable_le_audio=False)

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]
    self.ref.factory_reset()

  def test_1_set_non_tws(self) -> None:
    self.ref.disable_tws()

  def test_2_set_battery_level_and_pair(self) -> None:
    self.ref.set_battery_level(_BATTERY_LEVEL)
    self.ref.start_pairing_mode()

    #################################################################
    # Check the battery level on reference side
    #################################################################
    battery_level = self.ref.get_battery_level()
    asserts.assert_equal(
        battery_level, _BATTERY_LEVEL, 'Failed to set battery level correctly.'
    )

    #################################################################
    # Check the battery level on phone side
    #################################################################
    # Pair the Android phone with ref.
    initial_name = bluetooth_utils.assert_device_discovered(
        self.ad, self.ref.bluetooth_address
    )
    bluetooth_utils.mbs_pair_with_retry(self.ad, self.ref.bluetooth_address)
    bluetooth_utils.assert_device_bonded_via_address(
        self.ad, self.ref.bluetooth_address
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    # Open system settings
    with bluetooth_utils.open_system_settings(self.ad):
      asserts.assert_true(
          self.ad.uia(textContains=f'{_BATTERY_LEVEL}%').wait.exists(
              _UI_UPDATE_TIME
          ),
          'Fail to find correct battery level from device list page.'
      )

  def teardown_test(self) -> None:
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    self.ref.create_output_excerpts(self.current_test_info)

  def teardown_class(self) -> None:
    bluetooth_utils.clear_bonded_devices(self.ad)


if __name__ == '__main__':
  test_runner.main()
