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
"""Generate the unit definitions for units.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections

from absl import app
from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import static_data

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


def get_data():
  """Get the game's static data from an actual game."""
  run_config = run_configs.get()

  with run_config.start(want_rgb=False) as controller:
    m = maps.get("Sequencer")  # Arbitrary ladder map.
    create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(
        map_path=m.path, map_data=m.data(run_config)))
    create.player_setup.add(type=sc_pb.Participant)
    create.player_setup.add(type=sc_pb.Computer, race=sc_common.Random,
                            difficulty=sc_pb.VeryEasy)
    join = sc_pb.RequestJoinGame(race=sc_common.Random,
                                 options=sc_pb.InterfaceOptions(raw=True))

    controller.create_game(create)
    controller.join_game(join)
    return controller.data_raw()


def generate_py_units(data):
  """Generate the list of units in units.py."""
  units = collections.defaultdict(list)
  for unit in sorted(data.units, key=lambda a: a.name):
    if unit.unit_id in static_data.UNIT_TYPES:
      units[unit.race].append(unit)

  def print_race(name, race):
    print("class %s(enum.IntEnum):" % name)
    print('  """%s units."""' % name)
    for unit in units[race]:
      print("  %s = %s" % (unit.name, unit.unit_id))
    print("\n")

  print_race("Neutral", sc_common.NoRace)
  print_race("Protoss", sc_common.Protoss)
  print_race("Terran", sc_common.Terran)
  print_race("Zerg", sc_common.Zerg)


def main(unused_argv):
  data = get_data()
  print("-" * 60)

  generate_py_units(data)


if __name__ == "__main__":
  app.run(main)
