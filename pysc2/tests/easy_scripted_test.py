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
"""Solve the nm_easy map using a fixed policy by reading the feature layers."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest


from pysc2.agents import scripted_agent
from pysc2.env import run_loop
from pysc2.env import sc2_env
from pysc2.tests import utils


class TestEasy(utils.TestCase):
  steps = 100
  step_mul = 10

  def test_mn_easy_win(self):
    with sc2_env.SC2Env(
        "TestMNEasy",
        step_mul=self.step_mul,
        game_steps_per_episode=self.steps * self.step_mul) as env:
      agent = scripted_agent.MNEasyWin()
      run_loop.run_loop([agent], env, self.steps)

    # Win all that finish: episodes - 1 <= reward <= episodes
    self.assertLessEqual(agent.episodes - 1, agent.reward)
    self.assertLessEqual(agent.reward, agent.episodes)
    self.assertEqual(agent.steps, self.steps)

  def test_mn_easy_lose(self):
    with sc2_env.SC2Env(
        "TestMNEasy",
        step_mul=self.step_mul,
        game_steps_per_episode=self.steps * self.step_mul) as env:
      agent = scripted_agent.MNEasyLose()
      run_loop.run_loop([agent], env, self.steps)

    # Lose all that finish: episodes - 1 <= -reward <= episodes
    self.assertLessEqual(agent.episodes - 1, -agent.reward)
    self.assertLessEqual(-agent.reward, agent.episodes)
    self.assertEqual(agent.steps, self.steps)


if __name__ == "__main__":
  unittest.main()
