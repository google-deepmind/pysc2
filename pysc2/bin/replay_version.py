#!/usr/bin/python
# Copyright 2022 DeepMind Technologies Ltd. All Rights Reserved.
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
"""Generate version information from replays."""

import os

from absl import app

from pysc2 import run_configs
from pysc2.lib import replay


def main(argv):
  if len(argv) <= 1:
    raise app.UsageError(
        "Please give one or more replay files/directories to scan as argv.")

  run_config = run_configs.get()

  # Use a set over the full version struct to catch cases where Blizzard failed
  # to update the version field properly (eg 5.0.0).
  versions = set()

  def replay_version(replay_path):
    """Query a replay for information."""
    if replay_path.lower().endswith("sc2replay"):
      data = run_config.replay_data(replay_path)
      try:
        version = replay.get_replay_version(data)
      except (ValueError, KeyError):
        pass  # Either corrupt or just old.
      except Exception as e:  # pylint: disable=broad-except
        print("Invalid replay:", replay_path, e)
      else:
        versions.add(version)

  try:
    for path in argv[1:]:
      if os.path.isdir(path):
        for root, _, files in os.walk(path):
          for file in files:
            replay_version(os.path.join(root, file))
      else:
        replay_version(path)
  except KeyboardInterrupt:
    pass

  for version in sorted(versions):
    print(version)


if __name__ == "__main__":
  app.run(main)
