#!/usr/bin/python
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
"""Print the list of defined maps."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import app

from pysc2 import maps


def main(unused_argv):
  for _, map_class in sorted(maps.get_maps().items()):
    mp = map_class()
    if mp.path:
      print(mp, "\n")


if __name__ == "__main__":
  app.run(main)
