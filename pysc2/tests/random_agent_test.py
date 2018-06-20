#!/usr/bin/python
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
"""Run a random agent for a few steps."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest
from absl.testing import parameterized

from pysc2.agents import random_agent
from pysc2.env import run_loop
from pysc2.env import sc2_env
from pysc2.tests import utils


class TestRandomAgent(parameterized.TestCase, utils.TestCase):

  @parameterized.named_parameters(
      ("features", sc2_env.AgentInterfaceFormat(
          feature_dimensions=sc2_env.Dimensions(screen=84, minimap=64))),
      ("rgb", sc2_env.AgentInterfaceFormat(
          rgb_dimensions=sc2_env.Dimensions(screen=128, minimap=64))),
      ("all", sc2_env.AgentInterfaceFormat(
          feature_dimensions=sc2_env.Dimensions(screen=84, minimap=64),
          rgb_dimensions=sc2_env.Dimensions(screen=128, minimap=64),
          action_space=sc2_env.ActionSpace.FEATURES,
          use_unit_counts=True,
          use_feature_units=True)),
  )
  def test_random_agent(self, agent_interface_format):
    steps = 250
    step_mul = 8
    with sc2_env.SC2Env(
        map_name="Simple64",
        agent_interface_format=agent_interface_format,
        step_mul=step_mul,
        game_steps_per_episode=steps * step_mul//2) as env:
      agent = random_agent.RandomAgent()
      run_loop.run_loop([agent], env, steps)

    self.assertEqual(agent.steps, steps)


if __name__ == "__main__":
  absltest.main()
