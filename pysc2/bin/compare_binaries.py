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

import collections
import pprint
import re
import sys

from absl import app
from absl import flags
import deepdiff
from pysc2 import run_configs
from pysc2.lib import replay
from pysc2.lib import stopwatch

from google.protobuf import json_format
from s2clientprotocol import sc2api_pb2 as sc_pb


FLAGS = flags.FLAGS

flags.DEFINE_bool("diff", False, "Whether to diff the observations.")
flags.DEFINE_bool("truncate", False, "Whether to truncate the diffs.")

flags.DEFINE_integer("step_mul", 8, "Game steps per observation.")
flags.DEFINE_integer("count", 100000, "How many observations to run.")
flags.DEFINE_string("replay", None, "Name of a replay to show.")


def truncate(obj):
  if isinstance(obj, str):
    return obj[:47] + "..." if len(obj) > 50 else obj
  if isinstance(obj, dict):
    return {k: truncate(v) for k, v in obj.items()}
  if isinstance(obj, list):
    return [truncate(v) for v in obj]
  return obj


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
  timers = [stopwatch.StopWatch() for _ in versions]

  procs = []
  for v, t in zip(versions, timers):
    with t("launch"):
      procs.append(run_configs.get(version=v).start(want_rgb=False))
  controllers = [p.controller for p in procs]

  diff_counts = [0] * len(versions)
  diff_paths = collections.Counter()

  try:
    print("-" * 80)
    print(controllers[0].replay_info(replay_data))
    print("-" * 80)

    for controller, t in zip(controllers, timers):
      with t("start_replay"):
        controller.start_replay(start_replay)

    for _ in range(FLAGS.count):
      for controller, t in zip(controllers, timers):
        with t("step"):
          controller.step(FLAGS.step_mul)

      obs = []
      for controller, t in zip(controllers, timers):
        with t("observe"):
          obs.append(controller.observe())

      if FLAGS.diff:
        obs_dict = [json_format.MessageToDict(o) for o in obs]
        diffs = {i: deepdiff.DeepDiff(obs_dict[0], o, significant_digits=3)
                 for i, o in enumerate(obs_dict[1:], 1)}
        if any(diffs.values()):
          print((" Diff on step: %s " %
                 obs[0].observation.game_loop).center(80, "-"))
          for i, diff in diffs.items():
            if diff:
              print(version_names[i])
              diff_counts[i] += 1
              if FLAGS.truncate:
                diff = truncate(diff)
              pprint.pprint(diff)
              print()
              for _, vals in diff.items():
                for k in vals.keys():
                  k = re.sub(r"\d+", "i", k)  # Merge array indices.
                  diff_paths[k] += 1

      if obs[0].player_result:
        break
  except KeyboardInterrupt:
    pass
  finally:
    for p in procs:
      p.controller.quit()
      p.close()

  if FLAGS.diff:
    print(" Diff Counts by binary ".center(80, "-"))
    for v, count in zip(versions, diff_counts):
      print(" %5d %s" % (count, v.binary))
    print()

    print(" Diff Counts by observation path ".center(80, "-"))
    for v, count in diff_paths.most_common(100):
      print(" %5d %s" % (count, v))
    print()

  print(" Timings ".center(80, "-"))
  for v, t in zip(versions, timers):
    print(v.binary)
    print(t)


if __name__ == "__main__":
  app.run(main)
