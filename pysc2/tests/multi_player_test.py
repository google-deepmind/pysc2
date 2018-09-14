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
"""Test that multiplayer works independently of the SC2Env."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import logging
import os

from absl.testing import absltest
from future.builtins import range  # pylint: disable=redefined-builtin

from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import point
from pysc2.lib import portspicker
from pysc2.lib import run_parallel
from pysc2.tests import utils

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


def print_stage(stage):
  logging.info((" %s " % stage).center(80, "-"))


class TestMultiplayer(utils.TestCase):

  def test_multi_player(self):
    players = 2
    run_config = run_configs.get()
    parallel = run_parallel.RunParallel()
    map_inst = maps.get("Simple64")

    screen_size_px = point.Point(64, 64)
    minimap_size_px = point.Point(32, 32)
    interface = sc_pb.InterfaceOptions()
    screen_size_px.assign_to(interface.feature_layer.resolution)
    minimap_size_px.assign_to(interface.feature_layer.minimap_resolution)

    # Reserve a whole bunch of ports for the weird multiplayer implementation.
    ports = portspicker.pick_unused_ports(players * 2)
    logging.info("Valid Ports: %s", ports)

    # Actually launch the game processes.
    print_stage("start")
    sc2_procs = [run_config.start(extra_ports=ports, want_rgb=False)
                 for _ in range(players)]
    controllers = [p.controller for p in sc2_procs]

    try:
      # Save the maps so they can access it.
      map_path = os.path.basename(map_inst.path)
      print_stage("save_map")
      parallel.run((c.save_map, map_path, map_inst.data(run_config))
                   for c in controllers)

      # Create the create request.
      create = sc_pb.RequestCreateGame(
          local_map=sc_pb.LocalMap(map_path=map_path))
      for _ in range(players):
        create.player_setup.add(type=sc_pb.Participant)

      # Create the join request.
      join = sc_pb.RequestJoinGame(race=sc_common.Random, options=interface)
      join.shared_port = 0  # unused
      join.server_ports.game_port = ports.pop(0)
      join.server_ports.base_port = ports.pop(0)
      for _ in range(players - 1):
        join.client_ports.add(game_port=ports.pop(0), base_port=ports.pop(0))

      # Play a few short games.
      for _ in range(2):  # 2 episodes
        # Create and Join
        print_stage("create")
        controllers[0].create_game(create)
        print_stage("join")
        parallel.run((c.join_game, join) for c in controllers)

        print_stage("run")
        for game_loop in range(1, 10):  # steps per episode
          # Step the game
          parallel.run(c.step for c in controllers)

          # Observe
          obs = parallel.run(c.observe for c in controllers)
          for p_id, o in enumerate(obs):
            self.assertEqual(o.observation.game_loop, game_loop)
            self.assertEqual(o.observation.player_common.player_id, p_id + 1)

          # Act
          actions = [sc_pb.Action() for _ in range(players)]
          for action in actions:
            pt = (point.Point.unit_rand() * minimap_size_px).floor()
            pt.assign_to(action.action_feature_layer.camera_move.center_minimap)
          parallel.run((c.act, a) for c, a in zip(controllers, actions))

        # Done this game.
        print_stage("leave")
        parallel.run(c.leave for c in controllers)
    finally:
      print_stage("quit")
      # Done, shut down. Don't depend on parallel since it might be broken.
      for c in controllers:
        c.quit()
      for p in sc2_procs:
        p.close()
      portspicker.return_ports(ports)


if __name__ == "__main__":
  absltest.main()
