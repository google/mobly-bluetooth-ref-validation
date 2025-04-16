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

"""A Mobly Test to test Fast Pair initial pairing on reference device."""

import datetime
import logging
import time

from mobly import asserts
from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_WAIT_FOR_UI_UPDATE = datetime.timedelta(seconds=30)
_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)


class FastPairInitialPairTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test Fast Pair initial pairing on reference device."""

  ad: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self):
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    bluetooth_utils.setup_android_device(self.ad, setup_fast_pair=True)

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]

  def setup_test(self):
    self.ad.adb.shell('svc bluetooth disable')
    self.ref.factory_reset()
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ad.adb.shell('svc bluetooth enable')

  def test_fast_pair_initial_pairing(self):
    # Click 'Connect' button in the Fast Pair half sheet.
    asserts.assert_true(
        self.ad.uia(text='Connect').wait.click(_WAIT_FOR_UI_UPDATE),
        'Fail to press connect button on displayed halfsheet.',
    )

    # Expect 'Device connected' message and then click 'Done' button.
    asserts.assert_true(
        self.ad.uia(text='Device connected').wait.exists(_WAIT_FOR_UI_UPDATE),
        'Fail to show "Device connected" keyword on the halfsheet after'
        ' pairing.',
    )
    self.ad.uia(text='Done').click()

    # Confirm the devices are connected.
    bluetooth_utils.assert_device_bonded_via_address(
        self.ad,
        self.ref.bluetooth_address,
    )

  def teardown_test(self):
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    bluetooth_utils.clear_bonded_devices(self.ad)
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    self.ref.create_output_excerpts(self.current_test_info)


if __name__ == '__main__':
  test_runner.main()
