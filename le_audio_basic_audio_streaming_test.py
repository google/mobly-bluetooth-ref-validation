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

"""Test LE audio on Android + Bluetooth reference device."""

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
# from testing.utils import audio_recorder

_AUDIO_FILE_PATH = 'testing/assets/test_audio_music.wav'

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=3)
_AUDIO_PLAY_DURATION = datetime.timedelta(seconds=15)
_AUDIO_PLAY_INTERVAL = datetime.timedelta(seconds=10)

# Regex for detection of LE Audio streaming success logcat line
_LE_AUDIO_STREAMING_PATTERN = r'.*ASE state: Streaming \(0x4\).*'
_BT_LOGCAT_TAG = 'bluetooth'


class LEAudioTest(bt_base_test.BtRefBaseTest):
  """Test class for LE Audio test on Android + Bluetooth reference device."""

  ad: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self):
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    bluetooth_utils.setup_android_device(self.ad)

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]
    self.ref.factory_reset()

    # # Init audio recorder
    # self.recorder = audio_recorder.AudioRecorder()

  def test_1_pair_ref_and_enable_le_audio(self):
    # Discover and pair the devices
    bluetooth_utils.mbs_pair_devices(self.ad, self.ref.bluetooth_address)
    self.ref.set_on_head_state(True)
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    # Enable LE Audio on Android
    self.ad.log.info('Enabling LE Audio...')
    bluetooth_utils.set_le_audio_state_on_paired_device(self.ad, True)
    self.ad.log.info('LE Audio enabled.')
    self.lea_enabled = True

  def test_2_audio_streaming(self):
    asserts.skip_if(
        not hasattr(self, 'lea_enabled'),
        'LEA not enabled. Skip following steps.',
    )
    # Record the music play
    # logging.info('Start recording.')
    # utils.create_dir(self.current_test_info.output_path)
    # self.recorder.start(output_dir=self.current_test_info.output_path)

    # Start audio playing
    self.ad.log.info('Start playing audio...')
    with bluetooth_utils.push_and_play_audio_on_android(
        self.ad, _AUDIO_FILE_PATH
    ):
      # Check the ASE state is Streaming
      with self.ad.services.logcat_pubsub.event(
          pattern=_LE_AUDIO_STREAMING_PATTERN, tag=_BT_LOGCAT_TAG, level='I'
      ) as ase_state_event:
        asserts.assert_true(
            ase_state_event.wait(timeout=_AUDIO_PLAY_DURATION),
            'Failed to start LEA streaming after playing music for 15 seconds',
        )
      time.sleep(_AUDIO_PLAY_INTERVAL.total_seconds())

    self.ad.log.info('Finished audio playing.')

  def teardown_test(self):
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    self.ref.create_output_excerpts(self.current_test_info)

  def teardown_class(self):
    bluetooth_utils.clear_bonded_devices(self.ad)
    # self.recorder.stop()

if __name__ == '__main__':
  test_runner.main()
