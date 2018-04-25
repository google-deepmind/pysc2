# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Interface for tracking the number and/or latency of episodes and steps."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class _EventTimer(object):
  """Example event timer to measure step and observation times."""

  def __enter__(self):
    pass

  def __exit__(self, unused_exception_type, unused_exc_value, unused_traceback):
    pass


class Metrics(object):
  """Interface for tracking the number and/or latency of episodes and steps."""

  def __init__(self, map_name):
    pass

  def increment_instance(self):
    pass

  def increment_episode(self):
    pass

  def measure_step_time(self, num_steps=1):
    """Return a context manager to measure the time to perform N game steps."""
    del num_steps
    return _EventTimer()

  def measure_observation_time(self):
    """Return a context manager to measure the time to get an observation."""
    return _EventTimer()

  def close(self):
    pass

  def __del__(self):
    self.close()
