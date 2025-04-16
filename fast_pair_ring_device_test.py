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

"""A Mobly Test to test Fast Pair ring my device feature."""

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
_WAIT_FOR_UI_TRANSLATE = datetime.timedelta(seconds=6)
_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)

_FIND_DEVICE_SLICE_TITLE = 'Find device'


class FastPairRingDeviceTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test Fast Pair ring my device feature."""

  ad: android_device.AndroidDevice
  ref_primary: bluetooth_reference_device.BluetoothReferenceDeviceBase
  ref_secondary: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self):
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    bluetooth_utils.setup_android_device(self.ad, setup_fast_pair=True)

    # Register Bluetooth reference device
    refs = self.register_controller(bluetooth_reference_device, min_number=2)
    if refs[0].config.get('role', '') == 'primary':
      self.ref_primary = refs[0]
      self.ref_secondary = refs[1]
    else:
      self.ref_primary = refs[1]
      self.ref_secondary = refs[0]
    
  def setup_test(self):
    self.ad.adb.shell('svc bluetooth disable')
    utils.concurrent_exec(
        lambda d: d.factory_reset(),
        [[self.ref_primary], [self.ref_secondary]],
        raise_on_exception=True,
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ad.adb.shell('svc bluetooth enable')

  def test_ring_device_active_state(self):
    bluetooth_utils.fast_pair_android_and_ref(
        self.ad, self.ref_primary.bluetooth_address
    )

    with bluetooth_utils.open_device_detail_settings(self.ad):
      logging.info('Enter FindDevice page')
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
      logging.info('Start to check Connected string')
      asserts.assert_true(
          self.ad.uia(textContains='Connected').wait.exists(
              _WAIT_FOR_UI_TRANSLATE
          ),
          'Fail to get connected string when headset is connected on phone.',
      )
      logging.info('Start to check button enable state')
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

      # Starts to check ring device UI when headset is disconnected.
      self.ref_primary.disconnect(self.ad.mbs.btGetAddress())
      time.sleep(_WAIT_FOR_UI_UPDATE.total_seconds())

      logging.info('Start to check Disconnected string')
      asserts.assert_true(
          self.ad.uia(textContains='Disconnected').wait.exists(
              _WAIT_FOR_UI_TRANSLATE
          ),
          'Fail to get disconnected string when headset is disconnected on'
          ' phone.',
      )
      logging.info('Start to check button enable state')
      asserts.assert_false(
          self.ad.uia(text='Ring Left').enabled,
          'UI Fail because the left ring button is enabled when device is'
          ' disconnected.',
      )
      asserts.assert_false(
          self.ad.uia(text='Ring Right').enabled,
          'UI Fail because the right ring button is enabled when device is'
          ' disconnected.',
      )

  def teardown_test(self):
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    utils.concurrent_exec(
        lambda d: d.create_output_excerpts(self.current_test_info),
        [[self.ref_primary], [self.ref_secondary]],
        raise_on_exception=True,
    )
    bluetooth_utils.clear_bonded_devices(self.ad)    


if __name__ == '__main__':
  test_runner.main()
