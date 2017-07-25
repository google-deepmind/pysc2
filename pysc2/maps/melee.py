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
"""Define the custom map configs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from pysc2.maps import lib


class Melee(lib.Map):
  directory = "melee"
  players = 2
  game_steps_per_episode = 16 * 60 * 30  # 30 minute limit.


class TestEmpty(Melee):
  directory = "test"
  filename = "TestEmpty"


melee_maps = [
    "Simple64",
    "Simple96",
    "Simple128",
]

for name in melee_maps:
  globals()[name] = type(name, (Melee,), dict(filename=name))
