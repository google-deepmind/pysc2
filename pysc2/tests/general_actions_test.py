#!/usr/bin/python
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Verify that the general ids in stable ids match what we expect."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest
from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import actions
from pysc2.tests import utils

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


class TestGeneralActions(utils.TestCase):
  """Verify that the general ids in stable ids match what we expect."""

  def test_general_actions(self):
    run_config = run_configs.get()
    with run_config.start(want_rgb=False) as controller:
      map_inst = maps.get("Simple64")
      create = sc_pb.RequestCreateGame(
          realtime=False, disable_fog=False,
          local_map=sc_pb.LocalMap(map_path=map_inst.path,
                                   map_data=map_inst.data(run_config)))
      create.player_setup.add(type=sc_pb.Participant)
      create.player_setup.add(
          type=sc_pb.Computer, race=sc_common.Random, difficulty=sc_pb.VeryEasy)
      join = sc_pb.RequestJoinGame(race=sc_common.Random,
                                   options=sc_pb.InterfaceOptions(raw=True))
      controller.create_game(create)
      controller.join_game(join)

      abilities = controller.data().abilities

      errors = []

      for f in actions.FUNCTIONS:
        if abilities[f.ability_id].remaps_to_ability_id != f.general_id:
          errors.append("FUNCTIONS %s/%s has abilitiy %s, general %s, expected "
                        "general %s" % (
                            f.id, f.name, f.ability_id, f.general_id,
                            abilities[f.ability_id].remaps_to_ability_id))

      for f in actions.RAW_FUNCTIONS:
        if abilities[f.ability_id].remaps_to_ability_id != f.general_id:
          errors.append(
              "RAW_FUNCTIONS %s/%s has abilitiy %s, general %s, expected "
              "general %s" % (
                  f.id, f.name, f.ability_id, f.general_id,
                  abilities[f.ability_id].remaps_to_ability_id))

      print("\n".join(errors))
      self.assertFalse(errors)


if __name__ == "__main__":
  absltest.main()
