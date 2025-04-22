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

"""Test suite for one Android + Bluetooth reference device."""

from mobly import suite_runner

from testing import a2dp_avrcp_test
from testing import a2dp_test
from testing import advertisement_test
from testing import anc_disable_test
from testing import anc_enable_test
from testing import bt_forget_test
from testing import bt_pair_test
from testing import classic_connection_test
from testing import fast_pair_anc_test
from testing import fast_pair_initial_pair_test
from testing import lea_audio_streaming_test
from testing import lea_connection_test
from testing import non_tws_battery_level_test
from testing import on_head_state_test
from testing import power_on_off_test
from testing import serial_number_test
from testing import set_name_address_test
from testing import spatial_audio_disable_test
from testing import spatial_audio_enable_test


if __name__ == '__main__':
  suite_runner.run_suite([
      serial_number_test.SerialNumberTest,
      advertisement_test.AdvertisementTest,
      bt_pair_test.BtPairTest,
      classic_connection_test.ConnectionDisconnectionTest,
      bt_forget_test.BtForgetPairedDeviceTest,
      power_on_off_test.PowerOnOffTest,
      a2dp_test.MediaPlayTest,
      a2dp_avrcp_test.MediaControlTest,
      lea_connection_test.LEAConnectionTest,
      lea_audio_streaming_test.LEAudioTest,
      set_name_address_test.SetNameAddressTest,
      non_tws_battery_level_test.NonTwsTest,
      on_head_state_test.OnHeadStateTest,
      anc_disable_test.AncDisableTest,
      anc_enable_test.AncEnableTest,
      spatial_audio_disable_test.SpatialAudioDisableTest,
      spatial_audio_enable_test.SpatialAudioEnableTest,
      fast_pair_initial_pair_test.FastPairInitialPairTest,
      fast_pair_anc_test.FastPairAncTest,
  ])
