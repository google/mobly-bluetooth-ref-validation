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

"""Implementation of ADB logcat publisher.

This module implements an ADB logcat publisher which continuously monitors
an ADB logcat stream and publishes its results to any subscriber. This
implementation replaces the default logcat monitor used in mobly which saves
logcat streams in /tmp with no option to reconfigure the destination.
Due to the lack of inotify in OverlayFS, attempts to "tail -F" any files
could result in inconsistent timing of logcat lines.
"""

import collections
import datetime
import fnmatch
import re
import subprocess
import sys
import threading
from typing import Optional, Union

from dateutil.parser import parse as parse_date


_LOGCAT_LINE_REGEX = re.compile(
    r'(?P<time>\d\d-\d\d \d\d:\d\d:\d\d.\d\d\d)\s+'
    r'(?P<pid>\d+)\s+(?P<tid>\d+)\s+(?P<level>[VDIWEFS])\s+'
    r'(?P<tag>.+?)\s*:\s+(?P<message>.*)')


LogcatData = collections.namedtuple(
    'LogcatData', ['time', 'pid', 'tid', 'level', 'tag', 'message',
                   'host_time', 'line'])


class LogcatError(Exception):
  """Logcat publisher or subscriber error."""


class LogcatPublisher(object):
  """Implementation of an ADB logcat publisher class.

  The logcat publisher attaches to an existing logcat file, specified by the
  `logcat_file_path` initializer argument. As lines get appended to the
  logcat file, the publisher will monitor changes and publish a `LogcatData`
  object all of its subscribers. In the example logcat line:

    01-02 03:45:01.100  1000  1001 I MockManager: Starting service.

  The published object will contain the fields:

  - `time` is a `datetime` object reflecting the parsed value of
    `01-02 03:45:01.100`.
  - `pid` is an integer reflecting the parsed value of `1000`
  - `tid` is an integer reflecting the parsed value of `1001`
  - `level` is a string reflecting the parsed value of `I`
  - `tag` is a string reflecting the parsed value of `MockManager`
  - `message` is a string reflecting the parsed value of `Starting service.`
  - `host_time` is a `datetime` object reflecting the local time on the host.
  - `line` is a string reflecting the unparsed line.

  Note:
    Due to an issue with `inotify` on some versions of Linux, new log lines
    may not be observed in real time when the logcat file is written to
    `/tmp` and should not be used for logcat files created in that location.
    See details at
    https://bugs.launchpad.net/ubuntu/+source/linux/+bug/882147

  Args:
    logcat_file_path: local path of ADB logcat file.
  """

  def __init__(self, logcat_file_path):
    super(LogcatPublisher, self).__init__()
    self._logcat_file_path = logcat_file_path
    self._thread = None
    self._process = None
    self._subscribers = []

  def start(self):
    """Start the publisher process and task.

    Raises:
        LogcatError: If process is already running.
    """
    if self.is_active:
      raise LogcatError('Publisher process is already running.')

    if sys.platform == 'win32':
      cmd = [
          'powershell',
          'Get-Content',
          '-Wait',
          f'-Path "{self._logcat_file_path}"',
      ]
    else:
      cmd = ['tail', '-F', self._logcat_file_path]
    self._process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding='utf-8',
        errors='ignore')
    self._thread = threading.Thread(target=self._task)
    self._thread.daemon = True
    self._thread.start()

  def stop(self):
    """Stop the publisher process and task."""
    if self.is_active:
      self._process.terminate()
      self._process.wait()
      self._thread.join()

  def event(self, pattern='.*', tag='*', level='V'):
    """Context manager object for a logcat event.

    A context manager will be created that automatically subscribes to this
    publisher.

    Args:
      pattern: str, Regular expression pattern to trigger on.
      tag: str, Tag portion of filterspec string.
      level: str, Level portion of filterspec string.

    Returns:
      A context manager describing the event.
    """
    return LogcatEventSubscriber(self, pattern=pattern, tag=tag, level=level)

  @property
  def is_active(self):
    """Publisher is running."""
    return (self._process and self._process.returncode is None
            and self._thread and self._thread.is_alive())

  def subscribe(self, subscriber):
    """Subscribe a handler to this publisher.

    Args:
      subscriber: LogcatSubscriber, a logcat subscriber to subscribe.

    Raises:
      LogcatError: When subscriber is not a LogcatSubscriber.
    """
    if not isinstance(subscriber, LogcatSubscriber):
      raise TypeError('Attempted to subscribe a non-subscriber.')
    self._subscribers.append(subscriber)

  def unsubscribe(self, subscriber):
    """Unsubscribe a subscriber to this publisher.

    Args:
      subscriber: LogcatSubscriber, a logcat subscriber to unsubscribe.

    Raises:
      LogcatError: When the argument is not previously registered
        subscriber.
    """
    if subscriber not in self._subscribers:
      raise LogcatError('Attempted to unsubscribe a non-subscriber.')
    self._subscribers.remove(subscriber)

  def _task(self):
    """Main publisher thread task."""
    if self._process is None:
      raise ValueError('Process not running.')
    for line in iter(self._process.stdout.readline, ''):
      if self._process.returncode is not None:
        break
      match = _LOGCAT_LINE_REGEX.match(line)
      if match is None:
        continue

      pub_data = LogcatData(
          time=parse_date(match.group('time')),
          pid=int(match.group('pid')),
          tid=int(match.group('tid')),
          level=match.group('level'),
          tag=match.group('tag'),
          message=match.group('message').strip(),
          host_time=datetime.datetime.now(),
          line=line)

      for subscriber in self._subscribers:
        subscriber.handle(pub_data)


class LogcatSubscriber(object):
  """Base class for logcat subscriber."""

  def __init__(self):
    super(LogcatSubscriber, self).__init__()
    self._publisher = None

  def subscribe(self, publisher):
    """Subscribe this object to a publisher.

    Args:
      publisher: LogcatPublisher, a logcat publisher to subscribe to.

    Raises:
      LogcatError: If publisher is not a LogcatPublisher.
    """
    if not isinstance(publisher, LogcatPublisher):
      raise TypeError('"publisher" is not a LogcatPublisher.')
    publisher.subscribe(self)
    self._publisher = publisher

  def unsubscribe(self):
    """Unsubscribe this object to its publisher."""
    if self._publisher:
      self._publisher.unsubscribe(self)
    self._publisher = None

  def handle(self, data):
    """Abstract subscribe handler method.

    This abstract method defines the subscribe handler and must be
    overridden by derived class.

    Args:
      data: LogcatData, Data to handle.

    Raises:
      LogcatError: If subclass method is not implemented.
    """
    raise NotImplementedError('"handle" is a required subscriber method.')


class LogcatEventSubscriber(LogcatSubscriber):
  """Logcat event subscriber class.

  This class waits for a particular logcat event to occur.

  Args:
    publisher: LogcatPublisher, Logcat publisher to subscribe to.
    pattern: str, Regular expression pattern to trigger on.
    tag: str, Tag portion of filterspec string.
    level: str, Level portion of filterspec string.
  """
  _LOG_LEVELS = 'VDIWEF'

  def __init__(self, publisher, pattern='.*', tag='*', level='V'):
    super(LogcatEventSubscriber, self).__init__()
    self._event = threading.Event()
    self._pattern = (re.compile(pattern) if isinstance(pattern, str)
                     else pattern)
    self._tag = tag
    self._levels = (self._LOG_LEVELS if level == '*'
                    else self._LOG_LEVELS[self._LOG_LEVELS.find(level):])
    self.trigger = None
    self.match = None
    self.subscribe(publisher)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.unsubscribe()

  def clear(self):
    """Clears any set event."""
    self.trigger = None
    self.match = None
    self._event.clear()

  def set(self):
    """Set an event."""
    if not self._event.is_set():
      self._event.set()

  def wait(
      self,
      timeout: Optional[Union[float, datetime.timedelta]] = None,
  ) -> bool:
    """Wait until the trigger expression is seen.

    Args:
      timeout: float in seconds or timedelta, timeout for the operation.

    Returns:
      True except if a timeout is given and the operation times out.
    """
    if isinstance(timeout, datetime.timedelta):
      timeout = timeout.total_seconds()
    return self._event.wait(timeout)

  def is_set(self) -> bool:
    """Returns True if the trigger expression has been seen, False otherwise."""
    return self._event.is_set()

  def handle(self, data):
    """Handle a logcat subscription message.

    Args:
      data: LogcatData, Data to handle.
    """
    if self.trigger:
      return
    if data.tag is None or not fnmatch.fnmatchcase(data.tag, self._tag):
      return
    if data.level is None or data.level not in self._levels:
      return
    self.match = self._pattern.match(data.message)
    if self.match:
      self.trigger = data
      self._event.set()
