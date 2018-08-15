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
"""Expose static data in a more useful form than the raw protos."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import six


class StaticData(object):
  """Expose static data in a more useful form than the raw protos."""

  def __init__(self, data):
    """Takes data from RequestData."""
    self._units = {u.unit_id: u.name for u in data.units}
    self._unit_stats = {u.unit_id: u for u in data.units}
    self._abilities = {a.ability_id: a for a in data.abilities}
    self._general_abilities = {a.remaps_to_ability_id
                               for a in data.abilities
                               if a.remaps_to_ability_id}

    for a in six.itervalues(self._abilities):
      a.hotkey = a.hotkey.lower()

  @property
  def abilities(self):
    return self._abilities

  @property
  def units(self):
    return self._units

  @property
  def unit_stats(self):
    return self._unit_stats

  @property
  def general_abilities(self):
    return self._general_abilities


# List of known unit types. It is taken from:
# https://github.com/Blizzard/s2client-api/blob/master/include/sc2api/sc2_typeenums.h
UNIT_TYPES = [
    4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,
    24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
    43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61,
    62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
    81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99,
    100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114,
    115, 116, 117, 118, 119, 120, 125, 126, 127, 128, 129, 130, 131, 132, 133,
    134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 149,
    150, 151, 268, 289, 311, 322, 324, 330, 335, 341, 342, 343, 344, 365, 371,
    373, 376, 377, 472, 473, 474, 483, 484, 485, 486, 487, 488, 489, 490, 493,
    494, 495, 496, 498, 499, 500, 501, 502, 503, 504, 517, 518, 559, 560, 561,
    562, 563, 564, 588, 589, 590, 591, 608, 630, 638, 639, 640, 641, 643, 661,
    663, 664, 665, 666, 687, 688, 689, 690, 691, 692, 693, 694, 732, 733, 734,
    796, 797, 801, 824, 830, 880, 881, 884, 885, 886, 887, 892, 893, 894, 1904,
    1908, 1910, 1911, 1912, 1913,
]
