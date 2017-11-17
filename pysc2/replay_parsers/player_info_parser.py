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
"""Example parser to collect some basic state data from replays.
   The parser collects the General player information at each step,
   along with the winning player_id of the replay"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import six
import numpy as np

from pysc2.replay_parsers import base_parser

class PlayerInfoParser(base_parser.BaseParser):
  """Example parser for collection General player information
  from replays."""
  def valid_replay(self, info, ping):
    """Make sure the replay isn't corrupt, and is worth looking at."""
    if (info.HasField("error") or
    info.base_build != ping.base_build or  # different game version
    info.game_duration_loops < 1000 or
    len(info.player_info) != 2):
    # Probably corrupt, or just not interesting.
      return False
    for p in info.player_info:
      if p.player_apm < 10 or p.player_mmr < 1000:
    # Low APM = player just standing around.
    # Low MMR = corrupt replay or player who is weak.
        return False
    return True

  def parse_step(self, obs, feat, info):
    # Obtain feature layers from current step observations
    all_features = feat.transform_obs(obs.observation)
    player_resources = all_features['player'].tolist()

    if info.player_info[0].player_result.result == 'Victory':
      winner = 1
    else:
      winner = 2
    # Return current replay step data to be appended and save to file
    return [player_resources,winner]
