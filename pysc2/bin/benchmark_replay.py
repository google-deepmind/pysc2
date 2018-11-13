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

from absl import app
from absl import flags
from pysc2 import run_configs
from pysc2.lib import actions
from pysc2.lib import features
from pysc2.lib import point_flag
from pysc2.lib import replay
from pysc2.lib import stopwatch

from s2clientprotocol import sc2api_pb2 as sc_pb

FLAGS = flags.FLAGS
flags.DEFINE_integer("step_mul", 8, "Game steps per observation.")
point_flag.DEFINE_point("feature_screen_size", "64",
                        "Resolution for screen feature layers.")
point_flag.DEFINE_point("feature_minimap_size", "64",
                        "Resolution for minimap feature layers.")
point_flag.DEFINE_point("rgb_screen_size", None,
                        "Resolution for rendered screen.")
point_flag.DEFINE_point("rgb_minimap_size", None,
                        "Resolution for rendered minimap.")
flags.DEFINE_bool("use_feature_units", True,
                  "Whether to include feature units.")
flags.DEFINE_bool("use_raw_units", True,
                  "Whether to include raw units.")
flags.DEFINE_string("replay", None, "Name of a replay to show.")
flags.DEFINE_string("map_path", None, "Override the map for this replay.")
flags.mark_flag_as_required("replay")


def main(argv):
  if len(argv) > 1:
    raise app.UsageError("Too many command-line arguments.")

  stopwatch.sw.enable()

  interface = sc_pb.InterfaceOptions()
  interface.raw = FLAGS.use_feature_units or FLAGS.use_raw_units
  interface.score = True
  interface.feature_layer.width = 24
  if FLAGS.feature_screen_size and FLAGS.feature_minimap_size:
    FLAGS.feature_screen_size.assign_to(interface.feature_layer.resolution)
    FLAGS.feature_minimap_size.assign_to(
        interface.feature_layer.minimap_resolution)
  if FLAGS.rgb_screen_size and FLAGS.rgb_minimap_size:
    FLAGS.rgb_screen_size.assign_to(interface.render.resolution)
    FLAGS.rgb_minimap_size.assign_to(interface.render.minimap_resolution)

  run_config = run_configs.get()
  replay_data = run_config.replay_data(FLAGS.replay)
  start_replay = sc_pb.RequestStartReplay(
      replay_data=replay_data,
      options=interface,
      observed_player_id=1)
  version = replay.get_replay_version(replay_data)
  run_config = run_configs.get(version=version)  # Replace the run config.

  try:
    with run_config.start(
        want_rgb=interface.HasField("render")) as controller:
      info = controller.replay_info(replay_data)
      print(" Replay info ".center(60, "-"))
      print(info)
      print("-" * 60)
      map_path = FLAGS.map_path or info.local_map_path
      if map_path:
        start_replay.map_data = run_config.map_data(map_path)
      controller.start_replay(start_replay)

      feats = features.features_from_game_info(
          game_info=controller.game_info(),
          use_feature_units=FLAGS.use_feature_units,
          use_raw_units=FLAGS.use_raw_units,
          use_unit_counts=interface.raw,
          use_camera_position=False,
          action_space=actions.ActionSpace.FEATURES)

      while True:
        controller.step(FLAGS.step_mul)
        obs = controller.observe()
        feats.transform_obs(obs)
        if obs.player_result:
          break
  except KeyboardInterrupt:
    pass

  print(stopwatch.sw)


if __name__ == "__main__":
  app.run(main)
