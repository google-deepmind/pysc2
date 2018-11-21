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

import functools

from absl.testing import absltest

from pysc2.env import sc2_env
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import units

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import debug_pb2 as sc_debug
from s2clientprotocol import raw_pb2 as sc_raw
from s2clientprotocol import sc2api_pb2 as sc_pb


def get_units(obs, filter_fn=None, owner=None, unit_type=None):
  """Return a dict of units that match the filter."""
  if unit_type and not isinstance(unit_type, (list, tuple)):
    unit_type = (unit_type,)
  return {u.tag: u for u in obs.observation.raw_data.units
          if ((filter_fn is None or filter_fn(u)) and
              (owner is None or u.owner == owner) and
              (unit_type is None or u.unit_type in unit_type))}


def get_unit(*args, **kwargs):
  """Return the first unit that matches, or None."""
  try:
    return next(iter(get_units(*args, **kwargs).values()))
  except StopIteration:
    return None


def _xy_locs(mask):
  """Mask should be a set of bools from comparison with a feature layer."""
  ys, xs = mask.nonzero()
  return [point.Point(x, y) for x, y in zip(xs, ys)]


def setup(**kwargs):
  """A decorator to replace unittest.setUp so it can take args."""
  def decorator(func):
    @functools.wraps(func)
    def inner(self):
      try:
        self.start(**kwargs)
        func(self)
      finally:
        self.close()
    return inner
  return decorator


class ObsTest(absltest.TestCase):

  def start(self, show_cloaked=True):  # Instead of setUp.
    # use SC2Env to make it easy to set up a multiplayer game.
    self._dont_use_env = sc2_env.SC2Env(
        map_name="Flat64",
        players=[sc2_env.Agent(sc2_env.Race.protoss, "test1"),
                 sc2_env.Agent(sc2_env.Race.protoss, "test2")],
        step_mul=1,
        game_steps_per_episode=1000,
        agent_interface_format=sc2_env.AgentInterfaceFormat(
            feature_dimensions=sc2_env.Dimensions(screen=64, minimap=64),
            show_cloaked=show_cloaked,
            use_raw_units=True))
    self._controllers = self._dont_use_env._controllers
    self._parallel = self._dont_use_env._parallel
    self._info = self._controllers[0].game_info()
    self._features = features.features_from_game_info(self._info)
    self._map_size = point.Point.build(self._info.start_raw.map_size)
    print("Map size:", self._map_size)
    self.step()  # Get into the game properly.

  def close(self):  # Instead of tearDown.
    self._dont_use_env.close()
    self._dont_use_env = None
    self._controllers = None
    self._parallel = None

  def step(self, count=4):
    return self._parallel.run((c.step, count) for c in self._controllers)

  def observe(self, disable_fog=False):
    return self._parallel.run((c.observe, disable_fog)
                              for c in self._controllers)

  def move_camera(self, x, y):
    action = sc_pb.Action()
    action.action_feature_layer.camera_move.center_minimap.x = x
    action.action_feature_layer.camera_move.center_minimap.y = y
    return self._parallel.run((c.act, action) for c in self._controllers)

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

  def kill_unit(self, unit_tags):
    if not isinstance(unit_tags, (list, tuple)):
      unit_tags = [unit_tags]
    return self.debug(kill_unit=sc_debug.DebugKillUnit(tag=unit_tags))

  def assert_layers(self, layers, pos, **kwargs):
    for k, v in sorted(kwargs.items()):
      self.assertEqual(layers[k, pos.y, pos.x], v,
                       msg="%s[%s, %s]: expected: %s, got: %s" % (
                           k, pos.y, pos.x, v, layers[k, pos.y, pos.x]))

  def assert_unit(self, unit, **kwargs):
    self.assertTrue(unit)
    for k, v in sorted(kwargs.items()):
      if k == "pos":
        self.assertAlmostEqual(unit.pos.x, v[0])
        self.assertAlmostEqual(unit.pos.y, v[1])
      else:
        self.assertEqual(getattr(unit, k), v,
                         msg="%s: expected: %s, got: %s\n%s" % (
                             k, v, getattr(unit, k), unit))

  @setup()
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

  @setup(show_cloaked=False)
  def test_hide_cloaked(self):
    self.assertFalse(self._info.options.show_cloaked)

    self.god()
    self.move_camera(32, 32)

    # Create some units. One cloaked, one to see it without detection.
    self.create_unit(unit_type=units.Protoss.DarkTemplar, owner=1, pos=(50, 50))
    self.create_unit(unit_type=units.Protoss.Sentry, owner=2, pos=(48, 50))

    self.step(16)
    obs = self.observe()

    # Verify both can see it, but that only the owner knows details.
    p1 = get_unit(obs[0], unit_type=units.Protoss.DarkTemplar)
    p2 = get_unit(obs[1], unit_type=units.Protoss.DarkTemplar)

    self.assert_unit(p1, display_type=sc_raw.Visible, health=40, shield=80,
                     cloak=sc_raw.CloakedAllied)
    self.assertIsNone(p2)

    screen1 = self._features.transform_obs(obs[0])["feature_screen"]
    screen2 = self._features.transform_obs(obs[1])["feature_screen"]
    dt = _xy_locs(screen1.unit_type == units.Protoss.DarkTemplar)[0]
    self.assert_layers(screen1, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=40, unit_shields=80, cloaked=1)
    self.assert_layers(screen2, dt, unit_type=0,
                       unit_hit_points=0, unit_shields=0, cloaked=0)

    # Create an observer so the opponent has detection.
    self.create_unit(unit_type=units.Protoss.Observer, owner=2, pos=(48, 48))

    self.step(16)  # It takes a few frames for the observer to detect.
    obs = self.observe()

    # Verify both can see it, with the same details
    p1 = get_unit(obs[0], unit_type=units.Protoss.DarkTemplar)
    p2 = get_unit(obs[1], unit_type=units.Protoss.DarkTemplar)
    self.assert_unit(p1, display_type=sc_raw.Visible, health=40, shield=80,
                     cloak=sc_raw.CloakedAllied)
    self.assert_unit(p2, display_type=sc_raw.Visible, health=40, shield=80,
                     cloak=sc_raw.CloakedDetected)

    screen1 = self._features.transform_obs(obs[0])["feature_screen"]
    screen2 = self._features.transform_obs(obs[1])["feature_screen"]
    dt = _xy_locs(screen1.unit_type == units.Protoss.DarkTemplar)[0]
    self.assert_layers(screen1, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=40, unit_shields=80, cloaked=1)
    self.assert_layers(screen2, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=40, unit_shields=80, cloaked=1)

  @setup()
  def test_show_cloaked(self):
    self.assertTrue(self._info.options.show_cloaked)

    self.god()
    self.move_camera(32, 32)

    # Create some units. One cloaked, one to see it without detection.
    self.create_unit(unit_type=units.Protoss.DarkTemplar, owner=1, pos=(50, 50))
    self.create_unit(unit_type=units.Protoss.Sentry, owner=2, pos=(48, 50))

    self.step(16)
    obs = self.observe()

    # Verify both can see it, but that only the owner knows details.
    p1 = get_unit(obs[0], unit_type=units.Protoss.DarkTemplar)
    p2 = get_unit(obs[1], unit_type=units.Protoss.DarkTemplar)

    self.assert_unit(p1, display_type=sc_raw.Visible, health=40, shield=80,
                     cloak=sc_raw.CloakedAllied)
    self.assert_unit(p2, display_type=sc_raw.Hidden, health=0, shield=0,
                     cloak=sc_raw.Cloaked)

    screen1 = self._features.transform_obs(obs[0])["feature_screen"]
    screen2 = self._features.transform_obs(obs[1])["feature_screen"]
    dt = _xy_locs(screen1.unit_type == units.Protoss.DarkTemplar)[0]
    self.assert_layers(screen1, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=40, unit_shields=80, cloaked=1)
    self.assert_layers(screen2, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=0, unit_shields=0, cloaked=1)

    # Create an observer so the opponent has detection.
    self.create_unit(unit_type=units.Protoss.Observer, owner=2, pos=(48, 48))

    self.step(16)  # It takes a few frames for the observer to detect.
    obs = self.observe()

    # Verify both can see it, with the same details
    p1 = get_unit(obs[0], unit_type=units.Protoss.DarkTemplar)
    p2 = get_unit(obs[1], unit_type=units.Protoss.DarkTemplar)
    self.assert_unit(p1, display_type=sc_raw.Visible, health=40, shield=80,
                     cloak=sc_raw.CloakedAllied)
    self.assert_unit(p2, display_type=sc_raw.Visible, health=40, shield=80,
                     cloak=sc_raw.CloakedDetected)

    screen1 = self._features.transform_obs(obs[0])["feature_screen"]
    screen2 = self._features.transform_obs(obs[1])["feature_screen"]
    dt = _xy_locs(screen1.unit_type == units.Protoss.DarkTemplar)[0]
    self.assert_layers(screen1, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=40, unit_shields=80, cloaked=1)
    self.assert_layers(screen2, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=40, unit_shields=80, cloaked=1)

  @setup()
  def test_pos(self):
    self.create_unit(unit_type=units.Protoss.Archon, owner=1, pos=(40, 50))
    self.create_unit(unit_type=units.Protoss.Observer, owner=1, pos=(60, 50))

    self.step()
    obs = self.observe()

    archon = get_unit(obs[0], unit_type=units.Protoss.Archon)
    observer = get_unit(obs[0], unit_type=units.Protoss.Observer)

    self.assertAlmostEqual(archon.pos.x, 40)
    self.assertAlmostEqual(archon.pos.y, 50)
    self.assertAlmostEqual(observer.pos.x, 60)
    self.assertAlmostEqual(observer.pos.y, 50)
    self.assertLess(archon.pos.z, observer.pos.z)  # The observer flies.
    self.assertGreater(archon.radius, observer.radius)

    # Move them towards the center, make sure they move and rotate.
    self.raw_unit_command(0, 16, (archon.tag, observer.tag), (50, 45))

    self.step(40)
    obs2 = self.observe()

    archon2 = get_unit(obs2[0], unit_type=units.Protoss.Archon)
    observer2 = get_unit(obs2[0], unit_type=units.Protoss.Observer)

    self.assertGreater(archon2.pos.x, 40)
    self.assertLess(observer2.pos.x, 60)
    self.assertLess(archon2.pos.z, observer2.pos.z)
    self.assertNotEqual(archon.facing, archon2.facing)
    self.assertNotEqual(observer.facing, observer2.facing)

  @setup()
  def test_fog(self):
    obs = self.observe()

    def assert_visible(unit, display_type, alliance, cloak):
      self.assert_unit(unit, display_type=display_type, alliance=alliance,
                       cloak=cloak)

    self.create_unit(unit_type=units.Protoss.Sentry, owner=1, pos=(50, 52))
    self.create_unit(unit_type=units.Protoss.DarkTemplar, owner=1, pos=(52, 52))

    self.step()
    obs = self.observe()

    assert_visible(get_unit(obs[0], unit_type=units.Protoss.Sentry),
                   sc_raw.Visible, sc_raw.Self, sc_raw.NotCloaked)
    assert_visible(get_unit(obs[0], unit_type=units.Protoss.DarkTemplar),
                   sc_raw.Visible, sc_raw.Self, sc_raw.CloakedAllied)
    self.assertIsNone(get_unit(obs[1], unit_type=units.Protoss.Sentry))
    self.assertIsNone(get_unit(obs[1], unit_type=units.Protoss.DarkTemplar))

    obs = self.observe(disable_fog=True)

    assert_visible(get_unit(obs[0], unit_type=units.Protoss.Sentry),
                   sc_raw.Visible, sc_raw.Self, sc_raw.NotCloaked)
    assert_visible(get_unit(obs[0], unit_type=units.Protoss.DarkTemplar),
                   sc_raw.Visible, sc_raw.Self, sc_raw.CloakedAllied)
    assert_visible(get_unit(obs[1], unit_type=units.Protoss.Sentry),
                   sc_raw.Hidden, sc_raw.Enemy, sc_raw.CloakedUnknown)
    assert_visible(get_unit(obs[1], unit_type=units.Protoss.DarkTemplar),
                   sc_raw.Hidden, sc_raw.Enemy, sc_raw.CloakedUnknown)


if __name__ == "__main__":
  absltest.main()
