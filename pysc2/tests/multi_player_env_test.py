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
"""Test that the multiplayer environment works."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest
from absl.testing import parameterized
from future.builtins import range  # pylint: disable=redefined-builtin

from pysc2.agents import random_agent
from pysc2.env import run_loop
from pysc2.env import sc2_env
from pysc2.tests import utils


class TestMultiplayerEnv(parameterized.TestCase, utils.TestCase):

  @parameterized.named_parameters(
      ("features", {"feature_screen_size": 84, "feature_minimap_size": 64}),
      ("rgb", {"rgb_screen_size": 84, "rgb_minimap_size": 64}),
  )
  def test_multi_player_env(self, params):
    steps = 100
    step_mul = 16
    players = 2
    with sc2_env.SC2Env(
        map_name="Simple64",
        players=[sc2_env.Agent(sc2_env.Race.random),
                 sc2_env.Agent(sc2_env.Race.random)],
        step_mul=step_mul,
        game_steps_per_episode=steps * step_mul // 2,
        **params) as env:
      agents = [random_agent.RandomAgent() for _ in range(players)]
      run_loop.run_loop(agents, env, steps)


if __name__ == "__main__":
  absltest.main()
