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

"""Test power on/off changes Fast Pair advertising state."""

import datetime
import sys

from mobly import asserts
from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

from testing import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

# Constants for timeouts
_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)
_INITIAL_PAIR_DISCOVER_TIME = datetime.timedelta(seconds=30)
_SUBSEQUENT_PAIR_CONNECTION_TIME = datetime.timedelta(seconds=90)
_WAIT_FOR_UI_UPDATE = datetime.timedelta(seconds=30)

# Constants for the widget resource ID
_FAST_PAIR_HALFSHEET_IMAGE_ID = 'com.google.android.gms:id/image_view'

_FAST_PAIR_TAG = 'NearbyDiscovery'
_BLOOM_FILTER_CHANGED_PATTERN = (
    r'.*FastPairCache: Bloom filter changed, mac=[A-Z0-9:]+, '
    r'newData=(?P<bloom_filter_data>[A-Za-z0-9]+).*'
)
_BLOOM_FILTER_DISCOVERED_PATTERN = (
    r'.*FastPairCache: Bloom filter changed, mac=(?P<address>[A-Z0-9:]+), '
    r'newData={bloom_filter_data}.*'
)
_BLOOM_FILTER_CHECKED_PATTERN = (
    r'.*FastPair: Checking bloom filter BleAdvHandler.*, mac={address},.*'
)


def grep_pattern_from_logcat(
    ad: android_device.AndroidDevice, pattern: str
) -> list[str]:
  if sys.platform == 'win32':
    cmd = [
        'powershell',
        'Get-Content',
        f'-Path "{ad.services.logcat.adb_logcat_file_path}"',
    ]
  else:
    cmd = ['cat', ad.services.logcat.adb_logcat_file_path]
  (return_code, out, err) = utils.run_command(cmd)
  return utils.grep(pattern, out)


class FastPairPowerOnOffTest(bt_base_test.BtRefBaseTest):
  """Test class for subsequent pairing test on Android + BT reference."""

  ad_a: android_device.AndroidDevice
  ad_b: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self):
    super().setup_class()

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]

    # Register two Android device controllers.
    ads = self.register_controller(android_device, 2)
    self.ad_a, self.ad_b = ads
    utils.concurrent_exec(
        bluetooth_utils.setup_android_device,
        [
            [self.ad_a, True, True, True],
            [self.ad_b, True, True, True],
        ],
        raise_on_exception=True,
    )

  def setup_test(self):
    self.ref.factory_reset()
    self.ref.set_component_number(1)
    self.ref.start_pairing_mode()

  def test_fast_pair_power_on_off(self):
    bloom_filter = None
    #################################################################
    # Pair the first Android phone and check bloom filter.
    #################################################################
    with self.ad_a.services.logcat_pubsub.event(
        pattern=_BLOOM_FILTER_CHANGED_PATTERN,
        tag=_FAST_PAIR_TAG,
        level='I',
    ) as bloom_filter_change_event:
      bluetooth_utils.fast_pair_android_and_ref(
          self.ad_a, self.ref.bluetooth_address
      )
      asserts.assert_true(
          bloom_filter_change_event.wait(timeout=_WAIT_FOR_UI_UPDATE),
          f'Fail to wait for bloom filter update after Fast Pair.'
      )
      # Get new bloom filter from log
      matched = re.match(
          _BLOOM_FILTER_CHANGED_PATTERN,
          bloom_filter_change_event.trigger.message,
      )
      bloom_filter = matched['bloom_filter_data']

    #################################################################
    # Find new BLE address with target bloom filter
    #################################################################
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    pattern = _BLOOM_FILTER_DISCOVERED_PATTERN.format(
        bloom_filter_data=bloom_filter
    )
    matched = grep_pattern_from_logcat(self.ad_b, pattern)
    if matched:
      rotated_address = re.search(pattern, matched[0])['address']
    else:
      asserts.fail('Failed to find bloom filter changed message on phone B')

    #################################################################
    # Power off BT ref, `ad_a` disconnect and bloom filter no more received
    #################################################################
    with self.ad_b.services.logcat_pubsub.event(
        pattern=_BLOOM_FILTER_CHECKED_PATTERN.format(
            address=rotated_address
        ),
        tag=_FAST_PAIR_TAG,
        level='I',
    ) as bloom_filter_event:
      # TODO: Replace with `power_off` API when ready
      self.ref.close_box()
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

      bluetooth_utils.assert_device_disconnected(
          self.ad_a,
          self.ref.bluetooth_address,
          fail_message='Fail to power off. Board is still connected with Android after 30s',
      )
      asserts.assert_false(
          bloom_filter_event.wait(timeout=_WAIT_FOR_UI_UPDATE),
          f'Fail to wait for bloom filter disappear after BT ref power off.'
      )

    #################################################################
    # Power on BT ref, `ad_a` reconnect and bloom filter received
    #################################################################
    with self.ad_b.services.logcat_pubsub.event(
        pattern=_BLOOM_FILTER_CHECKED_PATTERN.format(
            address=rotated_address
        ),
        tag=_FAST_PAIR_TAG,
        level='I',
    ) as bloom_filter_event:
      # TODO: Replace with `power_on` API when ready
      self.ref.open_box()
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

      bluetooth_utils.assert_device_connected(
          self.ad_a,
          self.ref.bluetooth_address,
          fail_message='Fail to power on. Board is not re-connected with Android after 30s',
      )
      asserts.assert_true(
          bloom_filter_event.wait(timeout=_WAIT_FOR_UI_UPDATE),
          f'Fail to wait for bloom filter appear after BT ref power on.'
      )

  def teardown_test(self):
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    utils.concurrent_exec(
        bluetooth_utils.clear_bonded_devices,
        [[self.ad_a], [self.ad_b]],
        raise_on_exception=True,
    )
    utils.concurrent_exec(
        lambda d: d.services.create_output_excerpts_all(self.current_test_info),
        param_list=[[self.ad_a], [self.ad_b]],
        raise_on_exception=True,
    )
    self.ref.create_output_excerpts(self.current_test_info)


if __name__ == '__main__':
  test_runner.main()
