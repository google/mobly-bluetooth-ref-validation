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

"""Mobly controller module for a BES Bluetooth device (BES dev board)."""

from __future__ import annotations

from collections.abc import Sequence
import datetime
import enum
import logging
import os
import pathlib
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Union

import dacite
from mobly import logger as mobly_logger
from mobly import runtime_test_info
from mobly import signals
from mobly import utils as mobly_utils

from testing.mobly.platforms.bluetooth import bluetooth_reference_device_base
from testing.mobly.platforms.bluetooth.bes import bes_device_config
from testing.mobly.platforms.bluetooth.bes import bes_hid_tool
from testing.mobly.platforms.bluetooth.bes import bes_log_pubsub
from testing.mobly.platforms.bluetooth.bes import constants
from testing.mobly.platforms.bluetooth.bes import logger
from testing.mobly.platforms.bluetooth.lib import file_clipper
from testing.mobly.platforms.bluetooth.lib import utils


# This is used in the config file located in the test lab's home directory.
MOBLY_CONTROLLER_CONFIG_NAME = 'BesDevice'

# Error messages used in this module.
_DEVICE_CONFIG_ERROR_MSG = (
    'Failed to parse device configs when creating BES devices: '
)
_PUBLISHER_NOT_STARTED_MESSAGE = 'BES log publisher not started.'
_LOG_CLIPPER_NOT_STARTED_MESSAGE = 'BES log clipper not started.'
_NO_LOG_OUTPUT_MESSAGE = (
    'No log output from BES board. Please power on the board by pressing the'
    ' `PWR` and `RST` button.'
)
_NO_OUTPUT_FILENAME_MESSAGE = 'No output filename. Run start() first.'

# Default filename of the log file on the host machine.
_DEFAULT_LOG_FILENAME = 'bes_log_{timestamp}.txt'
# Default baud rate of the serial connection
_DEFAULT_BAUD_RATE = 1152000

# The commands to communicate with BES devboard via serial connection
_CONFIG_SERIAL_PORT_COMMAND = 'stty -echo -F {serial_port} speed {speed}'
_READ_SERIAL_COMMAND = 'cat {serial_port}'
_WRITE_SERIAL_COMMAND = 'echo -e -n "{command}" > {serial_port}'

# The wait time for a command to process
_SEND_BES_COMMAND_INTERVAL = datetime.timedelta(seconds=1)
_REBOOT_WAIT_TIME = datetime.timedelta(seconds=3)
_BES_EXECUTION_TIMEOUT = datetime.timedelta(seconds=10)
_REBOOT_TIMEOUT = datetime.timedelta(seconds=30)

# Regexs for parsing BES response
_COMMAND_NOT_SUPPORTED_PATTERN = re.compile(r'.*command not supported!.*')
_REBOOT_DONE_PATTERN = re.compile(r'.*bt_stack_init_done.*')
_FIRMWARE_BUILD_DATE_PATTERN = re.compile(r'.*BUILD_DATE=(?P<build_date>.*)')
_FIRMWARE_VERSION_PATTERN = re.compile(r'.*REV_INFO=(?P<version>.*)')
_DEVICE_INFO_PATTERN = re.compile(r'(?P<key>.*): (?P<value>.*)')
_GET_VOLUME_PATTERN = re.compile(r'.*volume=(?P<level>\d+).*')
_GET_BLE_VOLUME_PATTERN = re.compile(r'.*BLE volume=(?P<level>\d+).*')
_GET_BATTERY_LEVEL_PATTERN = re.compile(r'.*battery_level: (?P<level>\d+).*')
_GET_BATTERY_LEVEL_TWS_PATTERN = re.compile(
    r'Main ear battery_level: (?P<left_level>\d+)\nRemote ear battery_level:'
    r' (?P<right_level>\d+)(\nCase battery_level: (?P<case_level>\d+))?.*'
)
_SEPARATER = '\r\n' if sys.platform == 'win32' else '\n'
_PAIRED_DEVICE_INFO_PATTERN = re.compile(
    rf'addr: (?P<addr>.*){_SEPARATER}.*name: (?P<name>.*)'
)
_LE_PAIRED_DEVICE_INFO_PATTERN = re.compile(r'BLE addr: (?P<addr>.*)')
_BOX_STATE_PATTERN = re.compile(r'box_state=(?P<state>.*)')
_ACCESS_MODE_PATTERN = r'.*Access mode changed to {access_mode}.*'

# The key name mapping from BES response to `BluetoothInfo` dataclass
_DEVICE_INFO_KEY_MAP = {
    'bt_addr': 'bluetooth_address',
    'ble_addr': 'ble_address',
    'bt_name': 'bluetooth_name',
    'ble_name': 'ble_name',
}


class BesDeviceError(signals.ControllerError):
  """Raised for errors related to the BesDevice controller module."""


class BesRuntimeError(Exception):
  """Raised when BES board encounters error during runtime."""


class CommandTimeoutError(BesRuntimeError):
  """Raised when BES command execution times out."""


class ErrorType(enum.Enum):
    """The type of the BES runtime error."""
    NO_ERROR = 0
    RESOURCE_BUSY_ERROR = 1
    COMMAND_PARAM_ERROR = 2
    COMMAND_NOT_SUPPORT_ERROR = 3
    TIMEOUT_ERROR = 4
    BT_STACK_ERROR = 5
    UNKNOWN_ERROR = 6


class BesCommandError(BesRuntimeError):
  """Raised when BES command execution failed on the board."""

  def __init__(self, command: str, error_code: int):
    super().__init__(
        'BES command execution failed on the board. '
        f'Command: {command}. Error type: {ErrorType(error_code)}'
    )


class AccessMode(enum.IntEnum):
  """The type of the BES runtime error."""
  INIT_PAIRING = 0
  DISABLE_PAIRING = 2
  ENABLE_PAIRING = 3


@enum.unique
class AncMode(enum.IntEnum):
  """The ANC mode of the device."""
  OFF = 0
  ON = 1
  TRANSPARENT = 2

  @classmethod
  def from_string(cls, mode: str) -> 'AncMode':
    """Converts a string to an ANC mode."""
    mode = mode.lower()
    if mode == 'off':
      return cls.OFF
    elif mode == 'on':
      return cls.ON
    elif mode in ('transparent', 'transparency'):
      return cls.TRANSPARENT
    else:
      raise ValueError(f'Invalid ANC mode: {mode}')


def create(configs: Sequence[dict[str, Any]]) -> List[BesDevice]:
  """Creates BesDevice controller objects.

  Mobly uses this to instantiate BesDevice controller objects from configs.
  The configs come from Mobly configs that look like:

    ```config.yaml
    TestBeds:
    - Name: SampleTestBed
      Controllers:
        BesDevice:
        - serial_port: '/dev/ttyUSB0'
          bluetooth_address: '11:22:33:44:55:66'
    ```

  Each config should have required key-value pair 'serial_port' and
  'bluetooth_address'.

  Args:
    configs: a list of dicts, each representing a configuration for a BES
      device.

  Returns:
    A list of BesDevice objects.

  Raises:
    errors.BtReferenceError: Invalid controller configs are given.
  """
  try:
    device_configs = bes_device_config.from_dicts(configs)
  except Exception as e:
    raise BesDeviceError(_DEVICE_CONFIG_ERROR_MSG, e) from e

  devices = []
  for config in device_configs:
    logging.debug(
        'Creating BES device %s on serial port %s',
        config.bluetooth_address,
        config.serial_port,
    )
    devices.append(BesDevice(config))

  return devices


def destroy(devices: Sequence[BesDevice]) -> None:
  """Destroys BesDevice objects.

  Mobly uses this to destroy BesDevice objects created by `create`.

  Args:
    devices: list of BesDevice.
  """
  for device in devices:
    try:
      device.destroy()
    except Exception:  # pylint: disable=broad-except
      logging.exception('Failed to clean up device properly: %s', repr(device))


def get_info(devices: Sequence[BesDevice]) -> Sequence[dict[str, Any]]:
  """Gets info from the BtReferenceDevice objects used in a test run.

  Args:
    devices: A list of BtReferenceDevice objects.

  Returns:
    list of dict, each representing info for input devices.
  """
  return [dict() for d in devices]


class BesDevice(bluetooth_reference_device_base.BluetoothReferenceDeviceBase):
  """Mobly controller for a BES device.

  The BES device is a Bluetooth development board. Each object of this class
  represents one BES device in Mobly.

  The BES board should be attached to a local Linux workstation that runs as Mobly
  host.

  Attributes:
    bluetooth_address: The unique BRE/DR address (classic Bluetooth address)
      of the device.
    config: The configurations for the device.
    debug_tag: A string that represents this device in the debug info.
    log_path: The local path on the host to save logs in the test.
    log: A logger adapted from root logger with an added prefix
      '[BesDevice|<bluetooth_address>] 'specific to a test device.
  """

  bluetooth_address: str

  _debug_tag: str

  _log_collecting_process: Optional[Union[logger.SystemLogger, subprocess.Popen[Any]]] = None
  _log_clipper: Optional[file_clipper.FileClipper] = None
  _publisher: Optional[bes_log_pubsub.BesLogPublisher] = None
  _output_filename: Optional[str] = None

  def __init__(self, config: bes_device_config.DeviceConfig) -> None:
    self.config = config
    self.bluetooth_address = self.config.bluetooth_address

    # logging.log_path only exists when this is used in a Mobly test run.
    log_path_base = getattr(logging, 'log_path', '/tmp/logs')
    device_log_directory_name = mobly_logger.sanitize_filename(
        f'BesDevice_{config.bluetooth_address}'
    )
    self._debug_tag = config.bluetooth_address
    self.log_path = os.path.join(log_path_base, device_log_directory_name)
    mobly_utils.create_dir(self.log_path)
    self.log = mobly_logger.PrefixLoggerAdapter(
        logging.getLogger(),
        {
            mobly_logger.PrefixLoggerAdapter.EXTRA_KEY_LOG_PREFIX: (
                f'[BesDevice|{self.debug_tag}]'
            )
        },
    )

    try:
      self._init_bes_connection()
      return
    except Exception:  # pylint: disable=broad-except
      self.destroy()
      if not config.enable_hard_reset:
        raise
      self.log.warning(
          'Failed to initialize BES device. Start to try hard power on the'
          ' board. If the board still fails to initialize, please contact lab'
          ' team to manually recover the board.'
      )

    # Try to hard reset the BES board.
    try:
      bes_hid_tool.power_on_local()
      self._init_bes_connection()
      return
    except Exception:  # pylint: disable=broad-except
      self.destroy()
      raise

  def _init_bes_connection(self) -> None:
    """Initializes the BES board connection."""
    # Builds serial connection with the board and starts streaming board
    # output.
    self._start_serial_connection()
    self._generate_output_filename()
    # Initializes Bluetooth address of the board.
    try:
      self._set_bt_address_to_configured_address()
    except (BesCommandError, CommandTimeoutError):
      self.log.exception(
          'Failed to set Bluetooth address to configured address. Retrying.'
      )
      # Retry once if the command fails. If the USB connection is not stable,
      # or the board is not in good state, there might be some junk data in
      # UART input buffer of the board, causing the board to fail to recognize
      # the target command. A retry helps in this case.
      time.sleep(_BES_EXECUTION_TIMEOUT.total_seconds())
      self._set_bt_address_to_configured_address()

  @property
  def debug_tag(self) -> str:
    """A string that represents this device in the debug info.

    This will be used as part of the prefix of debugging messages emitted by
    this device object, like log lines and the message of DeviceError. Default
    value is the Bluetooth address of the board.
    """
    return self._debug_tag

  @debug_tag.setter
  def debug_tag(self, tag: str) -> None:
    """Sets the debug tag."""
    self.log.set_log_prefix(f'[BesDevice|{tag}]')
    self.log.debug('Logging debug tag set to "%s"', tag)
    self._debug_tag = tag

  def __repr__(self) -> str:
    return f'<BesDevice|{self.debug_tag}>'

  def __del__(self) -> None:
    self.destroy()

  def destroy(self) -> None:
    """Tears BesDevice object down."""
    self._stop_serial_connection()

  def _execute_command(self, command: str) -> None:
    """Executes a command to control the serial connection."""
    mobly_utils.run_command(command, shell=True)

  def _configure_serial_connection(self) -> None:
    """Configures the serial connection with BES board."""
    self._execute_command(
        _CONFIG_SERIAL_PORT_COMMAND.format(
            serial_port=self.config.serial_port,
            speed=_DEFAULT_BAUD_RATE,
        )
    )

  def _start_log_streaming(self, local_log_path: pathlib.Path) -> None:
    """Starts streaming the log output from the BES board."""
    command = _READ_SERIAL_COMMAND.format(serial_port=self.config.serial_port)
    if not self.config.shell_mode:
      self._log_collecting_process = logger.SystemLogger()
      if not self._log_collecting_process.open_port(
        self.config.serial_port, _DEFAULT_BAUD_RATE, str(local_log_path)
      ):
        raise Error('Open serial port timeout')
      self._log_collecting_process.start()
    else:
      self._configure_serial_connection()
      self._log_collecting_process = mobly_utils.start_standing_subprocess(
          f'{command} > {local_log_path}', shell=True
      )

    self._log_clipper = file_clipper.FileClipper(local_log_path)
    self._publisher = bes_log_pubsub.BesLogPublisher(local_log_path)
    self._publisher.start()

  def _log_board_time(self, filename: str) -> None:
    """Logs the current time of the BES board for log alignment."""
    if self._publisher is None:
      raise BesDeviceError(_PUBLISHER_NOT_STARTED_MESSAGE)

    with self._publisher.event() as event:
      if not event.wait(timeout=_REBOOT_TIMEOUT) or event.trigger is None:
        raise BesDeviceError(_NO_LOG_OUTPUT_MESSAGE)
      device_time = event.trigger.time
      self.log.info(
          f'Log alignment: current BES device time is {device_time}, output'
          f' filename {filename}'
      )

  def _start_serial_connection(self) -> None:
    """Starts the serial connection with BES board."""
    timestamp = mobly_logger.get_log_file_timestamp()
    host_log_path = pathlib.Path(
        self.log_path, _DEFAULT_LOG_FILENAME.format(timestamp=timestamp)
    )
    self._start_log_streaming(host_log_path)

  def _set_bt_address_to_configured_address(self) -> None:
    """Sets the Bluetooth and BLE address to the configured address."""
    device_info = self.get_device_info()
    if (
        device_info.bluetooth_address != self.bluetooth_address.upper()
        or device_info.ble_address != self.bluetooth_address.upper()
    ):
      self.set_address(self.bluetooth_address)

  def _stop_serial_connection(self) -> None:
    """Stops the serial connection with BES board."""
    if self._log_collecting_process is not None:
      if not self.config.shell_mode:
        self._log_collecting_process.stop()
      else:
        mobly_utils.stop_standing_subprocess(self._log_collecting_process)
      self._log_collecting_process = None

    if self._log_clipper is not None:
      self._log_clipper.close()
      self._log_clipper = None

    if self._publisher is not None:
      self._publisher.stop()
      self._publisher = None

  def create_output_excerpts(
      self, test_info: runtime_test_info.RuntimeTestInfo
  ) -> List[pathlib.Path]:
    """Creates excerpts for specified logs and returns the excerpt paths.

    Args:
      test_info: `self.current_test_info` in a Mobly test.

    Returns:
      The list of absolute paths to excerpt files.

    Raises:
      BesDeviceError: If the log clipper is not started or no output filename.
    """
    if self._log_clipper is None:
      raise BesDeviceError(_LOG_CLIPPER_NOT_STARTED_MESSAGE)

    if self._output_filename is None:
      raise BesDeviceError(_NO_OUTPUT_FILENAME_MESSAGE)

    mobly_utils.create_dir(test_info.output_path)
    excerpts_path = pathlib.Path(test_info.output_path, self._output_filename)
    self.log.debug('Creating output excerpts as file: %s', excerpts_path)
    self._log_clipper.clip_new_content(excerpts_path)
    # self._generate_output_filename()
    return [excerpts_path]

  def _generate_output_filename(self) -> None:
    timestamp = mobly_logger.get_log_file_timestamp()
    bluetooth_address_escape = self.bluetooth_address.replace(':', '-')
    self._output_filename = (
        f'bes_log,{bluetooth_address_escape},{timestamp}.txt'
    )
    self._log_board_time(self._output_filename)

  def _send_bes_command(self, command: str, wait_response: bool = True) -> str:
    """Sends the serial command to the BES devboard."""
    if self._publisher is None:
      raise BesDeviceError(_PUBLISHER_NOT_STARTED_MESSAGE)

    with (
        self._publisher.bes_response() as response,
        self._publisher.event(pattern=_COMMAND_NOT_SUPPORTED_PATTERN) as event,
    ):
      time.sleep(_SEND_BES_COMMAND_INTERVAL.total_seconds())
      if not self.config.shell_mode:
        self._log_collecting_process.send_command(str(command))
      else:
        self._execute_command(
            _WRITE_SERIAL_COMMAND.format(
                command=str(command) + '\\r\\n',
                serial_port=self.config.serial_port,
            )
        )
      if not wait_response:
        return ''
      if not response.wait(timeout=_BES_EXECUTION_TIMEOUT):
        if event.is_set():
          raise BesCommandError(
              error_code=ErrorType.COMMAND_NOT_SUPPORT_ERROR.value,
              command=command,
          )
        raise CommandTimeoutError(
            f'Failed to wait for response of the command: {command}'
        )
      data = response.trigger
      # For pytype check. `response.wait()` ensures data is not None.
      assert data is not None
      self.log.info(
          f'Response: {data.status} (error code {data.error_code})'
          f' {data.message}'
      )
      if data.error_code != 0:
        raise BesCommandError(error_code=data.error_code, command=command)
      return data.message

  def _get_firmware_version(
      self, build_date_str: str, version_str: str
  ) -> None:
    """Gets the firmware version of the BES board."""
    info_list = []
    if matched := _FIRMWARE_VERSION_PATTERN.match(version_str):
      info_list.append(matched['version'].strip())
    if matched := _FIRMWARE_BUILD_DATE_PATTERN.match(build_date_str):
      build_date = '_'.join(matched['build_date'].strip().split())
      info_list.append(build_date)
    self._version = ':'.join(info_list)
    self.log.info(f'BES firmware version: {self._version}')

  def _reboot_and_wait_for_completion(
      self,
      reboot_command: str,
      fail_message: str,
      access_mode_after_reboot: AccessMode = AccessMode.INIT_PAIRING,
  ) -> None:
    """Executes the reboot command and waits for the reboot completion."""
    if self._publisher is None:
      raise BesDeviceError(_PUBLISHER_NOT_STARTED_MESSAGE)

    with (
        self._publisher.event(pattern=_REBOOT_DONE_PATTERN) as reboot_done,
        self._publisher.event(
            pattern=_FIRMWARE_BUILD_DATE_PATTERN
        ) as build_date,
        self._publisher.event(pattern=_FIRMWARE_VERSION_PATTERN) as version,
        self._publisher.event(
            pattern=_ACCESS_MODE_PATTERN.format(
                access_mode=access_mode_after_reboot
            )
        ) as access_mode,
    ):
      self._send_bes_command(reboot_command, wait_response=False)
      if version.wait(timeout=_REBOOT_TIMEOUT) and version.trigger is not None:
        self._get_firmware_version(
            build_date.trigger.message, version.trigger.message
        )
      if not reboot_done.wait(timeout=_REBOOT_TIMEOUT):
        raise BesRuntimeError(fail_message)
      if not access_mode.wait(timeout=_REBOOT_TIMEOUT):
        raise BesRuntimeError(
            f'Failed to wait for access mode {access_mode_after_reboot} after'
            ' reboot.'
        )

    # Wait for a short time to reduce flakiness.
    time.sleep(_REBOOT_WAIT_TIME.total_seconds())

  def reboot(self) -> None:
    self._reboot_and_wait_for_completion(
        reboot_command=constants.BESCommand.REBOOT,
        fail_message='Failed to wait for device reboot.',
    )

  def factory_reset(self, wait_for_access: bool = True) -> None:
    self._reboot_and_wait_for_completion(
        reboot_command=constants.BESCommand.FACTORY_RESET,
        fail_message='Failed to wait for device factory reset.',
        access_mode_after_reboot=(
            AccessMode.ENABLE_PAIRING
            if wait_for_access
            else AccessMode.INIT_PAIRING
        ),
    )

  def power_on(self) -> None:
    self.open_box()

  def power_off(self) -> None:
    self.close_box()

  def get_serial_number(self) -> str:
    return self._send_bes_command(constants.BESCommand.GET_SERIAL_NUMBER)

  def get_device_info(self) -> bluetooth_reference_device_base.BluetoothInfo:
    device_info = self._send_bes_command(constants.BESCommand.GET_DEVICE_INFO)
    info_dict = dict(_DEVICE_INFO_PATTERN.findall(device_info))
    map_key_name = (
        lambda x: _DEVICE_INFO_KEY_MAP[x] if x in _DEVICE_INFO_KEY_MAP else x
    )
    try:
      return dacite.from_dict(
          data_class=bluetooth_reference_device_base.BluetoothInfo,
          data={map_key_name(key): value for key, value in info_dict.items()},
      )
    except dacite.MissingValueError as e:
      raise BesRuntimeError(
          f'Failed to parse device info: {device_info}'
      ) from e

  def set_address(self, address: str) -> None:
    """Sets the Bluetooth address of the device.

    This command reboots the device for the new address to take effect.

    Args:
      address: The new Bluetooth address to be set on the BES board.

    Raises:
      ValueError: If the given Bluetooth address is not valid.
    """
    if not utils.is_valid_address(address):
      raise ValueError(f'Invalid Bluetooth address {address}.')
    self._send_bes_command(
        f'{constants.BESCommand.SET_ADDRESS} {address}',
        wait_response=False,
    )
    time.sleep(3)
    self.reboot()

  def set_name(self, bluetooth_name: str, ble_name: str) -> None:
    """Sets the classic Bluetooth name and BLE name of the device.

    This command reboots the device for the new name to take effect.
    If you want to set both address and Fast Pair parameters, call
    `set_name_and_fp_params` instead of calling `set_name` and `set_fp_params`
    sequentially.

    Args:
      bluetooth_name: The new classic Bluetooth name of the device.
      ble_name: The new BLE name of the device.
    """
    self._send_bes_command(
        f'{constants.BESCommand.SET_NAME} "{bluetooth_name}" "{ble_name}"'
    )
    self.reboot()

  def get_fast_pair_support(self) -> bool:
    return True

  def enable_fast_pair(self) -> None:
    raise NotImplementedError('Not implemented yet.')

  def disable_fast_pair(self) -> None:
    raise NotImplementedError('Not implemented yet.')

  def get_fp_params(self) -> tuple[str, str]:
    raise NotImplementedError('Not implemented yet.')

  def set_fp_params(self, model_id: str, private_key: str) -> None:
    """Sets the Fast Pair parameters of the device.

    This command reboots the device for the new parameters to take effect.
    If you want to set both address and Fast Pair parameters, call
    `set_name_and_fp_params` instead of calling `set_name` and `set_fp_params`
    sequentially.

    Args:
      model_id: Google Fast Pair model ID (format XXXXXX or 0xXXXXXX).
      private_key: Google Fast Pair anti-spoofing key (base64, uncompressed).
    """
    # Set FP model ID
    reversed_model_id = utils.reverse_fp_model_id(model_id)
    self._send_bes_command(
        rf'{constants.BESCommand.SET_FP_MODEL_ID} {reversed_model_id}'
    )

    time.sleep(_SEND_BES_COMMAND_INTERVAL.total_seconds())

    decoded_private_key = utils.decode_fp_private_key(private_key)
    self._send_bes_command(
        rf'{constants.BESCommand.SET_FP_PRIVATE_KEY} {decoded_private_key}'
    )

    self.reboot()

  def set_name_and_fp_params(
      self,
      bluetooth_name: str,
      ble_name: str,
      model_id: str,
      private_key: str,
  ) -> None:
    """Sets the Bluetooth name and Fast Pair parameters of the device.

    This command reboots the device for the new settings to take effect.

    Args:
      bluetooth_name: The new classic Bluetooth name of the device.
      ble_name: The new BLE name of the device.
      model_id: Google Fast Pair model ID (format XXXXXX or 0xXXXXXX).
      private_key: Google Fast Pair anti-spoofing key (base64, uncompressed).
    """
    self._send_bes_command(
        f'{constants.BESCommand.SET_NAME} "{bluetooth_name}" "{ble_name}"'
    )
    time.sleep(_SEND_BES_COMMAND_INTERVAL.total_seconds())
    self.set_fp_params(model_id, private_key)

  def get_sass_support(self) -> bool:
    return True

  def enable_sass(self) -> None:
    raise NotImplementedError('Not implemented yet.')

  def disable_sass(self) -> None:
    raise NotImplementedError('Not implemented yet.')

  def get_lea_support(self) -> bool:
    return True

  def enable_lea(self) -> None:
    raise NotImplementedError('Not implemented yet.')

  def disable_lea(self) -> None:
    raise NotImplementedError('Not implemented yet.')

  def set_single_point(self) -> None:
    self._send_bes_command(f'{constants.BESCommand.SET_LINK_POINT} 1')

  def set_multi_point(self) -> None:
    self._send_bes_command(f'{constants.BESCommand.SET_LINK_POINT} 2')

  def start_pairing_mode(
      self, timeout: Optional[datetime.timedelta] = None
  ) -> None:
    del timeout  # Unused, waiting for firmware update to support timeout
    self._send_bes_command(constants.BESCommand.START_PAIRING_MODE)

  def stop_pairing_mode(self) -> None:
    self._send_bes_command(constants.BESCommand.STOP_PAIRING_MODE)

  def connect(self, address: str) -> None:
    if not utils.is_valid_address(address):
      raise ValueError(f'Invalid Bluetooth address {address}.')

    address = address.replace(':', '').upper()
    self._send_bes_command(f'{constants.BESCommand.CONNECT} {address}')

  def disconnect(self, address: str) -> None:
    if not utils.is_valid_address(address):
      raise ValueError(f'Invalid Bluetooth address {address}.')

    address = address.replace(':', '').upper()
    self._send_bes_command(f'{constants.BESCommand.DISCONNECT} {address}')

  def clear_paired_devices(self) -> None:
    self._send_bes_command(constants.BESCommand.CLEAR_PAIRED_DEVICES)

  def get_anc_support(self) -> bool:
    return True

  def enable_anc(self) -> None:
    return

  def disable_anc(self) -> None:
    raise NotImplementedError('Method `disable_anc` not implemented yet.')

  def get_anc_mode(self) -> str:
    raise NotImplementedError('Not implemented yet.')

  def set_anc_mode(self, mode: str | AncMode) -> None:
    if isinstance(mode, str):
      mode = AncMode.from_string(mode)
    self._send_bes_command(f'{constants.BESCommand.SET_ANC_MODE} {mode.value}')

  def get_spatial_audio_support(self) -> bool:
    return True

  def enable_spatial_audio(self) -> None:
    self._send_bes_command(
        f'{constants.BESCommand.SET_SPATIAL_AUDIO_ENABLE} 1'
    )

  def disable_spatial_audio(self) -> None:
    self._send_bes_command(
        f'{constants.BESCommand.SET_SPATIAL_AUDIO_ENABLE} 0'
    )

  def enable_tws(self) -> None:
    self._send_bes_command(f'{constants.BESCommand.SET_TWS_ENABLE} 1')

  def disable_tws(self) -> None:
    self._send_bes_command(f'{constants.BESCommand.SET_TWS_ENABLE} 0')

  def pair_tws(self) -> None:
    self._send_bes_command(constants.BESCommand.TWS_PAIRING)

  def set_component_number(self, number: int) -> None:
    if number not in (1, 2):
      raise ValueError(f'Invalid component number {number}')
    self._send_bes_command(
        f'{constants.BESCommand.SET_COMPONENT_NUMBER} {number}'
    )

  def get_component_number(self) -> int:
    return self._send_bes_command(constants.BESCommand.GET_COMPONENT_NUMBER)

  @enum.unique
  class BoxState(enum.Enum):
    """The state of the TWS earpods and box."""
    IN_BOX_CLOSED = 'IN_BOX_CLOSED'
    IN_BOX_OPEN = 'IN_BOX_OPEN'
    OUT_BOX = 'OUT_BOX'
    OUT_BOX_WEARED = 'OUT_BOX_WEARED'

    @property
    def is_box_open(self) -> bool:
      return self in (self.IN_BOX_OPEN, self.OUT_BOX, self.OUT_BOX_WEARED)

    @property
    def is_in_box(self) -> bool:
      return self in (self.IN_BOX_CLOSED, self.IN_BOX_OPEN)

    @property
    def is_on_head(self) -> bool:
      return self == self.OUT_BOX_WEARED

  def _get_box_state(self) -> BoxState:
    """Gets the box state of the board."""
    result = self._send_bes_command(constants.BESCommand.GET_BOX_STATE)
    if matched := _BOX_STATE_PATTERN.match(result):
      return self.BoxState(matched['state'])
    raise BesRuntimeError(
        f'Failed to get box state from command result: {result}'
    )

  def get_box_open_state(self) -> bool:
    """Gets if the box is open."""
    return self._get_box_state().is_box_open

  def get_in_box_state(self) -> bool:
    """Gets if the TWS earpod is in the box."""
    return self._get_box_state().is_in_box

  def set_in_box_state(self, in_box: bool) -> None:
    """Sets if the TWS earpod is in the box."""
    current_state = self._get_box_state()
    # Current state matches the target state, no need to change.
    if current_state.is_in_box == in_box:
      return
    # Current state does not match the target state, change the state.
    if current_state.is_in_box:
      if not current_state.is_box_open:
        self._send_bes_command(constants.BESCommand.OPEN_BOX)
      self._send_bes_command(constants.BESCommand.FETCH_OUT)
    else:
      if current_state.is_on_head:
        self._send_bes_command(constants.BESCommand.WEAR_DOWN)
      self._send_bes_command(constants.BESCommand.PUT_IN)

  def get_on_head_state(self) -> bool:
    """Gets if the TWS earpod is on head."""
    return self._get_box_state().is_on_head

  def set_on_head_state(self, on_head: bool) -> None:
    """Sets if the TWS earpod is on head."""
    current_state = self._get_box_state()
    # Current state matches the target state, no need to change.
    if current_state.is_on_head == on_head:
      return
    # Current state does not match the target state, change the state.
    if current_state.is_on_head:
      self.wear_down()
    else:
      if not current_state.is_box_open:
        self._send_bes_command(constants.BESCommand.OPEN_BOX)
      if current_state.is_in_box:
        self._send_bes_command(constants.BESCommand.FETCH_OUT)
      self._send_bes_command(constants.BESCommand.WEAR_UP)

  def open_box(self) -> None:
    if self.get_box_open_state():
      raise BesRuntimeError('The box is already open, cannot re-open.')
    self._send_bes_command(constants.BESCommand.OPEN_BOX)

  def fetch_out(self) -> None:
    if not self.get_in_box_state():
      raise BesRuntimeError('The BES device is not in box, cannot fetch out.')
    self._send_bes_command(constants.BESCommand.FETCH_OUT)

  def wear_up(self) -> None:
    current_state = self._get_box_state()
    if current_state.is_on_head:
      raise BesRuntimeError(
          'The BES device is already on head, cannot wear up.'
      )
    if current_state.is_in_box:
      raise BesRuntimeError('The BES device is in box, cannot wear up.')
    self._send_bes_command(constants.BESCommand.WEAR_UP)

  def wear_down(self) -> None:
    if not self.get_on_head_state():
      raise BesRuntimeError('The BES device is not on head, cannot wear down.')
    self._send_bes_command(constants.BESCommand.WEAR_DOWN)

  def put_in(self) -> None:
    current_state = self._get_box_state()
    if current_state.is_in_box:
      raise BesRuntimeError('The BES device is already in box, cannot put in.')
    if current_state.is_on_head:
      raise BesRuntimeError('The BES device is on head, cannot put in.')
    self._send_bes_command(constants.BESCommand.PUT_IN)

  def close_box(self) -> None:
    if not self.get_box_open_state():
      raise BesRuntimeError('The box is already closed, cannot re-close.')
    self._send_bes_command(constants.BESCommand.CLOSE_BOX)

  def set_battery_level(self, level: int) -> None:
    """Sets the fake battery level of the device.

    Args:
      level: The fake battery level of the device, in the range of 0-100.
        `level=80` represents that the battery is 80% full.

    Raises:
      ValueError: If the given battery level is not in the valid range.
    """
    if not 0 <= level <= 100:
      raise ValueError(
          f'Invalid battery level {level}, should be in the range of 0-100.'
      )
    self._send_bes_command(
        f'{constants.BESCommand.SET_BATTERY_LEVEL} {level} {level}'
    )

  def set_battery_level_tws(
      self, left_level: int, right_level: int, case_level: int | None = None,
  ) -> None:
    """Sets the fake battery level of the earbuds in a TWS pair.

    Args:
      left_level: The fake battery level of the left earbud in a pair of TWS
        earbuds, in the range of 0-100. `level=80` represents that the battery
        is 80% full.
      right_level: The fake battery level of the right earbud in a pair of TWS
        earbuds, in the range of 0-100
      case_level: The fake battery level of the case in a pair of TWS earbuds,
        in the range of 0-100. If None, there will be no case level set.

    Raises:
      ValueError: If the given battery level is not in the valid range.
    """
    if not 0 <= left_level <= 100:
      raise ValueError(
          f'Invalid battery level {left_level}, should be in the range of'
          ' 0-100.'
      )
    if not 0 <= right_level <= 100:
      raise ValueError(
          f'Invalid battery level {right_level}, should be in the range of'
          ' 0-100.'
      )
    if case_level is not None and not 0 <= case_level <= 100:
      raise ValueError(
          f'Invalid battery level {case_level}, should be in the range of'
          ' 0-100.'
      )
    if case_level is not None:
      self._send_bes_command(
          f'{constants.BESCommand.SET_BATTERY_LEVEL} {left_level} {right_level}'
          f' {case_level}'
      )
    else:
      self._send_bes_command(
          f'{constants.BESCommand.SET_BATTERY_LEVEL} {left_level} {right_level}'
      )

  def get_battery_level(self) -> int:
    """Gets the fake battery level of the board.

    Returns:
      The fake battery level of the board, in the range of 0-100.
      `level=80` represents that the battery is 80% full.

    Raises:
      BesRuntimeError: If failed to get valid battery level from the BES
        response.
    """
    result = self._send_bes_command(constants.BESCommand.GET_BATTERY_LEVEL)
    if matched := _GET_BATTERY_LEVEL_PATTERN.match(result):
      return int(matched['level'])
    raise BesRuntimeError(
        f'Failed to get battery level from command result: {result}'
    )

  def get_battery_level_tws(self) -> tuple[int, int, int | None]:
    """Gets the fake battery level of the board and its remote peer in TWS mode.

    Returns:
      A tuple of 3 integers, representing the fake battery level of the left
      earbud, right earbud, and case in a TWS device, in the range of 0-100.
      `level=80` represents that the battery is 80% full. The case level will
      be None if the BES is not v2.

    Raises:
      BesRuntimeError: If failed to get valid battery level from the BES
        response.
    """
    result = self._send_bes_command(constants.BESCommand.GET_BATTERY_LEVEL)
    if matched := _GET_BATTERY_LEVEL_TWS_PATTERN.match(result):
      left_level = int(matched['left_level'])
      right_level = int(matched['right_level'])
      case_level = int(matched['case_level']) if matched['case_level'] else None
      if (
          left_level < 0
          or left_level > 100
          or right_level < 0
          or right_level > 100
      ):
        raise BesRuntimeError(
            f'Failed to get valid battery level from command result: {result}'
        )
      return left_level, right_level, case_level
    raise BesRuntimeError(
        'Failed to get battery level of TWS earbuds from command result:'
        f' {result}'
    )

  def get_paired_devices(self) -> List[Dict[str, str]]:
    raw_result = self._send_bes_command(constants.BESCommand.GET_PAIRED_DEVICES)
    result = [
        {
            'Name': matched['name'],
            'Address': utils.lsb_addr_to_bd_addr(matched['addr']),
        }
        for matched in _PAIRED_DEVICE_INFO_PATTERN.finditer(raw_result)
    ] + [
        {
            'Name': '',
            'Address': utils.lsb_addr_to_bd_addr(matched['addr']),
        }
        for matched in _LE_PAIRED_DEVICE_INFO_PATTERN.finditer(raw_result)
    ]
    return result

  def media_play(self) -> None:
    self._send_bes_command(constants.BESCommand.MEDIA_PLAY)

  def media_pause(self) -> None:
    self._send_bes_command(constants.BESCommand.MEDIA_PAUSE)

  def media_next(self) -> None:
    self._send_bes_command(constants.BESCommand.MEDIA_NEXT)

  def media_prev(self) -> None:
    self._send_bes_command(constants.BESCommand.MEDIA_PREV)

  def volume_up(self, level: int = 1) -> None:
    for _ in range(level):
      self._send_bes_command(constants.BESCommand.VOLUME_UP)

  def volume_down(self, level: int = 1) -> None:
    for _ in range(level):
      self._send_bes_command(constants.BESCommand.VOLUME_DOWN)

  def set_volume(self, level: int) -> None:
    """Sets the volume of the device to a given level.

    Args:
      level: The target volume level, in the range of [0, 127].

    Raises:
      ValueError: If the given volume level is not in the valid range.
    """
    if level < 0 or level > 127:
      raise ValueError(
          f'Invalid volume level {level}, should be in the range of [0, 127].'
      )

    self._send_bes_command(f'{constants.BESCommand.SET_VOLUME} {level}')

  def get_volume(self) -> int:
    """Gets the volume of the device.

    Returns:
      The volume level of the device.

    Raises:
      BesRuntimeError: If failed to get valid volume level from the BES
        response.
    """
    result = self._send_bes_command(constants.BESCommand.GET_VOLUME)
    if matched := _GET_VOLUME_PATTERN.search(result):
      return int(matched['level'])
    raise BesRuntimeError(
        f'Failed to get volume level from command result: {result}'
    )

  def get_ble_volume(self) -> int:
    """Gets the BLE volume of the device.

    Returns:
      The volume level of the device.

    Raises:
      BesRuntimeError: If failed to get valid volume level from the BES
        response.
    """
    result = self._send_bes_command(constants.BESCommand.GET_VOLUME)
    if matched := _GET_BLE_VOLUME_PATTERN.search(result):
      return int(matched['level'])
    raise BesRuntimeError(
        f'Failed to get BLE volume level from command result: {result}'
    )

  def call_accept(self) -> None:
    self._send_bes_command(constants.BESCommand.CALL_ACCEPT)

  def call_decline(self) -> None:
    self._send_bes_command(constants.BESCommand.CALL_DECLINE)

  def call_hold(self) -> None:
    self._send_bes_command(constants.BESCommand.CALL_HOLD)

  def call_redial(self) -> None:
    self._send_bes_command(constants.BESCommand.CALL_REDIAL)
