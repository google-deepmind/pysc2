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
"""Run SC2 and connect as a human client to watch a replay."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2 import run_configs
from pysc2.lib import flag_utils
from pysc2.lib import point
from pysc2.lib import renderer_human
from pysc2.lib import stopwatch

from google.apputils import app
import gflags as flags
from s2clientproto import sc2api_pb2 as sc_pb


FLAGS = flags.FLAGS
flags.DEFINE_integer("fps", 20, "Frames per second to run the game.")
flags.DEFINE_integer("step_mul", 1, "Game steps per agent step.")
flags.DEFINE_bool("render_sync", False, "Turn on sync rendering.")
flags.DEFINE_integer("max_game_steps", 0, "Total game steps to run.")
flags.DEFINE_bool("disable_fog", False, "Disable fog of war.")
flags.DEFINE_integer("observed_player", 1, "Which player to observe.")
flags.DEFINE_bool("profile", False, "Whether to turn on code profiling.")
flags.DEFINE_bool("trace", False, "Whether to trace the code execution.")
flags.DEFINE_string("resolution", "64,64", "Resolution for feature layers.")
flags.DEFINE_string("map_path", None, "Override the map for this replay.")
flags.DEFINE_string("replay", None, "Name of a replay to use.")


def main(argv):
  """Run SC2 and connect as a human client to watch a replay."""
  stopwatch.sw.enabled = FLAGS.profile or FLAGS.trace
  stopwatch.sw.trace = FLAGS.trace

  run_config = run_configs.get()

  replay_path = flag_utils.positional_flag("Replay name", FLAGS.replay, argv)

  if not replay_path.lower().endswith("sc2replay"):
    print("Must be a replay. Use the sc_client for maps.")
    return

  resolution = point.Point(*(int(i) for i in FLAGS.resolution.split(",")))

  interface = sc_pb.InterfaceOptions(
      raw=True, score=True,
      feature_layer=sc_pb.SpatialCameraSetup(width=24))
  resolution.assign_to(interface.feature_layer.resolution)
  resolution.assign_to(interface.feature_layer.minimap_resolution)

  replay_data = run_config.replay_data(replay_path)

  start_replay = sc_pb.RequestStartReplay(
      replay_data=replay_data,
      options=interface,
      disable_fog=FLAGS.disable_fog,
      observed_player_id=FLAGS.observed_player)

  with run_config.start() as controller:
    info = controller.replay_info(replay_data)
    print(" Replay info ".center(60, "-"))
    print(info)
    print("-" * 60)

    map_path = FLAGS.map_path or info.local_map_path
    if map_path:
      start_replay.map_data = run_config.map_data(map_path)

    controller.start_replay(start_replay)

    renderer = renderer_human.RendererHuman(
        fps=FLAGS.fps, step_mul=FLAGS.step_mul, render_sync=FLAGS.render_sync)
    renderer.run(run_config, controller, max_game_steps=FLAGS.max_game_steps)


if __name__ == "__main__":
  app.run()
