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
"""Test that some of the maps work."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import os
import random

from future.builtins import range  # pylint: disable=redefined-builtin

from pysc2 import maps
from pysc2 import run_configs
from pysc2.tests import utils

from pysc2.lib import basetest
from s2clientprotocol import sc2api_pb2 as sc_pb


class MapsTest(utils.TestCase):

  def test_list_all_maps(self):
    """Make sure all maps can be read."""
    all_maps = maps.get_maps()
    run_config = run_configs.get()
    for _, map_class in sorted(all_maps.items()):
      map_inst = map_class()
      logging.info("map: %s", map_inst.name)
      self.assertTrue(run_config.map_data(map_inst.path),
                      msg="Failed on %s" % map_inst)

  def test_load_random_map(self):
    """Test loading a few random maps."""
    all_maps = maps.get_maps()
    run_config = run_configs.get()

    with run_config.start() as controller:
      # Test only a few random maps when run locally to minimize time.
      count = 5
      map_sample = random.sample(all_maps.items(), min(count, len(all_maps)))
      for _, map_class in sorted(map_sample):
        m = map_class()
        logging.info("Loading map: %s", m.name)
        create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(
            map_path=m.path, map_data=run_config.map_data(m.path)))
        create.player_setup.add(type=sc_pb.Participant)
        create.player_setup.add(type=sc_pb.Computer, race=sc_pb.Random,
                                difficulty=sc_pb.VeryEasy)
        join = sc_pb.RequestJoinGame(race=sc_pb.Random,
                                     options=sc_pb.InterfaceOptions(raw=True))

        controller.create_game(create)
        controller.join_game(join)

        # Verify it has the right mods and isn't running into licensing issues.
        info = controller.game_info()
        logging.info("Mods for %s: %s", m.name, info.mod_names)
        self.assertIn("Mods/Void.SC2Mod", info.mod_names)
        self.assertIn("Mods/VoidMulti.SC2Mod", info.mod_names)

        # Verify it can be played without making actions.
        for _ in range(3):
          controller.step()
          controller.observe()


if __name__ == "__main__":
  basetest.main()
