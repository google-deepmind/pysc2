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

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import data_pb2 as sc_data
from s2clientprotocol import sc2api_pb2 as sc_pb


flags.DEFINE_enum("command", None, ["csv", "python"], "What to generate.")
flags.mark_flag_as_required("command")
FLAGS = flags.FLAGS


def get_data():
  """Retrieve static data from the game."""
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

    print(",".join(str(s) for s in [
        ability.ability_id,
        ability.link_name,
        ability.link_index,
        ability.button_name,
        ability.hotkey,
        ability.friendly_name,
        general,
        mismatch,
    ]))


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


# The union of ability_counts and available_abilities over ~300k 3.15 replays,
# plus the new ones in SC2 4.0.
used_abilities = {
    1, 4, 6, 7, 16, 17, 18, 19, 23, 26, 28, 30, 32, 36, 38, 42, 44, 46, 74, 76,
    78, 80, 110, 140, 142, 144, 146, 148, 150, 152, 154, 156, 158, 160, 162,
    164, 166, 167, 169, 171, 173, 174, 181, 195, 199, 203, 207, 211, 212, 216,
    217, 247, 249, 250, 251, 253, 255, 261, 265, 295, 296, 298, 299, 304, 305,
    306, 307, 308, 309, 312, 313, 314, 315, 316, 318, 319, 320, 321, 322, 323,
    324, 326, 327, 328, 329, 331, 333, 348, 380, 382, 383, 386, 388, 390, 392,
    393, 394, 396, 397, 399, 401, 403, 405, 407, 408, 410, 413, 415, 416, 417,
    419, 421, 422, 451, 452, 454, 455, 484, 485, 487, 488, 517, 518, 520, 522,
    524, 554, 556, 558, 560, 561, 562, 563, 591, 594, 595, 596, 597, 614, 620,
    621, 622, 623, 624, 626, 650, 651, 652, 653, 654, 655, 656, 657, 658, 710,
    730, 731, 732, 761, 764, 766, 768, 790, 793, 799, 803, 804, 805, 820, 855,
    856, 857, 861, 862, 863, 864, 865, 866, 880, 881, 882, 883, 884, 885, 886,
    887, 889, 890, 891, 892, 893, 894, 895, 911, 913, 914, 916, 917, 919, 920,
    921, 922, 946, 948, 950, 954, 955, 976, 977, 978, 979, 994, 1006, 1036,
    1038, 1039, 1042, 1062, 1063, 1064, 1065, 1066, 1067, 1068, 1069, 1070,
    1093, 1094, 1097, 1126, 1152, 1154, 1155, 1156, 1157, 1158, 1159, 1160,
    1161, 1162, 1163, 1165, 1166, 1167, 1183, 1184, 1186, 1187, 1188, 1189,
    1190, 1191, 1192, 1193, 1194, 1216, 1217, 1218, 1219, 1220, 1221, 1223,
    1225, 1252, 1253, 1282, 1283, 1312, 1313, 1314, 1315, 1316, 1317, 1342,
    1343, 1344, 1345, 1346, 1348, 1351, 1352, 1353, 1354, 1356, 1372, 1373,
    1374, 1376, 1378, 1380, 1382, 1384, 1386, 1388, 1390, 1392, 1394, 1396,
    1406, 1408, 1409, 1413, 1414, 1416, 1417, 1418, 1419, 1433, 1435, 1437,
    1438, 1440, 1442, 1444, 1446, 1448, 1449, 1450, 1451, 1454, 1455, 1482,
    1512, 1514, 1516, 1517, 1518, 1520, 1522, 1524, 1526, 1528, 1530, 1532,
    1562, 1563, 1564, 1565, 1566, 1567, 1568, 1592, 1593, 1594, 1622, 1623,
    1628, 1632, 1664, 1682, 1683, 1684, 1691, 1692, 1693, 1694, 1725, 1727,
    1729, 1730, 1731, 1732, 1733, 1763, 1764, 1766, 1768, 1819, 1825, 1831,
    1832, 1833, 1834, 1847, 1848, 1853, 1974, 1978, 1998, 2014, 2016, 2048,
    2057, 2063, 2067, 2073, 2081, 2082, 2095, 2097, 2099, 2108, 2110, 2112,
    2113, 2114, 2116, 2146, 2162, 2244, 2324, 2328, 2330, 2331, 2332, 2333,
    2338, 2340, 2342, 2346, 2350, 2354, 2358, 2362, 2364, 2365, 2368, 2370,
    2371, 2373, 2375, 2376, 2387, 2389, 2391, 2393, 2505, 2535, 2542, 2544,
    2550, 2552, 2558, 2560, 2588, 2594, 2596, 2700, 2704, 2708, 2709, 2714,
    2720, 3707, 3709, 3739, 3741, 3743, 3745, 3747, 3749, 3751, 3753, 3755,
    3757, 3765,
}


frivolous = {6, 7}  # Dance and Cheer
# These need a slot id and so are exposed differently.
cancel_slot = {313, 1039, 305, 307, 309, 1832, 1834, 3672}
unload_unit = {410, 415, 397, 1440, 2373, 1409, 914, 3670}

skip_abilities = cancel_slot | unload_unit | frivolous


if __name__ == "__main__":
  app.run(main)
