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

"""Test Bluetooth name and address setter of reference device."""

import datetime
import logging
import random
import time

from mobly import asserts
from mobly import logger as mobly_logger
from mobly import test_runner
from mobly.controllers import android_device

from testing import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)

_TARGET_BT_NAME = 'bt {timestamp}'
_TARGET_BLE_NAME = 'ble {timestamp}'
_TARGET_ADDRESS = '11:22:23:33:33:61'


class SetNameAddressTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test Bluetooth name and address setter."""

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
    self.ref.set_component_number(1)

  def test_ref_set_name_and_address(self) -> None:
    timestamp = mobly_logger.get_log_file_timestamp()
    bluetooth_name = _TARGET_BT_NAME.format(timestamp=timestamp)
    ble_name = _TARGET_BLE_NAME.format(timestamp=timestamp)
    self.ad.adb.shell('svc bluetooth disable')
    try:
      self.ref.set_name(
          bluetooth_name=bluetooth_name,
          ble_name=ble_name,
      )
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
      self.ref.set_address(_TARGET_ADDRESS)
      self.ref.start_pairing_mode()
    finally:
      self.ad.adb.shell('svc bluetooth enable')

    #################################################################
    # Check the BT ref name and address from ref side
    #################################################################

    ref_info = self.ref.get_device_info()
    asserts.assert_equal(ref_info.bluetooth_address, _TARGET_ADDRESS)
    asserts.assert_equal(ref_info.ble_address, _TARGET_ADDRESS)
    asserts.assert_equal(ref_info.bluetooth_name, bluetooth_name)
    asserts.assert_equal(ref_info.ble_name, ble_name)

    #################################################################
    # Check the BT ref name and address from phone side
    #################################################################

    def bt_name_and_address_discovered():
      for device in self.ad.mbs.btDiscoverAndGetResults():
        if device['Address'] == _TARGET_ADDRESS:
          name = device['Name']
          if name == bluetooth_name or name == ble_name[:12]:
            return True
      return False

    bluetooth_utils.assert_wait_condition_true(
        bt_name_and_address_discovered,
        fail_message='Failed to discover target device with correct BT name and address.',
    )

  def teardown_test(self) -> None:
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    self.ref.create_output_excerpts(self.current_test_info)
    bluetooth_utils.clear_bonded_devices(self.ad)


if __name__ == '__main__':
  test_runner.main()
