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

"""A Mobly Test to test Fast Pair ANC mode sync feature."""

import datetime
import logging
import re
import time

from mobly import asserts
from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

from testing import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_WAIT_FOR_UI_UPDATE = datetime.timedelta(seconds=30)
_FAST_PAIR_PAIR_TIME = datetime.timedelta(seconds=30)
_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)

# ANC slice title
_ANC_SLICE_TITLE = 'Active Noise Control'
_ANC_GRAY_OUT_CONTENT_DESCRIPTION = 'Disabled'
_ANC_MODE_OFF_SUMMARY = 'Noise Control off'
_ANC_MODE_OFF = 'Off'
_ANC_MODE_ON_SUMMARY = 'Active Noise Cancellation on'
_ANC_MODE_ON = 'Noise Cancellation'
_ANC_MODE_TRANSPARENT_SUMMARY = 'Transparency mode on'
_ANC_MODE_TRANSPARENT = 'Transparency'


# Fast Pair log pattern
_FAST_PAIR_TAG = 'NearbyDiscovery'
_ANC_MODE_DISCOVERED_PATTERN = (
    r'.*ActiveNoiseCancellationModule: update dataStore for mac=[A-Z0-9:]+, '
    r'AncVersionCode=[0-9], SupportedAncMode=(?P<supported_anc_mode>.*), '
    r'EnabledAncMode=(?P<enabled_anc_mode>.*), AncIndex=(?P<index>[0-9]).*'
)


class FastPairAncModeSyncTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test Fast Pair ANC mode sync feature."""

  initial_pair_phone: android_device.AndroidDevice
  subsequent_pair_phone: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self):
    super().setup_class()

    # Register two Android device controllers.
    ads = self.register_controller(android_device, 2)
    self.initial_pair_phone, self.subsequent_pair_phone = ads
    utils.concurrent_exec(
        bluetooth_utils.setup_android_device,
        [
            [self.initial_pair_phone, True, True, True],
            [self.subsequent_pair_phone, True, True, True],
        ],
        raise_on_exception=True,
    )

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]

  def test_1_initial_pair_and_verify_anc(self):
    self.initial_pair_phone.adb.shell('svc bluetooth disable')
    self.ref.factory_reset()
    self.ref.set_component_number(1)
    self.ref.start_pairing_mode()
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.initial_pair_phone.adb.shell('svc bluetooth enable')

    with self.initial_pair_phone.services.logcat_pubsub.event(
        pattern=_ANC_MODE_DISCOVERED_PATTERN,
        tag=_FAST_PAIR_TAG,
        level='I',
    ) as anc_event:
      bluetooth_utils.fast_pair_android_and_ref(
          self.initial_pair_phone, self.ref.bluetooth_address
      )
      asserts.assert_true(
          anc_event.wait(timeout=_WAIT_FOR_UI_UPDATE),
          f'Fail to wait for ANC message stream event after Fast Pair.'
      )
      # Check ANC mode from message stream
      matched = re.match(
          _ANC_MODE_DISCOVERED_PATTERN, anc_event.trigger.message
      )
      self.supported_anc_modes = matched['supported_anc_mode'].split(',')
      self.enabled_anc_modes = matched['enabled_anc_mode'].split(',')
      self.active_index = int(matched['index'])
      asserts.assert_greater(
          len(self.supported_anc_modes), 0, 'Supported ANC mode count is 0'
      )
      for mode in self.enabled_anc_modes:
        asserts.assert_in(
            mode,
            self.supported_anc_modes, 
            (
                f'Enabled ANC mode "{mode}" not in supported ANC mode list '
                f'{self.supported_anc_modes}'
            ),
        )
      asserts.assert_greater(self.active_index, 0, 'ANC index should not be 0')

  def test_2_subsequent_pair_verify_anc(self):
    asserts.skip_if(
        not hasattr(self, 'active_index'),
        'Devices not paired and have valid anc status. Skip following steps.',
    )

    bluetooth_utils.fast_pair_subsequent_pair_android_and_ref(
        self.subsequent_pair_phone, self.ref.bluetooth_address
    )
    self.paired_second = True

    with bluetooth_utils.open_device_detail_settings(self.subsequent_pair_phone):
      asserts.assert_true(
          self.subsequent_pair_phone.uia(text=_ANC_SLICE_TITLE).wait.exists(
              _WAIT_FOR_UI_UPDATE
          ),
          'Fail to find ANC slice from Device detail page when device is'
          ' connected.',
      )

  def test_3_change_anc_mode_verify_mode_sync(self):
    asserts.skip_if(
        not hasattr(self, 'paired_second'),
        'Not paired with second device, abort.',
    )

    self.ref.set_on_head_state(True)
    time.sleep(_WAIT_FOR_UI_UPDATE.total_seconds())

    with bluetooth_utils.open_device_detail_settings(self.initial_pair_phone):
      # Verify the anc mode on phone A as precondition.
      if self.initial_pair_phone.uia(
          textContains=_ANC_MODE_OFF_SUMMARY
      ).wait.exists(_WAIT_FOR_UI_UPDATE):
        target_anc_mode = _ANC_MODE_ON
        target_summary = _ANC_MODE_ON_SUMMARY
      else:
        target_anc_mode = _ANC_MODE_OFF
        target_summary = _ANC_MODE_OFF_SUMMARY

      with bluetooth_utils.open_device_detail_settings(self.subsequent_pair_phone):
        # Click target ANC button on phone A
        asserts.assert_true(
            self.initial_pair_phone.uia(
                text=target_anc_mode
            ).parent.wait.click(_WAIT_FOR_UI_UPDATE),
            f'Failed to click ANC mode - {target_anc_mode} button in on phone A',
        )
        time.sleep(_WAIT_FOR_UI_UPDATE.total_seconds())
        asserts.assert_true(
            self.initial_pair_phone.uia(
                textContains=target_summary
            ).wait.exists(_WAIT_FOR_UI_UPDATE),
            f'Failed to show "{target_summary}" in ANC summary from phone A',
        )
        asserts.assert_true(
            self.subsequent_pair_phone.uia(
                textContains=target_summary
            ).wait.exists(_WAIT_FOR_UI_UPDATE),
            f'Failed to show "{target_summary}" in ANC summary from phone B',
        )

  def test_4_set_anc_mode_from_board_verify_mode_sync(self):
    asserts.skip_if(
        not hasattr(self, 'paired_second'),
        'Not paired with second device, abort.',
    )

    self.ref.set_anc_mode('transparency')
    time.sleep(_WAIT_FOR_UI_UPDATE.total_seconds())

    with bluetooth_utils.open_device_detail_settings(self.initial_pair_phone):
      # Verify the anc mode is transparency on phone A.
      asserts.assert_true(
          self.initial_pair_phone.uia(
              textContains=_ANC_MODE_TRANSPARENT_SUMMARY
          ).wait.exists(_WAIT_FOR_UI_UPDATE),
          'Not showing ANC mode - Transparency in ANC summary from phone A.'
          ' Failed to set ANC mode.',
      )
      with bluetooth_utils.open_device_detail_settings(self.subsequent_pair_phone):
        # Verify the anc mode is transparency on phone B.
        asserts.assert_true(
            self.subsequent_pair_phone.uia(
                textContains=_ANC_MODE_TRANSPARENT_SUMMARY
            ).wait.exists(_WAIT_FOR_UI_UPDATE),
            'Not showing ANC mode - Transparency in ANC summary from phone B.'
            ' Failed to set ANC mode.',
        )

  def teardown_test(self):
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    utils.concurrent_exec(
        lambda d: d.services.create_output_excerpts_all(self.current_test_info),
        param_list=[[self.initial_pair_phone], [self.subsequent_pair_phone]],
        raise_on_exception=True,
    )
    self.ref.create_output_excerpts(self.current_test_info)

  def teardown_class(self):
    utils.concurrent_exec(
        bluetooth_utils.clear_bonded_devices,
        [[self.initial_pair_phone], [self.subsequent_pair_phone]],
        raise_on_exception=True,
    )


if __name__ == '__main__':
  test_runner.main()
