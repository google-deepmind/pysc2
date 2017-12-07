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
"""Generate the action definitions for units.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import itertools

import six
from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import static_data

from absl import app
from absl import flags
from s2clientprotocol import data_pb2 as sc_data
from s2clientprotocol import sc2api_pb2 as sc_pb


def get_data():
  run_config = run_configs.get()

  with run_config.start() as controller:
    m = maps.get("Sequencer")  # Arbitrary ladder map.
    create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(
        map_path=m.path, map_data=m.data(run_config)))
    create.player_setup.add(type=sc_pb.Participant)
    create.player_setup.add(type=sc_pb.Computer, race=sc_pb.Random,
                            difficulty=sc_pb.VeryEasy)
    join = sc_pb.RequestJoinGame(race=sc_pb.Random,
                                 options=sc_pb.InterfaceOptions(raw=True))

    controller.create_game(create)
    controller.join_game(join)
    return controller.data()


def generate_py_units(data):
  """Generate the list of units in units.py."""
  def print_unit(un_id, name, race):
    print("    %s_%s: %s," % (race, name, un_id))
  
  for un_id in six.iterkeys(data.units):
    if un_id in terran_units:
      print_unit(un_id, data.units[un_id], 'Terran')
      
    if un_id in zerg_units:
      print_unit(un_id, data.units[un_id], 'Zerg')
      
    if un_id in protoss_units:
      print_unit(un_id, data.units[un_id], 'Protoss')
      
    if un_id in neutral_units:
      print_unit(un_id, data.units[un_id], 'Neutral')

def main(unused_argv):
  data = get_data()
  print("-" * 60)

  generate_py_units(data)

# List of known unit types. It is taken from:
# https://github.com/Blizzard/s2client-api/blob/master/include/sc2api/sc2_typeenums.h
terran_units = {
  29, 31, 55, 21, 46, 38, 37, 57, 24, 18, 36, 692, 22, 27, 43, 40, 39, 30, 50,
  26, 53, 484, 689, 734, 51, 48, 54, 23, 268, 132, 134, 130, 56, 49, 20, 45,
  25, 33, 32, 28, 44, 42, 41, 19, 47, 52, 691, 34, 35, 498, 500, 830, 58, 11,
  6, 5
}

zerg_units = {
  9, 115, 8, 96, 289, 114, 113, 12, 15, 14, 13, 17, 16, 112, 87, 137, 138, 104,
  116, 103, 90, 88, 102, 86, 101, 107, 117, 91, 94, 150, 111, 127, 7, 100, 151,
  489, 693, 504, 502, 503, 501, 108, 142, 95, 106, 128, 893, 129, 126, 125,
  688, 687, 110, 118, 97, 89, 98, 139, 92, 99, 140, 493, 494, 892, 109, 93,
  499, 105, 119, 824
}

protoss_units = {
  311, 801, 141, 61, 79, 4, 72, 69, 76, 694, 733, 64, 63, 62, 75, 83, 85, 10,
  488, 59, 82, 495, 732, 78, 66, 84, 60, 894, 70, 71, 77, 74, 67, 496, 68, 65,
  80, 133, 81, 136, 73
}

neutral_units = {
  886, 887, 490, 588, 561, 485, 589, 562, 559, 560, 590, 591, 486, 487, 365,
  377, 376, 371, 641, 135, 324, 665, 666, 341, 483, 608, 884, 885, 796, 797,
  880, 146, 147, 344, 335, 881, 343, 473, 474, 330, 342, 149
}


if __name__ == "__main__":
  app.run(main)
