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

"""A Mobly Test to test the serial number function on reference device."""

import datetime
import logging
import time

from mobly import asserts
from mobly import test_runner

import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=5)


class SerialNumberTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test the serial number function on reference device."""

  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]

  def test_get_serial_number(self) -> None:
    serial_number = self.ref.get_serial_number()
    asserts.assert_not_equal(
        serial_number, '', 'Device serial number should not be empty.'
    )
    logging.info(
        'The serial number of the device is: %s', serial_number
    )

  def teardown_test(self) -> None:
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())
    self.ref.create_output_excerpts(self.current_test_info)


if __name__ == '__main__':
  test_runner.main()
