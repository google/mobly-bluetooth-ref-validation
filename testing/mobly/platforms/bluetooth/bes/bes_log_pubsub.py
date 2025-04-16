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

"""Module for log publisher and BES response subscriber.

This module implements a log publisher which continuously monitors a log file
and publishes its results to any subscriber. The subscribers wait for given
patterns to appear in the logs.

The BES response subscriber specifically waits for the BES command response in
the log and parses the data, execution results and error code from the raw log.
"""
from __future__ import annotations

import dataclasses
import datetime
import logging
import re
import threading
from typing import Any, List, Optional

from testing.mobly.platforms.android.services import logcat_pubsub

# Error messages
_PROCESS_NOT_RUNNING_ERROR_MESSAGE = (
    'Log Publisher: streaming process is not running.'
)

# Patterns to parse BES logs
_BES_LOG_LINE_REGEX = re.compile(
    r'(?P<time>\d+)\/(?:.+\/)*(?P<level>[VDIWEFS])\/'
    r'(?P<tag>.+?)\s*\/.+\|\s*(?P<message>.*)'
)
_RESPONSE_REGEX = re.compile(r'\[MOBLY_TEST\]:(?P<message>.*)')
_RESPONSE_STATUS_REGEX = re.compile(
    r'result: (?P<status>FAIL|SUCCESS), error_code=(?P<error_code>\d+)'
)


@dataclasses.dataclass(frozen=True)
class LogParsedData:
  """The data parsed from a BES log line.

  Attributes:
    time: The time on the BES board when the line is logged.
    level: The log level of the line.
    tag: The log tag of the line.
    message: The message contained by the log line.
    host_time: The local time on the host.
    line: The full unparsed string of the line.
  """
  time: str
  level: str
  tag: str
  message: str
  host_time: datetime.datetime
  line: str


@dataclasses.dataclass(frozen=True)
class BesResponseData:
  """The data parsed from a BES command response.

  Attributes:
    status: The status of BES command execution.
    error_code: The error code of the execution. 0 if the execution status is
      SUCCESS. Non-zero error code if the execution status is FAIL.
    message: The detailed message contained in the response.
  """
  status: str
  error_code: int
  message: str


class BesLogPublisher(logcat_pubsub.LogcatPublisher):
  """Log event publisher class.

  This is a subclass of Android service logcat_pubsub.LogcatPublisher.
  It continuously monitors a log file and publishes its results to any
  subscriber. The main difference is that this class matches BES log pattern
  before publishing.

  Example BES log line:

    10516/R-M/I/AUDFLG/ 10 | [AUD][DECODER][SYNC]reset_data

  The published object will contain the fields:

  - `time` is a string reflecting the parsed value of `10516`, which is the
    system clock of the BES board starting from last reboot.
  - `level` is a string reflecting the parsed value of `I`, which is the log
    level of this line.
  - `tag` is a string reflecting the parsed value of `AUDFLG`.
  - `message` is a string reflecting the parsed value of
    `[AUD][DECODER][SYNC]reset_data`, which is the detailed message.
  - `host_time` is a `datetime` object reflecting the local time on the host.
  - `line` is a string reflecting the unparsed line.
  """

  def bes_response(self) -> BesResponseSubscriber:
    """Creates a context manager object for a BES command response.

    A context manager will be created that automatically subscribes to this
    publisher.

    Returns:
      A context manager describing the event.
    """
    return BesResponseSubscriber(self)

  def _task(self) -> None:
    """Main publisher thread task."""
    if self._process is None or self._process.stdout is None:
      logging.error(_PROCESS_NOT_RUNNING_ERROR_MESSAGE)
      return

    pub_data = None
    for line in iter(self._process.stdout.readline, ''):
      if self._process.returncode is not None:
        break
      line = line.strip()
      if not line:
        continue
      if matched := _BES_LOG_LINE_REGEX.search(line):
        pub_data = LogParsedData(
            time=matched['time'],
            level=matched['level'],
            tag=matched['tag'],
            message=matched['message'],
            host_time=datetime.datetime.now(),
            line=line,
        )
      # Use the time, level and tag of the previous log line to parse the
      # unformatted log line. Unformatted logs lines are usually long HCI data
      # of its previous line that cannot fit into one line in serial outputs.
      else:
        if pub_data is None:
          continue
        pub_data = LogParsedData(
            time=pub_data.time,
            level=pub_data.level,
            tag=pub_data.tag,
            message=line,
            host_time=datetime.datetime.now(),
            line=line,
        )

      for subscriber in self._subscribers:
        subscriber.handle(pub_data)


class BesResponseSubscriber(logcat_pubsub.LogcatSubscriber):
  r"""Log event subscriber class.

  This class waits for the first BES response to occur after it subscribes to
  the `BesLogPublisher`.

  A BES response may contain multiple lines of data starting with
  "[MOBLY_TEST]:" tag, with an ending line contiaing execution status.
  Example:

  [MOBLY_TEST]:bt_addr: 112233445566
  [MOBLY_TEST]:ble_addr: 112233445566
  [MOBLY_TEST]:bt_name: bt
  [MOBLY_TEST]:ble_name: ble
  [MOBLY_TEST]:result: SUCCESS, error_code=0

  The above example is the response of BES command "get_device_info", which has
  4 data lines and 1 status line.
  This class collects all the data lines until a status line occurs. The above
  example will be parsed into:

  BesResponseData(
      status='SUCCESS',
      error_code=0,
      message=(
          'bt_addr: 112233445566\n'
          'ble_addr: 112233445566\n'
          'bt_name:bt\n'
          'ble_name: ble'
      ),
  )

  Attributes:
    trigger: The parsed BES response data that matches the expected trigger
      expression.
  """

  _event: threading.Event
  _log_cache: List[str]
  trigger: Optional[BesResponseData] = None

  def __init__(self, publisher: BesLogPublisher) -> None:
    """Initializes the instance."""
    super().__init__()

    self.name = 'BesResponseSubscriber'
    self.trigger = None
    self._event = threading.Event()
    self._log_cache = []
    self.subscribe(publisher)

  def __enter__(self) -> 'BesResponseSubscriber':
    return self

  def __exit__(self, *_: Any) -> None:
    self.unsubscribe()

  def clear(self) -> None:
    """Clears any set event."""
    self.trigger = None
    self._log_cache.clear()
    self._event.clear()

  def wait(
      self,
      timeout: Optional[float | datetime.timedelta] = None,
  ) -> bool:
    """Waits until the trigger expression is seen.

    Args:
      timeout: Timeout seconds for the operation. If None, there will be no
        timeout for the operation.

    Returns:
      True if the trigger event is set. False if a timeout is given and the
      operation times out.
    """
    if isinstance(timeout, datetime.timedelta):
      timeout = timeout.total_seconds()
    return self._event.wait(timeout)

  def is_set(self) -> bool:
    """Returns True if the trigger expression has been seen, False otherwise."""
    return self._event.is_set()

  def handle(self, data: LogParsedData) -> None:
    """Handles a log subscription message from the publisher.

    Args:
      data: LogParsedData, the published data to handle.
    """
    if self.trigger is not None:
      return

    if matched := _RESPONSE_REGEX.search(data.message):
      message = matched['message'].strip()
      if status_matched := _RESPONSE_STATUS_REGEX.search(message):
        self.trigger = BesResponseData(
            status=status_matched['status'],
            error_code=int(status_matched['error_code']),
            message='\n'.join(self._log_cache),
        )
        self._event.set()
      else:
        self._log_cache.append(message)
