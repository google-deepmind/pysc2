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
"""Verify that the game renders rgb pixels."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest
from future.builtins import range  # pylint: disable=redefined-builtin

import numpy as np

from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import features
from pysc2.tests import utils

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


class TestRender(utils.TestCase):

  def test_render(self):
    interface = sc_pb.InterfaceOptions()
    interface.raw = True
    interface.score = True
    interface.feature_layer.width = 24
    interface.feature_layer.resolution.x = 84
    interface.feature_layer.resolution.y = 84
    interface.feature_layer.minimap_resolution.x = 64
    interface.feature_layer.minimap_resolution.y = 64
    interface.render.resolution.x = 256
    interface.render.resolution.y = 256
    interface.render.minimap_resolution.x = 128
    interface.render.minimap_resolution.y = 128

    run_config = run_configs.get()
    with run_config.start() as controller:
      map_inst = maps.get("Simple64")
      create = sc_pb.RequestCreateGame(
          realtime=False, disable_fog=False,
          local_map=sc_pb.LocalMap(map_path=map_inst.path,
                                   map_data=map_inst.data(run_config)))
      create.player_setup.add(type=sc_pb.Participant)
      create.player_setup.add(
          type=sc_pb.Computer, race=sc_common.Random, difficulty=sc_pb.VeryEasy)
      join = sc_pb.RequestJoinGame(race=sc_common.Random, options=interface)
      controller.create_game(create)
      controller.join_game(join)

      game_info = controller.game_info()

      # Can fail if rendering is disabled.
      self.assertEqual(interface, game_info.options)

      for _ in range(50):
        controller.step(8)
        observation = controller.observe()

        obs = observation.observation
        rgb_screen = features.Feature.unpack_rgb_image(obs.render_data.map)
        rgb_minimap = features.Feature.unpack_rgb_image(obs.render_data.minimap)
        fl_screen = np.stack(f.unpack(obs) for f in features.SCREEN_FEATURES)
        fl_minimap = np.stack(f.unpack(obs) for f in features.MINIMAP_FEATURES)

        # Right shapes.
        self.assertEqual(rgb_screen.shape, (256, 256, 3))
        self.assertEqual(rgb_minimap.shape, (128, 128, 3))
        self.assertEqual(fl_screen.shape,
                         (len(features.SCREEN_FEATURES), 84, 84))
        self.assertEqual(fl_minimap.shape,
                         (len(features.MINIMAP_FEATURES), 64, 64))

        # Not all black.
        self.assertTrue(rgb_screen.any())
        self.assertTrue(rgb_minimap.any())
        self.assertTrue(fl_screen.any())
        self.assertTrue(fl_minimap.any())

        if observation.player_result:
          break

if __name__ == "__main__":
  absltest.main()
