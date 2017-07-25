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
"""Query a replay for information."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

from pysc2 import run_configs
from pysc2.lib import flag_utils
from pysc2.lib import stopwatch

from google.apputils import app
import gflags as flags

stopwatch.sw.enabled = True

FLAGS = flags.FLAGS
flags.DEFINE_string("replay_dir", None, "Path to a directory of replays")


def main(argv):
  """Query a replay for information."""
  run_config = run_configs.get()

  replay_dir = flag_utils.positional_flag("Replay dir", FLAGS.replay_dir, argv)
  replay_dir = run_config.abs_replay_path(replay_dir)
  print("Checking: ", replay_dir)

  with run_config.start() as controller:
    bad_replays = []
    for file_path in run_config.replay_paths(replay_dir):
      file_name = os.path.basename(file_path)
      info = controller.replay_info(run_config.replay_data(file_path))
      if info.HasField("error"):
        print("failed:", file_name, info.error, info.error_details)
        bad_replays.append(file_name)
      else:
        print(u",".join(unicode(s) for s in (
            file_name,
            info.base_build,
            info.map_name,
            info.game_duration_loops,
        )))
    if bad_replays:
      print("Replays with errors:")
      print("\n".join(bad_replays))

  print(stopwatch.sw)


if __name__ == "__main__":
  app.run()
