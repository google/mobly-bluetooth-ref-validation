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

"""Test A2DP media play on Android + Bluetooth reference device."""

import datetime
import logging
import time

from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

from testing import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_MEDIA_PLAY_DURATION = datetime.timedelta(seconds=10)

_AUDIO_FILE_PATH = 'testing/assets/test_audio_music.wav'


class MediaPlayTest(bt_base_test.BtRefBaseTest):
  """Test media play on Android + Bluetooth reference device."""

  ad: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self):
    super().setup_class()

    # Register an Android device controller
    self.ad = self.register_controller(android_device)[0]
    bluetooth_utils.setup_android_device(self.ad)

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]

  def setup_test(self):
    # Pair the devices
    self.ref.factory_reset()
    self.ref.set_component_number(1)
    self.ref.start_pairing_mode()

    bluetooth_utils.mbs_pair_devices(self.ad, self.ref.bluetooth_address)
    bluetooth_utils.set_le_audio_state_on_paired_device(
        self.ad, False, skip_if_no_button=True
    )
    self.ad.mbs.btA2dpConnect(self.ref.bluetooth_address.upper())

  def test_media_play(self):
    bt_address = self.ref.bluetooth_address.upper()

    # Start audio playing
    with bluetooth_utils.push_and_play_audio_on_android(
        self.ad, _AUDIO_FILE_PATH
    ):
      bluetooth_utils.assert_wait_condition_true(
          lambda: self.ad.mbs.btIsA2dpPlaying(bt_address),
          fail_message='Failed to start playing media.',
      )
      time.sleep(_MEDIA_PLAY_DURATION.total_seconds())

  def teardown_test(self):
    bluetooth_utils.clear_bonded_devices(self.ad)
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    self.ref.create_output_excerpts(self.current_test_info)


if __name__ == '__main__':
  test_runner.main()
