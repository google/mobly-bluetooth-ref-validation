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

"""Streams the logs from the BES board to local."""

import datetime
import logging
import os
import time
import threading
from typing import List

from mobly import logger as mobly_logger
import serial

_OPEN_SERIAL_PORT_TIMEOUT = datetime.timedelta(seconds=5)


class Error(Exception):
  """Raised for exceptions that occurred in BaseTestClass."""


class SystemLogger(object):
  """record system log."""

  def __init__(self) -> None:
    super(SystemLogger, self).__init__()
    self.sys_log_port = None
    self.rate = None
    self.serial_port = None
    self.record_file = None
    self.file_handle = None
    self.record_folder = None
    self.hci_log_file = None
    self.hci_file_handle = None
    self.recording_dump = False
    self.need_switch = False
    self.stop_record_log = False
    self.max_file_size = 1024 * 1024 * 15

    self._lock = threading.Lock()
    self._thread = None

  @property
  def is_active(self):
    """Publisher is running."""
    return self._thread and self._thread.is_alive() and self.serial_port is not None and self.serial_port.isOpen()

  def open_port(
      self, port: str, rate: int, log_file: str, port_open_timeout: float = 1
  ) -> bool:
    """Opens device serial port."""
    self.sys_log_port = port
    self.rate = rate
    try:
      self.record_file = log_file
      self.file_handle = open(self.record_file, "ab+")

      self.serial_port = serial.Serial(
          port=self.sys_log_port,
          baudrate=self.rate,
          bytesize=serial.EIGHTBITS,
          parity=serial.PARITY_NONE,
          stopbits=serial.STOPBITS_ONE,
          timeout=port_open_timeout,
          rtscts=False,
          dsrdtr=False,
      )
      deadline = time.perf_counter() + _OPEN_SERIAL_PORT_TIMEOUT.total_seconds()
      while time.perf_counter() <= deadline:
        if self.serial_port.isOpen():
          return True
        time.sleep(0.1)
      return False
    except Exception as e:
      raise Error(f"open port '{self.sys_log_port}' fail") from e

  def start(self) -> None:
    if self.is_active:
      return
    self._thread = threading.Thread(target=self._start_record_log)
    self._thread.start()

  def stop(self) -> None:
    self.stop_log()
    self._thread.join()

  def send_command(self, command_str: str) -> None:
    """Sends command to device serial port."""
    try:
      logging.info(f"sending BES command: {command_str}")
      command_bytes = command_str.strip().encode() + b"\r\n"
      with self._lock:
        if self.serial_port is not None and self.serial_port.isOpen():
          self.serial_port.write(command_bytes)
        else:
          raise Error(f"serial port '{self.sys_log_port}' was not opened")
    except Exception as e:
      raise Error(f"send command '{command_str}' fail") from e

  def _log_handle(self, byte_raw: bytes, leftover: bytes) -> bytes:
    if self.file_handle is None:
      return b""
    byte_raw = leftover + byte_raw
    byte_list = byte_raw.split(b"\n")
    for line in byte_list[:-1]:
      time_str = mobly_logger.get_log_line_timestamp().encode("ascii")
      self.file_handle.write(time_str + b"\t" + line + b"\n")
    self.file_handle.flush()
    return byte_list[-1]

  def _start_record_log(self) -> None:
    """Starts to record log."""
    if self.file_handle is None:
      raise Error("log file was not opened")

    leftover = b""
    while True:
      try:
        with self._lock:
          if self.serial_port is None or not self.serial_port.isOpen() or self.stop_record_log:
            break
          if self.serial_port.in_waiting < 16:
            continue
          log_byte = self.serial_port.read(self.serial_port.in_waiting)
        leftover = self._log_handle(log_byte, leftover)
      except Exception:
        logging.exception("record system log fail")
        pass

  def stop_log(self) -> None:
    """Stops logging."""
    try:
      if self.serial_port:
        if self.serial_port.isOpen():
          with self._lock:
            self.serial_port.close()
            self.serial_port = None
          time.sleep(2)
          self.file_handle.close()
        else:
          raise Error(f"serial port '{self.sys_log_port}'' was not opened")
      else:
        raise Error(f"serial port '{self.sys_log_port}'' was not opened")
    except Exception as e:
      raise Error("stop log port fail") from e
    finally:
      self.file_handle = None
      self.stop_record_log = True
