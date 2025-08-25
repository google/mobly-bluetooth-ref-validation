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

"""Utils for setting up Android phone."""

import datetime
import time

from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb
from snippet_uiautomator import uiautomator

_MBS_UI_APK_PATH = 'testing/assets/mbs_uiautomator.apk'
_MBS_UI_PACKAGE = 'com.google.devtools.bettertogether.mbsuiautomator'

_BT_SNIPPET_APK_PATH = 'testing/assets/bluetooth_snippets.apk'
_BT_SNIPPET_PACKAGE = 'com.google.bluetooth.snippet'

_DELAY_AFTER_CHANGE_BT_STATUS = datetime.timedelta(seconds=3)


def load_bluetooth_snippet(
    ad: android_device.AndroidDevice,
    mbs_snippet_name: str = 'bt',
) -> None:
  """Install bluetooth snippet to DUT.

  Args:
    ad: The android device that needs to load snippet service.
    uiautomator_snippet_name: The attribute name attached the Snippet
      UiAutomator.
    mbs_snippet_name: The attribute name attached the BT snippet client.
  """
  ad.adb.install(_BT_SNIPPET_APK_PATH, replace=True)
  ad.load_snippet('bt', _BT_SNIPPET_PACKAGE)

def load_mbs_and_uiautomator(
    ad: android_device.AndroidDevice,
    uiautomator_snippet_name: str = 'ui',
    mbs_snippet_name: str = 'mbs',
) -> None:
  """Combines Mobly Bundled Snippets and Snippet UiAutomator.

  The MBS and Snippet UiAutomator will be loaded in the same snippet service.
  However, in order to keep the original calling method in Python, e.g.,
    - ad.mbs.makeToast('Hello, World!')
    - ad.ui(text='Chrome').info
  this method still creates two properties named `mbs` and `ui` separately even
  both of them point to the same snippet service.

  Args:
    ad: The android device that needs to load snippet service.
    uiautomator_snippet_name: The attribute name attached the Snippet
      UiAutomator.
    mbs_snippet_name: The attribute name attached the MBS snippet client.
  """
  if ad.services.has_service_by_name(uiautomator.ANDROID_SERVICE_NAME):
    ad.log.debug('The uiautomator service is already running')
    return

  ad.services.register(
      alias=uiautomator.ANDROID_SERVICE_NAME,
      service_class=uiautomator.UiAutomatorService,
      configs=uiautomator.UiAutomatorConfigs(
          snippet=uiautomator.Snippet(
              package_name=_MBS_UI_PACKAGE,
              file_path=_MBS_UI_APK_PATH,
              ui_public_service_name=uiautomator_snippet_name,
              custom_service_name=mbs_snippet_name,
          )
      ),
  )


def enable_bluetooth_hci_log(ad: android_device.AndroidDevice) -> None:
  """Enables bluetooth HCI log."""
  try:
    ad.adb.shell('setprop persist.bluetooth.btsnooplogmode full')
    ad.adb.shell('svc bluetooth disable')
    time.sleep(_DELAY_AFTER_CHANGE_BT_STATUS.total_seconds())
    ad.adb.shell('svc bluetooth enable')
    time.sleep(_DELAY_AFTER_CHANGE_BT_STATUS.total_seconds())
  except adb.AdbError:
    ad.log.exception('No permission to enable bluetoothe HCI log.')

