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
"""Run SC2 and connect as a human client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from pysc2 import maps
from pysc2 import run_configs
from pysc2.env import sc2_env
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
flags.DEFINE_enum("user_race", "R", sc2_env.races.keys(), "User's race.")
flags.DEFINE_enum("bot_race", "R", sc2_env.races.keys(), "AI race.")
flags.DEFINE_enum("difficulty", "1", sc2_env.difficulties.keys(),
                  "Bot's strength.")
flags.DEFINE_bool("profile", False, "Whether to turn on code profiling.")
flags.DEFINE_bool("trace", False, "Whether to trace the code execution.")
flags.DEFINE_string("resolution", "64,64", "Resolution for feature layers.")
flags.DEFINE_string("map", None, "Name of a map to use.")


def main(argv):
  """Run SC2 and connect as a human client."""
  stopwatch.sw.enabled = FLAGS.profile or FLAGS.trace
  stopwatch.sw.trace = FLAGS.trace

  run_config = run_configs.get()

  map_name = flag_utils.positional_flag("Map name", FLAGS.map, argv)
  map_inst = maps.get(map_name)

  resolution = point.Point(*(int(i) for i in FLAGS.resolution.split(",")))

  interface = sc_pb.InterfaceOptions(
      raw=True, score=True,
      feature_layer=sc_pb.SpatialCameraSetup(width=24))
  resolution.assign_to(interface.feature_layer.resolution)
  resolution.assign_to(interface.feature_layer.minimap_resolution)

  create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(
      map_path=map_inst.path, map_data=run_config.map_data(map_inst.path)))
  create.player_setup.add(type=sc_pb.Participant)
  create.player_setup.add(type=sc_pb.Computer,
                          race=sc2_env.races[FLAGS.bot_race],
                          difficulty=sc2_env.difficulties[FLAGS.difficulty])

  join = sc_pb.RequestJoinGame(race=sc2_env.races[FLAGS.user_race],
                               options=interface)

  with run_config.start() as controller:
    controller.create_game(create)
    controller.join_game(join)

    renderer = renderer_human.RendererHuman(
        fps=FLAGS.fps, step_mul=FLAGS.step_mul, render_sync=FLAGS.render_sync)
    renderer.run(run_config, controller, max_game_steps=FLAGS.max_game_steps,
                 game_steps_per_episode=map_inst.game_steps_per_episode)


if __name__ == "__main__":
  app.run()
