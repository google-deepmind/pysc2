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
"""Give a crude ascii rendering of the feature_screen."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from future.builtins import range  # pylint: disable=redefined-builtin

from pysc2.lib import units


def get_printable_unit_types():
  """Generate the list of printable unit type characters."""
  types = {
      units.Protoss.Assimilator: "a",
      units.Protoss.Probe: "p",
      units.Protoss.Stalker: "s",
      units.Terran.SCV: "s",
      units.Terran.Marine: "m",
      units.Terran.SupplyDepot: "D",
      units.Terran.SupplyDepotLowered: "D",
  }

  substrings = {
      "MineralField": "$",
      "VespeneGeyser": "&",
      "Collapsible": "@",
      "Debris": "@",
      "Destructible": "@",
      "Rock": "@",
  }
  for name, unit_type in units.Neutral.__members__.items():
    for substring, char in substrings.items():
      if substring in name:
        types[unit_type] = char

  for race in (units.Protoss, units.Terran, units.Zerg):
    for name, unit_type in race.__members__.items():
      if unit_type not in types:
        types[unit_type] = name[0]

  return types

_printable_unit_types = get_printable_unit_types()

VISIBILITY = "#+."  # Fogged, seen, visible.
PLAYER_RELATIVE = ".SANE"  # self, allied, neutral, enemy.


def _summary(obs, view, width):
  s = " %s: p%s; step: %s; money: %s, %s; food: %s/%s " % (
      view, obs.player.player_id, obs.game_loop[0], obs.player.minerals,
      obs.player.vespene, obs.player.food_used, obs.player.food_cap)
  return s.center(max(len(s) + 6, width), "-")


def screen(obs):
  """Give a crude ascii rendering of feature_screen."""
  unit_type = obs.feature_screen.unit_type
  selected = obs.feature_screen.selected
  visibility = obs.feature_screen.visibility_map
  max_y, max_x = unit_type.shape
  out = _summary(obs, "screen", max_y * 2) + "\n"
  for y in range(max_y):
    started = False
    for x in range(max_x):
      s = selected[y, x]
      u = unit_type[y, x]
      v = visibility[y, x]
      if started and not s:
        out += ")"
      elif not started and s:
        out += "("
      else:
        out += " "
      if u:
        out += _printable_unit_types.get(u, str(u))
      else:
        out += VISIBILITY[v]
      started = s
    if started:
      out += ")"
    out += "\n"
  return out


def minimap(obs):
  """Give a crude ascii rendering of feature_minimap."""
  player = obs.feature_minimap.player_relative
  selected = obs.feature_minimap.selected
  visibility = obs.feature_minimap.visibility_map
  max_y, max_x = visibility.shape
  out = _summary(obs, "minimap", max_y * 2) + "\n"
  for y in range(max_y):
    started = False
    for x in range(max_x):
      s = selected[y, x]
      p = player[y, x]
      v = visibility[y, x]
      if started and not s:
        out += ")"
      elif not started and s:
        out += "("
      else:
        out += " "
      if v:
        out += PLAYER_RELATIVE[p]
      else:
        out += VISIBILITY[v]
      started = s
    if started:
      out += ")"
    out += "\n"
  return out
