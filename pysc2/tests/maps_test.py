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

import functools
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


def get_maps(count=None, filter_fn=None):
  """Test only a few random maps to minimize time."""
  all_maps = {k: v for k, v in maps.get_maps().items()
              if filter_fn is None or filter_fn(v)}
  count = count or len(all_maps)
  return sorted(random.sample(all_maps.keys(), min(count, len(all_maps))))


_sc2_proc = None


def cache_sc2_proc(func):
  """A decorator to replace setUp/tearDown so it can handle exceptions."""
  @functools.wraps(func)
  def _cache_sc2_proc(self, *args, **kwargs):
    global _sc2_proc
    if not _sc2_proc:
      _sc2_proc = run_configs.get().start(want_rgb=False)
    try:
      func(self, _sc2_proc.controller, *args, **kwargs)
    except:  # pylint: disable=bare-except
      _sc2_proc.close()
      _sc2_proc = None
      raise
  return _cache_sc2_proc


class MapsTest(parameterized.TestCase, utils.TestCase):

  @classmethod
  def tearDownClass(cls):
    global _sc2_proc
    if _sc2_proc:
      _sc2_proc.close()
      _sc2_proc = None
    super(MapsTest, cls).tearDownClass()

  @parameterized.parameters(get_maps())
  def test_list_all_maps(self, map_name):
    """Make sure all maps can be read."""
    run_config = run_configs.get()
    map_inst = maps.get(map_name)
    logging.info("map: %s", map_inst.name)
    self.assertIsNotNone(map_inst.players)
    self.assertGreaterEqual(map_inst.players, 1)
    self.assertLessEqual(map_inst.players, 8)
    self.assertTrue(map_inst.data(run_config), msg="Failed on %s" % map_inst)

  @cache_sc2_proc
  def test_list_battle_net_maps(self, controller):
    map_names = get_maps(None, lambda m: m.battle_net is not None)
    map_list = set(maps.get(m).battle_net for m in map_names)

    available_maps = controller.available_maps()
    available_maps = set(available_maps.battlenet_map_names)

    unavailable = map_list - available_maps
    self.assertEmpty(unavailable)

  @parameterized.parameters(get_maps(5))
  @cache_sc2_proc
  def test_load_random_map(self, controller, map_name):
    """Test loading a few random maps."""
    m = maps.get(map_name)
    run_config = run_configs.get()

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

  @parameterized.parameters(get_maps(5, lambda m: m.battle_net is not None))
  @cache_sc2_proc
  def test_load_battle_net_map(self, controller, map_name):
    """Test loading a few random battle.net maps."""
    m = maps.get(map_name)

    logging.info("Loading battle.net map: %s", m.name)
    create = sc_pb.RequestCreateGame(battlenet_map_name=m.battle_net)
    create.player_setup.add(type=sc_pb.Participant)
    create.player_setup.add(type=sc_pb.Computer, race=sc_common.Random,
                            difficulty=sc_pb.VeryEasy)
    join = sc_pb.RequestJoinGame(race=sc_common.Random,
                                 options=sc_pb.InterfaceOptions(raw=True))

    controller.create_game(create)
    controller.join_game(join)

    # Verify it can be played without making actions.
    for _ in range(3):
      controller.step()
      controller.observe()


if __name__ == "__main__":
  absltest.main()
