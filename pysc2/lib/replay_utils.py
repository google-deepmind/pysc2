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
"""Utilities for replays."""

import io
import json
import mpyq

from pysc2.run_configs import lib as run_configs_lib


def get_replay_version(replay_data):
  replay_io = io.BytesIO()
  replay_io.write(replay_data)
  replay_io.seek(0)
  archive = mpyq.MPQArchive(replay_io).extract()
  metadata = json.loads(archive[b"replay.gamemetadata.json"].decode("utf-8"))
  return run_configs_lib.Version(
      game_version=".".join(metadata["GameVersion"].split(".")[:-1]),
      build_version=int(metadata["BaseBuild"][4:]),
      data_version=metadata.get("DataVersion"),  # Only in replays version 4.1+.
      binary=None)
