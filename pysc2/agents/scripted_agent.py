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
      target = [round(neutral_x.mean()), round(neutral_y.mean())]
      return FUNCTIONS.Move_screen("now", target)
    else:
      return FUNCTIONS.select_army("select")


class CollectMineralShards(base_agent.BaseAgent):
  """An agent specifically for solving the CollectMineralShards map."""

  def step(self, obs):
    super(CollectMineralShards, self).step(obs)
    if FUNCTIONS.Move_screen.id in obs.observation["available_actions"]:
      player_relative = obs.observation["feature_screen"][_PLAYER_RELATIVE]
      neutral_y, neutral_x = (player_relative == _PLAYER_NEUTRAL).nonzero()
      player_y, player_x = (player_relative == _PLAYER_SELF).nonzero()
      if not neutral_y.any() or not player_y.any():
        return FUNCTIONS.no_op()
      player = [round(player_x.mean()), round(player_y.mean())]
      closest, min_dist = None, None
      for p in zip(neutral_x, neutral_y):
        dist = numpy.linalg.norm(numpy.array(player) - numpy.array(p))
        if not min_dist or dist < min_dist:
          closest, min_dist = p, dist
      return FUNCTIONS.Move_screen("now", closest)
    else:
      return FUNCTIONS.select_army("select")


class CollectMineralShardsFeatureUnits(base_agent.BaseAgent):
  """An agent for solving the CollectMineralShards map with feature units."""
  current_player = 0
  previous_xy = None

  def step(self, obs):
    super(CollectMineralShardsFeatureUnits, self).step(obs)
    if not "feature_units" in obs.observation:
      raise Exception(
        "This agent requires that you enable feature_units. "
        "You can do this by passing --feature_units on the command line")
    player_units = [unit for unit in obs.observation["feature_units"] if
                    unit[features.FeatureUnit.ALLIANCE] == _PLAYER_SELF]
    if len(player_units) == 0:
      return FUNCTIONS.no_op()
    player_unit = player_units[self.current_player]
    player_xy = [player_unit[features.FeatureUnit.X],
                 player_unit[features.FeatureUnit.Y]]
    if not player_unit[features.FeatureUnit.IS_SELECTED]:
      return FUNCTIONS.select_point("select", player_xy)
    elif FUNCTIONS.Move_screen.id in obs.observation["available_actions"]:
      neutral_units = [unit for unit in obs.observation["feature_units"] if
                       unit[features.FeatureUnit.ALLIANCE] == _PLAYER_NEUTRAL]
      if len(neutral_units) == 0:
        return FUNCTIONS.no_op()
      closest, min_dist = None, None
      for neutral_unit in neutral_units:
        neutral_xy = [neutral_unit[features.FeatureUnit.X],
                      neutral_unit[features.FeatureUnit.Y]]
        dist = numpy.linalg.norm(numpy.array(player_xy) -
                                 numpy.array(neutral_xy))
        if not min_dist or dist < min_dist:
          if not self.previous_xy or not self.previous_xy == neutral_xy:
            closest, min_dist = neutral_xy, dist
      if not closest:
        return FUNCTIONS.no_op()
      self.current_player = 1 - self.current_player
      self.previous_xy = closest
      return FUNCTIONS.Move_screen("now", closest)
    else:
      return FUNCTIONS.no_op()


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
