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

from pysc2 import run_configs
from pysc2.lib import flag_utils

from google.apputils import app
import gflags as flags

FLAGS = flags.FLAGS
flags.DEFINE_string("replay", None, "Name of a replay to use.")


def main(argv):
  """Query a replay for information."""

  run_config = run_configs.get()
  replay_path = flag_utils.positional_flag("Replay name", FLAGS.replay, argv)

  if not replay_path.lower().endswith("sc2replay"):
    print("Must be a replay.")
    return

  with run_config.start() as controller:
    print(controller.replay_info(run_config.replay_data(replay_path)))

if __name__ == "__main__":
  app.run()
