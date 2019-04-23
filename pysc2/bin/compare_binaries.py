#!/usr/bin/python
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Compare the observations from multiple binaries."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys

from absl import app
from absl import flags
import deepdiff
from pysc2 import run_configs
from pysc2.lib import replay

from google.protobuf import json_format
from s2clientprotocol import sc2api_pb2 as sc_pb


FLAGS = flags.FLAGS
flags.DEFINE_string("replay", None, "Name of a replay to show.")


def main(argv):
  """Compare the observations from multiple binaries."""
  if not argv:
    sys.exit(
        "Please specify binaries to run. The version must match the replay.")

  version_names = argv[1:]

  interface = sc_pb.InterfaceOptions()
  interface.raw = True
  interface.raw_affects_selection = True
  interface.raw_crop_to_playable_area = True
  interface.score = True
  interface.show_cloaked = True
  interface.show_placeholders = True
  interface.feature_layer.width = 24
  interface.feature_layer.resolution.x = 48
  interface.feature_layer.resolution.y = 48
  interface.feature_layer.minimap_resolution.x = 48
  interface.feature_layer.minimap_resolution.y = 48
  interface.feature_layer.crop_to_playable_area = True
  interface.feature_layer.allow_cheating_layers = True

  run_config = run_configs.get()
  replay_data = run_config.replay_data(FLAGS.replay)
  start_replay = sc_pb.RequestStartReplay(
      replay_data=replay_data,
      options=interface,
      observed_player_id=1)
  version = replay.get_replay_version(replay_data)

  versions = [version._replace(binary=b) for b in version_names]
  procs = [run_configs.get(version=v).start(want_rgb=False) for v in versions]
  controllers = [p.controller for p in procs]

  try:
    for controller in controllers:
      controller.start_replay(start_replay)

    while True:
      for controller in controllers:
        controller.step()

      obs = [controller.observe() for controller in controllers]
      obs_dict = [json_format.MessageToDict(o) for o in obs]
      for i, o in enumerate(obs_dict):
        diff = deepdiff.DeepDiff(obs_dict[0], o)
        if diff:
          print("%s: %s" % (i, diff))

      if obs[0].player_result:
        break
  finally:
    for p in procs:
      p.controller.quit()
      p.close()


if __name__ == "__main__":
  app.run(main)
