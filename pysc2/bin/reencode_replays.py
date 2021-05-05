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
"""Run through a set of replays, generating new replays from them."""

import os

from absl import app
from absl import flags
from pysc2 import run_configs
from pysc2.lib import replay

from s2clientprotocol import sc2api_pb2 as sc_pb

FLAGS = flags.FLAGS

flags.DEFINE_string("input_dir", None, "Directory of replays to modify.")
flags.DEFINE_string("output_dir", None, "Where to write them.")


def main(_):
  run_config = run_configs.get()

  replay_list = sorted(run_config.replay_paths(FLAGS.input_dir))
  print(len(replay_list), "replays found.\n")

  version = replay.get_replay_version(run_config.replay_data(replay_list[0]))
  run_config = run_configs.get(version=version)  # Replace the run config.

  with run_config.start(want_rgb=False) as controller:
    for replay_path in replay_list:
      replay_data = run_config.replay_data(replay_path)
      info = controller.replay_info(replay_data)

      print(" Starting replay: ".center(60, "-"))
      print("Path:", replay_path)
      print("Size:", len(replay_data), "bytes")
      print(" Replay info: ".center(60, "-"))
      print(info)
      print("-" * 60)

      start_replay = sc_pb.RequestStartReplay(
          replay_data=replay_data,
          options=sc_pb.InterfaceOptions(score=True),
          record_replay=True,
          observed_player_id=1)
      if info.local_map_path:
        start_replay.map_data = run_config.map_data(info.local_map_path,
                                                    len(info.player_info))
      controller.start_replay(start_replay)

      while True:
        controller.step(1000)
        obs = controller.observe()
        if obs.player_result:
          print("Stepped", obs.observation.game_loop, "game loops")
          break

      replay_data = controller.save_replay()

      replay_save_loc = os.path.join(FLAGS.output_dir,
                                     os.path.basename(replay_path))
      with open(replay_save_loc, "wb") as f:
        f.write(replay_data)

      print("Wrote replay, ", len(replay_data), " bytes to:", replay_save_loc)


if __name__ == "__main__":
  app.run(main)
