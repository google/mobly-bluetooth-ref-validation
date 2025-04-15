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

"""Test suite for one Android + two Bluetooth reference device."""

from mobly import suite_runner

import fast_pair_ring_device_test
import tws_one_component_battery_level_test
import tws_two_components_battery_level_test


if __name__ == '__main__':
  suite_runner.run_suite([
      tws_one_component_battery_level_test.TwsOneComponentTest,
      tws_two_components_battery_level_test.TwsTwoComponentsTest,
      fast_pair_ring_device_test.FastPairRingDeviceTest,
  ])
