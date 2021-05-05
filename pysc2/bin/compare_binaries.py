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

import collections
import sys

from absl import app
from absl import flags
from pysc2 import run_configs
from pysc2.lib import image_differencer
from pysc2.lib import proto_diff
from pysc2.lib import remote_controller
from pysc2.lib import replay
from pysc2.lib import stopwatch

from s2clientprotocol import sc2api_pb2 as sc_pb


FLAGS = flags.FLAGS

flags.DEFINE_bool("diff", False, "Whether to diff the observations.")
flags.DEFINE_integer("truncate", 0,
                     "Number of characters to truncate diff values to, or 0 "
                     "for no truncation.")

flags.DEFINE_integer("step_mul", 8, "Game steps per observation.")
flags.DEFINE_integer("count", 100000, "How many observations to run.")
flags.DEFINE_string("replay", None, "Name of a replay to show.")


def _clear_non_deterministic_fields(obs):
  for unit in obs.observation.raw_data.units:
    unit.ClearField("tag")
    for order in unit.orders:
      order.ClearField("target_unit_tag")

  for action in obs.actions:
    if action.HasField("action_raw"):
      if action.action_raw.HasField("unit_command"):
        action.action_raw.unit_command.ClearField("target_unit_tag")


def _is_remote(arg):
  return ":" in arg


def main(argv):
  """Compare the observations from multiple binaries."""
  if len(argv) <= 1:
    sys.exit(
        "Please specify binaries to run / to connect to. For binaries to run, "
        "specify the executable name. For remote connections, specify "
        "<hostname>:<port>. The version must match the replay.")

  targets = argv[1:]

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
      observed_player_id=1,
      realtime=False)
  version = replay.get_replay_version(replay_data)

  timers = []
  controllers = []
  procs = []
  for target in targets:
    timer = stopwatch.StopWatch()
    timers.append(timer)
    with timer("launch"):
      if _is_remote(target):
        host, port = target.split(":")
        controllers.append(remote_controller.RemoteController(host, int(port)))
      else:
        proc = run_configs.get(
            version=version._replace(binary=target)).start(want_rgb=False)
        procs.append(proc)
        controllers.append(proc.controller)

  diff_counts = [0] * len(controllers)
  diff_paths = collections.Counter()

  try:
    print("-" * 80)
    print(controllers[0].replay_info(replay_data))
    print("-" * 80)

    for controller, t in zip(controllers, timers):
      with t("start_replay"):
        controller.start_replay(start_replay)

    # Check the static data.
    static_data = []
    for controller, t in zip(controllers, timers):
      with t("data"):
        static_data.append(controller.data_raw())

    if FLAGS.diff:
      diffs = {i: proto_diff.compute_diff(static_data[0], d)
               for i, d in enumerate(static_data[1:], 1)}
      if any(diffs.values()):
        print(" Diff in static data ".center(80, "-"))
        for i, diff in diffs.items():
          if diff:
            print(targets[i])
            diff_counts[i] += 1
            print(diff.report(truncate_to=FLAGS.truncate))
            for path in diff.all_diffs():
              diff_paths[path.with_anonymous_array_indices()] += 1
      else:
        print("No diffs in static data.")

    # Run some steps, checking speed and diffing the observations.
    for _ in range(FLAGS.count):
      for controller, t in zip(controllers, timers):
        with t("step"):
          controller.step(FLAGS.step_mul)

      obs = []
      for controller, t in zip(controllers, timers):
        with t("observe"):
          obs.append(controller.observe())

      if FLAGS.diff:
        for o in obs:
          _clear_non_deterministic_fields(o)

        diffs = {i: proto_diff.compute_diff(obs[0], o)
                 for i, o in enumerate(obs[1:], 1)}
        if any(diffs.values()):
          print((" Diff on step: %s " %
                 obs[0].observation.game_loop).center(80, "-"))
          for i, diff in diffs.items():
            if diff:
              print(targets[i])
              diff_counts[i] += 1
              print(diff.report([image_differencer.image_differencer],
                                truncate_to=FLAGS.truncate))
              for path in diff.all_diffs():
                diff_paths[path.with_anonymous_array_indices()] += 1

      if obs[0].player_result:
        break
  except KeyboardInterrupt:
    pass
  finally:
    for c in controllers:
      c.quit()
      c.close()

    for p in procs:
      p.close()

  if FLAGS.diff:
    print(" Diff Counts by target ".center(80, "-"))
    for target, count in zip(targets, diff_counts):
      print(" %5d %s" % (count, target))
    print()

    print(" Diff Counts by observation path ".center(80, "-"))
    for path, count in diff_paths.most_common(100):
      print(" %5d %s" % (count, path))
    print()

  print(" Timings ".center(80, "-"))
  for v, t in zip(targets, timers):
    print(v)
    print(t)


if __name__ == "__main__":
  app.run(main)
