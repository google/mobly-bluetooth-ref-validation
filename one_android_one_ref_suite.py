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

import a2dp_avrcp_test
import a2dp_test
import advertisement_test
import anc_disable_test
import anc_enable_test
import bt_forget_test
import bt_pair_test
import connection_disconnection_test
import fast_pair_anc_test
import fast_pair_initial_pair_test
import le_audio_basic_audio_streaming_test
import le_audio_media_control_test
import non_tws_battery_level_test
import on_head_state_test
import serial_number_test
import set_fp_params_test
import set_name_address_test
import spatial_audio_disable_test
import spatial_audio_enable_test


if __name__ == '__main__':
  suite_runner.run_suite([
      serial_number_test.SerialNumberTest,
      advertisement_test.AdvertisementTest,
      bt_pair_test.BtPairTest,
      connection_disconnection_test.ConnectionDisconnectionTest,
      bt_forget_test.BtForgetPairedDeviceTest,
      a2dp_test.MediaPlayTest,
      a2dp_avrcp_test.MediaControlTest,
      le_audio_basic_audio_streaming_test.LEAudioTest,
      le_audio_media_control_test.LEAudioControlTest,
      set_name_address_test.SetNameAddressTest,
      non_tws_battery_level_test.NonTwsTest,
      on_head_state_test.OnHeadStateTest,
      anc_disable_test.AncDisableTest,
      anc_enable_test.AncEnableTest,
      spatial_audio_disable_test.SpatialAudioDisableTest,
      spatial_audio_enable_test.SpatialAudioEnableTest,
      set_fp_params_test.SetFastPairParamsTest,
      fast_pair_initial_pair_test.FastPairInitialPairTest,
      fast_pair_anc_test.FastPairAncTest,
  ])
