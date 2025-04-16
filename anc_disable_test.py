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

"""Test Bluetooth disable ANC feature of reference device."""

import datetime
import time
import uuid

from mobly import asserts
from mobly import test_runner
from mobly.controllers import android_device

import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)
_WAIT_FOR_UI_TRANSLATE = datetime.timedelta(seconds=6)
_WAIT_FOR_UI_UPDATE = datetime.timedelta(seconds=30)

# ANC slice title
_ANC_SLICE_TITLE = 'Active Noise Control'


class AncDisableTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test ANC disable feature of reference device."""

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

  def test_disable_anc(self) -> None:
    self.ref.disable_anc()
    self.ref.start_pairing_mode()

    # Pair the Android phone with ref.
    bluetooth_utils.mbs_pair_devices(self.ad, self.ref.bluetooth_address)

    self.ref.set_on_head_state(True)
    time.sleep(_WAIT_FOR_UI_UPDATE.total_seconds())

    with bluetooth_utils.open_device_detail_settings(self.ad):
      asserts.assert_false(
          self.ad.uia(text=_ANC_SLICE_TITLE).wait.exists(
              _WAIT_FOR_UI_TRANSLATE
          ),
          'Failed to disable ANC feature. ANC slice shown in Device Detail'
          ' when headset is connected on phone.',
      )
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

  def teardown_test(self) -> None:
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    self.ref.create_output_excerpts(self.current_test_info)


if __name__ == '__main__':
  test_runner.main()
