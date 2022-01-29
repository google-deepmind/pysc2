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
"""Test that the debug commands work."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest

from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import units

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import debug_pb2 as sc_debug
from s2clientprotocol import sc2api_pb2 as sc_pb


class DebugTest(absltest.TestCase):

  def test_multi_player(self):
    run_config = run_configs.get()
    map_inst = maps.get("Simple64")

    with run_config.start(want_rgb=False) as controller:

      create = sc_pb.RequestCreateGame(
          local_map=sc_pb.LocalMap(
              map_path=map_inst.path, map_data=map_inst.data(run_config)))
      create.player_setup.add(type=sc_pb.Participant)
      create.player_setup.add(
          type=sc_pb.Computer,
          race=sc_common.Terran,
          difficulty=sc_pb.VeryEasy)
      join = sc_pb.RequestJoinGame(race=sc_common.Terran,
                                   options=sc_pb.InterfaceOptions(raw=True))

      controller.create_game(create)
      controller.join_game(join)

      info = controller.game_info()
      map_size = info.start_raw.map_size

      controller.step(2)

      obs = controller.observe()

      def get_marines(obs):
        return {u.tag: u for u in obs.observation.raw_data.units
                if u.unit_type == units.Terran.Marine}

      self.assertEmpty(get_marines(obs))

      controller.debug(sc_debug.DebugCommand(
          create_unit=sc_debug.DebugCreateUnit(
              unit_type=units.Terran.Marine,
              owner=1,
              pos=sc_common.Point2D(x=map_size.x // 2, y=map_size.y // 2),
              quantity=5)))

      controller.step(2)

      obs = controller.observe()

      marines = get_marines(obs)
      self.assertEqual(5, len(marines))

      tags = sorted(marines.keys())

      controller.debug([
          sc_debug.DebugCommand(kill_unit=sc_debug.DebugKillUnit(
              tag=[tags[0]])),
          sc_debug.DebugCommand(unit_value=sc_debug.DebugSetUnitValue(
              unit_value=sc_debug.DebugSetUnitValue.Life, value=5,
              unit_tag=tags[1])),
      ])

      controller.step(2)

      obs = controller.observe()

      marines = get_marines(obs)
      self.assertEqual(4, len(marines))
      self.assertNotIn(tags[0], marines)
      self.assertEqual(marines[tags[1]].health, 5)


if __name__ == "__main__":
  absltest.main()
