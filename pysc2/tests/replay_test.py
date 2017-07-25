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
"""Test some replays can load."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import unittest


from pysc2 import run_configs
from pysc2.tests import utils

from s2clientproto import sc2api_pb2 as sc_pb


class ReplaysTest(utils.TestCase):

  def test_load_replays(self):
    """Test loading a few replays."""

    run_config = run_configs.get()

    with run_config.start() as controller:
      for replay_path in run_config.replay_paths("guitar_test"):
        logging.info("Loading replay: %s", replay_path)

        replay_data = run_config.replay_data(replay_path)

        start_replay = sc_pb.RequestStartReplay(
            replay_data=replay_data,
            options=sc_pb.InterfaceOptions(raw=True),
            observed_player_id=1)

        info = controller.replay_info(replay_data)
        logging.info(" Replay info ".center(60, "-"))
        logging.info(info)
        logging.info("-" * 60)

        if info.local_map_path:
          start_replay.map_data = run_config.map_data(info.local_map_path)

        controller.start_replay(start_replay)
        for _ in xrange(3):
          controller.step()
          controller.observe()


if __name__ == "__main__":
  unittest.main()
