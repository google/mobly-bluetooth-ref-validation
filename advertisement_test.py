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

"""A Mobly Test to test basic Bluetooth advertisement on reference device."""

import datetime
import time

from mobly import test_runner
from mobly.controllers import android_device

import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)


class AdvertisementTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test basic Bluetooth advertisement on reference device."""

  ad: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    bluetooth_utils.setup_android_device(self.ad)

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]
    self.ref.factory_reset()
    self.ref.set_component_number(1)

  def test_ref_enable_pairing_then_disable(self) -> None:
    board_address = self.ref.bluetooth_address.upper()

    #################################################################
    # Start advertisement
    #################################################################
    self.ref.start_pairing_mode()

    # Confirm the reference device is discovered.
    def ref_discovered_by_phone() -> bool:
      return board_address.upper() in [
          d['Address'] for d in self.ad.mbs.btDiscoverAndGetResults()
      ]
    bluetooth_utils.assert_wait_condition_true(
        ref_discovered_by_phone,
        fail_message='Bluetooth refernece device is not discovered',
    )

    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    #################################################################
    # Stop advertisement
    #################################################################
    self.ref.stop_pairing_mode()

    # Confirm the reference device is discovered.
    def ref_not_discovered_by_phone() -> bool:
      return board_address.upper() not in [
          d['Address'] for d in self.ad.mbs.btDiscoverAndGetResults()
      ]
    bluetooth_utils.assert_wait_condition_true(
        ref_not_discovered_by_phone,
        fail_message='Bluetooth reference device is still discovered',
    )

  def teardown_test(self) -> None:
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    self.ref.create_output_excerpts(self.current_test_info)


if __name__ == '__main__':
  test_runner.main()
