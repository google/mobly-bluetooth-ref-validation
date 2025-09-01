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

"""Test Bluetooth disable spatial audio feature of reference device."""

import datetime
import time
import uuid

from mobly import asserts
from mobly import test_runner
from mobly.controllers import android_device

from testing import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)
_WAIT_FOR_UI_TRANSLATE = datetime.timedelta(seconds=6)
_WAIT_FOR_UI_UPDATE = datetime.timedelta(seconds=30)

_SPATIAL_AUDIO_TITLE = 'Spatial Audio'


class SpatialAudioDisableTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test spatial audio disable feature of reference device."""

  ad: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    self.ad.reboot()
    bluetooth_utils.setup_android_device(self.ad)

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]
    self.ref.factory_reset()
    self.ref.set_component_number(1)

  def test_disable_spatial_audio(self) -> None:
    self.ref.disable_spatial_audio()
    self.ref.start_pairing_mode()

    # Pair the Android phone with ref.
    bluetooth_utils.assert_device_discovered(
      self.ad, self.ref.bluetooth_address
    )
    bluetooth_utils.mbs_pair_with_retry(self.ad, self.ref.bluetooth_address)
    bluetooth_utils.assert_device_bonded_via_address(
      self.ad, self.ref.bluetooth_address
    )

    # Enable Spatial Audio buttton state
    with bluetooth_utils.open_device_detail_settings(self.ad):
      self.ad.log.info('Scroll to find Spatial Audio button.')
      self.ad.uia(scrollable=True).scroll.down(text=_SPATIAL_AUDIO_TITLE)

      if self.ad.uia(text=_SPATIAL_AUDIO_TITLE).wait.exists(
          _WAIT_FOR_UI_TRANSLATE
      ):
        self.ad.log.info('Found Spatial Audio button.')
        spatial_audio_switch = self.ad.uia(text=_SPATIAL_AUDIO_TITLE).right(
            clazz='android.widget.Switch'
        )
        if spatial_audio_switch.checked and spatial_audio_switch.enabled:
          asserts.fail(
              'Failed to disable spatial Spatial Audio. '
              'Spatial Audio button still shown and active in Device Detail.'
          )

  def teardown_test(self) -> None:
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    self.ref.create_output_excerpts(self.current_test_info)
    bluetooth_utils.clear_bonded_devices(self.ad)


if __name__ == '__main__':
  test_runner.main()
