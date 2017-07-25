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
"""Register/import the maps, and offer a way to create one by name.

Users of maps should import this module:
  from pysc2 import maps
and create the maps by name:
  maps.get("MapName")

If you want to create your own map, then import the map lib and subclass Map.
Your subclass will be implicitly registered as a map that can be constructed by
name, as long as it is imported somewhere.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2.maps import ladder
from pysc2.maps import lib
from pysc2.maps import melee
from pysc2.maps import mini_games


# Use `get` to create a map by name.
get = lib.get
get_maps = lib.get_maps
