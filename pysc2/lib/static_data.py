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
  def general_abilities(self):
    return self._general_abilities
