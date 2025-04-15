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

"""Logcat Publisher and Subscriber Mobly Service."""

from mobly.controllers.android_device_lib.services import base_service
from testing.mobly.platforms.android.services import logcat_pubsub


class LogcatPublisherConfig(object):
  """Config object for logcat publisher service.

  Args:
    logcat_file_path: String, Path to local logcat file on host.
  """

  def __init__(self, logcat_file_path):
    self.logcat_file_path = logcat_file_path


class LogcatPublisherService(base_service.BaseService):
  """Logcat Publisher Mobly Service.

  Args:
    android_device: AndroidDevice, Mobly device controller object.
    configs: LogcatPublisherConfig, Configuration parameters for this service.
  """

  def __init__(self, android_device, configs=None):
    if configs:
      logcat_file_path = configs.logcat_file_path
    else:
      logcat_file_path = android_device.services.logcat.adb_logcat_file_path
    self.publisher = logcat_pubsub.LogcatPublisher(
        logcat_file_path=logcat_file_path)

  def start(self):
    """Start the publisher process and task."""
    self.publisher.start()

  def stop(self):
    """Stop the publisher process and task."""
    self.publisher.stop()

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
    return self.publisher.event(pattern=pattern, tag=tag, level=level)

  @property
  def is_alive(self):
    """Publisher is running."""
    return self.publisher.is_active

  def subscribe(self, subscriber_service):
    """Subscribe a handler to this publisher.

    Args:
      subscriber_service: LogcatSubscriberService, a logcat subscriber service
        to subscribe.
    """
    self.publisher.subscribe(subscriber=subscriber_service.subscriber)

  def unsubscribe(self, subscriber_service):
    """Unsubscribe a subscriber to this publisher.

    Args:
      subscriber_service: LogcatSubscriberService, a logcat subscriber service
        to unsubscribe.
    """
    self.publisher.unsubscribe(subscriber=subscriber_service.subscriber)


class LogcatSubscriberConfig(object):
  """Config object for logcat subscriber service.

  Args:
    publisher_service: LogcatPublisherService, logcat publisher service to
      subscribe to.
  """

  def __init__(self, publisher_service):
    self.publisher_service = publisher_service


class LogcatSubscriberService(base_service.BaseService):
  """Logcat Subscriber Mobly Service.

  Args:
    android_device: AndroidDevice, Mobly device controller object.
    configs: LogcatSubscriberConfig, Configuration parameters for this service.
  """

  def __init__(self, android_device, configs=None):
    self.subscriber = logcat_pubsub.LogcatSubscriber()
    if configs:
      self.subscribe(configs.publisher_service)

  def start(self):
    """Start the subscriber service.

    This method has no effect but is required as part of the service interface.
    """

  def stop(self):
    """Start the subscriber service.

    This method has no effect but is required as part of the service interface.
    """

  def subscribe(self, publisher_service):
    """Subscribe this object to a publisher service.

    Args:
      publisher_service: LogcatPublisherService, A logcat publisher service
        to subscribe to.
    """
    self.subscriber.subscribe(publisher_service.publisher)

  def unsubscribe(self):
    """Unsubscribe this object to its publisher service."""
    self.subscriber.unsubscribe()
