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

from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import actions
from pysc2.lib import buffs
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import portspicker
from pysc2.lib import run_parallel
from pysc2.lib import units

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import debug_pb2 as sc_debug
from s2clientprotocol import error_pb2 as sc_error
from s2clientprotocol import raw_pb2 as sc_raw
from s2clientprotocol import sc2api_pb2 as sc_pb


def get_units(obs, filter_fn=None, owner=None, unit_type=None, tag=None):
  """Return a dict of units that match the filter."""
  if unit_type and not isinstance(unit_type, (list, tuple)):
    unit_type = (unit_type,)
  out = {}
  for u in obs.observation.raw_data.units:
    if ((filter_fn is None or filter_fn(u)) and
        (owner is None or u.owner == owner) and
        (unit_type is None or u.unit_type in unit_type) and
        (tag is None or u.tag == tag)):
      out[u.tag] = u
  return out


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
    def _setup(self):
      try:
        print((" %s: Starting game " % func.__name__).center(80, "-"))
        self.start_game(**kwargs)
        func(self)
        self.start_replay()
        print((" %s: Starting replay " % func.__name__).center(80, "-"))
        func(self)
      finally:
        self.close()
    return _setup
  return decorator


def only_in_game(func):
  @functools.wraps(func)
  def decorator(self, *args, **kwargs):
    if self._in_game:
      return func(self, *args, **kwargs)
  return decorator


class ObsTest(absltest.TestCase):

  def start_game(self, show_cloaked=True, disable_fog=False):
    """Start a multiplayer game with options."""
    self._disable_fog = disable_fog
    run_config = run_configs.get()
    self._parallel = run_parallel.RunParallel()  # Needed for multiplayer.
    map_inst = maps.get("Flat64")
    self._map_data = map_inst.data(run_config)

    self._ports = portspicker.pick_unused_ports(4)
    self._sc2_procs = [run_config.start(extra_ports=self._ports, want_rgb=False)
                       for _ in range(2)]
    self._controllers = [p.controller for p in self._sc2_procs]

    self._parallel.run((c.save_map, map_inst.path, self._map_data)
                       for c in self._controllers)

    self._interface = sc_pb.InterfaceOptions(
        raw=True, score=False, show_cloaked=show_cloaked)
    self._interface.feature_layer.width = 24
    self._interface.feature_layer.resolution.x = 64
    self._interface.feature_layer.resolution.y = 64
    self._interface.feature_layer.minimap_resolution.x = 64
    self._interface.feature_layer.minimap_resolution.y = 64

    create = sc_pb.RequestCreateGame(
        random_seed=1, disable_fog=self._disable_fog,
        local_map=sc_pb.LocalMap(map_path=map_inst.path))
    create.player_setup.add(type=sc_pb.Participant)
    create.player_setup.add(type=sc_pb.Participant)

    join = sc_pb.RequestJoinGame(race=sc_common.Protoss,
                                 options=self._interface)
    join.shared_port = 0  # unused
    join.server_ports.game_port = self._ports[0]
    join.server_ports.base_port = self._ports[1]
    join.client_ports.add(game_port=self._ports[2],
                          base_port=self._ports[3])

    self._controllers[0].create_game(create)
    self._parallel.run((c.join_game, join) for c in self._controllers)

    self._info = self._controllers[0].game_info()
    self._features = features.features_from_game_info(
        self._info, use_raw_units=True)

    self._map_size = point.Point.build(self._info.start_raw.map_size)
    print("Map size:", self._map_size)
    self._in_game = True
    self.step()  # Get into the game properly.

  def start_replay(self):
    """Switch from the game to a replay."""
    self.step(300)
    replay_data = self._controllers[0].save_replay()
    self._parallel.run(c.leave for c in self._controllers)
    for player_id, controller in enumerate(self._controllers):
      controller.start_replay(sc_pb.RequestStartReplay(
          replay_data=replay_data,
          map_data=self._map_data,
          options=self._interface,
          disable_fog=self._disable_fog,
          observed_player_id=player_id+1))
    self._in_game = False
    self.step()  # Get into the game properly.

  def close(self):  # Instead of tearDown.
    # Don't use parallel since it might be broken by an exception.
    if hasattr(self, "_controllers") and self._controllers:
      for c in self._controllers:
        c.quit()
      self._controllers = None
    if hasattr(self, "_sc2_procs") and self._sc2_procs:
      for p in self._sc2_procs:
        p.close()
      self._sc2_procs = None

    if hasattr(self, "_ports") and self._ports:
      portspicker.return_ports(self._ports)
      self._ports = None
    self._parallel = None

  def step(self, count=4):
    return self._parallel.run((c.step, count) for c in self._controllers)

  def observe(self, disable_fog=False):
    return self._parallel.run((c.observe, disable_fog)
                              for c in self._controllers)

  @only_in_game
  def move_camera(self, x, y):
    action = sc_pb.Action()
    action.action_feature_layer.camera_move.center_minimap.x = x
    action.action_feature_layer.camera_move.center_minimap.y = y
    return self._parallel.run((c.act, action) for c in self._controllers)

  @only_in_game
  def raw_unit_command(self, player, ability_id, unit_tags, pos=None,
                       target=None):
    if isinstance(ability_id, str):
      ability_id = actions.FUNCTIONS[ability_id].ability_id
    action = sc_pb.Action()
    cmd = action.action_raw.unit_command
    cmd.ability_id = ability_id
    if isinstance(unit_tags, (list, tuple)):
      cmd.unit_tags.extend(unit_tags)
    else:
      cmd.unit_tags.append(unit_tags)
    if pos:
      cmd.target_world_space_pos.x = pos[0]
      cmd.target_world_space_pos.y = pos[1]
    elif target:
      cmd.target_unit_tag = target
    response = self._controllers[player].act(action)
    for result in response.result:
      self.assertEqual(result, sc_error.Success)

  @only_in_game
  def debug(self, player=0, **kwargs):
    self._controllers[player].debug([sc_debug.DebugCommand(**kwargs)])

  def god(self):
    """Stop the units from killing each other so we can observe them."""
    self.debug(0, game_state=sc_debug.god)
    self.debug(1, game_state=sc_debug.god)

  def create_unit(self, unit_type, owner, pos, quantity=1):
    if isinstance(pos, tuple):
      pos = sc_common.Point2D(x=pos[0], y=pos[1])
    elif isinstance(pos, sc_common.Point):
      pos = sc_common.Point2D(x=pos.x, y=pos.y)
    return self.debug(create_unit=sc_debug.DebugCreateUnit(
        unit_type=unit_type, owner=owner, pos=pos, quantity=quantity))

  def kill_unit(self, unit_tags):
    if not isinstance(unit_tags, (list, tuple)):
      unit_tags = [unit_tags]
    return self.debug(kill_unit=sc_debug.DebugKillUnit(tag=unit_tags))

  def set_energy(self, tag, energy):
    self.debug(unit_value=sc_debug.DebugSetUnitValue(
        unit_value=sc_debug.DebugSetUnitValue.Energy, value=energy,
        unit_tag=tag))

  def assert_point(self, proto_pos, pos):
    self.assertAlmostEqual(proto_pos.x, pos[0])
    self.assertAlmostEqual(proto_pos.y, pos[1])

  def assert_layers(self, layers, pos, **kwargs):
    for k, v in sorted(kwargs.items()):
      self.assertEqual(layers[k, pos.y, pos.x], v,
                       msg="%s[%s, %s]: expected: %s, got: %s" % (
                           k, pos.y, pos.x, v, layers[k, pos.y, pos.x]))

  def assert_unit(self, unit, **kwargs):
    self.assertTrue(unit)
    self.assertIsInstance(unit, sc_raw.Unit)
    for k, v in sorted(kwargs.items()):
      if k == "pos":
        self.assert_point(unit.pos, v)
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
    self.raw_unit_command(0, "Hallucination_Archon_quick", tag)

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

    self.assert_point(archon.pos, (40, 50))
    self.assert_point(observer.pos, (60, 50))
    self.assertLess(archon.pos.z, observer.pos.z)  # The observer flies.
    self.assertGreater(archon.radius, observer.radius)

    # Move them towards the center, make sure they move.
    self.raw_unit_command(0, "Move_screen", (archon.tag, observer.tag),
                          (50, 45))

    self.step(40)
    obs2 = self.observe()

    archon2 = get_unit(obs2[0], unit_type=units.Protoss.Archon)
    observer2 = get_unit(obs2[0], unit_type=units.Protoss.Observer)

    self.assertGreater(archon2.pos.x, 40)
    self.assertLess(observer2.pos.x, 60)
    self.assertLess(archon2.pos.z, observer2.pos.z)

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

  @setup()
  def test_effects(self):
    def get_effect_proto(obs, effect_id):
      for e in obs.observation.raw_data.effects:
        if e.effect_id == effect_id:
          return e
      return None

    def get_effect_obs(obs, effect_id):
      for e in obs:
        if e.effect == effect_id:
          return e
      return None

    self.god()
    self.move_camera(32, 32)

    # Create some sentries.
    self.create_unit(unit_type=units.Protoss.Sentry, owner=1, pos=(50, 50))
    self.create_unit(unit_type=units.Protoss.Stalker, owner=1, pos=(48, 50))
    self.create_unit(unit_type=units.Protoss.Phoenix, owner=2, pos=(50, 48))

    self.step()
    obs = self.observe()

    # Give enough energy.
    sentry = get_unit(obs[0], unit_type=units.Protoss.Sentry)
    stalker = get_unit(obs[0], unit_type=units.Protoss.Stalker)
    pheonix = get_unit(obs[0], unit_type=units.Protoss.Phoenix)
    self.set_energy(sentry.tag, 200)
    self.set_energy(pheonix.tag, 200)

    self.step()
    obs = self.observe()

    self.raw_unit_command(0, "Effect_GuardianShield_quick", sentry.tag)

    self.step(16)
    obs = self.observe()

    self.assertIn(buffs.Buffs.GuardianShield,
                  get_unit(obs[0], tag=sentry.tag).buff_ids)
    self.assertIn(buffs.Buffs.GuardianShield,
                  get_unit(obs[1], tag=sentry.tag).buff_ids)
    self.assertIn(buffs.Buffs.GuardianShield,
                  get_unit(obs[0], tag=stalker.tag).buff_ids)
    self.assertIn(buffs.Buffs.GuardianShield,
                  get_unit(obs[1], tag=stalker.tag).buff_ids)
    self.assertNotIn(buffs.Buffs.GuardianShield,
                     get_unit(obs[0], tag=pheonix.tag).buff_ids)
    self.assertNotIn(buffs.Buffs.GuardianShield,
                     get_unit(obs[1], tag=pheonix.tag).buff_ids)

    # Both players should see the shield.
    e = get_effect_proto(obs[0], features.Effects.GuardianShield)
    self.assertIsNotNone(e)
    self.assert_point(e.pos[0], (50, 50))
    self.assertEqual(e.alliance, sc_raw.Self)
    self.assertEqual(e.owner, 1)
    self.assertGreater(e.radius, 3)

    e = get_effect_proto(obs[1], features.Effects.GuardianShield)
    self.assertIsNotNone(e)
    self.assert_point(e.pos[0], (50, 50))
    self.assertEqual(e.alliance, sc_raw.Enemy)
    self.assertEqual(e.owner, 1)
    self.assertGreater(e.radius, 3)

    # Should show up on the feature layers too.
    transformed_obs1 = self._features.transform_obs(obs[0])
    transformed_obs2 = self._features.transform_obs(obs[1])
    screen1 = transformed_obs1["feature_screen"]
    screen2 = transformed_obs2["feature_screen"]
    sentry_pos = _xy_locs(screen1.unit_type == units.Protoss.Sentry)[0]
    self.assert_layers(screen1, sentry_pos, unit_type=units.Protoss.Sentry,
                       effects=features.Effects.GuardianShield,
                       buffs=buffs.Buffs.GuardianShield)
    self.assert_layers(screen2, sentry_pos, unit_type=units.Protoss.Sentry,
                       effects=features.Effects.GuardianShield,
                       buffs=buffs.Buffs.GuardianShield)
    phoenix_pos = _xy_locs(screen1.unit_type == units.Protoss.Phoenix)[0]
    self.assert_layers(screen1, phoenix_pos, unit_type=units.Protoss.Phoenix,
                       effects=features.Effects.GuardianShield, buffs=0)
    self.assert_layers(screen2, phoenix_pos, unit_type=units.Protoss.Phoenix,
                       effects=features.Effects.GuardianShield, buffs=0)

    # Also in the raw_effects.
    raw1 = transformed_obs1["raw_effects"]
    e = get_effect_obs(raw1, features.Effects.GuardianShield)
    self.assertIsNotNone(e)
    # Not located at (50, 50) due to map shape and minimap coords.
    self.assertGreater(e.x, 40)
    self.assertGreater(e.y, 40)
    self.assertEqual(e.alliance, sc_raw.Self)
    self.assertEqual(e.owner, 1)
    self.assertGreater(e.radius, 3)

    self.raw_unit_command(1, "Effect_GravitonBeam_screen", pheonix.tag,
                          target=stalker.tag)

    self.step(32)
    obs = self.observe()

    self.assertIn(buffs.Buffs.GravitonBeam,
                  get_unit(obs[0], tag=stalker.tag).buff_ids)
    self.assertIn(buffs.Buffs.GravitonBeam,
                  get_unit(obs[1], tag=stalker.tag).buff_ids)
    self.assertNotIn(buffs.Buffs.GravitonBeam,
                     get_unit(obs[0], tag=sentry.tag).buff_ids)
    self.assertNotIn(buffs.Buffs.GravitonBeam,
                     get_unit(obs[1], tag=sentry.tag).buff_ids)
    self.assertNotIn(buffs.Buffs.GravitonBeam,
                     get_unit(obs[0], tag=pheonix.tag).buff_ids)
    self.assertNotIn(buffs.Buffs.GravitonBeam,
                     get_unit(obs[1], tag=pheonix.tag).buff_ids)

  @setup()
  def test_active(self):
    obs = self.observe()

    # P1 can see P2.
    self.create_unit(unit_type=units.Protoss.Observer, owner=1,
                     pos=get_unit(obs[1], unit_type=units.Protoss.Nexus).pos)

    self.step(32)  # Make sure visibility updates.
    obs = self.observe()

    for i, o in enumerate(obs):
      # Probes are active gathering
      for u in get_units(o, unit_type=units.Protoss.Probe).values():
        self.assert_unit(u, display_type=sc_raw.Visible, is_active=True)

      # Own Nexus is idle
      nexus = get_unit(o, unit_type=units.Protoss.Nexus, owner=i+1)
      self.assert_unit(nexus, display_type=sc_raw.Visible, is_active=False)
      self.assertEmpty(nexus.orders)

      # Give it an action.
      self.raw_unit_command(i, "Train_Probe_quick", nexus.tag)

    # P1 can tell P2's Nexus is idle.
    nexus = get_unit(obs[0], unit_type=units.Protoss.Nexus, owner=2)
    self.assert_unit(nexus, display_type=sc_raw.Visible, is_active=False)

    # Observer is idle.
    self.assert_unit(get_unit(obs[0], unit_type=units.Protoss.Observer),
                     display_type=sc_raw.Visible, is_active=False)
    self.assert_unit(get_unit(obs[1], unit_type=units.Protoss.Observer),
                     display_type=sc_raw.Hidden, is_active=False)

    self.step(32)
    obs = self.observe()

    # All Nexus are now active
    nexus0 = get_unit(obs[0], unit_type=units.Protoss.Nexus, owner=1)  # own
    nexus1 = get_unit(obs[0], unit_type=units.Protoss.Nexus, owner=2)  # other
    nexus2 = get_unit(obs[1], unit_type=units.Protoss.Nexus)
    self.assert_unit(nexus0, display_type=sc_raw.Visible, is_active=True)
    self.assert_unit(nexus1, display_type=sc_raw.Visible, is_active=True)
    self.assert_unit(nexus2, display_type=sc_raw.Visible, is_active=True)
    self.assertLen(nexus0.orders, 1)
    self.assertLen(nexus2.orders, 1)
    self.assertEmpty(nexus1.orders)  # Can't see opponent's orders

    # Go back to a snapshot
    self.kill_unit(get_unit(obs[0], unit_type=units.Protoss.Observer).tag)

    self.step(100)  # Make sure visibility updates.
    obs = self.observe()

    self.assertIsNone(get_unit(obs[0], unit_type=units.Protoss.Observer))

    # Own Nexus is now active, snapshot isn't.
    nexus0 = get_unit(obs[0], unit_type=units.Protoss.Nexus, owner=1)  # own
    nexus1 = get_unit(obs[0], unit_type=units.Protoss.Nexus, owner=2)  # other
    nexus2 = get_unit(obs[1], unit_type=units.Protoss.Nexus)
    self.assert_unit(nexus0, display_type=sc_raw.Visible, is_active=True)
    self.assert_unit(nexus1, display_type=sc_raw.Snapshot, is_active=False)
    self.assert_unit(nexus2, display_type=sc_raw.Visible, is_active=True)
    self.assertLen(nexus0.orders, 1)
    self.assertLen(nexus2.orders, 1)
    self.assertEmpty(nexus1.orders)  # Can't see opponent's orders

  @setup(disable_fog=True)
  def test_disable_fog(self):
    obs = self.observe()

    for i, o in enumerate(obs):
      # Probes are active gathering
      for u in get_units(o, unit_type=units.Protoss.Probe).values():
        self.assert_unit(u, display_type=sc_raw.Visible, is_active=True)

      # All Nexus are idle.
      own = get_unit(o, unit_type=units.Protoss.Nexus, owner=i+1)
      other = get_unit(o, unit_type=units.Protoss.Nexus, owner=2-i)
      self.assert_unit(own, display_type=sc_raw.Visible, is_active=False)
      self.assert_unit(other, display_type=sc_raw.Visible, is_active=False)
      self.assertEmpty(own.orders)
      self.assertEmpty(other.orders)

      # Give it an action.
      self.raw_unit_command(i, "Train_Probe_quick", own.tag)

    self.step(32)
    obs = self.observe()

    # All Nexus are active.
    for i, o in enumerate(obs):
      own = get_unit(o, unit_type=units.Protoss.Nexus, owner=i+1)
      other = get_unit(o, unit_type=units.Protoss.Nexus, owner=2-i)
      self.assert_unit(own, display_type=sc_raw.Visible, is_active=True)
      self.assert_unit(other, display_type=sc_raw.Visible, is_active=True)
      self.assertLen(own.orders, 1)
      self.assertEmpty(other.orders)


if __name__ == "__main__":
  absltest.main()
