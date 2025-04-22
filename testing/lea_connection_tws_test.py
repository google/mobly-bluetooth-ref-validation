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

"""A Mobly Test to test basic Bluetooth connection on Android + reference device."""

import datetime
import logging
import time

from mobly import asserts
from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

from testing import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)
_LONG_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=30)
_WAIT_FOR_UI_UPDATE = datetime.timedelta(seconds=60)


class LEAConnectionTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test basic Bluetooth connection on Android + BT ref."""

  ad: android_device.AndroidDevice
  ref_primary: bluetooth_reference_device.BluetoothReferenceDeviceBase
  ref_secondary: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    bluetooth_utils.setup_android_device(self.ad, enable_le_audio=True)

    # Register Bluetooth reference devices.
    refs = self.register_controller(bluetooth_reference_device, min_number=2)
    self.ref_primary, self.ref_secondary = bluetooth_utils.get_tws_device(refs)

    utils.concurrent_exec(
        lambda d: d.factory_reset(),
        [[self.ref_primary], [self.ref_secondary]],
        raise_on_exception=True,
    )
    utils.concurrent_exec(
        lambda d: d.pair_tws(),
        [[self.ref_primary], [self.ref_secondary]],
        raise_on_exception=True,
    )
    self.ref_primary.set_component_number(2)
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ref_primary.start_pairing_mode()

  def setup_test(self) -> None:
    bluetooth_utils.mbs_pair_devices(
        self.ad, self.ref_primary.bluetooth_address
    )
    bluetooth_utils.set_le_audio_state_on_paired_device(self.ad, True)

  def test_lea_connect_disconnect(self) -> None:
    android_address = self.ad.mbs.btGetAddress()

    with bluetooth_utils.open_device_detail_settings(self.ad):
      # Confirm the devices are connected.
      asserts.assert_true(
          self.ad.uia(text='Active').wait.exists(_WAIT_FOR_UI_UPDATE),
          '[Initial] Fail to confirm devices are connected.'
      )

      #################################################################
      # Trigger disconnection / reconnection from the Android side.
      #################################################################
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
      self.ad.uia(text='Disconnect').click()

      def is_disconnected() -> bool:
        button = self.ad.uia(text='Connect')
        return button.exists and button.enabled

      bluetooth_utils.assert_wait_condition_true(
          is_disconnected,
          _WAIT_FOR_UI_UPDATE,
          '[Disconnection test 1/2] Fail to disconnect from the Android'
          ' phone.',
      )

      time.sleep(_LONG_DELAYS_BETWEEN_ACTIONS.total_seconds())
      self.ad.uia(text='Connect').click()
      asserts.assert_true(
          self.ad.uia(text='Active').wait.exists(_WAIT_FOR_UI_UPDATE),
          '[Reconnection test 1/2] Fail to reconnect from the Android phone.'
      )


      #################################################################
      # Trigger disconnection / reconnection from the reference side.
      #################################################################
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
      utils.concurrent_exec(
          lambda d: d.disconnect(android_address),
          [[self.ref_primary], [self.ref_secondary]],
          raise_on_exception=True,
      )

      bluetooth_utils.assert_wait_condition_true(
          is_disconnected,
          _WAIT_FOR_UI_UPDATE,
          '[Disconnection test 2/2] Fail to disconnect from the Bluetooth'
          ' reference device.'
      )

      # Reconnect the headset
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
      utils.concurrent_exec(
          lambda d: d.connect(android_address),
          [[self.ref_primary], [self.ref_secondary]],
          raise_on_exception=True,
      )
      asserts.assert_true(
          self.ad.uia(text='Active').wait.exists(_WAIT_FOR_UI_UPDATE),
          '[Reconnection test 2/2] Fail to reconnect from the Bluetooth'
          ' reference device.'
      )

  def teardown_test(self) -> None:
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    utils.concurrent_exec(
        lambda d: d.create_output_excerpts(self.current_test_info),
        [[self.ref_primary], [self.ref_secondary]],
        raise_on_exception=True,
    )

  def teardown_class(self) -> None:
    bluetooth_utils.clear_bonded_devices(self.ad)


if __name__ == '__main__':
  test_runner.main()
