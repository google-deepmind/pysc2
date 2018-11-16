#!/usr/bin/python
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Test that various observations do what you'd expect."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest

from pysc2.env import sc2_env
from pysc2.lib import units

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import debug_pb2 as sc_debug
from s2clientprotocol import sc2api_pb2 as sc_pb


def get_units(obs, filter_fn=None, owner=None, unit_type=None):
  return {u.tag: u for u in obs.observation.raw_data.units
          if ((filter_fn is None or filter_fn(u)) and
              (owner is None or u.owner == owner) and
              (unit_type is None or u.unit_type == unit_type))}


def get_unit(*args, **kwargs):
  return next(iter(get_units(*args, **kwargs).values()))


class ObsTest(absltest.TestCase):

  def setUp(self):
    # use SC2Env to make it easy to set up a multiplayer game.
    self._dont_use_env = sc2_env.SC2Env(
        map_name="Flat64",
        players=[sc2_env.Agent(sc2_env.Race.protoss, "test1"),
                 sc2_env.Agent(sc2_env.Race.protoss, "test2")],
        step_mul=1,
        game_steps_per_episode=1000,
        agent_interface_format=sc2_env.AgentInterfaceFormat(
            feature_dimensions=sc2_env.Dimensions(screen=64, minimap=64),
            use_raw_units=True))
    self._controllers = self._dont_use_env._controllers
    self._parallel = self._dont_use_env._parallel
    self.info = self._controllers[0].game_info()
    self.step()  # Get into the game properly.

  def tearDown(self):
    self._dont_use_env.close()
    self._dont_use_env = None
    self._controllers = None
    self._parallel = None

  def step(self, count=4):
    return self._parallel.run((c.step, count) for c in self._controllers)

  def observe(self):
    return self._parallel.run(c.observe for c in self._controllers)

  def raw_unit_command(self, player, ability_id, unit_tags, pos=None):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = ability_id
    if isinstance(unit_tags, (list, tuple)):
      action.action_raw.unit_command.unit_tags.extend(unit_tags)
    else:
      action.action_raw.unit_command.unit_tags.append(unit_tags)
    if pos:
      action.action_raw.unit_command.target_world_space_pos.x = pos[0]
      action.action_raw.unit_command.target_world_space_pos.y = pos[1]
    self._controllers[player].act(action)

  def debug(self, player=0, **kwargs):
    self._controllers[player].debug([sc_debug.DebugCommand(**kwargs)])

  def god(self):
    """Stop the units from killing each other so we can observe them."""
    self.debug(0, game_state=sc_debug.god)
    self.debug(1, game_state=sc_debug.god)

  def create_unit(self, unit_type, owner, pos, quantity=1):
    if isinstance(pos, tuple):
      pos = sc_common.Point2D(x=pos[0], y=pos[1])
    return self.debug(create_unit=sc_debug.DebugCreateUnit(
        unit_type=unit_type, owner=owner, pos=pos, quantity=quantity))

  def test_hallucination(self):
    self.god()

    # Create some sentries.
    self.create_unit(unit_type=units.Protoss.Sentry, owner=1, pos=(50, 50))
    self.create_unit(unit_type=units.Protoss.Sentry, owner=2, pos=(50, 48))

    self.step()
    obs = self.observe()

    # Give one enough energy.
    tag = get_unit(obs[0], unit_type=units.Protoss.Sentry, owner=1).tag
    self.debug(unit_value=sc_debug.DebugSetUnitValue(
        unit_value=sc_debug.DebugSetUnitValue.Energy, value=200, unit_tag=tag))

    self.step()
    obs = self.observe()

    # Create a hallucinated archon.
    self.raw_unit_command(0, 146, tag)  # Hallucinate Archon

    self.step()
    obs = self.observe()

    # Verify the owner knows it's a hallucination, but the opponent doesn't.
    p1 = get_unit(obs[0], unit_type=units.Protoss.Archon)
    p2 = get_unit(obs[1], unit_type=units.Protoss.Archon)
    self.assertTrue(p1.is_hallucination)
    self.assertFalse(p2.is_hallucination)

    # Create an observer so the opponent has detection.
    self.create_unit(unit_type=units.Protoss.Observer, owner=2, pos=(48, 50))

    self.step()
    obs = self.observe()

    # Verify the opponent now also knows it's a hallucination.
    p1 = get_unit(obs[0], unit_type=units.Protoss.Archon)
    p2 = get_unit(obs[1], unit_type=units.Protoss.Archon)
    self.assertTrue(p1.is_hallucination)
    self.assertTrue(p2.is_hallucination)


if __name__ == "__main__":
  absltest.main()
