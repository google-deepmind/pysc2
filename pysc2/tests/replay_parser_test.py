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
"""Process a test replay using the ActionParser replay parser"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2 import run_configs
from pysc2.replay_parsers import action_parser
from pysc2.bin import process_replays
from pysc2.tests import utils

from absl.testing import absltest as basetest


class TestBaseParser(utils.TestCase):

  def __init__(self):
    run_config = run_configs.get()
    self.processor = process_replays.ReplayProcessor(proc_id = 0,
                                                     run_config = run_config,
                                                     replay_queue = None,
                                                     stats_queue = None,
                                                     parser_cls = action_parser)

  #def boolean_valid_replay(self):



if __name__ == "__main__":
  basetest.main()
