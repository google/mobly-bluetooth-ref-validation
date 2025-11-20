"""A Mobly Test to test Fast Pair initial pairing on reference device."""

import datetime
import logging
import re
import time

from mobly import asserts
from mobly import base_test
from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

from testing import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device
from testing.utils import bluetooth_utils

_WAIT_FOR_UI_UPDATE = datetime.timedelta(seconds=30)
_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)

_BATTERY_LEFT = 90
_BATTERY_RIGHT = 70
_BATTERY_CASE = 80
_BATTERY_LEFT_LOW = 10
_BATTERY_RIGHT_LOW = 10
_BATTERY_CASE_LOW = 90

# Fast Pair log pattern
_FAST_PAIR_TAG = 'NearbyDiscovery'
_BATTERY_LEVEL_PATTERN = (
    r'.*handle battery=(?P<battery_level>[0-9A-F]*).*'
)


class FastPairSetBatteryTwsTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test Fast Pair initial pairing on reference device."""

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
    self.ref_primary.set_component_number(2)
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ref_primary.start_pairing_mode()

  def test_1_fast_pair_initial_pair_check_battery(self):
    self.ref_primary.set_battery_level_tws(
        _BATTERY_LEFT, _BATTERY_RIGHT, _BATTERY_CASE
    )

    # battery_level is updated show on phone But cannot be read back from 
    # bluetooth ref device
    # (battery_left, battery_right, battery_case) = (
    #     self.ref_primary.get_battery_level_tws()
    # )
    # asserts.assert_equal(battery_left, _BATTERY_LEFT)
    # asserts.assert_equal(battery_right, _BATTERY_RIGHT)
    # asserts.assert_equal(battery_case, _BATTERY_CASE)

    with self.ad.services.logcat_pubsub.event(
        pattern=_BATTERY_LEVEL_PATTERN,
        tag=_FAST_PAIR_TAG,
        level='I',
    ) as battery_event:
      bluetooth_utils.fast_pair_android_and_ref(
          self.ad, self.ref_primary.bluetooth_address
      )
      asserts.assert_true(
          battery_event.wait(timeout=_WAIT_FOR_UI_UPDATE),
          f'Fail to wait for battery message stream event after Fast Pair.'
      )
      # Check battery level from message stream
      matched = re.match(
          _BATTERY_LEVEL_PATTERN, battery_event.trigger.message
      )
      battery_level = matched['battery_level']
      logging.info(f'Found battery level {battery_level}')
      asserts.assert_equal(battery_level, '5A4650')

    with bluetooth_utils.open_device_detail_settings(self.ad):
      asserts.assert_true(
          self.ad.uia(textContains=f'{_BATTERY_LEFT}%').wait.exists(
              _WAIT_FOR_UI_UPDATE
          ),
          'Fail to find correct left ear battery from device detail page.'
      )
      asserts.assert_true(
          self.ad.uia(textContains=f'{_BATTERY_RIGHT}%').wait.exists(
              _WAIT_FOR_UI_UPDATE
          ),
          'Fail to find correct right ear battery from device detail page.'
      )
      asserts.assert_true(
          self.ad.uia(textContains=f'{_BATTERY_CASE}%').wait.exists(
              _WAIT_FOR_UI_UPDATE
          ),
          'Fail to find correct case battery from device detail page.'
      )

  def test_2_update_battery_level(self):
    self.ref_primary.set_battery_level_tws(
        _BATTERY_LEFT_LOW, _BATTERY_RIGHT_LOW, _BATTERY_CASE_LOW
    )

    # battery_level is updated show on phone But cannot be read back from 
    # bluetooth ref device
    # (battery_left, battery_right, battery_case) = (
    #     self.ref_primary.get_battery_level_tws()
    # )
    # asserts.assert_equal(battery_left, _BATTERY_LEFT_LOW)
    # asserts.assert_equal(battery_right, _BATTERY_RIGHT_LOW)
    # asserts.assert_equal(battery_case, _BATTERY_CASE_LOW)

    with bluetooth_utils.open_device_detail_settings(self.ad):
      asserts.assert_true(
          self.ad.uia(textContains=f'{_BATTERY_LEFT_LOW}%').wait.exists(
              _WAIT_FOR_UI_UPDATE
          ),
          'Fail to find updated left ear battery from device detail page.'
      )
      asserts.assert_true(
          self.ad.uia(textContains=f'{_BATTERY_RIGHT_LOW}%').wait.exists(
              _WAIT_FOR_UI_UPDATE
          ),
          'Fail to find updated right ear battery from device detail page.'
      )
      asserts.assert_true(
          self.ad.uia(textContains=f'{_BATTERY_CASE_LOW}%').wait.exists(
              _WAIT_FOR_UI_UPDATE
          ),
          'Fail to find updated case battery from device detail page.'
      )


  def teardown_test(self):
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ad.services.create_output_excerpts_all(self.current_test_info)
    utils.concurrent_exec(
        lambda d: d.create_output_excerpts(self.current_test_info),
        [[self.ref_primary], [self.ref_secondary]],
        raise_on_exception=True,
    )

  def teardown_class(self):
    bluetooth_utils.clear_bonded_devices(self.ad)


if __name__ == '__main__':
  test_runner.main()
