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

"""A Mobly Test to test Bluetooth forget action on reference device."""

import datetime
import logging
import time

from mobly import asserts
from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import fast_pair_utils

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)


class BtForgetPairedDeviceTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test Bluetooth forget action on reference device."""

  ad: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    fast_pair_utils.setup_android_device(self.ad)

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]

  def setup_test(self) -> None:
    self.ref.factory_reset()
    fast_pair_utils.mbs_pair_devices(self.ad, self.ref.bluetooth_address)

  def test_bt_forget(self) -> None:
    android_address = self.ad.mbs.btGetAddress()
    board_address = self.ref.bluetooth_address.upper()

    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    paired_android_list = self.ref.get_paired_devices()
    asserts.assert_in(
        android_address, [d['Address'].upper() for d in paired_android_list]
    )

    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ref.clear_paired_devices()

    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    asserts.assert_false(
        self.ref.get_paired_devices(),
        msg='Paired device list not empty!'
    )
    fast_pair_utils.assert_device_disconnected(board_address)

  def teardown_test(self) -> None:
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    self.ref.create_output_excerpts(self.current_test_info)
    fast_pair_utils.clear_bonded_devices(self.ad)


if __name__ == '__main__':
  test_runner.main()
