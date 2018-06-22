#!/usr/bin/python
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Tests for portspicker.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest
from absl.testing import parameterized
from pysc2.lib import portspicker


class PortsTest(parameterized.TestCase):

  @parameterized.parameters(range(10))
  def testNonContiguousReservation(self, num_ports):
    reserved = portspicker.pick_unused_ports(num_ports)
    self.assertEqual(len(reserved), num_ports)
    portspicker.return_ports(reserved)

  @parameterized.parameters(range(10))
  def testContiguousReservation(self, num_ports):
    reserved = portspicker.pick_contiguous_unused_ports(num_ports)
    self.assertEqual(len(reserved), num_ports)
    portspicker.return_ports(reserved)


if __name__ == "__main__":
  absltest.main()
