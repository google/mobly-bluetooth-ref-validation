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

"""The serial command constants for BES devboard."""

import enum

_COMMAND_PREFIX = 'mobly_test:'


@enum.unique
class BESCommand(enum.Enum):
  """Serial commands to control BES Device."""

  POWER_ON = 'power_on'
  POWER_OFF = 'power_off'
  REBOOT = 'reboot'
  FACTORY_RESET = 'factory_reset'
  GET_DEVICE_INFO = 'get_device_info'
  GET_SERIAL_NUMBER = 'get_wlt_sn'
  SET_NAME = 'set_name'
  SET_ADDRESS = 'set_address'
  SET_FP_MODEL_ID = 'set_model_id'
  SET_FP_PRIVATE_KEY = 'set_gfps_private_key'
  SET_LINK_POINT = 'set_link_point'

  # TWS preparation
  SET_TWS_ENABLE = 'set_link_tws'
  SET_COMPONENT_NUMBER = 'set_lea_csip'
  GET_COMPONENT_NUMBER = 'get_lea_csip'
  TWS_PAIRING = 'tws_pairing'
  GET_BOX_STATE = 'get_box_state'
  OPEN_BOX = 'open_box'
  FETCH_OUT = 'fetch_out'
  WEAR_UP = 'wear_up'
  WEAR_DOWN = 'wear_down'
  PUT_IN = 'put_in'
  CLOSE_BOX = 'close_box'

  # Basic connection
  START_PAIRING_MODE = 'enable_pairing'
  STOP_PAIRING_MODE = 'disable_pairing'
  CONNECT = 'connect'
  DISCONNECT = 'disconnect'
  CLEAR_PAIRED_DEVICES = 'clear_paired_device'
  GET_PAIRED_DEVICES = 'get_paired_device'

  # Battery
  SET_BATTERY_LEVEL = 'set_battery_level'
  GET_BATTERY_LEVEL = 'get_battery_level'

  # Volume
  VOLUME_UP = 'volume_plus'
  VOLUME_DOWN = 'volume_dec'
  GET_VOLUME = 'get_volume'
  SET_VOLUME = 'set_volume'

  # Media
  MEDIA_PLAY = 'media_play'
  MEDIA_PAUSE = 'media_pause'
  MEDIA_NEXT = 'media_next'
  MEDIA_PREV = 'media_prev'

  # Call
  CALL_ACCEPT = 'call_accept'
  CALL_DECLINE = 'call_decline'
  CALL_HOLD = 'call_hold'
  CALL_REDIAL = 'call_redial'

  # ANC
  SET_ANC_MODE = 'set_anc'

  # Spatial Audio
  SET_SPATIAL_AUDIO_ENABLE = 'set_spatial_audio'

  def __str__(self):
    return f'{_COMMAND_PREFIX}{self.value}'
