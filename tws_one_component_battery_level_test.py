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

"""Test Bluetooth one component TWS pairing of reference device."""

import datetime
import time
import uuid

from mobly import asserts
from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import fast_pair_utils

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=3)
_WAIT_FOR_UI_TRANSLATE = datetime.timedelta(seconds=6)
_WAIT_FOR_UI_UPDATE = datetime.timedelta(seconds=30)
_UI_UPDATE_TIME = datetime.timedelta(seconds=60)

_FIND_DEVICE_SLICE_TITLE = 'Find device'

_BATTERY_LEFT = 80
_BATTERY_RIGHT = 66


class TwsOneComponentTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test TWS pairing of reference device."""

  ad: android_device.AndroidDevice
  ref_primary: bluetooth_reference_device.BluetoothReferenceDeviceBase
  ref_secondary: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    fast_pair_utils.setup_android_device(self.ad)

    # Register Bluetooth reference device
    refs = self.register_controller(bluetooth_reference_device, min_number=2)
    if refs[0].config.get('role', '') == 'primary':
      self.ref_primary = refs[0]
      self.ref_secondary = refs[1]
    else:
      self.ref_primary = refs[1]
      self.ref_secondary = refs[0]
    utils.concurrent_exec(
        lambda d: d.factory_reset(),
        [[self.ref_primary], [self.ref_secondary]],
        raise_on_exception=True,
    )

  def test_1_set_tws_one_component(self) -> None:
    utils.concurrent_exec(
        lambda d: d.enable_tws(),
        [[self.ref_primary], [self.ref_secondary]],
        raise_on_exception=True,
    )
    utils.concurrent_exec(
        lambda d: d.pair_tws(),
        [[self.ref_primary], [self.ref_secondary]],
        raise_on_exception=True,
    )
    self.ref_primary.set_component_number(1)


  def test_2_set_battery_level_and_pair(self) -> None:
    self.ref_primary.set_battery_level_tws(_BATTERY_LEFT, _BATTERY_RIGHT)
    self.ref_primary.get_battery_level()
    self.ref_secondary.get_battery_level()

    # Pair the Android phone with ref.
    initial_name = fast_pair_utils.assert_device_discovered(
      self.ad, self.ref_primary.bluetooth_address
    )
    self.ad.mbs.btPairDevice(self.ref_primary.bluetooth_address.upper())
    fast_pair_utils.assert_device_bonded_via_address(
      self.ad, self.ref_primary.bluetooth_address
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    with fast_pair_utils.open_system_settings(self.ad):
      # Check battery level of each ear
      asserts.assert_true(
          self.ad.uia(textContains=f'L: {_BATTERY_LEFT}%').wait.exists(
              _UI_UPDATE_TIME
          ),
          'Fail to find correct left ear battery from device detail page.'
      )
      asserts.assert_true(
          self.ad.uia(textContains=f'R: {_BATTERY_RIGHT}%').wait.exists(
              _UI_UPDATE_TIME
          ),
          'Fail to find correct right ear battery from device detail page.'
      )

  def test_3_check_paired_device_detail(self):
    with fast_pair_utils.open_device_detail_settings(self.ad):
      # Check only one address in device detail
      self.ad.uia(scrollable=True).scroll.down(textContains='Bluetooth address')
      bluetooth_address_text = self.ad.uia(textContains='Bluetooth address').text
      bluetooth_address_list = bluetooth_address_text.replace(
          "Device's Bluetooth address:", ''
      ).strip().split()
      asserts.assert_equal(
          len(bluetooth_address_list),
          1,
          'Fail to find correct address from device detail page.'
      )

      # Enter FindDevice page.
      self.ad.uia(scrollable=True).scroll.up(
          textContains=_FIND_DEVICE_SLICE_TITLE
      )
      if not self.ad.uia(
          textContains=_FIND_DEVICE_SLICE_TITLE
      ).wait.click(_WAIT_FOR_UI_UPDATE):
        asserts.assert_true(
            self.ad.uia(scrollable=True).scroll.down.click(
                textContains=_FIND_DEVICE_SLICE_TITLE,
            ),
            'Fail to enter Find Device page.',
        )
      # Starts to check ring device UI when headset is connected.
      asserts.assert_true(
          self.ad.uia(textContains='Connected').wait.exists(
              _WAIT_FOR_UI_TRANSLATE
          ),
          'Fail to get connected string when headset is connected on phone.',
      )
      asserts.assert_true(
          self.ad.uia(text='Ring Left', enabled=True).wait.exists(
              _WAIT_FOR_UI_TRANSLATE
          ),
          'UI Fail because the left ring button is not enabled when device is'
          ' connected.',
      )
      asserts.assert_true(
          self.ad.uia(text='Ring Right').enabled,
          'UI Fail because the right ring button is not enabled when device is'
          ' connected.',
      )

  def teardown_test(self) -> None:
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    utils.concurrent_exec(
        lambda d: d.create_output_excerpts(self.current_test_info),
        [[self.ref_primary], [self.ref_secondary]],
        raise_on_exception=True,
    )


if __name__ == '__main__':
  test_runner.main()
