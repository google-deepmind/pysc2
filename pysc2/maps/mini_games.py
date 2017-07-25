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
"""Define the mini game map configs. These are maps made by Deepmind."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from pysc2.maps import lib


class MiniGame(lib.Map):
  directory = "mini_games"
  players = 1
  score_index = 0
  game_steps_per_episode = 0
  step_mul = 8


class TestMNEasy(MiniGame):
  directory = "test"
  filename = "mn_easy"
  score_index = None


mini_games = [
    "CombatFocus",  # 120s
    "CombatFocusNoMarinePenalty",  # 120s
    "CombatFocusRestoreMarines",  # 120s
    "CombatFocusUnselected",  # 120s
    "CombatFocusUnselectedNoMarinePenalty",  # 120s
    "CombatFocusUnselectedRestoreMarines",  # 120s
    "CombatGroup",  # 180s
    "CombatGroupUnselected",  # 180s
    "MacroEconomy",  # 180s
    "MacroEconomyRandomSpawn",  # 180s
    "MovementBeaconSparseReward",  # 120s
    "MovementBeaconSparseRewardRandomSpawn",  # 120s
    "MovementBeaconSparseRewardUnselected",  # 120s
    "MovementBeaconSparseRewardUnselectedRandomSpawn",  # 120s
    "MovementTSPunselected2marinesRandomSpawn",  # 120s
    "MovementTSPunselected2marinesRandomSpawnUniformSpread",  # 120s
]


for name in mini_games:
  globals()[name] = type(name, (MiniGame,), dict(filename=name))
