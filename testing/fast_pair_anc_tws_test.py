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

"""A Mobly Test to test Fast Pair ANC feature."""

import datetime
import re
import time

from mobly import asserts
from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

from testing import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)
_WAIT_FOR_UI_TRANSLATE = datetime.timedelta(seconds=20)
_WAIT_FOR_UI_UPDATE = datetime.timedelta(seconds=15)

# ANC slice title
_ANC_SLICE_TITLE = 'Noise cancellation|Active Noise Control|active noise control'
_ANC_GRAY_OUT_CONTENT_DESCRIPTION = 'Off'

# Fast Pair log pattern
_FAST_PAIR_TAG = 'NearbyDiscovery'
_ANC_MODE_DISCOVERED_PATTERN = (
    r'.*ActiveNoiseCancellationModule: update dataStore for mac=[A-Z0-9:]+, '
    r'AncVersionCode=[0-9], SupportedAncMode=(?P<supported_anc_mode>.*), '
    r'EnabledAncMode=(?P<enabled_anc_mode>.*), AncIndex=(?P<index>[0-9]).*'
)


class FastPairAncTwsTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test Fast Pair personalize name feature."""

  ad: android_device.AndroidDevice
  ref_primary: bluetooth_reference_device.BluetoothReferenceDeviceBase
  ref_secondary: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register an Android device controller.
    self.ad = self.register_controller(android_device)[0]
    bluetooth_utils.setup_android_device(
        self.ad,
        setup_fast_pair=True,
        enable_wifi=True,
        enable_le_audio=True,
    )

    # Register Bluetooth reference devices.
    refs = self.register_controller(bluetooth_reference_device, min_number=2)
    self.ref_primary, self.ref_secondary = bluetooth_utils.get_tws_device(refs)

  def _verify_anc_slice_gray_out(
      self,
      is_gray_out: bool,
  ) -> None:
    anc_gray_out_obj = (
        self.ad.uia(textMatches=_ANC_SLICE_TITLE)
        .top(clazz='android.widget.RadioButton'))
    if is_gray_out:
      asserts.assert_false(
          anc_gray_out_obj.enabled,
          'Failed to get ANC content description is Disabled when headset is'
          ' not on head.',
      )
    else:
      asserts.assert_true(
          anc_gray_out_obj.wait.exists(_WAIT_FOR_UI_TRANSLATE),
          'Get ANC content description is Disabled when headset is on head.',
      )

  def test_1_enable_anc_and_pair(self) -> None:
    self.ad.adb.shell('svc bluetooth disable')
    utils.concurrent_exec(
        lambda d, wait_access: d.factory_reset(wait_access),
        [[self.ref_primary, True], [self.ref_secondary, False]],
        raise_on_exception=True,
    )
    utils.concurrent_exec(
        lambda d: d.pair_tws(),
        [[self.ref_primary], [self.ref_secondary]],
        raise_on_exception=True,
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ref_primary.set_component_number(2)
    self.ref_primary.enable_anc()
    self.ref_primary.start_pairing_mode()
    self.ad.adb.shell('svc bluetooth enable')

    with self.ad.services.logcat_pubsub.event(
        pattern=_ANC_MODE_DISCOVERED_PATTERN,
        tag=_FAST_PAIR_TAG,
        level='I',
    ) as anc_event:
      bluetooth_utils.fast_pair_android_and_ref(
          self.ad, self.ref_primary.bluetooth_address
      )
      self.paired = True
      asserts.assert_true(
          anc_event.wait(timeout=_WAIT_FOR_UI_UPDATE),
          f'Fail to wait for ANC message stream event after Fast Pair.'
      )
      # Check ANC mode from message stream
      matched = re.match(
          _ANC_MODE_DISCOVERED_PATTERN, anc_event.trigger.message
      )
      supported_anc_modes = matched['supported_anc_mode'].split(',')
      enabled_anc_modes = matched['enabled_anc_mode'].split(',')
      active_index = int(matched['index'])
      asserts.assert_greater(
          len(supported_anc_modes), 0, 'Supported ANC mode count is 0'
      )
      for mode in enabled_anc_modes:
        asserts.assert_in(
            mode,
            supported_anc_modes, 
            (
                f'Enabled ANC mode "{mode}" not in supported ANC mode list '
                f'{supported_anc_modes}'
            ),
        )
      asserts.assert_greater(active_index, 0, 'ANC index should not be 0')

  def test_2_anc_ui_enable_when_on_head(self) -> None:
    asserts.skip_if(
        not hasattr(self, 'paired'),
        'Devices not paired. Skip following steps.',
    )

    self.ref_primary.set_on_head_state(True)
    time.sleep(_WAIT_FOR_UI_UPDATE.total_seconds())

    with bluetooth_utils.open_device_detail_settings(self.ad):
      # Check ANC slice shown in device detail and enabled
      asserts.assert_true(
          self.ad.uia(textMatches=_ANC_SLICE_TITLE).wait.exists(
              _WAIT_FOR_UI_TRANSLATE
          ),
          'Fail to find ANC slice from Device detail page when device is'
          ' connected.',
      )
      self.has_anc_slice = True
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
      self._verify_anc_slice_gray_out(is_gray_out=False)

  def test_3_anc_ui_change_when_mode_change(self):
    asserts.skip_if(
        not hasattr(self, 'has_anc_slice'),
        'ANC slice not shown in step 2. Skip following steps.',
    )

    self.ref_primary.set_anc_mode('transparent')
    time.sleep(_WAIT_FOR_UI_UPDATE.total_seconds())

    with bluetooth_utils.open_device_detail_settings(self.ad):
      # Check ANC slice shown in device detail and enabled
      asserts.assert_true(
          self.ad.uia(textContains='Transparency').wait.exists(
              _WAIT_FOR_UI_TRANSLATE
          ),
          'Fail to set ANC mode to transparent from board',
      )

  def test_4_anc_ui_gray_out_when_not_on_head(self):
    asserts.skip_if(
        not hasattr(self, 'has_anc_slice'),
        'ANC slice not shown in step 2. Skip following steps.',
    )

    self.ref_primary.set_on_head_state(False)
    time.sleep(_WAIT_FOR_UI_UPDATE.total_seconds())

    with bluetooth_utils.open_device_detail_settings(self.ad):
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
      self._verify_anc_slice_gray_out(is_gray_out=True)
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

  def test_step_5_hide_anc_slice_when_disconnected(self):
    asserts.skip_if(
        not hasattr(self, 'has_anc_slice'),
        'ANC slice not shown in step 2. Skip following steps.',
    )

    utils.concurrent_exec(
        lambda d: d.disconnect(self.ad.mbs.btGetAddress()),
        [[self.ref_primary], [self.ref_secondary]],
        raise_on_exception=True,
    )
    time.sleep(_WAIT_FOR_UI_UPDATE.total_seconds())

    with bluetooth_utils.open_device_detail_settings(self.ad):
      asserts.assert_false(
          self.ad.uia(textMatches=_ANC_SLICE_TITLE).wait.exists(
              _WAIT_FOR_UI_TRANSLATE
          ),
          'Fail to hide ANC slice in Device Detail when headset is disconnected'
          ' on phone.',
      )
      time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

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
