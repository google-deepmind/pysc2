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
"""Tests for features."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from future.builtins import range  # pylint: disable=redefined-builtin
import numpy
import six
from pysc2.lib import actions
from pysc2.lib import features
from pysc2.lib import point

from google.protobuf import text_format
from absl.testing import absltest as basetest
from s2clientprotocol import sc2api_pb2 as sc_pb


# Heavily trimmed, so this is useful for testing actions, but not observations.
observation_text_proto = """
player_common {
  player_id: 1
  minerals: 0
  vespene: 0
  food_cap: 10
  food_used: 0
  food_army: 0
  food_workers: 0
  idle_worker_count: 0
  army_count: 0
  warp_gate_count: 0
  larva_count: 0
}
game_loop: 20
"""


class AvailableActionsTest(basetest.TestCase):

  always_expected = {
      "no_op", "move_camera", "select_point", "select_rect",
      "select_control_group"
  }

  def setUp(self):
    super(AvailableActionsTest, self).setUp()
    self.obs = text_format.Parse(observation_text_proto, sc_pb.Observation())
    self.features = features.Features(screen_size_px=(84, 80),
                                      minimap_size_px=(64, 67))

  def assertAvail(self, expected):
    actual = self.features.available_actions(self.obs)
    actual_names = {actions.FUNCTIONS[i].name for i in actual}
    self.assertEqual(actual_names, set(expected) | self.always_expected)

  def testAlways(self):
    self.assertAvail([])

  def testSelectUnit(self):
    self.obs.ui_data.multi.units.add(unit_type=1)
    self.assertAvail(["select_unit"])

  def testSelectIdleWorkder(self):
    self.obs.player_common.idle_worker_count = 1
    self.assertAvail(["select_idle_worker"])

  def testSelectArmy(self):
    self.obs.player_common.army_count = 3
    self.assertAvail(["select_army"])

  def testSelectWarpGates(self):
    self.obs.player_common.warp_gate_count = 1
    self.assertAvail(["select_warp_gates"])

  def testSelectLarva(self):
    self.obs.player_common.larva_count = 2
    self.assertAvail(["select_larva"])

  def testQuick(self):
    self.obs.abilities.add(ability_id=32)
    self.assertAvail(["Effect_Salvage_quick"])

  def testScreen(self):
    self.obs.abilities.add(ability_id=326, requires_point=True)
    self.assertAvail(["Build_SensorTower_screen"])

  def testScreenMinimap(self):
    self.obs.abilities.add(ability_id=17, requires_point=True)
    self.assertAvail(["Patrol_screen", "Patrol_minimap"])

  def testScreenAutocast(self):
    self.obs.abilities.add(ability_id=386, requires_point=True)
    self.assertAvail(["Effect_Heal_screen", "Effect_Heal_autocast"])

  def testScreenQuick(self):
    a = self.obs.abilities.add(ability_id=421)

    self.features._hide_specific_actions = True
    a.requires_point = False
    self.assertAvail(["Build_TechLab_quick"])
    a.requires_point = True
    self.assertAvail(["Build_TechLab_screen"])

    self.features._hide_specific_actions = False
    a.requires_point = False
    self.assertAvail(["Build_TechLab_Barracks_quick", "Build_TechLab_quick"])
    a.requires_point = True
    self.assertAvail(["Build_TechLab_Barracks_screen", "Build_TechLab_screen"])

  def testGeneral(self):
    self.obs.abilities.add(ability_id=1374)
    self.features._hide_specific_actions = False
    self.assertAvail(["BurrowDown_quick", "BurrowDown_Baneling_quick"])
    self.features._hide_specific_actions = True
    self.assertAvail(["BurrowDown_quick"])

  def testGeneralType(self):
    a = self.obs.abilities.add(ability_id=1376)
    self.features._hide_specific_actions = False
    self.assertAvail(["BurrowUp_quick", "BurrowUp_Baneling_quick",
                      "BurrowUp_autocast", "BurrowUp_Baneling_autocast"])
    self.features._hide_specific_actions = True
    self.assertAvail(["BurrowUp_quick", "BurrowUp_autocast"])

    a.ability_id = 2110
    self.features._hide_specific_actions = False
    self.assertAvail(["BurrowUp_quick", "BurrowUp_Lurker_quick"])
    self.features._hide_specific_actions = True
    self.assertAvail(["BurrowUp_quick"])

  def testMany(self):
    add = [
        (23, True),  # Attack
        (318, True),  # Build_CommandCenter
        (320, True),  # Build_Refinery
        (319, True),  # Build_SupplyDepot
        (316, True),  # Effect_Repair_SCV
        (295, True),  # Harvest_Gather_SCV
        (16, True),  # Move
        (17, True),  # Patrol
        (4, False),  # Stop
    ]
    for a, r in add:
      self.obs.abilities.add(ability_id=a, requires_point=r)
    self.features._hide_specific_actions = False
    self.assertAvail([
        "Attack_Attack_minimap",
        "Attack_Attack_screen",
        "Attack_minimap",
        "Attack_screen",
        "Build_CommandCenter_screen",
        "Build_Refinery_screen",
        "Build_SupplyDepot_screen",
        "Effect_Repair_screen",
        "Effect_Repair_autocast",
        "Effect_Repair_SCV_autocast",
        "Effect_Repair_SCV_screen",
        "Harvest_Gather_screen",
        "Harvest_Gather_SCV_screen",
        "Move_minimap",
        "Move_screen",
        "Patrol_minimap",
        "Patrol_screen",
        "Stop_quick",
        "Stop_Stop_quick"
    ])
    self.features._hide_specific_actions = True
    self.assertAvail([
        "Attack_minimap",
        "Attack_screen",
        "Build_CommandCenter_screen",
        "Build_Refinery_screen",
        "Build_SupplyDepot_screen",
        "Effect_Repair_screen",
        "Effect_Repair_autocast",
        "Harvest_Gather_screen",
        "Move_minimap",
        "Move_screen",
        "Patrol_minimap",
        "Patrol_screen",
        "Stop_quick",
    ])


class FeaturesTest(basetest.TestCase):

  def testFunctionsIdsAreConsistent(self):
    for i, f in enumerate(actions.FUNCTIONS):
      self.assertEqual(i, f.id, "id doesn't match for %s" % f.id)

  def testAllVersionsOfAnAbilityHaveTheSameGeneral(self):
    for ability_id, funcs in six.iteritems(actions.ABILITY_IDS):
      self.assertEqual(len({f.general_id for f in funcs}), 1,
                       "Multiple generals for %s" % ability_id)

  def testValidFunctionsAreConsistent(self):
    feats = features.Features(screen_size_px=(84, 80), minimap_size_px=(64, 67))

    valid_funcs = feats.action_spec()
    for func_def in valid_funcs.functions:
      func = actions.FUNCTIONS[func_def.id]
      self.assertEqual(func_def.id, func.id)
      self.assertEqual(func_def.name, func.name)
      self.assertEqual(len(func_def.args), len(func.args))

  def gen_random_function_call(self, action_spec, func_id):
    args = [[numpy.random.randint(0, size) for size in arg.sizes]
            for arg in action_spec.functions[func_id].args]
    return actions.FunctionCall(func_id, args)

  def testIdsMatchIndex(self):
    feats = features.Features(screen_size_px=(84, 80), minimap_size_px=(64, 67))
    action_spec = feats.action_spec()
    for func_index, func_def in enumerate(action_spec.functions):
      self.assertEqual(func_index, func_def.id)
    for type_index, type_def in enumerate(action_spec.types):
      self.assertEqual(type_index, type_def.id)

  def testReversingUnknownAction(self):
    feats = features.Features(screen_size_px=(84, 80), minimap_size_px=(64, 67),
                              hide_specific_actions=False)
    sc2_action = sc_pb.Action()
    sc2_action.action_feature_layer.unit_command.ability_id = 6  # Cheer
    func_call = feats.reverse_action(sc2_action)
    self.assertEqual(func_call.function, 0)  # No-op

  def testSpecificActionsAreReversible(self):
    """Test that the `transform_action` and `reverse_action` are inverses."""
    feats = features.Features(screen_size_px=(84, 80), minimap_size_px=(64, 67),
                              hide_specific_actions=False)
    action_spec = feats.action_spec()

    for func_def in action_spec.functions:
      for _ in range(10):
        func_call = self.gen_random_function_call(action_spec, func_def.id)

        sc2_action = feats.transform_action(
            None, func_call, skip_available=True)
        func_call2 = feats.reverse_action(sc2_action)
        sc2_action2 = feats.transform_action(
            None, func_call2, skip_available=True)
        if func_def.id == actions.FUNCTIONS.select_rect.id:
          # Need to check this one manually since the same rect can be
          # defined in multiple ways.
          def rect(a):
            return point.Rect(point.Point(*a[1]).floor(),
                              point.Point(*a[2]).floor())

          self.assertEqual(func_call.function, func_call2.function)
          self.assertEqual(len(func_call.arguments), len(func_call2.arguments))
          self.assertEqual(func_call.arguments[0], func_call2.arguments[0])
          self.assertEqual(rect(func_call.arguments),
                           rect(func_call2.arguments))
        else:
          self.assertEqual(func_call, func_call2, msg=sc2_action)
        self.assertEqual(sc2_action, sc2_action2)


if __name__ == "__main__":
  basetest.main()
