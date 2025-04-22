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

"""Test Bluetooth on-head status of the reference device."""

import datetime
import time
import uuid

from mobly import asserts
from mobly import test_runner

from testing import bt_base_test
from testing.mobly.platforms.bluetooth import bluetooth_reference_device

_DELAYS_BETWEEN_ACTIONS = datetime.timedelta(seconds=2)


class OnHeadStateTest(bt_base_test.BtRefBaseTest):
  """A Mobly Test to test on-head status of reference device."""

  ref: bluetooth_reference_device.BluetoothReferenceDeviceBase

  def setup_class(self) -> None:
    super().setup_class()

    # Register Bluetooth reference device
    self.ref = self.register_controller(bluetooth_reference_device)[0]
    self.ref.factory_reset()

  def test_1_tws_user_actions(self) -> None:
    self.ref.fetch_out()
    asserts.assert_false(
        self.ref.get_in_box_state(),
        'Failed to get correct in-box state after fetch_out, expect False, got True'
    )
    asserts.assert_false(
        self.ref.get_on_head_state(),
        'Failed to get correct on-head state after fetch_out, expect False, got True'
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    self.ref.wear_up()
    asserts.assert_false(
        self.ref.get_in_box_state(),
        'Failed to get correct in-box state after wear_up, expect False, got True'
    )
    asserts.assert_true(
        self.ref.get_on_head_state(),
        'Failed to get correct on-head state after wear_up, expect True, got False'
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    self.ref.wear_down()
    asserts.assert_false(
        self.ref.get_in_box_state(),
        'Failed to get correct in-box state after wear_down, expect False, got True'
    )
    asserts.assert_false(
        self.ref.get_on_head_state(),
        'Failed to get correct on-head state after wear_down, expect False, got True'
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    self.ref.put_in()
    asserts.assert_true(
        self.ref.get_in_box_state(),
        'Failed to get correct in-box state after put_in, expect True, got False'
    )
    asserts.assert_false(
        self.ref.get_on_head_state(),
        'Failed to get correct on-head state after put_in, expect False, got True'
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    self.ref.close_box()
    asserts.assert_true(
        self.ref.get_in_box_state(),
        'Failed to get correct in-box state after close_box, expect True, got False'
    )
    asserts.assert_false(
        self.ref.get_on_head_state(),
        'Failed to get correct on-head state after close_box, expect False, got True'
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    self.ref.open_box()
    asserts.assert_true(
        self.ref.get_in_box_state(),
        'Failed to get correct in-box state after open_box, expect True, got False'
    )
    asserts.assert_false(
        self.ref.get_on_head_state(),
        'Failed to get correct on-head state after open_box, expect False, got True'
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

  def test_2_tws_set_states(self) -> None:
    self.ref.set_in_box_state(False)
    asserts.assert_false(
        self.ref.get_in_box_state(),
        'Failed to set in-box state to False'
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    self.ref.set_on_head_state(True)
    asserts.assert_false(
        self.ref.get_in_box_state(),
        'Failed to set in-box state to False'
    )
    asserts.assert_true(
        self.ref.get_on_head_state(),
        'Failed to set on-head state to True'
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    self.ref.set_on_head_state(False)
    asserts.assert_false(
        self.ref.get_on_head_state(),
        'Failed to set on-head state to False'
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

    self.ref.set_in_box_state(True)
    asserts.assert_true(
        self.ref.get_in_box_state(),
        'Failed to set in-box state to True'
    )
    asserts.assert_false(
        self.ref.get_on_head_state(),
        'Failed to set on-head state to False'
    )
    time.sleep(_DELAYS_BETWEEN_ACTIONS.total_seconds())

  def teardown_test(self) -> None:
    self.ref.create_output_excerpts(self.current_test_info)


if __name__ == '__main__':
  test_runner.main()
