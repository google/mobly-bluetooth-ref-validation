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

"""Test LE audio control on Android + Bluetooth reference device."""

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

_MEDIA_LOCAL_PATH = '/data/local/tmp/test_audio_music.wav'
_MEDIA_FILE = 'testing/assets/test_audio_music.wav'

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=3)
_MEDIA_PLAY_DURATION = datetime.timedelta(seconds=10)


class LEAudioControlTest(bt_base_test.BtRefBaseTest):
  """Test class for LE Audio control test on Android + reference device."""

  ad: android_device.AndroidDevice
  ref_primary: bluetooth_reference_device.BluetoothReferenceDeviceBase
  ref_secondary: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    bluetooth_utils.setup_android_device(
        self.ad, enable_wifi=True, enable_le_audio=True
    )

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
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ref_primary.start_pairing_mode()

  def test_1_pair_bes_and_enable_le_audio(self):
    # Discover and pair the devices
    bluetooth_utils.mbs_pair_devices(
        self.ad, self.ref_primary.bluetooth_address
    )
    self.ref_primary.set_on_head_state(True)
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    self.lea_enabled = True

  def test_2_media_control(self):
    asserts.skip_if(
        not hasattr(self, 'lea_enabled'),
        'LEA not enabled. Skip following steps.',
    )

    # Open Youtube and start playing video.
    # We can't use Mobly snippet to play audio here because the audio played by
    # MBS cannot be paused from the headset.
    try:
      ref_address = self.ref_primary.bluetooth_address.upper()
      self.ad.adb.push([_MEDIA_FILE, _MEDIA_LOCAL_PATH])
      self.ad.mbs.media3StartLocalFile(_MEDIA_LOCAL_PATH)

      bluetooth_utils.assert_wait_condition_true(
          lambda: self.ad.mbs.media3IsPlayerPlaying(),
          fail_message='Failed to start playing media.',
      )
      bluetooth_utils.assert_wait_condition_true(
          lambda: bluetooth_utils.is_media_route_on_lea(self.ad, ref_address),
          fail_message='Failed to start playing media.',
      )

      #################################################################
      # Volume control
      #################################################################
      target_volume = 100
      self.ref_primary.set_volume(target_volume)
      asserts.assert_almost_equal(
          self.ref_primary.get_ble_volume(), target_volume, delta=5
      )

      initial_volume = self.ad.mbs.getMusicVolume()
      self.ref_primary.volume_up(10)
      bluetooth_utils.assert_wait_condition_true(
          lambda: self.ad.mbs.getMusicVolume() > initial_volume,
          fail_message='Failed to increase media volume.',
      )

      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
      initial_volume = self.ad.mbs.getMusicVolume()
      self.ref_primary.volume_down(10)
      bluetooth_utils.assert_wait_condition_true(
          lambda: self.ad.mbs.getMusicVolume() < initial_volume,
          fail_message='Failed to decrease media volume.',
      )

      #################################################################
      # Media pause/play
      #################################################################
      self.ref_primary.media_pause()
      bluetooth_utils.assert_wait_condition_true(
          lambda: not self.ad.mbs.media3IsPlayerPlaying(),
          fail_message='Failed to pause media.',
      )

      self.ref_primary.media_play()
      bluetooth_utils.assert_wait_condition_true(
          lambda: self.ad.mbs.media3IsPlayerPlaying(),
          fail_message='Failed to pause media.',
      )
      bluetooth_utils.assert_wait_condition_true(
          lambda: bluetooth_utils.is_media_route_on_lea(self.ad, ref_address),
          fail_message='Failed to replay media.',
      )

      #################################################################
      # Media fast forward/backward
      #################################################################
      # No assertions. Need to manually check the video and audio.
      self.ref_primary.media_next()
      time.sleep(_MEDIA_PLAY_DURATION.total_seconds())

      self.ref_primary.media_prev()
      time.sleep(_MEDIA_PLAY_DURATION.total_seconds())
    finally:
      # Stops video playing
      self.ad.mbs.media3Stop()

    self.ad.log.info('Finished media streaming.')

  def teardown_test(self) -> None:
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
