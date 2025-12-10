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

"""The base test class for BT validation."""

import logging

from mobly import base_test
from mobly import records
from mobly import test_runner
from mobly import utils
from mobly.controllers import android_device

from testing.utils import constants


def _pull_bt_snoop_logs(
    ads: list[android_device.AndroidDevice],
    destination: str,
):
  def _pull_bt_snoop_log(ad):
    if not ad.is_adb_root:
      ad.log.warning(
          'Andoird device is not rooted. Skip BT snoop collection.'
      )
      return
    ad.adb.pull([
        '/data/misc/bluetooth/logs/btsnoop_hci.log',
        f'{destination}/btsnoop_hci_{ad.serial}.log',
    ])

  utils.concurrent_exec(
      _pull_bt_snoop_log,
      [[ad] for ad in ads],
      raise_on_exception=True,
  )


class BtRefBaseTest(base_test.BaseTestClass):
  """A Mobly base test for BT validation."""

  def setup_class(self):
    suite_name = f'{constants.SUITE_NAME}: {constants.VERSION}'
    self.record_data({
        'properties': {
            'suite_name': f'[{suite_name}]',
        }
    })

  def _capture_bug_reports(
      self, ads: list[android_device.AndroidDevice]
  ) -> None:
    logging.info('Capturing bugreport from android, this may take a while...')
    _pull_bt_snoop_logs(ads, self.current_test_info.output_path)

  def on_fail(self, record: records.TestResultRecord) -> None:
    super().on_fail(record)
    if hasattr(self, 'ad'):
      self._capture_bug_reports([self.ad])
    elif hasattr(self, 'ad_a') and hasattr(self, 'ad_b'):
      self._capture_bug_reports([self.ad_a, self.ad_b])
    elif hasattr(self, 'initial_pair_phone') and hasattr(
        self, 'subsequent_pair_phone'
    ):
      self._capture_bug_reports(
          [self.initial_pair_phone, self.subsequent_pair_phone]
      )
