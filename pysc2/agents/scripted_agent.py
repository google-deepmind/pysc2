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
"""Scripted agents for a few maps."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from pysc2.agents import base_agent
from pysc2.lib import actions

_IMMEDIATE = [0]


class MNEasyWin(base_agent.BaseAgent):
  """An agent specifically for solving the mn_easy map."""
  MOVE_TOWARDS = 3  # beacon

  def step(self, obs):
    super(MNEasyWin, self).step(obs)
    player_relative = obs.observation["screen"][5]
    target_rows, target_cols = (player_relative == self.MOVE_TOWARDS).nonzero()
    target_center = [int(target_cols.mean()), int(target_rows.mean())]
    return actions.FunctionCall(
        function_id=actions.FUNCTIONS.Move_screen.id,
        arguments=[_IMMEDIATE, target_center])


class MNEasyLose(MNEasyWin):
  """An agent specifically for losing the mn_easy map."""
  MOVE_TOWARDS = 4  # enemy
