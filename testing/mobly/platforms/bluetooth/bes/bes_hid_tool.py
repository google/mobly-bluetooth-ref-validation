"""HID tool for BES boards."""

import datetime
import logging
import pathlib
import re
import time

from mobly import utils as mobly_utils


# The command to install the hidapi library
_HIDAPI_PKG_NAME = 'libhidapi-dev'
_HIDLIB_LIST_COMMAND = f'apt list --installed | grep {_HIDAPI_PKG_NAME}'
_HIDLIB_INSTALL_COMMAND_LOCAL = (
    f'sudo apt-get update && sudo apt-get -y install {_HIDAPI_PKG_NAME}'
)

# The file path of the HID tool script in google3
_HID_TOOL_CODE_PATH = 'testing/mobly/platforms/bluetooth/tools/hidtool.c'

# The directory path pattern to save cache files
_LOCAL_CACHE_DIR_PATH = '/tmp'

_DEFAULT_HIDTOOL_NAME = 'hidtool.o'

_HIDTOOL_COMPILE_COMMAND = 'gcc -o {output_path} {source_path} -lhidapi-hidraw'
_HIDTOOL_RUN_COMMAND_ON_HOST = 'sudo {tool_path} {command}'

_MCU_VERSION_REGEX = r'V\d\.\d\.\d'
_STABLE_MCU_VERSION = 'V1.0.3'

# Timeouts for waiting for the BES boards to be ready
_SHORT_TIMEOUT = datetime.timedelta(seconds=10)
_LONG_TIMEOUT = datetime.timedelta(seconds=30)


def _install_hidapi_lib_local() -> None:
  """Installs hidapi library on Mobly host."""
  _, stdout, _ = mobly_utils.run_command(_HIDLIB_LIST_COMMAND, shell=True)
  if stdout:
    logging.info('HID library is already installed.')
    return

  mobly_utils.run_command(_HIDLIB_INSTALL_COMMAND_LOCAL, shell=True)

  _, stdout, _ = mobly_utils.run_command(_HIDLIB_LIST_COMMAND, shell=True)
  if _HIDAPI_PKG_NAME.encode() not in stdout:
    raise RuntimeError('Failed to install HID library on host.')


def _compile_hidtool_local() -> None:
  """Compiles HID tool source code to a binary on Mobly host."""
  output_file_path = pathlib.Path(
      _LOCAL_CACHE_DIR_PATH,
      _DEFAULT_HIDTOOL_NAME,
  )
  print(output_file_path)
  result = mobly_utils.run_command(
      cmd=_HIDTOOL_COMPILE_COMMAND.format(
          output_path=output_file_path,
          source_path=_HID_TOOL_CODE_PATH,
      ),
      shell=True,
  )
  print(result)
  if not output_file_path.is_file():
    raise FileNotFoundError('Failed to compile HID tool')
  logging.info('HID tool compiled as %s', output_file_path)


def _run_hidtool_local(action_command: str) -> str:
  """Runs HID tool on Mobly host."""
  tool_path = pathlib.Path(
      _LOCAL_CACHE_DIR_PATH,
      _DEFAULT_HIDTOOL_NAME,
  )
  logging.info('HID run command: %s', action_command)
  return mobly_utils.run_command(
      _HIDTOOL_RUN_COMMAND_ON_HOST.format(
          tool_path=tool_path, command=action_command
      ),
      shell=True,
      universal_newlines=True,
  )[1]


def _check_mcu_version_local() -> None:
  """Checks if the MCU version is a stable version on Mobly host.

  BES v2 board has 2 USB ports, 1 for remote control and 1 for data streaming.
  Each port requires a different firmware. The MCU firmware controls button
  press and the BT firmware controls data streaming and other BT features.

  The MCU firmware can only be flashed manually. So we need to check if
  the current MCU version is a stable version. If not, please file a ticket to
  the lab team to flash the MCU firmware.

  Raises:
    RuntimeError: If the MCU version is not a stable version.
  """
  version_result = _run_hidtool_local('WLTVER?')
  for matched in re.findall(_MCU_VERSION_REGEX, version_result):
    if matched != _STABLE_MCU_VERSION:
      raise RuntimeError(
          f'Current MCU version {matched} is not a stable version.'
          ' Please flash the MCU firmware to the stable version'
          f' {_STABLE_MCU_VERSION}.'
      )


def power_on_local() -> None:
  """Powers on the BES boards connected to Mobly host."""
  # 1. Install required libraries on host.
  # _install_hidapi_lib_local()

  # 2. Compile the HID tool on host.
  _compile_hidtool_local()

  # 3. Check the MCU version.
  _check_mcu_version_local()
  time.sleep(_SHORT_TIMEOUT.total_seconds())

  # 4. Run power on and reboot commands one by one to recover the BES boards.
  _run_hidtool_local('mobly_test:power_on')
  time.sleep(_LONG_TIMEOUT.total_seconds())
  _run_hidtool_local('mobly_test:reboot')
  time.sleep(_LONG_TIMEOUT.total_seconds())
