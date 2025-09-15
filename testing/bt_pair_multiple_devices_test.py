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

"""A Mobly Test to test basic Bluetooth pairing on reference device."""

import datetime
import time

from mobly import base_test
from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

from testing import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)

_REPEAT_RUN_NUMBER = 5


class BtPairMultipleTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test basic Bluetooth pairing on reference device."""

  ad_a: android_device.AndroidDevice
  ad_b: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register an Android device controller.
    self.ad_a, self.ad_b, *_ = self.register_controller(module=android_device, min_number=2)
    utils.concurrent_exec(
        bluetooth_utils.setup_android_device,
        param_list=[[self.ad_a], [self.ad_b]],
        raise_on_exception=True,
    )

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]

  def setup_test(self) -> None:
    self.ref.factory_reset()
    self.ref.set_component_number(1)
    self.ref.start_pairing_mode()

  @base_test.repeat(_REPEAT_RUN_NUMBER, max_consecutive_error=3)
  def test_bt_pair_multiple_devices(self) -> None:
    ref_address = self.ref.bluetooth_address.upper()

    bluetooth_utils.mbs_pair_devices(self.ad_a, ref_address)

    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ref.start_pairing_mode()
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    bluetooth_utils.mbs_pair_devices(self.ad_b, ref_address)

  def teardown_test(self) -> None:
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    utils.concurrent_exec(
        bluetooth_utils.clear_bonded_devices,
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
