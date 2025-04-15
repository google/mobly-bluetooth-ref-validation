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

"""Common utils used in Mobly Bluetooth reference devices."""

import base64
import re

_VALID_ADDRESS_PATTERN = re.compile('([0-9A-Fa-f]{2}:){5}([0-9A-Fa-f]{2})')
_RAW_ADDRESS_PATTERN = re.compile('^[0-9A-Fa-f]{12}$')
_ONE_BYTE_PATTERN = re.compile('[0-9A-Fa-f]{2}')
_RAW_MODEL_ID_PATTERN = re.compile(r'^[0-9A-Fa-f]{6}$')


def is_valid_address(address: str) -> bool:
  """Returns True if the given address is a valid Bluetooth Device Address."""
  return _VALID_ADDRESS_PATTERN.fullmatch(address) is not None


def lsb_addr_to_bd_addr(lsb_address: str) -> str:
  """Converts the address from LSB order to Bluetooth device address.

  This method converts the address in in LSB order to Bluetooth Device Address
  (BD_ADDR) format.

  Example: EEFF33221100 => 00:11:22:33:FF:EE

  Args:
    lsb_address: The address string in LSB order.

  Returns:
    A valid Bluetooth device address.
  """
  if is_valid_address(lsb_address):
    return lsb_address
  if _RAW_ADDRESS_PATTERN.match(lsb_address):
    return ':'.join(
        reversed(
            [
                matched.group(0)
                for matched in _ONE_BYTE_PATTERN.finditer(lsb_address)
            ]
        )
    )
  raise ValueError(f'Cannot convert {lsb_address} to Bluetooth device address.')


def reverse_fp_model_id(fp_model_id: str) -> str:
  """Reverses the Fast Pair model ID and add colons."""
  if fp_model_id.startswith('0x'):
    fp_model_id = fp_model_id[2:]
  if _RAW_MODEL_ID_PATTERN.match(fp_model_id):
    return ':'.join(
        reversed(
            [
                matched.group(0)
                for matched in _ONE_BYTE_PATTERN.finditer(fp_model_id)
            ]
        )
    ).lower()
  raise ValueError(f'Invalid Fast Pair model ID {fp_model_id}.')


def decode_fp_private_key(private_key: str) -> str:
  """Decodes the Fast Pair private key to hex string."""
  try:
    decoded_private_key = base64.b64decode(private_key.encode('ascii'))
  except ValueError as e:
    raise ValueError(f'Invalid Fast Pair private key {private_key}.') from e

  if len(decoded_private_key) != 32:
    raise ValueError(f'Invalid Fast Pair private key {private_key}.')

  return decoded_private_key.hex()
