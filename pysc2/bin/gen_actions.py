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
"""Generate the action definitions for actions.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import itertools

from absl import app
from absl import flags
import six
from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import static_data

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import data_pb2 as sc_data
from s2clientprotocol import sc2api_pb2 as sc_pb


flags.DEFINE_enum("command", None, ["csv", "python"], "What to generate.")
flags.DEFINE_string("map", "Acropolis", "Which map to use.")
flags.mark_flag_as_required("command")
FLAGS = flags.FLAGS


def get_data():
  """Retrieve static data from the game."""
  run_config = run_configs.get()

  with run_config.start(want_rgb=False) as controller:
    m = maps.get(FLAGS.map)
    create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(
        map_path=m.path, map_data=m.data(run_config)))
    create.player_setup.add(type=sc_pb.Participant)
    create.player_setup.add(type=sc_pb.Computer, race=sc_common.Random,
                            difficulty=sc_pb.VeryEasy)
    join = sc_pb.RequestJoinGame(race=sc_common.Random,
                                 options=sc_pb.InterfaceOptions(raw=True))

    controller.create_game(create)
    controller.join_game(join)
    return controller.data()


def generate_name(ability):
  return (ability.friendly_name or ability.button_name or
          ability.link_name)


def sort_key(data, ability):
  # Alphabetical, with specifics immediately after their generals.
  name = generate_name(ability)
  if ability.remaps_to_ability_id:
    general = data.abilities[ability.remaps_to_ability_id]
    name = "%s %s" % (generate_name(general), name)
  return name


def generate_csv(data):
  """Generate a CSV of the abilities for easy commenting."""
  print(",".join([
      "ability_id",
      "link_name",
      "link_index",
      "button_name",
      "hotkey",
      "friendly_name",
      "remap_to",
      "mismatch",
  ]))
  for ability in sorted(six.itervalues(data.abilities),
                        key=lambda a: sort_key(data, a)):
    ab_id = ability.ability_id
    if ab_id in skip_abilities or (ab_id not in data.general_abilities and
                                   ab_id not in used_abilities):
      continue

    general = ""
    if ab_id in data.general_abilities:
      general = "general"
    elif ability.remaps_to_ability_id:
      general = ability.remaps_to_ability_id

    mismatch = ""
    if ability.remaps_to_ability_id:
      def check_mismatch(ability, parent, attr):
        if getattr(ability, attr) != getattr(parent, attr):
          return "%s: %s" % (attr, getattr(ability, attr))

      parent = data.abilities[ability.remaps_to_ability_id]
      mismatch = "; ".join(filter(None, [
          check_mismatch(ability, parent, "available"),
          check_mismatch(ability, parent, "target"),
          check_mismatch(ability, parent, "allow_minimap"),
          check_mismatch(ability, parent, "allow_autocast"),
          check_mismatch(ability, parent, "is_building"),
          check_mismatch(ability, parent, "footprint_radius"),
          check_mismatch(ability, parent, "is_instant_placement"),
          check_mismatch(ability, parent, "cast_range"),
      ]))

    print(",".join(map(str, [
        ability.ability_id,
        ability.link_name,
        ability.link_index,
        ability.button_name,
        ability.hotkey,
        ability.friendly_name,
        general,
        mismatch,
    ])))


def generate_py_abilities(data):
  """Generate the list of functions in actions.py."""
  def print_action(func_id, name, func, ab_id, general_id):
    args = [func_id, '"%s"' % name, func, ab_id]
    if general_id:
      args.append(general_id)
    print("    Function.ability(%s)," % ", ".join(str(v) for v in args))

  func_ids = itertools.count(12)  # Leave room for the ui funcs.
  for ability in sorted(six.itervalues(data.abilities),
                        key=lambda a: sort_key(data, a)):
    ab_id = ability.ability_id
    if ab_id in skip_abilities or (ab_id not in data.general_abilities and
                                   ab_id not in used_abilities):
      continue

    name = generate_name(ability).replace(" ", "_")

    if ability.target in (sc_data.AbilityData.Target.Value("None"),
                          sc_data.AbilityData.PointOrNone):
      print_action(next(func_ids), name + "_quick", "cmd_quick", ab_id,
                   ability.remaps_to_ability_id)
    if ability.target != sc_data.AbilityData.Target.Value("None"):
      print_action(next(func_ids), name+ "_screen", "cmd_screen", ab_id,
                   ability.remaps_to_ability_id)
      if ability.allow_minimap:
        print_action(next(func_ids), name + "_minimap", "cmd_minimap", ab_id,
                     ability.remaps_to_ability_id)
    if ability.allow_autocast:
      print_action(next(func_ids), name + "_autocast", "autocast", ab_id,
                   ability.remaps_to_ability_id)


def main(unused_argv):
  data = get_data()
  print("-" * 60)

  if FLAGS.command == "csv":
    generate_csv(data)
  elif FLAGS.command == "python":
    generate_py_abilities(data)

used_abilities = set(static_data.ABILITIES)

frivolous = {6, 7}  # Dance and Cheer
# These need a slot id and so are exposed differently.
cancel_slot = {313, 1039, 305, 307, 309, 1832, 1834, 3672}
unload_unit = {410, 415, 397, 1440, 2373, 1409, 914, 3670}

skip_abilities = cancel_slot | unload_unit | frivolous


if __name__ == "__main__":
  app.run(main)
