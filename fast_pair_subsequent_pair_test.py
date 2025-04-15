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

"""Test Fast Pair subsequent pairing on Android + BT ref."""

import datetime

from mobly import asserts
from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import fast_pair_utils

# Constants for timeouts
_INITIAL_PAIR_DISCOVER_TIME = datetime.timedelta(seconds=30)
_SUBSEQUENT_PAIR_CONNECTION_TIME = datetime.timedelta(seconds=90)
_WAIT_FOR_UI_UPDATE = datetime.timedelta(seconds=30)

# Constants for the widget resource ID
_FAST_PAIR_HALFSHEET_IMAGE_ID = 'com.google.android.gms:id/image_view'


class FastPairSubsequentPairTest(bt_base_test.BtRefBaseTest):
  """Test class for subsequent pairing test on Android + BT ref."""

  initial_pair_phone: android_device.AndroidDevice
  subsequent_pair_phone: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self):
    super().setup_class()

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]

    # Register two Android device controllers.
    ads = self.register_controller(android_device, 2)
    self.initial_pair_phone, self.subsequent_pair_phone = ads
    utils.concurrent_exec(
        fast_pair_utils.setup_android_device,
        [[self.initial_pair_phone, True], [self.subsequent_pair_phone, True]],
        raise_on_exception=True,
    )

  def setup_test(self):
    self.ref.factory_reset()

  def test_fast_pair_subsequent_pairing(self):
    #################################################################
    # Pair the first Android phone.
    #################################################################
    # Click 'Connect' button.
    asserts.assert_true(
        self.initial_pair_phone.uia(text='Connect').wait.click(
            _WAIT_FOR_UI_UPDATE
        ),
        f'[First AndroidDevice|{self.initial_pair_phone.serial}] Fail to find'
        ' `Connect` button from halfsheet.',
    )

    # Expect 'Device connected' message and then click 'Done' button.
    asserts.assert_true(
        self.initial_pair_phone.uia(text='Device connected').wait.exists(
            _WAIT_FOR_UI_UPDATE
        ),
        f'[First AndroidDevice|{self.initial_pair_phone.serial}] Fail to pair'
        ' with Fast Pair provider.',
    )
    self.initial_pair_phone.uia(text='Done').click()

    # Confirm the first phone and reference device are connected.
    fast_pair_utils.assert_device_bonded_via_address(
        self.initial_pair_phone,
        self.ref.bluetooth_address,
        fail_message=(
            f'[First AndroidDevice|{self.initial_pair_phone.serial}] Fail to'
            ' confirm bonded devices after paired.'
        ),
    )

    #################################################################
    # Pair the second Android phone.
    #################################################################
    if self.subsequent_pair_phone.uia(res=_FAST_PAIR_HALFSHEET_IMAGE_ID).exists:
      self.subsequent_pair_phone.uia.press.back()

    self.subsequent_pair_phone.uia.open.notification()
    asserts.assert_true(
        self.subsequent_pair_phone.uia(
            text='Your saved device is available'
        ).wait.click(_INITIAL_PAIR_DISCOVER_TIME),
        f'[Subsequent AndroidDevice|{self.subsequent_pair_phone.serial}] Fail'
        ' to receive subsequent pair notification',
    )

    # Confirm the second phone and reference device are connected.
    fast_pair_utils.assert_device_bonded_via_address(
        self.subsequent_pair_phone,
        self.ref.bluetooth_address,
        timeout=_SUBSEQUENT_PAIR_CONNECTION_TIME,
        fail_message=(
            f'[Subsequent AndroidDevice|{self.subsequent_pair_phone.serial}]'
            ' Fail to subsequent pair with Fast Pair provider.'
        ),
    )

  def teardown_test(self):
    utils.concurrent_exec(
        fast_pair_utils.clear_bonded_devices,
        [[self.initial_pair_phone], [self.subsequent_pair_phone]],
        raise_on_exception=True,
    )
    utils.concurrent_exec(
        lambda d: d.services.create_output_excerpts_all(self.current_test_info),
        param_list=[[self.initial_pair_phone], [self.subsequent_pair_phone]],
        raise_on_exception=True,
    )
    self.ref.create_output_excerpts(self.current_test_info)


if __name__ == '__main__':
  test_runner.main()
