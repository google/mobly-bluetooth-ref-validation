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
import time

from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

from testing import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_MEDIA_PLAY_DURATION = datetime.timedelta(seconds=10)

_MEDIA_LOCAL_PATH = '/data/local/tmp/test_audio_music.wav'
_MEDIA_FILE = 'testing/assets/test_audio_music.wav'


class MediaPlayTest(bt_base_test.BtRefBaseTest):
  """Test media play on Android + Bluetooth reference device."""

  ad: android_device.AndroidDevice
  ref_primary: bluetooth_reference_device.BluetoothReferenceDeviceBase
  ref_secondary: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    bluetooth_utils.setup_android_device(self.ad, enable_le_audio=False)

    # Register Bluetooth reference devices.
    refs = self.register_controller(bluetooth_reference_device, min_number=2)
    self.ref_primary, self.ref_secondary = bluetooth_utils.get_tws_device(refs)

  def setup_test(self):
    # Pair the devices
    utils.concurrent_exec(
        lambda d, wait_access: d.factory_reset(wait_access),
        [[self.ref_primary, True], [self.ref_secondary, False]],
        raise_on_exception=True,
    )
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
    self.ref_primary.set_component_number(2)

    bluetooth_utils.mbs_pair_devices(self.ad, self.ref_primary.bluetooth_address)
    self.ad.mbs.btA2dpConnect(self.ref_primary.bluetooth_address.upper())

  def test_media_play(self):
    bt_address = self.ref_primary.bluetooth_address.upper()
    self.ad.adb.push([_MEDIA_FILE, _MEDIA_LOCAL_PATH])

    try:
      self.ad.mbs.media3StartLocalFile(_MEDIA_LOCAL_PATH)

      bluetooth_utils.assert_wait_condition_true(
          lambda: self.ad.mbs.media3IsPlayerPlaying(),
          fail_message='Failed to start playing media.',
      )
      bluetooth_utils.assert_wait_condition_true(
          lambda: self.ad.mbs.btIsA2dpPlaying(bt_address),
          fail_message='Failed to start playing media.',
      )
    finally:
      self.ad.mbs.media3Stop()

  def teardown_test(self):
    bluetooth_utils.clear_bonded_devices(self.ad, [self.ref_primary.bluetooth_address])
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    utils.concurrent_exec(
        lambda d: d.create_output_excerpts(self.current_test_info),
        [[self.ref_primary], [self.ref_secondary]],
        raise_on_exception=True,
    )


if __name__ == '__main__':
  test_runner.main()
