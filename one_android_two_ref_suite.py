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

from testing import a2dp_avrcp_tws_test
from testing import a2dp_tws_test
from testing import bt_pair_tws_test
from testing import fast_pair_anc_tws_test
from testing import fast_pair_initial_pair_tws_test
from testing import fast_pair_reconnection_tws_test
from testing import fast_pair_ring_device_tws_test
from testing import lea_audio_streaming_tws_test
from testing import lea_connection_tws_test
from testing import lea_media_control_tws_test
from testing import lea_power_on_off_tws_test
from testing import power_on_off_tws_test
from testing import tws_one_component_battery_level_test
from testing import tws_two_components_battery_level_test


if __name__ == '__main__':
  suite_runner.run_suite([
      bt_pair_tws_test.BtPairTwsTest,
      a2dp_tws_test.MediaPlayTest,
      a2dp_avrcp_tws_test.MediaControlTest,
      tws_one_component_battery_level_test.TwsOneComponentTest,
      tws_two_components_battery_level_test.TwsTwoComponentsTest,
      power_on_off_tws_test.PowerOnOffTwsTest,
      lea_connection_tws_test.LEAConnectionTest,
      lea_power_on_off_tws_test.LEAPowerOnOffTwsTest,
      lea_audio_streaming_tws_test.LEAudioTest,
      lea_media_control_tws_test.LEAudioControlTest,
      fast_pair_initial_pair_tws_test.FastPairInitialPairTwsTest,
      fast_pair_anc_tws_test.FastPairAncTwsTest,
      fast_pair_ring_device_tws_test.FastPairRingDeviceTest,
      fast_pair_reconnection_tws_test.FastPairReconnectionTwsTest,
  ])
