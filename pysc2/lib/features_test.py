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

import copy
import pickle

from absl.testing import absltest
from absl.testing import parameterized
from future.builtins import range  # pylint: disable=redefined-builtin
import numpy
import six
from pysc2.lib import actions
from pysc2.lib import features
from pysc2.lib import point

from google.protobuf import text_format
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


RECTANGULAR_DIMENSIONS = features.Dimensions(screen=(84, 80), minimap=(64, 67))
SQUARE_DIMENSIONS = features.Dimensions(screen=84, minimap=64)


class AvailableActionsTest(absltest.TestCase):

  always_expected = {
      "no_op", "move_camera", "select_point", "select_rect",
      "select_control_group"
  }

  def setUp(self):
    super(AvailableActionsTest, self).setUp()
    self.obs = text_format.Parse(observation_text_proto, sc_pb.Observation())
    self.hideSpecificActions(True)

  def hideSpecificActions(self, hide_specific_actions):  # pylint: disable=invalid-name
    self.features = features.Features(features.AgentInterfaceFormat(
        feature_dimensions=RECTANGULAR_DIMENSIONS,
        hide_specific_actions=hide_specific_actions))

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

    self.hideSpecificActions(True)
    a.requires_point = False
    self.assertAvail(["Build_TechLab_quick"])
    a.requires_point = True
    self.assertAvail(["Build_TechLab_screen"])

    self.hideSpecificActions(False)
    a.requires_point = False
    self.assertAvail(["Build_TechLab_Barracks_quick", "Build_TechLab_quick"])
    a.requires_point = True
    self.assertAvail(["Build_TechLab_Barracks_screen", "Build_TechLab_screen"])

  def testGeneral(self):
    self.obs.abilities.add(ability_id=1374)
    self.hideSpecificActions(False)
    self.assertAvail(["BurrowDown_quick", "BurrowDown_Baneling_quick"])
    self.hideSpecificActions(True)
    self.assertAvail(["BurrowDown_quick"])

  def testGeneralType(self):
    a = self.obs.abilities.add(ability_id=1376)
    self.hideSpecificActions(False)
    self.assertAvail(["BurrowUp_quick", "BurrowUp_Baneling_quick",
                      "BurrowUp_autocast", "BurrowUp_Baneling_autocast"])
    self.hideSpecificActions(True)
    self.assertAvail(["BurrowUp_quick", "BurrowUp_autocast"])

    a.ability_id = 2110
    self.hideSpecificActions(False)
    self.assertAvail(["BurrowUp_quick", "BurrowUp_Lurker_quick"])
    self.hideSpecificActions(True)
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
    self.hideSpecificActions(False)
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
    self.hideSpecificActions(True)
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


class ToPointTest(absltest.TestCase):

  def testIntAsString(self):
    value = features._to_point("32")
    self.assertEqual(value, point.Point(32, 32))

  def testIntStringTwoTuple(self):
    value = features._to_point(("32", 64))
    self.assertEqual(value, point.Point(32, 64))

  def testNoneInputReturnsNoneOutput(self):
    with self.assertRaises(AssertionError):
      features._to_point(None)

  def testNoneAsFirstElementOfTupleRaises(self):
    with self.assertRaises(TypeError):
      features._to_point((None, 32))

  def testNoneAsSecondElementOfTupleRaises(self):
    with self.assertRaises(TypeError):
      features._to_point((32, None))

  def testSingletonTupleRaises(self):
    with self.assertRaises(ValueError):
      features._to_point((32,))

  def testThreeTupleRaises(self):
    with self.assertRaises(ValueError):
      features._to_point((32, 32, 32))


class DimensionsTest(absltest.TestCase):

  def testScreenSizeWithoutMinimapRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(screen=84)

  def testScreenWidthWithoutHeightRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(screen=(84, 0), minimap=64)

  def testScreenWidthHeightWithoutMinimapRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(screen=(84, 80))

  def testMinimapWidthAndHeightWithoutScreenRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(minimap=(64, 67))

  def testScreenSmallerThanMinimapRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(screen=84, minimap=100)

  def testNoneNoneRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(screen=None, minimap=None)

  def testSingularZeroesRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(screen=0, minimap=0)

  def testTwoZeroesRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(screen=(0, 0), minimap=(0, 0))

  def testThreeTupleScreenRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(screen=(1, 2, 3), minimap=32)

  def testThreeTupleMinimapRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(screen=64, minimap=(1, 2, 3))

  def testNegativeScreenRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(screen=-64, minimap=32)

  def testNegativeMinimapRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(screen=64, minimap=-32)

  def testNegativeScreenTupleRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(screen=(-64, -64), minimap=32)

  def testNegativeMinimapTupleRaises(self):
    with self.assertRaises(ValueError):
      features.Dimensions(screen=64, minimap=(-32, -32))


class TestParseAgentInterfaceFormat(parameterized.TestCase):

  def test_no_arguments_raises(self):
    with self.assertRaises(ValueError):
      features.parse_agent_interface_format()

  @parameterized.parameters((32, None), (None, 32))
  def test_invalid_feature_combinations_raise(self, screen, minimap):
    with self.assertRaises(ValueError):
      features.parse_agent_interface_format(
          feature_screen=screen,
          feature_minimap=minimap)

  def test_valid_feature_specification_is_parsed(self):
    agent_interface_format = features.parse_agent_interface_format(
        feature_screen=32,
        feature_minimap=(24, 24))

    self.assertEqual(
        agent_interface_format.feature_dimensions.screen,
        point.Point(32, 32))

    self.assertEqual(
        agent_interface_format.feature_dimensions.minimap,
        point.Point(24, 24))

  @parameterized.parameters((32, None), (None, 32))
  def test_invalid_minimap_combinations_raise(self, screen, minimap):
    with self.assertRaises(ValueError):
      features.parse_agent_interface_format(
          rgb_screen=screen,
          rgb_minimap=minimap)

  def test_valid_minimap_specification_is_parsed(self):
    agent_interface_format = features.parse_agent_interface_format(
        rgb_screen=32,
        rgb_minimap=(24, 24))

    self.assertEqual(
        agent_interface_format.rgb_dimensions.screen,
        point.Point(32, 32))

    self.assertEqual(
        agent_interface_format.rgb_dimensions.minimap,
        point.Point(24, 24))

  def test_invalid_action_space_raises(self):
    with self.assertRaises(KeyError):
      features.parse_agent_interface_format(
          feature_screen=64,
          feature_minimap=64,
          action_space="UNKNOWN_ACTION_SPACE")

  @parameterized.parameters(actions.ActionSpace.__members__.keys())
  def test_valid_action_space_is_parsed(self, action_space):
    agent_interface_format = features.parse_agent_interface_format(
        feature_screen=32,
        feature_minimap=(24, 24),
        rgb_screen=64,
        rgb_minimap=(48, 48),
        action_space=action_space)

    self.assertEqual(
        agent_interface_format.action_space,
        actions.ActionSpace[action_space])

  def test_camera_width_world_units_are_parsed(self):
    agent_interface_format = features.parse_agent_interface_format(
        feature_screen=32,
        feature_minimap=(24, 24),
        camera_width_world_units=77)

    self.assertEqual(agent_interface_format.camera_width_world_units, 77)

  def test_use_feature_units_is_parsed(self):
    agent_interface_format = features.parse_agent_interface_format(
        feature_screen=32,
        feature_minimap=(24, 24),
        use_feature_units=True)

    self.assertEqual(agent_interface_format.use_feature_units, True)


class FeaturesTest(absltest.TestCase):

  def testFunctionsIdsAreConsistent(self):
    for i, f in enumerate(actions.FUNCTIONS):
      self.assertEqual(i, f.id, "id doesn't match for %s" % f.id)

  def testAllVersionsOfAnAbilityHaveTheSameGeneral(self):
    for ability_id, funcs in six.iteritems(actions.ABILITY_IDS):
      self.assertEqual(len({f.general_id for f in funcs}), 1,
                       "Multiple generals for %s" % ability_id)

  def testValidFunctionsAreConsistent(self):
    feats = features.Features(features.AgentInterfaceFormat(
        feature_dimensions=RECTANGULAR_DIMENSIONS))

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
    feats = features.Features(features.AgentInterfaceFormat(
        feature_dimensions=RECTANGULAR_DIMENSIONS))
    action_spec = feats.action_spec()
    for func_index, func_def in enumerate(action_spec.functions):
      self.assertEqual(func_index, func_def.id)
    for type_index, type_def in enumerate(action_spec.types):
      self.assertEqual(type_index, type_def.id)

  def testReversingUnknownAction(self):
    feats = features.Features(features.AgentInterfaceFormat(
        feature_dimensions=RECTANGULAR_DIMENSIONS,
        hide_specific_actions=False))
    sc2_action = sc_pb.Action()
    sc2_action.action_feature_layer.unit_command.ability_id = 6  # Cheer
    func_call = feats.reverse_action(sc2_action)
    self.assertEqual(func_call.function, 0)  # No-op

  def testSpecificActionsAreReversible(self):
    """Test that the `transform_action` and `reverse_action` are inverses."""
    feats = features.Features(features.AgentInterfaceFormat(
        feature_dimensions=RECTANGULAR_DIMENSIONS,
        hide_specific_actions=False))
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

  def testCanPickleSpecs(self):
    feats = features.Features(features.AgentInterfaceFormat(
        feature_dimensions=SQUARE_DIMENSIONS))
    action_spec = feats.action_spec()
    observation_spec = feats.observation_spec()

    self.assertEqual(action_spec, pickle.loads(pickle.dumps(action_spec)))
    self.assertEqual(observation_spec,
                     pickle.loads(pickle.dumps(observation_spec)))

  def testCanPickleFunctionCall(self):
    func = actions.FUNCTIONS.select_point("select", [1, 2])
    self.assertEqual(func, pickle.loads(pickle.dumps(func)))

  def testCanDeepcopyNumpyFunctionCall(self):
    arguments = [numpy.float32] * len(actions.Arguments._fields)
    dtypes = actions.FunctionCall(
        function=numpy.float32,
        arguments=actions.Arguments(*arguments))
    self.assertEqual(dtypes, copy.deepcopy(dtypes))

  def testSizeConstructors(self):
    feats = features.Features(features.AgentInterfaceFormat(
        feature_dimensions=SQUARE_DIMENSIONS))
    spec = feats.action_spec()
    self.assertEqual(spec.types.screen.sizes, (84, 84))
    self.assertEqual(spec.types.screen2.sizes, (84, 84))
    self.assertEqual(spec.types.minimap.sizes, (64, 64))

    feats = features.Features(features.AgentInterfaceFormat(
        feature_dimensions=RECTANGULAR_DIMENSIONS))
    spec = feats.action_spec()
    self.assertEqual(spec.types.screen.sizes, (84, 80))
    self.assertEqual(spec.types.screen2.sizes, (84, 80))
    self.assertEqual(spec.types.minimap.sizes, (64, 67))

    feats = features.Features(features.AgentInterfaceFormat(
        feature_dimensions=RECTANGULAR_DIMENSIONS))
    spec = feats.action_spec()
    self.assertEqual(spec.types.screen.sizes, (84, 80))
    self.assertEqual(spec.types.screen2.sizes, (84, 80))
    self.assertEqual(spec.types.minimap.sizes, (64, 67))

    # Missing one or the other of game_info and dimensions.
    with self.assertRaises(ValueError):
      features.Features()

    # Resolution/action space mismatch.
    with self.assertRaises(ValueError):
      features.Features(features.AgentInterfaceFormat(
          feature_dimensions=RECTANGULAR_DIMENSIONS,
          action_space=actions.ActionSpace.RGB))
    with self.assertRaises(ValueError):
      features.Features(features.AgentInterfaceFormat(
          rgb_dimensions=RECTANGULAR_DIMENSIONS,
          action_space=actions.ActionSpace.FEATURES))
    with self.assertRaises(ValueError):
      features.Features(features.AgentInterfaceFormat(
          feature_dimensions=RECTANGULAR_DIMENSIONS,
          rgb_dimensions=RECTANGULAR_DIMENSIONS))

  def testFlRgbActionSpec(self):
    feats = features.Features(features.AgentInterfaceFormat(
        feature_dimensions=RECTANGULAR_DIMENSIONS,
        rgb_dimensions=features.Dimensions(screen=(128, 132), minimap=(74, 77)),
        action_space=actions.ActionSpace.FEATURES))
    spec = feats.action_spec()
    self.assertEqual(spec.types.screen.sizes, (84, 80))
    self.assertEqual(spec.types.screen2.sizes, (84, 80))
    self.assertEqual(spec.types.minimap.sizes, (64, 67))

    feats = features.Features(features.AgentInterfaceFormat(
        feature_dimensions=RECTANGULAR_DIMENSIONS,
        rgb_dimensions=features.Dimensions(screen=(128, 132), minimap=(74, 77)),
        action_space=actions.ActionSpace.RGB))
    spec = feats.action_spec()
    self.assertEqual(spec.types.screen.sizes, (128, 132))
    self.assertEqual(spec.types.screen2.sizes, (128, 132))
    self.assertEqual(spec.types.minimap.sizes, (74, 77))

  def testFlRgbObservationSpec(self):
    feats = features.Features(features.AgentInterfaceFormat(
        feature_dimensions=RECTANGULAR_DIMENSIONS,
        rgb_dimensions=features.Dimensions(screen=(128, 132), minimap=(74, 77)),
        action_space=actions.ActionSpace.FEATURES))
    obs_spec = feats.observation_spec()
    self.assertEqual(obs_spec["feature_screen"], (17, 80, 84))
    self.assertEqual(obs_spec["feature_minimap"], (7, 67, 64))
    self.assertEqual(obs_spec["rgb_screen"], (132, 128, 3))
    self.assertEqual(obs_spec["rgb_minimap"], (77, 74, 3))


if __name__ == "__main__":
  absltest.main()
