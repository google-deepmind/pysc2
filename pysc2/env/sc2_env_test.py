#!/usr/bin/python
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Test for sc2_env."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest
from absl.testing import parameterized

from pysc2.env import sc2_env


class TestNameCroppingAndDeduplication(parameterized.TestCase):

  @parameterized.named_parameters(
      ("empty", [], []),
      ("single_no_crop", ["agent_1"], ["agent_1"]),
      ("single_cropped",
       ["very_long_agent_name_experimental_1"],
       ["very_long_agent_name_experimenta"]),
      ("no_dupes_no_crop",
       ["agent_1", "agent_2"],
       ["agent_1", "agent_2"]),
      ("no_dupes_cropped",
       ["a_very_long_agent_name_experimental",
        "b_very_long_agent_name_experimental"],
       ["a_very_long_agent_name_experimen",
        "b_very_long_agent_name_experimen"]),
      ("dupes_no_crop",
       ["agent_1", "agent_1"],
       ["(1) agent_1", "(2) agent_1"]),
      ("dupes_cropped",
       ["very_long_agent_name_experimental_c123",
        "very_long_agent_name_experimental_c456"],
       ["(1) very_long_agent_name_experim",
        "(2) very_long_agent_name_experim"]),
  )
  def test(self, names, expected_output):
    self.assertEqual(sc2_env.crop_and_deduplicate_names(names), expected_output)


if __name__ == "__main__":
  absltest.main()
