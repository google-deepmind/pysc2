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
"""Unit test tools."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import logging

from absl.testing import absltest
from pysc2.lib import stopwatch


class TestCase(absltest.TestCase):
  """A test base class that enables stopwatch profiling."""

  def setUp(self):
    super(TestCase, self).setUp()
    stopwatch.sw.clear()
    self._sw_enabled = stopwatch.sw.enabled
    stopwatch.sw.enabled = True

  def tearDown(self):
    super(TestCase, self).tearDown()
    s = str(stopwatch.sw)
    if s:
      logging.info("Stop watch profile:\n%s", s)
    stopwatch.sw.enabled = self._sw_enabled
