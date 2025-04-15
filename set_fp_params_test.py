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

"""Test Fast Pair parameter setters on Bluetooth reference device."""

import datetime
import time

from mobly import asserts
from mobly import test_runner
from mobly.controllers import android_device

import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import fast_pair_utils

_WAIT_FOR_UI_UPDATE = datetime.timedelta(seconds=30)
_FAST_PAIR_DISCOVER_TIME = datetime.timedelta(seconds=30)
_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)

_FAST_PAIR_TAG = 'NearbyDiscovery'
_MODEL_ID_DISCOVERED_PATTERN = (
    r'.*FastPairCache: device found with model id, mac=[A-Z0-9:]+, '
    r'(modelId|model-id)=({model_id_upper}|{model_id_lower}).*'
)

_MODEL_ID = 'C8633B'
_PRIVATE_KEY = 'qAVNQ2HH0iGpmw8sUaonUE50FXKXwr263/vDsSqDtog='


class SetFastPairParamsTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test Fast Pair parameters setter."""

  ad: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self):
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    fast_pair_utils.setup_android_device(self.ad, setup_fast_pair=True)

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]
    self.ref.factory_reset()

  def test_set_model_id_and_private_key(self):
    self.ref.set_fp_params(model_id=_MODEL_ID, private_key=_PRIVATE_KEY)

    #################################################################
    # Android discover reference device via Fast Pair
    #################################################################
    # Check the model ID discovered
    with self.ad.services.logcat_pubsub.event(
        pattern=_MODEL_ID_DISCOVERED_PATTERN.format(
            model_id_upper=_MODEL_ID.upper(),
            model_id_lower=_MODEL_ID.lower(),
        ),
        tag=_FAST_PAIR_TAG,
        level='I',
    ) as discovery_event:
      fast_pair_utils.clear_android_fast_pair_cache(self.ad)
      asserts.assert_true(
          discovery_event.wait(timeout=_FAST_PAIR_DISCOVER_TIME),
          f'Fail to find device with model ID {_MODEL_ID}.'
      )

    #################################################################
    # Android pair with reference device via Fast Pair
    #################################################################
    # Click 'Connect' button in the Fast Pair half sheet.
    asserts.assert_true(
        self.ad.uia(text='Connect').wait.click(_WAIT_FOR_UI_UPDATE),
        'Fail to press connect button on displayed halfsheet.',
    )

    # Expect 'Device connected' message and then click 'Done' button.
    asserts.assert_true(
        self.ad.uia(text='Device connected').wait.exists(_WAIT_FOR_UI_UPDATE),
        'Fail to show "Device connected" keyword on the halfsheet after'
        ' pairing.',
    )
    self.ad.uia(text='Done').click()

    # Confirm the devices are connected.
    fast_pair_utils.assert_device_bonded_via_address(
        self.ad,
        self.ref.bluetooth_address,
    )

  def teardown_test(self):
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    self.ref.create_output_excerpts(self.current_test_info)


if __name__ == '__main__':
  test_runner.main()
