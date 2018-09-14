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
"""Test that two built in bots can be watched by an observer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest
from future.builtins import range  # pylint: disable=redefined-builtin

from pysc2 import maps
from pysc2 import run_configs
from pysc2.tests import utils

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


class TestObserver(utils.TestCase):

  def test_observer(self):
    run_config = run_configs.get()
    map_inst = maps.get("Simple64")

    with run_config.start(want_rgb=False) as controller:
      create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(
          map_path=map_inst.path, map_data=map_inst.data(run_config)))
      create.player_setup.add(
          type=sc_pb.Computer, race=sc_common.Random, difficulty=sc_pb.VeryEasy)
      create.player_setup.add(
          type=sc_pb.Computer, race=sc_common.Random, difficulty=sc_pb.VeryHard)
      create.player_setup.add(type=sc_pb.Observer)
      controller.create_game(create)

      join = sc_pb.RequestJoinGame(
          options=sc_pb.InterfaceOptions(),  # cheap observations
          observed_player_id=0)
      controller.join_game(join)

      outcome = False
      for _ in range(60 * 60):  # 60 minutes should be plenty.
        controller.step(16)
        obs = controller.observe()
        if obs.player_result:
          print("Outcome after %s steps (%0.1f game minutes):" % (
              obs.observation.game_loop, obs.observation.game_loop / (16 * 60)))
          for r in obs.player_result:
            print("Player %s: %s" % (r.player_id, sc_pb.Result.Name(r.result)))
          outcome = True
          break

      self.assertTrue(outcome)


if __name__ == "__main__":
  absltest.main()
