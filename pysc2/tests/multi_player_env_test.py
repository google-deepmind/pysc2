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

from absl.testing import absltest
from absl.testing import parameterized

from pysc2.agents import no_op_agent
from pysc2.agents import random_agent
from pysc2.env import run_loop
from pysc2.env import sc2_env
from pysc2.tests import utils

from s2clientprotocol import common_pb2 as common_pb
from s2clientprotocol import sc2api_pb2 as sc_pb


class TestMultiplayerEnv(parameterized.TestCase, utils.TestCase):

  @parameterized.named_parameters(
      ("features",
       sc2_env.AgentInterfaceFormat(
           feature_dimensions=sc2_env.Dimensions(screen=84, minimap=64))),
      ("rgb",
       sc2_env.AgentInterfaceFormat(
           rgb_dimensions=sc2_env.Dimensions(screen=84, minimap=64))),
      ("features_and_rgb", [
          sc2_env.AgentInterfaceFormat(
              feature_dimensions=sc2_env.Dimensions(screen=84, minimap=64)),
          sc2_env.AgentInterfaceFormat(
              rgb_dimensions=sc2_env.Dimensions(screen=128, minimap=32))
      ]),
      ("passthrough_and_features", [
          sc_pb.InterfaceOptions(
              raw=True,
              score=True,
              feature_layer=sc_pb.SpatialCameraSetup(
                  resolution=common_pb.Size2DI(x=84, y=84),
                  minimap_resolution=common_pb.Size2DI(x=64, y=64),
                  width=24)),
          sc2_env.AgentInterfaceFormat(
              feature_dimensions=sc2_env.Dimensions(screen=84, minimap=64))
      ]),
  )
  def test_multi_player_env(self, agent_interface_format):
    steps = 100
    step_mul = 16
    players = 2
    if not isinstance(agent_interface_format, list):
      agent_interface_format = [agent_interface_format] * players
    with sc2_env.SC2Env(
        map_name="Simple64",
        players=[sc2_env.Agent(sc2_env.Race.random, "random"),
                 sc2_env.Agent(sc2_env.Race.random, "random")],
        step_mul=step_mul,
        game_steps_per_episode=steps * step_mul // 2,
        agent_interface_format=agent_interface_format) as env:
      agents = [
          random_agent.RandomAgent() if isinstance(
              aif, sc2_env.AgentInterfaceFormat) else no_op_agent.NoOpAgent()
          for aif in agent_interface_format
      ]
      run_loop.run_loop(agents, env, steps)


if __name__ == "__main__":
  absltest.main()
