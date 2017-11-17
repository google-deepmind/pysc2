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
"""Process a test replay using the replay parsers
  A replay named "test_replay.SC2Replay" is required to exist in
  the StarCraft II install Replay directory."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import multiprocessing

from pysc2 import run_configs
from pysc2.replay_parsers import base_parser
from pysc2.replay_parsers import action_parser
from pysc2.bin import process_replays
from pysc2.tests import utils

from absl.testing import absltest as basetest


class TestBaseParser(utils.TestCase):
  
  def test_true_valid_replay(self):
    '''BaseParser returns valid_replay = True for all replays,
      test the replay info loading and assert BaseParser does
      return True for valid_replay call'''

    run_config = run_configs.get()
    processor = process_replays.ReplayProcessor(proc_id = 0,
                                                run_config = run_config,
                                                replay_queue = None,
                                                stats_queue = None,
                                                parser_cls = base_parser.BaseParser)
    with run_config.start() as controller:
      ping = controller.ping()
      replay_path = "test_replay.SC2Replay"
      replay_data = run_config.replay_data(replay_path)
      info = controller.replay_info(replay_data)
      self.assertTrue(processor.stats.parser.valid_replay(info, ping))

  def test_parse_replay(self):
    '''Run the process_replay script for the test replay file and ensure
       consistency of processing meta data'''

    run_config = run_configs.get()
    stats_queue = multiprocessing.Queue()
    processor = process_replays.ReplayProcessor(proc_id = 0,
                                                run_config = run_config,
                                                replay_queue = None,
                                                stats_queue = stats_queue,
                                                parser_cls = action_parser.ActionParser)
    with run_config.start() as controller:
      ping = controller.ping()
      replay_path = "test_replay.SC2Replay"
      processor.load_replay(replay_path, controller, ping)
      # Test replay count == 2 (one for each player persepctive in test replay)
      self.assertEqual(processor.stats.parser.replays, 2)
      # Ensure test replay is valid for ActionParser
      self.assertFalse(processor.stats.parser.invalid_replays)
      # Test parser processes more than 1 step from test replay 
      self.assertTrue(processor.stats.parser.steps > 0)  

if __name__ == "__main__":
  basetest.main()
