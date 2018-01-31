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

_PLAYER_SELF = features.PlayerRelative.SELF
_PLAYER_NEUTRAL = features.PlayerRelative.NEUTRAL  # beacon/minerals
_PLAYER_ENEMY = features.PlayerRelative.ENEMY

FUNCTIONS = actions.FUNCTIONS


class MoveToBeacon(base_agent.BaseAgent):
  """An agent specifically for solving the MoveToBeacon map."""

  def step(self, obs):
    super(MoveToBeacon, self).step(obs)
    if FUNCTIONS.Move_screen.id in obs.observation.available_actions:
      player_relative = obs.observation.feature_screen.player_relative
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
    if FUNCTIONS.Move_screen.id in obs.observation.available_actions:
      player_relative = obs.observation.feature_screen.player_relative
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
  """An agent for solving the CollectMineralShards map with feature units.

  Controls the two marines independently:
  - select marine
  - move to nearest mineral shard that wasn't the previous target
  - swap marine and repeat
  """

  def setup(self, obs_spec, action_spec):
    super(CollectMineralShardsFeatureUnits, self).setup(obs_spec, action_spec)
    if "feature_units" not in obs_spec:
      raise Exception("This agent requires the feature_units observation.")

  def reset(self):
    super(CollectMineralShardsFeatureUnits, self).reset()
    self._current_marine = 0
    self._previous_mineral_xy = None

  def step(self, obs):
    super(CollectMineralShardsFeatureUnits, self).step(obs)
    marines = [unit for unit in obs.observation.feature_units
               if unit.alliance == _PLAYER_SELF]
    if not marines:
      return FUNCTIONS.no_op()
    marine_unit = marines[self._current_marine]
    marine_xy = [marine_unit.x, marine_unit.y]

    if not marine_unit.is_selected:
      # Nothing selected or the wrong marine is selected.
      return FUNCTIONS.select_point("select", marine_xy)

    if FUNCTIONS.Move_screen.id in obs.observation.available_actions:
      # Find and move to the nearest mineral.
      minerals = [unit for unit in obs.observation.feature_units
                  if unit.alliance == _PLAYER_NEUTRAL]
      closest_mineral_xy, min_dist = None, numpy.inf
      for mineral in minerals:
        mineral_xy = [mineral.x, mineral.y]
        if mineral_xy != self._previous_mineral_xy:
          dist = numpy.linalg.norm(
              numpy.array(marine_xy) - numpy.array(mineral_xy))
          if dist < min_dist:
            closest_mineral_xy, min_dist = mineral_xy, dist
      if closest_mineral_xy:
        # Swap to the other marine.
        self._current_marine = 1 - self._current_marine
        self._previous_mineral_xy = closest_mineral_xy
        return FUNCTIONS.Move_screen("now", closest_mineral_xy)

    return FUNCTIONS.no_op()


class DefeatRoaches(base_agent.BaseAgent):
  """An agent specifically for solving the DefeatRoaches map."""

  def step(self, obs):
    super(DefeatRoaches, self).step(obs)
    if FUNCTIONS.Attack_screen.id in obs.observation.available_actions:
      player_relative = obs.observation.feature_screen.player_relative
      roach_y, roach_x = (player_relative == _PLAYER_ENEMY).nonzero()
      if not roach_y.any():
        return FUNCTIONS.no_op()
      index = numpy.argmax(roach_y)
      target = [roach_x[index], roach_y[index]]
      return FUNCTIONS.Attack_screen("now", target)
    elif FUNCTIONS.select_army.id in obs.observation.available_actions:
      return FUNCTIONS.select_army("select")
    else:
      return FUNCTIONS.no_op()
