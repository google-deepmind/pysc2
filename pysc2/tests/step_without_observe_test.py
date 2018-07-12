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


class StepWithoutObserveTest(utils.TestCase):

  def test_returns_observation_on_first_step_despite_no_observe(self):
    with sc2_env.SC2Env(
        map_name="DefeatRoaches",
        players=[sc2_env.Agent(sc2_env.Race.random)],
        step_mul=1,
        agent_interface_format=AGENT_INTERFACE_FORMAT) as env:
      timestep = env.step(
          actions=[actions.FUNCTIONS.no_op()],
          update_observation=[False])

      self.assertEqual(
          timestep[0].observation.game_loop[0],
          1)

  def test_returns_old_observation_when_no_observe(self):
    with sc2_env.SC2Env(
        map_name="DefeatRoaches",
        players=[sc2_env.Agent(sc2_env.Race.random)],
        step_mul=1,
        agent_interface_format=AGENT_INTERFACE_FORMAT) as env:

      for step in range(10):
        observe = step % 3 == 0
        timestep = env.step(
            actions=[actions.FUNCTIONS.no_op()],
            update_observation=[observe])

        expected_game_loop = 3 * (step // 3) + 1
        self.assertEqual(
            timestep[0].observation.game_loop[0],
            expected_game_loop)

  def test_respects_observe_parameter_per_player(self):
    with sc2_env.SC2Env(
        map_name="Simple64",
        players=[
            sc2_env.Agent(sc2_env.Race.random),
            sc2_env.Agent(sc2_env.Race.random),
        ],
        step_mul=1,
        agent_interface_format=AGENT_INTERFACE_FORMAT) as env:

      for step in range(10):
        observe = step % 3 == 0
        timestep = env.step(
            actions=[actions.FUNCTIONS.no_op()] * 2,
            update_observation=[observe, True])

        expected_game_loop = 3 * (step // 3) + 1
        self.assertEqual(
            timestep[0].observation.game_loop[0],
            expected_game_loop)

        self.assertEqual(
            timestep[1].observation.game_loop[0],
            step + 1)

  def test_episode_ends_when_not_observing(self):
    with sc2_env.SC2Env(
        map_name="Simple64",
        players=[
            sc2_env.Agent(sc2_env.Race.random),
            sc2_env.Bot(sc2_env.Race.random, sc2_env.Difficulty.cheat_insane)],
        step_mul=1000,
        agent_interface_format=AGENT_INTERFACE_FORMAT) as env:

      ended = False
      for _ in range(100):
        timestep = env.step(
            actions=[actions.FUNCTIONS.no_op()],
            update_observation=[False])

        if timestep[0].last():
          ended = True
          break

      self.assertTrue(ended)


if __name__ == "__main__":
  absltest.main()
