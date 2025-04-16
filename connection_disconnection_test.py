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

from mobly import test_runner
from mobly.controllers import android_device

import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)


class ConnectionDisconnectionTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test basic Bluetooth connection on Android + BT ref."""

  ad: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    bluetooth_utils.setup_android_device(self.ad)

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]

  def setup_test(self) -> None:
    self.ref.factory_reset()
    bluetooth_utils.mbs_pair_devices(self.ad, self.ref.bluetooth_address)
    bluetooth_utils.set_le_audio_state_on_paired_device(self.ad, False)

  def test_connect_disconnect(self) -> None:
    android_address = self.ad.mbs.btGetAddress()
    ref_address = self.ref.bluetooth_address.upper()

    # Confirm the devices are connected.
    bluetooth_utils.assert_device_connected(
        self.ad,
        ref_address,
        fail_message=(
            '[Initial] Fail to confirm devices are connected.'
        ),
    )

    #################################################################
    # Trigger disconnection / reconnection from the Android side.
    #################################################################
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ad.mbs.btA2dpDisconnect(ref_address)
    bluetooth_utils.assert_device_disconnected(
        self.ad,
        ref_address,
        fail_message=(
            '[Disconnection test 1/2] Fail to disconnect from the Android'
            ' phone.'
        ),
    )

    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ad.mbs.btA2dpConnect(ref_address)
    bluetooth_utils.assert_device_connected(
        self.ad,
        ref_address,
        fail_message=(
            '[Reconnection test 1/2] Fail to reconnect from the Android phone.'
        ),
    )

    #################################################################
    # Trigger disconnection / reconnection from the reference side.
    #################################################################
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ref.disconnect(android_address)
    bluetooth_utils.assert_device_disconnected(
        self.ad,
        ref_address,
        fail_message=(
            '[Disconnection test 2/2] Fail to disconnect from the Bluetooth'
            ' reference device.'
        ),
    )

    # Reconnect the headset
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ref.connect(android_address)
    bluetooth_utils.assert_device_connected(
        self.ad,
        ref_address,
        fail_message=(
            '[Reconnection test 2/2] Fail to reconnect from the Bluetooth'
            ' reference device.'
        ),
    )

  def teardown_test(self) -> None:
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    self.ref.create_output_excerpts(self.current_test_info)
    bluetooth_utils.clear_bonded_devices(self.ad)
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())


if __name__ == '__main__':
  test_runner.main()
