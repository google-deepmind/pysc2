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
from pysc2.lib import replay
from pysc2.lib import stopwatch

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


flags.DEFINE_integer("count", 1000, "How many observations to run.")
flags.DEFINE_integer("step_mul", 16, "How many game steps per observation.")
flags.DEFINE_string("replay", None, "Which replay to run.")
flags.DEFINE_string("map", "Catalyst", "Which map to run.")
FLAGS = flags.FLAGS


def interface_options(score=False, raw=False, features=None, rgb=None,
                      crop=True):
  """Get an InterfaceOptions for the config."""
  interface = sc_pb.InterfaceOptions()
  interface.score = score
  interface.raw = raw
  if features:
    if isinstance(features, int):
      screen, minimap = features, features
    else:
      screen, minimap = features
    interface.feature_layer.width = 24
    interface.feature_layer.resolution.x = screen
    interface.feature_layer.resolution.y = screen
    interface.feature_layer.minimap_resolution.x = minimap
    interface.feature_layer.minimap_resolution.y = minimap
    interface.feature_layer.crop_to_playable_area = crop
  if rgb:
    if isinstance(rgb, int):
      screen, minimap = rgb, rgb
    else:
      screen, minimap = rgb
    interface.render.resolution.x = screen
    interface.render.resolution.y = screen
    interface.render.minimap_resolution.x = minimap
    interface.render.minimap_resolution.y = minimap
  return interface


configs = [
    ("raw", interface_options(raw=True)),
    ("raw-feat-48", interface_options(raw=True, features=48)),
    ("raw-feat-128", interface_options(raw=True, features=128)),
    ("raw-feat-128-48", interface_options(raw=True, features=(128, 48))),
    ("feat-32", interface_options(features=32)),
    ("feat-48", interface_options(features=48)),
    ("feat-72-no-crop", interface_options(features=72, crop=False)),
    ("feat-72", interface_options(features=72)),
    ("feat-96", interface_options(features=96)),
    ("feat-128", interface_options(features=128)),
    ("rgb-64", interface_options(rgb=64)),
    ("rgb-128", interface_options(rgb=128)),
]


def main(unused_argv):
  stopwatch.sw.enable()

  results = []
  try:
    for config, interface in configs:
      print((" Starting: %s " % config).center(60, "-"))
      timeline = []

      run_config = run_configs.get()

      if FLAGS.replay:
        replay_data = run_config.replay_data(FLAGS.replay)
        start_replay = sc_pb.RequestStartReplay(
            replay_data=replay_data, options=interface, disable_fog=False,
            observed_player_id=2)
        version = replay.get_replay_version(replay_data)
        run_config = run_configs.get(version=version)  # Replace the run config.
      else:
        map_inst = maps.get(FLAGS.map)
        create = sc_pb.RequestCreateGame(
            realtime=False, disable_fog=False, random_seed=1,
            local_map=sc_pb.LocalMap(map_path=map_inst.path,
                                     map_data=map_inst.data(run_config)))
        create.player_setup.add(type=sc_pb.Participant)
        create.player_setup.add(type=sc_pb.Computer, race=sc_common.Terran,
                                difficulty=sc_pb.VeryEasy)
        join = sc_pb.RequestJoinGame(options=interface, race=sc_common.Protoss)

      with run_config.start(
          want_rgb=interface.HasField("render")) as controller:

        if FLAGS.replay:
          info = controller.replay_info(replay_data)
          print(" Replay info ".center(60, "-"))
          print(info)
          print("-" * 60)
          if info.local_map_path:
            start_replay.map_data = run_config.map_data(info.local_map_path)
          controller.start_replay(start_replay)
        else:
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

  print(stopwatch.sw)


if __name__ == "__main__":
  app.run(main)
