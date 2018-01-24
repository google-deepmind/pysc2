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
"""Scripted agents."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy

from pysc2.agents import base_agent
from pysc2.lib import actions
from pysc2.lib import features

_PLAYER_RELATIVE = features.SCREEN_FEATURES.player_relative.index
_PLAYER_SELF = features.PlayerRelative.SELF
_PLAYER_NEUTRAL = features.PlayerRelative.NEUTRAL  # beacon/minerals
_PLAYER_ENEMY = features.PlayerRelative.ENEMY

FUNCTIONS = actions.FUNCTIONS


class MoveToBeacon(base_agent.BaseAgent):
  """An agent specifically for solving the MoveToBeacon map."""

  def step(self, obs):
    super(MoveToBeacon, self).step(obs)
    if FUNCTIONS.Move_screen.id in obs.observation["available_actions"]:
      player_relative = obs.observation["feature_screen"][_PLAYER_RELATIVE]
      neutral_y, neutral_x = (player_relative == _PLAYER_NEUTRAL).nonzero()
      if not neutral_y.any():
        return FUNCTIONS.no_op()
      target = [int(neutral_x.mean()), int(neutral_y.mean())]
      return FUNCTIONS.Move_screen("now", target)
    else:
      return FUNCTIONS.select_army("select")


class CollectMineralShards(base_agent.BaseAgent):
  """An agent specifically for solving the CollectMineralShards map."""
  current_player = 0

  def step(self, obs):
    super(CollectMineralShards, self).step(obs)
    player_units = list(filter(lambda unit: unit[1] == _PLAYER_SELF, obs.observation['feature_units']))
    if len(player_units) == 0:
      return FUNCTIONS.no_op()
    player_unit = player_units[self.current_player]
    player_xy = [player_unit[12], player_unit[13]]
    if player_unit[17] and FUNCTIONS.Move_screen.id in obs.observation["available_actions"]:
      neutral_units = list(filter(lambda unit: unit[1] == _PLAYER_NEUTRAL, obs.observation['feature_units']))
      if len(neutral_units) == 0:
        return FUNCTIONS.no_op()
      closest, min_dist = None, None
      for neutral_unit in neutral_units:
        neutral_xy = [neutral_unit[12], neutral_unit[13]]
        dist = numpy.linalg.norm(numpy.array(player_xy) - numpy.array(neutral_xy))
        if not min_dist or dist < min_dist:
          closest, min_dist = neutral_xy, dist
      self.current_player = 1 if self.current_player == 0 else 0
      return FUNCTIONS.Move_screen("now", closest)
    else:
      return FUNCTIONS.select_point("select", player_xy)


class DefeatRoaches(base_agent.BaseAgent):
  """An agent specifically for solving the DefeatRoaches map."""

  def step(self, obs):
    super(DefeatRoaches, self).step(obs)
    if FUNCTIONS.Attack_screen.id in obs.observation["available_actions"]:
      player_relative = obs.observation["feature_screen"][_PLAYER_RELATIVE]
      roach_y, roach_x = (player_relative == _PLAYER_ENEMY).nonzero()
      if not roach_y.any():
        return FUNCTIONS.no_op()
      index = numpy.argmax(roach_y)
      target = [roach_x[index], roach_y[index]]
      return FUNCTIONS.Attack_screen("now", target)
    elif FUNCTIONS.select_army.id in obs.observation["available_actions"]:
      return FUNCTIONS.select_army("select")
    else:
      return FUNCTIONS.no_op()
