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
"""Query one or more replays for information."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

from absl import app
from future.builtins import str  # pylint: disable=redefined-builtin

from pysc2 import run_configs
from pysc2.lib import remote_controller

from pysc2.lib import gfile
from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


def _replay_index(replay_dir):
  """Output information for a directory of replays."""
  run_config = run_configs.get()
  replay_dir = run_config.abs_replay_path(replay_dir)
  print("Checking: ", replay_dir)

  with run_config.start(want_rgb=False) as controller:
    print("-" * 60)
    print(",".join((
        "filename",
        "build",
        "map_name",
        "game_duration_loops",
        "players",
        "P1-outcome",
        "P1-race",
        "P1-apm",
        "P2-race",
        "P2-apm",
    )))

    try:
      bad_replays = []
      for file_path in run_config.replay_paths(replay_dir):
        file_name = os.path.basename(file_path)
        try:
          info = controller.replay_info(run_config.replay_data(file_path))
        except remote_controller.RequestError as e:
          bad_replays.append("%s: %s" % (file_name, e))
          continue
        if info.HasField("error"):
          print("failed:", file_name, info.error, info.error_details)
          bad_replays.append(file_name)
        else:
          out = [
              file_name,
              info.base_build,
              info.map_name,
              info.game_duration_loops,
              len(info.player_info),
              sc_pb.Result.Name(info.player_info[0].player_result.result),
              sc_common.Race.Name(info.player_info[0].player_info.race_actual),
              info.player_info[0].player_apm,
          ]
          if len(info.player_info) >= 2:
            out += [
                sc_common.Race.Name(
                    info.player_info[1].player_info.race_actual),
                info.player_info[1].player_apm,
            ]
          print(u",".join(str(s) for s in out))
    except KeyboardInterrupt:
      pass
    finally:
      if bad_replays:
        print("\n")
        print("Replays with errors:")
        print("\n".join(bad_replays))


def _replay_info(replay_path):
  """Query a replay for information."""
  if not replay_path.lower().endswith("sc2replay"):
    print("Must be a replay.")
    return

  run_config = run_configs.get()
  with run_config.start(want_rgb=False) as controller:
    info = controller.replay_info(run_config.replay_data(replay_path))
  print("-" * 60)
  print(info)


def main(argv):
  if not argv:
    raise ValueError("No replay directory or path specified.")
  if len(argv) > 2:
    raise ValueError("Too many arguments provided.")
  path = argv[1]

  try:
    if gfile.IsDirectory(path):
      return _replay_index(path)
    else:
      return _replay_info(path)
  except KeyboardInterrupt:
    pass


def entry_point():  # Needed so the setup.py scripts work.
  app.run(main)


if __name__ == "__main__":
  app.run(main)
