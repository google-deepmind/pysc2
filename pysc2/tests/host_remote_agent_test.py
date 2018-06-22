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
"""Test host_remote_agent.py."""

from absl.testing import absltest

from pysc2.env import host_remote_agent
from pysc2.lib import remote_controller
from pysc2.lib import run_parallel
from pysc2.tests import utils

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


NUM_MATCHES = 2
STEPS = 100


class TestHostRemoteAgent(utils.TestCase):

  def testVsBot(self):
    bot_first = True
    for _ in range(NUM_MATCHES):
      with host_remote_agent.VsBot() as game:
        game.create_game(
            map_name="Simple64",
            bot_difficulty=sc_pb.VeryHard,
            bot_first=bot_first)
        controller = remote_controller.RemoteController(
            host=game.host,
            port=game.host_port)

        join = sc_pb.RequestJoinGame(options=sc_pb.InterfaceOptions(raw=True))
        join.race = sc_common.Random
        controller.join_game(join)
        for _ in range(STEPS):
          controller.step()
          response_observation = controller.observe()
          if response_observation.player_result:
            break

        controller.leave()
        controller.close()
        bot_first = not bot_first

  def testVsAgent(self):
    parallel = run_parallel.RunParallel()
    for _ in range(NUM_MATCHES):
      with host_remote_agent.VsAgent() as game:
        game.create_game("Simple64")
        controllers = [
            remote_controller.RemoteController(
                host=host,
                port=host_port)
            for host, host_port in zip(game.hosts, game.host_ports)]

        join = sc_pb.RequestJoinGame(options=sc_pb.InterfaceOptions(raw=True))
        join.race = sc_common.Random
        join.shared_port = 0
        join.server_ports.game_port = game.lan_ports[0]
        join.server_ports.base_port = game.lan_ports[1]
        join.client_ports.add(
            game_port=game.lan_ports[2],
            base_port=game.lan_ports[3])

        parallel.run((c.join_game, join) for c in controllers)
        for _ in range(STEPS):
          parallel.run(c.step for c in controllers)
          response_observations = [c.observe() for c in controllers]

          if response_observations[0].player_result:
            break

        parallel.run(c.leave for c in controllers)
        parallel.run(c.close for c in controllers)


if __name__ == "__main__":
  absltest.main()
