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

from __future__ import annotations

from collections.abc import Callable, Iterator
import contextlib
import datetime
import logging
import pathlib
import time
from typing import TypeAlias

from mobly import asserts
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb
from mobly.snippet import errors as snippet_errors

from testing.utils import android_utils
from testing.mobly.platforms.android.services import logcat_pubsub_service
from testing.mobly.platforms.bluetooth import bluetooth_reference_device

BtRefDevice: TypeAlias = bluetooth_reference_device.BluetoothReferenceDeviceBase

# Constants for Android Fast Pair config
_GMS_CORE_PACKAGE = 'com.google.android.gms'
_FAST_PAIR_DB_FOLDER = 'data/data/com.google.android.gms/files/nearby-fast-pair'

# ADB shell commands used to start/stop Bluetooth settings page on Android
_START_BT_SETTINGS_CMD = 'am start -a android.settings.BLUETOOTH_SETTINGS'
_STOP_SETTINGS_CMD = 'am force-stop com.android.settings'

# Youtube package
_YOUTUBE_PKG = 'com.google.android.youtube'

# Constants for the widget resource ID
_FAST_PAIR_HALFSHEET_IMAGE_ID = 'com.google.android.gms:id/card'

# Constants for operation time
_DELAY_TIME_FOR_OPERATION = datetime.timedelta(seconds=3)
_DELAY_AFTER_CHANGE_WIFI_STATUS = datetime.timedelta(seconds=5)
_WAIT_FOR_UI_TRANSLATE = datetime.timedelta(seconds=6)
_WAIT_FOR_FP_HALFSHEET = datetime.timedelta(seconds=30)
_BLUETOOTH_OPERATION_TIME = datetime.timedelta(seconds=30)
_WAIT_FOR_UI_UPDATE = datetime.timedelta(seconds=30)
_INITIAL_PAIR_DISCOVER_TIME = datetime.timedelta(seconds=30)
_SUBSEQUENT_PAIR_CONNECTION_TIME = datetime.timedelta(seconds=90)

# Error messages
_CONDITION_NOT_TRUE_MSG = 'The condition is not true after timeout.'
_BT_DISCOVER_FAILED_MSG = 'Failed to discover Bluetooth device'
_BT_PAIRED_FAILED_MSG = 'Failed to confirm Bluetooth is paired'
_BT_CONNECTED_FAILED_MSG = 'Failed to confirm Bluetooth is connected.'
_BT_DISCONNECTED_FAILED_MSG = 'Failed to confirm Bluetooth is disconnected.'
_BT_UPDATE_NAME_FAILED_MSG = (
    'Failed to update the name of the connected device.'
)
_FP_INITIAL_PAIR_FAIL_MSG = "Device couldn't connect. Fast Pair failed."


def clear_android_fast_pair_cache(ad: android_device.AndroidDevice) -> None:
  """Clears Fast Pair cache.

  Fully clears out the Fast Pair cache storage in Nearby module by removing
  the corresponding DB files and force-stopping GMS Core.

  Args:
    ad: The Android device to clear Fast Pair cache.
  """
  if not ad.is_adb_root:
    ad.log.warning(
        'Andoird device is not rooted. Skip clearing Fast Pair cache.'
    )
    return
  try:
    ad.adb.shell(['rm', '-rf', _FAST_PAIR_DB_FOLDER])
    ad.adb.shell(['am', 'force-stop', _GMS_CORE_PACKAGE])
  except adb.AdbError:
    ad.log.exception('No permission to clear fast pair cache.')


def clear_bonded_devices(ad: android_device.AndroidDevice) -> None:
  """Clears the bt bonded devices on android device.

  Args:
    ad: The Android device to clear all bonded bt devices.
  """
  while paired_devices := ad.mbs.btGetPairedDevices():
    device = paired_devices[0]
    ad.log.info('Unpairing %s (%s)', device['Address'], device['Name'])
    ad.mbs.btUnpairDevice(device['Address'])
    # By testing multiple times,
    # the test results show that this delay improves stability.
    time.sleep(_DELAY_TIME_FOR_OPERATION.total_seconds())


def set_bluetooth_le_audio(
    ad: android_device.AndroidDevice, target_state: bool
) -> None:
  """Enables Bluetooth LE Audio."""
  if not ad.is_adb_root:
    return
  current_state = ad.adb.getprop(
      'persist.bluetooth.leaudio.bypass_allow_list'
  ) == 'true'
  if current_state == target_state:
    return
  if target_state:
    ad.adb.shell('setprop persist.bluetooth.leaudio.bypass_allow_list true')
  else:
    ad.adb.shell('setprop persist.bluetooth.leaudio.bypass_allow_list false')
  ad.reboot()
  time.sleep(_DELAY_TIME_FOR_OPERATION.total_seconds())


def is_wifi_enabled(ad: android_device.AndroidDevice) -> bool:
  """Returns True if Wi-Fi is enabled, False otherwise."""
  return ad.adb.shell(['cmd', 'wifi', 'status']).startswith(b'Wifi is enabled')


def wifi_enable(ad: android_device.AndroidDevice) -> None:
  """Enables Wi-Fi."""
  if is_wifi_enabled(ad):
    ad.log.info('Wi-Fi was already enabled.')
    return
  ad.log.info('Enabling Wi-Fi...')
  ad.adb.shell(['cmd', 'wifi', 'set-wifi-enabled', 'enabled'])
  assert_wait_condition_true(
      lambda: is_wifi_enabled(ad),
      timeout=_DELAY_AFTER_CHANGE_WIFI_STATUS,
      fail_message='Fail to enable Wi-Fi',
      assert_if_failed=False,
  )


def wifi_disable(ad: android_device.AndroidDevice) -> None:
  """Enables Wi-Fi."""
  if not is_wifi_enabled(ad):
    ad.log.info('Wi-Fi was already disabled.')
    return
  ad.log.info('Disabling Wi-Fi...')
  ad.adb.shell(['cmd', 'wifi', 'set-wifi-enabled', 'disabled'])
  assert_wait_condition_true(
      lambda: not is_wifi_enabled(ad),
      timeout=_DELAY_AFTER_CHANGE_WIFI_STATUS,
      fail_message='Fail to disable Wi-Fi',
      assert_if_failed=False,
  )


def is_wifi_data_connected(ad: android_device.AndroidDevice) -> bool:
  """Returns True if WiFi data is connected, False otherwise."""
  try:
    return b'5 received' in ad.adb.shell(['ping', '-c', '5', '8.8.8.8'])
  except adb.AdbError:
    return False


def setup_android_device(
    ad: android_device.AndroidDevice,
    setup_fast_pair: bool = False,
    enable_le_audio: bool = True,
    enable_wifi: bool = False,
) -> None:
  """Sets up the Android device for Fast Pair."""
  # Load Mobly Bundled Snippets on the Android device. Mobly Bundled Snippets
  # should be preinstalled on the device.
  if not ad.is_adb_root and ad.is_rootable:
    ad.adb.root()
  ad.adb.shell(
      ['settings', 'put', 'global', 'development_settings_enabled', '1']
  )

  # Prepare for LE Audio
  if enable_le_audio:
    set_bluetooth_le_audio(ad, True)
  else:
    set_bluetooth_le_audio(ad, False)
    
  android_utils.load_bluetooth_snippet(ad)
  android_utils.load_mbs_and_uiautomator(ad, uiautomator_snippet_name='uia')

  # Enable Bluetooth
  if not ad.mbs.btIsEnabled():
    # ad.mbs.btEnable()
    ad.adb.shell('svc bluetooth enable')
    ad.adb.shell('settings put global bluetooth_on 1')
    ad.adb.shell('am broadcast -a android.intent.action.BLUETOOTH_ENABLE --ez_state true')

  if enable_wifi:
    wifi_enable(ad)
    assert_wait_condition_true(
        lambda: is_wifi_data_connected(ad),
        timeout=_DELAY_AFTER_CHANGE_WIFI_STATUS,
        fail_message='Failed to connect to WiFi data',
        assert_if_failed=False,
    )
  else:
    wifi_disable(ad)

  # Enable HCI log
  android_utils.enable_bluetooth_hci_log(ad)

  # Prepare for Fast Pair
  if setup_fast_pair and ad.is_adb_root:
    clear_android_fast_pair_cache(ad)

  clear_bonded_devices(ad)

  # Start logcat pubsub service
  ad.services.register(
      'logcat_pubsub', logcat_pubsub_service.LogcatPublisherService
  )


def get_tws_device(refs: list[BtRefDevice]) -> tuple[BtRefDevice, BtRefDevice]:
  """Returns two BT reference device instances representing a pair of TWS."""
  if len(refs) < 2:
    raise ValueError(f'Requires at least 2 BT ref devices, got {len(refs)}')
  if refs[0].config.get('role', '') == 'primary':
    return (refs[0], refs[1])
  return (refs[1], refs[0])


def mbs_pair_with_retry(ad: android_device.AndroidDevice, address: str) -> None:
  try:
    ad.mbs.btPairDevice(address.upper())
    return
  except snippet_errors.ApiError:
    logging.warning('BT pair failed once, retrying...')
    pass  # Retry for the first failure

  ad.mbs.btPairDevice(address.upper())


def mbs_pair_devices(ad: android_device.AndroidDevice, address: str) -> None:
  """Pairs the Android and reference device using MBS."""
  initial_name = assert_device_discovered(ad, address)
  logging.info(f'Discovered target device, name: {initial_name}')

  # Disable FastPair halfsheet
  while ad.uia(res=_FAST_PAIR_HALFSHEET_IMAGE_ID).wait.exists(
      _WAIT_FOR_FP_HALFSHEET
  ):
    logging.info('Found FP halfsheet, pressed.')
    ad.uia.press.back()
    time.sleep(_DELAY_TIME_FOR_OPERATION.total_seconds())

  mbs_pair_with_retry(ad, address)
  logging.info('Devices paired.')

  assert_device_bonded_via_address(ad, address)


def assert_wait_condition_true(
    func: Callable[[], bool],
    timeout: datetime.timedelta = _BLUETOOTH_OPERATION_TIME,
    assert_if_failed: bool = True,
    fail_message: str = _CONDITION_NOT_TRUE_MSG,
) -> None:
  """Asserts if the target function returns true in given timeout."""
  deadline = time.perf_counter() + timeout.total_seconds()
  while time.perf_counter() <= deadline:
    if func():
      return
    time.sleep(_DELAY_TIME_FOR_OPERATION.total_seconds())

  if assert_if_failed:
    asserts.fail(fail_message)
  else:
    logging.error(fail_message)


def assert_device_discovered(
    ad: android_device.AndroidDevice,
    address: str,
    timeout: datetime.timedelta = _BLUETOOTH_OPERATION_TIME,
    fail_message: str = _BT_DISCOVER_FAILED_MSG,
) -> str:
  """Discovers device with given Bluetooth address."""
  deadline = time.perf_counter() + timeout.total_seconds()
  while time.perf_counter() <= deadline:
    device_list = ad.mbs.btDiscoverAndGetResults()
    for device in device_list:
      if device['Address'].upper() == address.upper():
        return device['Name']
    time.sleep(_DELAY_TIME_FOR_OPERATION.total_seconds())
  asserts.fail(fail_message)


def assert_device_bonded_via_address(
    ad: android_device.AndroidDevice,
    address: str,
    timeout: datetime.timedelta = _BLUETOOTH_OPERATION_TIME,
    fail_message: str = _BT_PAIRED_FAILED_MSG,
) -> None:
  """Asserts if the paired device exists in the Android paired devices list.

  Args:
    ad: An Android device setup.
    address: The Bluetooth address of the other device.
    timeout: The maximum time to wait for Bluetooth paired.
    fail_message: The message to show when the device is not paired.
  """
  logging.debug(
      '[assert_device_bonded_via_address_impl] Address to find: %s', address
  )

  def check_device_bonded() -> bool:
    paired_device_list = [
        device['Address'].upper() for device in ad.mbs.btGetPairedDevices()
    ]
    logging.debug(
        '[assert_device_bonded_via_address_impl] Paired device list: %s',
        paired_device_list,
    )
    return address.upper() in paired_device_list

  assert_wait_condition_true(
      check_device_bonded, timeout, fail_message=fail_message,
  )


def assert_device_connected(
    ad: android_device.AndroidDevice,
    address: str,
    timeout: datetime.timedelta = _BLUETOOTH_OPERATION_TIME,
    fail_message: str = _BT_CONNECTED_FAILED_MSG,
) -> None:
  """Asserts if the target device is connected to Android device.

  Args:
    ad: An Android device setup.
    address: The Bluetooth address of the other device.
    timeout: The maximum time to wait for Bluetooth connection.
    fail_message: The message to show when the device is not connected after
      timeout.
  """
  logging.debug('[assert_device_connected] Address to find: %s', address)

  def check_device_connected() -> bool:
    connected_device_list = [
        device['Address'] for device in ad.mbs.btA2dpGetConnectedDevices()
    ]
    logging.debug(
        '[assert_device_connected] Connected device list: %s',
        connected_device_list,
    )
    return address.upper() in connected_device_list

  assert_wait_condition_true(
      check_device_connected, timeout, fail_message=fail_message
  )


def assert_device_disconnected(
    ad: android_device.AndroidDevice,
    address: str,
    timeout: datetime.timedelta = _BLUETOOTH_OPERATION_TIME,
    fail_message: str = _BT_DISCONNECTED_FAILED_MSG,
) -> None:
  """Asserts if the target device is disconnected from the Android device.

  Args:
    ad: An Android device setup.
    address: The Bluetooth address of the other device.
    timeout: The maximum time to wait for Bluetooth disconnection.
    fail_message: The message to show when the device is not disconnected after
      timeout.
  """
  logging.debug('[assert_device_disconnected] Address to find: %s', address)

  def check_device_disconnected() -> bool:
    connected_device_list = [
        device['Address'] for device in ad.mbs.btA2dpGetConnectedDevices()
    ]
    logging.debug(
        '[assert_device_disconnected] Connected device list: %s',
        connected_device_list,
    )
    return address.upper() not in connected_device_list

  assert_wait_condition_true(
      check_device_disconnected, timeout, fail_message=fail_message
  )


def assert_device_name_update(
    ad: android_device.AndroidDevice,
    address: str,
    initial_name: str,
    timeout: datetime.timedelta = _BLUETOOTH_OPERATION_TIME,
    assert_if_failed: bool = False,
    fail_message: str = _BT_UPDATE_NAME_FAILED_MSG,
) -> None:
  """Waits for the Android device to update the name of the connected device.

  Args:
    ad: An Android device setup.
    address: The Bluetooth address of the other device.
    initial_name: The initial name of the other device.
    timeout: The maximum time to wait for bluetooth paired.
    assert_if_failed: Whether to assert fail if device name is not changed after
      timeout.
    fail_message: The message to show when the device name is not changed after
      timeout.
  """
  def check_device_name_update() -> bool:
    connected_device_list = ad.mbs.btA2dpGetConnectedDevices()
    for device in connected_device_list:
      if device['Address'] == address and device['Name'] != initial_name:
        logging.info(
            '[assert_device_name_update] Device name changed: %s',
            device['Name'],
        )
        return True
    return False

  assert_wait_condition_true(
      check_device_name_update, timeout, assert_if_failed, fail_message
  )


def wait_fp_connected_and_close_halfsheet(
    ad: android_device.AndroidDevice,
    fail_message: str = _FP_INITIAL_PAIR_FAIL_MSG,
) -> None:
  assert_wait_condition_true(
      lambda: not ad.uia(textContains='Connecting').exists,
      timeout=_WAIT_FOR_FP_HALFSHEET,
      fail_message='Failed to wait for Fast Pair initial pair complete.',
  )
  if ad.uia(text='Skip').wait.exists(_WAIT_FOR_UI_TRANSLATE):
    ad.uia(text='Skip').click()
  if ad.uia(text='No thanks').exists:
    ad.uia(text='No thanks').click()
  if ad.uia(text='Done').exists:
    ad.uia(text='Done').click()
  if ad.uia(text="Couldn't connect").wait.exists(_WAIT_FOR_UI_TRANSLATE):
    asserts.fail(fail_message)
  ad.uia.press.back()


def fast_pair_android_and_ref(
    ad: android_device.AndroidDevice,
    address: str,
    fail_message: str = 'Fail to press connect button on displayed halfsheet.',
) -> None:
  """Fast Pair connect Android and the reference device.

  Args:
    ad: An Android device setup.
    address: The Bluetooth address of the reference device.
  """
  # Click 'Connect' button in the Fast Pair half sheet.
  asserts.assert_true(
      ad.uia(text='Connect').wait.click(_WAIT_FOR_UI_UPDATE),
      fail_message,
  )

  wait_fp_connected_and_close_halfsheet(ad)

  # Confirm the devices are connected.
  assert_device_bonded_via_address(ad, address)

  # Wait for the device to be ready
  time.sleep(_DELAY_TIME_FOR_OPERATION.total_seconds())


def fast_pair_subsequent_pair_android_and_ref(
    ad: android_device.AndroidDevice, address: str
) -> None:
  # Disable Fast Pair half sheet
  while ad.uia(res=_FAST_PAIR_HALFSHEET_IMAGE_ID).exists:
    ad.uia.press.back()

  ad.uia.open.notification()
  asserts.assert_true(
      ad.uia(
          text='Your saved device is available'
      ).wait.click(_INITIAL_PAIR_DISCOVER_TIME),
      f'[Subsequent AndroidDevice|{ad.serial}] Fail'
      ' to receive subsequent pair notification',
  )

  # Confirm the second phone and reference device are connected.
  assert_device_bonded_via_address(
      ad,
      address,
      timeout=_SUBSEQUENT_PAIR_CONNECTION_TIME,
      fail_message=(
          f'[Subsequent AndroidDevice|{ad.serial}]'
          ' Fail to subsequent pair with Fast Pair provider.'
      ),
  )

@contextlib.contextmanager
def open_system_settings(
    ad: android_device.AndroidDevice
) -> Iterator[None]:
  """Opens the system settings page on Android."""
  try:
    # Open system settings
    ad.adb.shell(_START_BT_SETTINGS_CMD)
    time.sleep(_DELAY_TIME_FOR_OPERATION.total_seconds())

    while ad.uia(res=_FAST_PAIR_HALFSHEET_IMAGE_ID).exists:
      ad.uia.press.back()
    yield
  finally:
    # Close system settings
    logging.info('stop setting')
    ad.adb.shell(_STOP_SETTINGS_CMD)


@contextlib.contextmanager
def open_device_detail_settings(
    ad: android_device.AndroidDevice
) -> Iterator[None]:
  """Opens the device detail settings page on Android."""
  with open_system_settings(ad):
    # Go to the setting page of the connected device
    ad.uia(res='com.android.settings:id/settings_button').click()
    time.sleep(_DELAY_TIME_FOR_OPERATION.total_seconds())
    try:
      yield
    finally:
      ad.uia.press.back()

def set_le_audio_state_on_paired_device(
    ad: android_device.AndroidDevice,
    target_state: bool,
    skip_if_no_button: bool = False,
) -> None:
  """Enable LE Audio on the paired device in Android device settings."""
  with open_device_detail_settings(ad):
    # Enable LE Audio by clicking the switch
    ad.uia(scrollable=True).scroll.down(text='LE Audio')
    if not ad.uia(text='LE Audio').wait.exists(_WAIT_FOR_UI_TRANSLATE):
      if skip_if_no_button:
        return
      asserts.fail('Faled to find LE Audio button on device settings page')

    le_audio_switch = ad.uia(text='LE Audio').right(
        clazz='android.widget.Switch'
    )
    if le_audio_switch.checked != target_state:
      le_audio_switch.click()

    def check_le_audio_state_via_ui() -> bool:
      ad.uia(scrollable=True).scroll.down(text='LE Audio')
      switch = ad.uia(text='LE Audio').right(clazz='android.widget.Switch')
      return switch.checked == target_state and switch.enabled

    assert_wait_condition_true(
        check_le_audio_state_via_ui,
        timeout=_WAIT_FOR_UI_UPDATE,
        fail_message=(
            f'Failed to set LE Audio state to {target_state} of the device '
            'on Android.'
        ),
    )


@contextlib.contextmanager
def push_and_play_audio_on_android(
    ad: android_device.AndroidDevice, local_audio_filepath: str
) -> Iterator[None]:
  """Pushes and plays audio on Android device.

  Args:
    ad: An Android device setup.
    local_audio_filepath: The local audio filepath to push and play.

  Yields:
      The context for user to trigger action while the audio is playing.
  """
  remote_audio_filepath = pathlib.PurePosixPath(
      ad.mbs.storageGetExternalStorageDirectory(),
      'Music',
      pathlib.Path(local_audio_filepath).name,
  )
  try:
    ad.adb.push([local_audio_filepath, str(remote_audio_filepath)])
    ad.mbs.mediaPlayAudioFile(str(remote_audio_filepath))
    yield
  finally:
    # Stops audio playing
    ad.mbs.mediaStop()
    ad.adb.shell(f'rm -f {remote_audio_filepath}')


@contextlib.contextmanager
def play_youtube_video_on_android(
    ad: android_device.AndroidDevice, youtube_video_id: str
) -> Iterator[None]:
  """Plays an Youtube video on Android device.

  Args:
    ad: An Android device setup.
    youtube_video_id: The ID of the video to play on Youtube.

  Yields:
      The context for user to trigger action while the video is playing.
  """
  try:
    ad.adb.shell(f'am force-stop {_YOUTUBE_PKG}')
    ad.adb.shell(
        f'pm grant {_YOUTUBE_PKG} android.permission.POST_NOTIFICATIONS'
    )
  except android_device.adb.AdbError:
    pass

  time.sleep(_DELAY_TIME_FOR_OPERATION.total_seconds())

  try:
    ad.adb.shell([
        'am',
        'start',
        '-a',
        'android.intent.action.VIEW',
        '-d',
        f'https://youtu.be/{youtube_video_id}',
    ])
    yield
  finally:
    # Stops video playing
    ad.adb.shell(f'am force-stop {_YOUTUBE_PKG}')


def is_media_route_on_lea(
    ad: android_device.AndroidDevice, target_address: str
) -> bool:
  """Returns True if the media route is on LE Audio device, False otherwise."""
  return ad.bt.media3IsLeaStreamActive() and ad.bt.btIsLeAudioConnected(target_address)
