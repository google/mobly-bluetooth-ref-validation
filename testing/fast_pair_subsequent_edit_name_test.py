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

"""A Mobly Test to test Fast Pair personalize name feature."""

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

# Constants for the regex string
_FAST_PAIR_TAG = 'FastPair'
_INITIAL_NAME_PATTERN = (
    r'.*FPDC: getProviderDeviceName: Name decrypted, '
    r'deviceName="(?P<name>.*)".*'
)
_UPDATE_NAME_PATTERN = (
  r'.*FPDC: setProviderDeviceNameForUpdate: Set provider name, '
  r'deviceName="(?P<name>.*)".*'
)
_RX_RENAME_TEXT = r'(Rename|RENAME)'


class FastPairSubsequentEditNameTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test Fast Pair ring my device feature."""

  initial_pair_phone: android_device.AndroidDevice
  subsequent_pair_phone: android_device.AndroidDevice
  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self):
    super().setup_class()

    # Register two Android device controllers.
    ads = self.register_controller(android_device, 2)
    self.initial_pair_phone, self.subsequent_pair_phone = ads
    utils.concurrent_exec(
        lambda ad: bluetooth_utils.setup_android_device(ad, enable_fast_pair=True),
        [[self.initial_pair_phone], [self.subsequent_pair_phone]],
        raise_on_exception=True,
    )

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]

    self.device_name = None
    self.new_device_name = None

  def test_1_initial_pair_with_null_name(self):
    self.initial_pair_phone.adb.shell('svc bluetooth disable')
    self.ref.factory_reset()
    self.ref.set_component_number(1)
    self.ref.start_pairing_mode()
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.initial_pair_phone.adb.shell('svc bluetooth enable')

    with self.initial_pair_phone.services.logcat_pubsub.event(
        pattern=_INITIAL_NAME_PATTERN,
        tag=_FAST_PAIR_TAG,
        level='I',
    ) as initial_name_event:
      with self.initial_pair_phone.services.logcat_pubsub.event(
          pattern=_UPDATE_NAME_PATTERN,
          tag=_FAST_PAIR_TAG,
          level='I',
      ) as update_name_event:
        bluetooth_utils.fast_pair_android_and_ref(
            self.initial_pair_phone, self.ref.bluetooth_address
        )
        asserts.assert_true(
            initial_name_event.wait(timeout=_FAST_PAIR_PAIR_TIME),
            'The initial paired device has no initial name.'
        )
        matched = re.match(
            _INITIAL_NAME_PATTERN, initial_name_event.trigger.message
        )
        if matched['name'] != 'null' and matched['name'] != 'NULL':
          asserts.fail(
            'Factory reset failed to reset Fast Pair name. '
            'The initial name of paired device is not NULL.'
          )
        if update_name_event.wait(timeout=_FAST_PAIR_PAIR_TIME):
          if match := re.match(
              _UPDATE_NAME_PATTERN, update_name_event.trigger.message
          ):
            self.device_name = match['name']
            logging.info('Updated name: %s', self.device_name)

  def test_2_edit_name(self):
    asserts.skip_if(
        self.device_name is None,
        'No device name from step 1 after initial pair',
    )

    device_rename_text = f'{self.device_name}_rename'
    with bluetooth_utils.open_system_settings(self.initial_pair_phone):
      asserts.assert_true(
          self.initial_pair_phone.uia(textContains=self.device_name).wait.exists(
              _WAIT_FOR_UI_UPDATE
          ),
          f'Fail to find {self.device_name} through saved devices in settings'
      )
      self.initial_pair_phone.uia(res='com.android.settings:id/settings_button').click()
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
      asserts.assert_true(
          self.initial_pair_phone.uia(textContains=self.device_name).wait.exists(
              _WAIT_FOR_UI_UPDATE
          ),
          f'Fail to find {self.device_name} in device detail page',
      )
      asserts.assert_true(
          self.initial_pair_phone.uia(descriptionMatches=_RX_RENAME_TEXT).wait.click(
              _WAIT_FOR_UI_UPDATE
          ),
          'Fail to click Rename button',
      )
      rename_edit_text = self.initial_pair_phone.uia(
          resourceId='com.android.settings:id/edittext',
          className='android.widget.EditText',
      )
      rename_edit_text.set_text(device_rename_text)
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
      asserts.assert_true(
          self.initial_pair_phone.uia(
              resourceId='android:id/button1',
              textMatches=_RX_RENAME_TEXT,
          ).wait.click(_WAIT_FOR_UI_UPDATE.total_seconds()),
          'Fail to click store Rename button',
      )
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
      asserts.assert_true(
          self.initial_pair_phone.uia(text=device_rename_text).wait.exists(),
          'Fail to rename headset',
      )
      self.new_device_name = device_rename_text

  def test_3_subsequent_pair_with_new_device_name(self):
    asserts.skip_if(
        self.new_device_name is None,
        'No device name from step 1 after initial pair',
    )

    bluetooth_utils.fast_pair_subsequent_pair_android_and_ref(
        self.subsequent_pair_phone, self.ref.bluetooth_address
    )
    with bluetooth_utils.open_system_settings(self.subsequent_pair_phone):
      asserts.assert_true(
          self.subsequent_pair_phone.uia(
              textContains=self.new_device_name
          ).wait.exists(_WAIT_FOR_UI_UPDATE),
          'Personalized name not set on the subsequent pair device.'
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
