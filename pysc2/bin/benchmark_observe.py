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

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


flags.DEFINE_integer("count", 500, "How many observations to run.")
flags.DEFINE_integer("step_mul", 8, "How many game steps per observation.")
FLAGS = flags.FLAGS


def interface_options(score=False, raw=False, features=None, rgb=None):
  """Get an InterfaceOptions for the config."""
  interface = sc_pb.InterfaceOptions()
  interface.score = score
  interface.raw = raw
  if features:
    interface.feature_layer.width = 24
    interface.feature_layer.resolution.x = features
    interface.feature_layer.resolution.y = features
    interface.feature_layer.minimap_resolution.x = features
    interface.feature_layer.minimap_resolution.y = features
  if rgb:
    interface.render.resolution.x = rgb
    interface.render.resolution.y = rgb
    interface.render.minimap_resolution.x = rgb
    interface.render.minimap_resolution.y = rgb
  return interface


def main(unused_argv):
  configs = [
      ("raw", interface_options(raw=True)),
      ("raw-feat-48", interface_options(raw=True, features=48)),
      ("feat-32", interface_options(features=32)),
      ("feat-48", interface_options(features=48)),
      ("feat-72", interface_options(features=72)),
      ("feat-96", interface_options(features=96)),
      ("feat-128", interface_options(features=128)),
      ("rgb-64", interface_options(rgb=64)),
      ("rgb-128", interface_options(rgb=128)),
  ]

  results = []
  try:
    for config, interface in configs:
      timeline = []

      run_config = run_configs.get()
      with run_config.start(
          want_rgb=interface.HasField("render")) as controller:
        map_inst = maps.get("Catalyst")
        create = sc_pb.RequestCreateGame(
            realtime=False, disable_fog=False, random_seed=1,
            local_map=sc_pb.LocalMap(map_path=map_inst.path,
                                     map_data=map_inst.data(run_config)))
        create.player_setup.add(type=sc_pb.Participant)
        create.player_setup.add(type=sc_pb.Computer, race=sc_common.Terran,
                                difficulty=sc_pb.VeryEasy)
        join = sc_pb.RequestJoinGame(race=sc_common.Protoss, options=interface)
        controller.create_game(create)
        controller.join_game(join)

        for _ in range(FLAGS.count):
          controller.step(FLAGS.step_mul)
          start = time.time()
          obs = controller.observe()
          timeline.append(time.time() - start)
          if obs.player_result:
            break

      results.append((config, timeline))
  except KeyboardInterrupt:
    pass

  names, values = zip(*results)

  print("\n\nTimeline:\n")
  print(",".join(names))
  for times in zip(*values):
    print(",".join("%0.2f" % (t * 1000) for t in times))


if __name__ == "__main__":
  app.run(main)
