#!/usr/bin/python
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Print the list of available maps according to the game."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import app

from pysc2 import run_configs


def main(unused_argv):
  with run_configs.get().start(want_rgb=False) as controller:
    available_maps = controller.available_maps()
  print("\n")
  print("Local map paths:")
  for m in sorted(available_maps.local_map_paths):
    print(" ", m)
  print()
  print("Battle.net maps:")
  for m in sorted(available_maps.battlenet_map_names):
    print(" ", m)


if __name__ == "__main__":
  app.run(main)
