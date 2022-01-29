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
"""Verify that we blow up if SC2 thinks we did something wrong."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest

from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import protocol
from pysc2.lib import remote_controller
from pysc2.tests import utils

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


class TestProtocolError(utils.TestCase):
  """Verify that we blow up if SC2 thinks we did something wrong."""

  def test_error(self):
    with run_configs.get().start(want_rgb=False) as controller:
      with self.assertRaises(remote_controller.RequestError):
        controller.create_game(sc_pb.RequestCreateGame())  # Missing map, etc.

      with self.assertRaises(protocol.ProtocolError):
        controller.join_game(sc_pb.RequestJoinGame())  # No game to join.

  def test_replay_a_replay(self):
    run_config = run_configs.get()
    with run_config.start(want_rgb=False) as controller:
      map_inst = maps.get("Flat64")
      map_data = map_inst.data(run_config)
      interface = sc_pb.InterfaceOptions(raw=True)

      # Play a quick game to generate a replay.
      create = sc_pb.RequestCreateGame(
          local_map=sc_pb.LocalMap(
              map_path=map_inst.path, map_data=map_data))
      create.player_setup.add(type=sc_pb.Participant)
      create.player_setup.add(type=sc_pb.Computer, race=sc_common.Terran,
                              difficulty=sc_pb.VeryEasy)
      join = sc_pb.RequestJoinGame(race=sc_common.Terran, options=interface)

      controller.create_game(create)
      controller.join_game(join)
      controller.step(100)
      obs = controller.observe()
      replay_data = controller.save_replay()

      # Run through the replay the first time, verifying that it finishes, but
      # wasn't recording a replay.
      start_replay = sc_pb.RequestStartReplay(
          replay_data=replay_data,
          map_data=map_data,
          options=interface,
          observed_player_id=1)

      controller.start_replay(start_replay)
      controller.step(1000)
      obs2 = controller.observe()
      self.assertEqual(obs.observation.game_loop, obs2.observation.game_loop)
      with self.assertRaises(protocol.ProtocolError):
        controller.save_replay()

      # Run through the replay a second time, verifying that it finishes, and
      # *was* recording a replay.
      start_replay.record_replay = True
      controller.start_replay(start_replay)
      controller.step(1000)
      obs2 = controller.observe()
      self.assertEqual(obs.observation.game_loop, obs2.observation.game_loop)
      replay_data2 = controller.save_replay()

      # Make sure the replay isn't too small. Variance is fine but empty is not.
      self.assertGreater(len(replay_data2), len(replay_data) * 0.8)

      # Run through the replay a third time, verifying that it finishes, but
      # still wasn't recording a replay.
      start_replay.record_replay = False
      controller.start_replay(start_replay)
      controller.step(1000)
      obs3 = controller.observe()
      self.assertEqual(obs.observation.game_loop, obs3.observation.game_loop)
      with self.assertRaises(protocol.ProtocolError):
        controller.save_replay()


if __name__ == "__main__":
  absltest.main()
