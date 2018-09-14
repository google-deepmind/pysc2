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

from absl import logging
import os
import random

from absl.testing import absltest
from absl.testing import parameterized
from future.builtins import range  # pylint: disable=redefined-builtin

from pysc2 import maps
from pysc2 import run_configs
from pysc2.tests import utils

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


def get_maps(count=None):
  """Test only a few random maps to minimize time."""
  all_maps = maps.get_maps()
  count = count or len(all_maps)
  return sorted(random.sample(all_maps.keys(), min(count, len(all_maps))))


class MapsTest(parameterized.TestCase, utils.TestCase):

  @parameterized.parameters(get_maps())
  def test_list_all_maps(self, map_name):
    """Make sure all maps can be read."""
    run_config = run_configs.get()
    map_inst = maps.get(map_name)
    logging.info("map: %s", map_inst.name)
    self.assertTrue(map_inst.data(run_config), msg="Failed on %s" % map_inst)

  @parameterized.parameters(get_maps(5))
  def test_load_random_map(self, map_name):
    """Test loading a few random maps."""
    m = maps.get(map_name)
    run_config = run_configs.get()

    with run_config.start(want_rgb=False) as controller:
      logging.info("Loading map: %s", m.name)
      create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(
          map_path=m.path, map_data=m.data(run_config)))
      create.player_setup.add(type=sc_pb.Participant)
      create.player_setup.add(type=sc_pb.Computer, race=sc_common.Random,
                              difficulty=sc_pb.VeryEasy)
      join = sc_pb.RequestJoinGame(race=sc_common.Random,
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
  absltest.main()
