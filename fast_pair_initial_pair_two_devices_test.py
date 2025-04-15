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

"""Mobly Test for Fast Pair on two Android devices with different accounts."""

import datetime
import logging
import time

from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import fast_pair_utils

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)


class FastPairInitialPairTwoDevicesTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to do Fast Pair initial pair on two Android devices."""

  ad_a: android_device.AndroidDevice
  ad_b: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register two Android device controllers.
    self.ad_a, self.ad_b, *_ = self.register_controller(android_device, 2)
    utils.concurrent_exec(
        fast_pair_utils.setup_android_device,
        param_list=[[self.ad_a, True], [self.ad_b, True]],
        raise_on_exception=True,
    )

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]

  def setup_test(self) -> None:
    self.ref.factory_reset()

  def test_bt_pair_multiple_devices(self) -> None:
    ref_address = self.ref.bluetooth_address.upper()

    fast_pair_utils.fast_pair_android_and_ref(self.ad_a, ref_address)

    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ref.start_pairing_mode()

    fast_pair_utils.fast_pair_android_and_ref(self.ad_b, ref_address)

  def teardown_test(self) -> None:
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    utils.concurrent_exec(
        fast_pair_utils.clear_bonded_devices,
        [[self.ad_a], [self.ad_b]],
        raise_on_exception=True,
    )
    utils.concurrent_exec(
        lambda d: d.services.create_output_excerpts_all(self.current_test_info),
        param_list=[[self.ad_a], [self.ad_b]],
        raise_on_exception=True,
    )
    self.ref.create_output_excerpts(self.current_test_info)
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())


if __name__ == '__main__':
  test_runner.main()
