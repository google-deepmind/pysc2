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
"""Test that stepping without observing works correctly for multiple players."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest

from pysc2.env import sc2_env
from pysc2.lib import actions
from pysc2.tests import utils


AGENT_INTERFACE_FORMAT = sc2_env.AgentInterfaceFormat(
    feature_dimensions=sc2_env.Dimensions(screen=32, minimap=32)
)


class StepMulOverrideTest(utils.TestCase):

  def test_returns_game_loop_zero_on_first_step_despite_override(self):
    with sc2_env.SC2Env(
        map_name="DefeatRoaches",
        players=[sc2_env.Agent(sc2_env.Race.random)],
        step_mul=1,
        agent_interface_format=AGENT_INTERFACE_FORMAT) as env:
      timestep = env.step(
          actions=[actions.FUNCTIONS.no_op()],
          step_mul=1234)

      self.assertEqual(
          timestep[0].observation.game_loop[0],
          0)

  def test_respects_override(self):
    with sc2_env.SC2Env(
        map_name="DefeatRoaches",
        players=[sc2_env.Agent(sc2_env.Race.random)],
        step_mul=1,
        agent_interface_format=AGENT_INTERFACE_FORMAT) as env:

      expected_game_loop = 0
      for delta in range(10):
        timestep = env.step(
            actions=[actions.FUNCTIONS.no_op()],
            step_mul=delta)

        expected_game_loop += delta
        self.assertEqual(
            timestep[0].observation.game_loop[0],
            expected_game_loop)


if __name__ == "__main__":
  absltest.main()
