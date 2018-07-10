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
"""Benchmark observation times."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time

from absl import app
from absl import flags
from future.builtins import range  # pylint: disable=redefined-builtin

from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import point_flag

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


flags.DEFINE_bool("raw", False, "Enable raw rendering")
point_flag.DEFINE_point("feature_size", "64", "Resolution for feature layers.")
point_flag.DEFINE_point("rgb_size", "64", "Resolution for rgb observations.")
FLAGS = flags.FLAGS


def main(unused_argv):
  interface = sc_pb.InterfaceOptions()
  interface.score = True
  interface.raw = FLAGS.raw
  if FLAGS.feature_size:
    interface.feature_layer.width = 24
    FLAGS.feature_size.assign_to(interface.feature_layer.resolution)
    FLAGS.feature_size.assign_to(interface.feature_layer.minimap_resolution)
  if FLAGS.rgb_size:
    FLAGS.rgb_size.assign_to(interface.render.resolution)
    FLAGS.rgb_size.assign_to(interface.render.minimap_resolution)

  timeline = []

  try:
    run_config = run_configs.get()
    with run_config.start() as controller:
      map_inst = maps.get("Simple64")
      create = sc_pb.RequestCreateGame(
          realtime=False, disable_fog=False, random_seed=1,
          local_map=sc_pb.LocalMap(map_path=map_inst.path,
                                   map_data=map_inst.data(run_config)))
      create.player_setup.add(type=sc_pb.Participant)
      create.player_setup.add(type=sc_pb.Computer, race=sc_common.Terran,
                              difficulty=sc_pb.VeryEasy)
      join = sc_pb.RequestJoinGame(race=sc_common.Random, options=interface)
      controller.create_game(create)
      controller.join_game(join)

      for _ in range(500):
        controller.step()
        start = time.time()
        obs = controller.observe()
        timeline.append(time.time() - start)
        if obs.player_result:
          break
  except KeyboardInterrupt:
    pass

  print("Timeline:")
  for t in timeline:
    print(t * 1000)


if __name__ == "__main__":
  app.run(main)
