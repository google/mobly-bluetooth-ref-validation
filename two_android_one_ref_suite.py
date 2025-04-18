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

"""Test suite for two Android + Bluetooth reference device."""

from mobly import suite_runner

import bt_pair_multiple_devices_test
import bt_pair_multi_point_test
import bt_pair_single_point_test
import fast_pair_anc_mode_sync_test
import fast_pair_initial_pair_two_devices_test
import fast_pair_subsequent_edit_name_test
import fast_pair_subsequent_pair_test


if __name__ == '__main__':
  suite_runner.run_suite([
      bt_pair_multiple_devices_test.BtPairMultipleTest,
      bt_pair_single_point_test.BtPairSinglePointTest,
      bt_pair_multi_point_test.BtPairMultiPointTest,
      fast_pair_initial_pair_two_devices_test.FastPairInitialPairTwoDevicesTest,
      fast_pair_subsequent_pair_test.FastPairSubsequentPairTest,
      fast_pair_subsequent_edit_name_test.FastPairSubsequentEditNameTest,
      fast_pair_anc_mode_sync_test.FastPairAncModeSyncTest,
  ])
