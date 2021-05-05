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

  print(" units.py ".center(60, "-"))
  print_race("Neutral", sc_common.NoRace)
  print_race("Protoss", sc_common.Protoss)
  print_race("Terran", sc_common.Terran)
  print_race("Zerg", sc_common.Zerg)


def generate_py_buffs(data):
  """Generate the list of buffs in buffs.py."""
  print(" buffs.py ".center(60, "-"))
  print("class Buffs(enum.IntEnum):")
  print('  """The list of buffs, as returned from RequestData."""')
  for buff in sorted(data.buffs, key=lambda a: a.name):
    if buff.name and buff.buff_id in static_data.BUFFS:
      print("  %s = %s" % (buff.name, buff.buff_id))
  print("\n")


def generate_py_upgrades(data):
  """Generate the list of upgrades in upgrades.py."""
  print(" upgrades.py ".center(60, "-"))
  print("class Upgrades(enum.IntEnum):")
  print('  """The list of upgrades, as returned from RequestData."""')
  for upgrade in sorted(data.upgrades, key=lambda a: a.name):
    if upgrade.name and upgrade.upgrade_id in static_data.UPGRADES:
      print("  %s = %s" % (upgrade.name, upgrade.upgrade_id))
  print("\n")


def main(unused_argv):
  data = get_data()
  generate_py_units(data)
  generate_py_buffs(data)
  generate_py_upgrades(data)


if __name__ == "__main__":
  app.run(main)
