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

from absl.testing import absltest

from pysc2.lib import actions
from pysc2.lib import buffs
from pysc2.lib import features
from pysc2.lib import units
from pysc2.tests import utils

from s2clientprotocol import debug_pb2 as sc_debug
from s2clientprotocol import raw_pb2 as sc_raw


# It seems the time from issuing an action until it has an effect is 2 frames.
# It'd be nice if that was faster, and it is 1 in single-player, but in
# multi-player it seems it needs to be propagated to the host and back, which
# takes 2 steps minimum. Unfortunately this also includes camera moves.
EXPECTED_ACTION_DELAY = 2


class ObsTest(utils.GameReplayTestCase):

  @utils.GameReplayTestCase.setup()
  def test_hallucination(self):
    self.god()

    # Create some sentries.
    self.create_unit(unit_type=units.Protoss.Sentry, owner=1, pos=(30, 30))
    self.create_unit(unit_type=units.Protoss.Sentry, owner=2, pos=(30, 28))

    self.step()
    obs = self.observe()

    # Give one enough energy.
    tag = utils.get_unit(obs[0], unit_type=units.Protoss.Sentry, owner=1).tag
    self.debug(unit_value=sc_debug.DebugSetUnitValue(
        unit_value=sc_debug.DebugSetUnitValue.Energy, value=200, unit_tag=tag))

    self.step()
    obs = self.observe()

    # Create a hallucinated archon.
    self.raw_unit_command(0, "Hallucination_Archon_quick", tag)

    self.step()
    obs = self.observe()

    # Verify the owner knows it's a hallucination, but the opponent doesn't.
    p1 = utils.get_unit(obs[0], unit_type=units.Protoss.Archon)
    p2 = utils.get_unit(obs[1], unit_type=units.Protoss.Archon)
    self.assertTrue(p1.is_hallucination)
    self.assertFalse(p2.is_hallucination)

    # Create an observer so the opponent has detection.
    self.create_unit(unit_type=units.Protoss.Observer, owner=2, pos=(28, 30))

    self.step()
    obs = self.observe()

    # Verify the opponent now also knows it's a hallucination.
    p1 = utils.get_unit(obs[0], unit_type=units.Protoss.Archon)
    p2 = utils.get_unit(obs[1], unit_type=units.Protoss.Archon)
    self.assertTrue(p1.is_hallucination)
    self.assertTrue(p2.is_hallucination)

  @utils.GameReplayTestCase.setup(show_cloaked=False)
  def test_hide_cloaked(self):
    self.assertFalse(self._info.options.show_cloaked)

    self.god()
    self.move_camera(32, 32)

    # Create some units. One cloaked, one to see it without detection.
    self.create_unit(unit_type=units.Protoss.DarkTemplar, owner=1, pos=(30, 30))
    self.create_unit(unit_type=units.Protoss.Sentry, owner=2, pos=(28, 30))

    self.step(16)
    obs = self.observe()

    # Verify both can see it, but that only the owner knows details.
    p1 = utils.get_unit(obs[0], unit_type=units.Protoss.DarkTemplar)
    p2 = utils.get_unit(obs[1], unit_type=units.Protoss.DarkTemplar)

    self.assert_unit(p1, display_type=sc_raw.Visible, health=40, shield=80,
                     cloak=sc_raw.CloakedAllied)
    self.assertIsNone(p2)

    screen1 = self._features.transform_obs(obs[0])["feature_screen"]
    screen2 = self._features.transform_obs(obs[1])["feature_screen"]
    dt = utils.xy_locs(screen1.unit_type == units.Protoss.DarkTemplar)[0]
    self.assert_layers(screen1, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=40, unit_shields=80, cloaked=1)
    self.assert_layers(screen2, dt, unit_type=0,
                       unit_hit_points=0, unit_shields=0, cloaked=0)

    # Create an observer so the opponent has detection.
    self.create_unit(unit_type=units.Protoss.Observer, owner=2, pos=(28, 28))

    self.step(16)  # It takes a few frames for the observer to detect.
    obs = self.observe()

    # Verify both can see it, with the same details
    p1 = utils.get_unit(obs[0], unit_type=units.Protoss.DarkTemplar)
    p2 = utils.get_unit(obs[1], unit_type=units.Protoss.DarkTemplar)
    self.assert_unit(p1, display_type=sc_raw.Visible, health=40, shield=80,
                     cloak=sc_raw.CloakedAllied)
    self.assert_unit(p2, display_type=sc_raw.Visible, health=40, shield=80,
                     cloak=sc_raw.CloakedDetected)

    screen1 = self._features.transform_obs(obs[0])["feature_screen"]
    screen2 = self._features.transform_obs(obs[1])["feature_screen"]
    dt = utils.xy_locs(screen1.unit_type == units.Protoss.DarkTemplar)[0]
    self.assert_layers(screen1, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=40, unit_shields=80, cloaked=1)
    self.assert_layers(screen2, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=40, unit_shields=80, cloaked=1)

  @utils.GameReplayTestCase.setup()
  def test_show_cloaked(self):
    self.assertTrue(self._info.options.show_cloaked)

    self.god()
    self.move_camera(32, 32)

    # Create some units. One cloaked, one to see it without detection.
    self.create_unit(unit_type=units.Protoss.DarkTemplar, owner=1, pos=(30, 30))
    self.create_unit(unit_type=units.Protoss.Sentry, owner=2, pos=(28, 30))

    self.step(16)
    obs = self.observe()

    # Verify both can see it, but that only the owner knows details.
    p1 = utils.get_unit(obs[0], unit_type=units.Protoss.DarkTemplar)
    p2 = utils.get_unit(obs[1], unit_type=units.Protoss.DarkTemplar)

    self.assert_unit(p1, display_type=sc_raw.Visible, health=40, shield=80,
                     cloak=sc_raw.CloakedAllied)
    self.assert_unit(p2, display_type=sc_raw.Hidden, health=0, shield=0,
                     cloak=sc_raw.Cloaked)

    screen1 = self._features.transform_obs(obs[0])["feature_screen"]
    screen2 = self._features.transform_obs(obs[1])["feature_screen"]
    dt = utils.xy_locs(screen1.unit_type == units.Protoss.DarkTemplar)[0]
    self.assert_layers(screen1, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=40, unit_shields=80, cloaked=1)
    self.assert_layers(screen2, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=0, unit_shields=0, cloaked=1)

    # Create an observer so the opponent has detection.
    self.create_unit(unit_type=units.Protoss.Observer, owner=2, pos=(28, 28))

    self.step(16)  # It takes a few frames for the observer to detect.
    obs = self.observe()

    # Verify both can see it, with the same details
    p1 = utils.get_unit(obs[0], unit_type=units.Protoss.DarkTemplar)
    p2 = utils.get_unit(obs[1], unit_type=units.Protoss.DarkTemplar)
    self.assert_unit(p1, display_type=sc_raw.Visible, health=40, shield=80,
                     cloak=sc_raw.CloakedAllied)
    self.assert_unit(p2, display_type=sc_raw.Visible, health=40, shield=80,
                     cloak=sc_raw.CloakedDetected)

    screen1 = self._features.transform_obs(obs[0])["feature_screen"]
    screen2 = self._features.transform_obs(obs[1])["feature_screen"]
    dt = utils.xy_locs(screen1.unit_type == units.Protoss.DarkTemplar)[0]
    self.assert_layers(screen1, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=40, unit_shields=80, cloaked=1)
    self.assert_layers(screen2, dt, unit_type=units.Protoss.DarkTemplar,
                       unit_hit_points=40, unit_shields=80, cloaked=1)

  @utils.GameReplayTestCase.setup()
  def test_pos(self):
    self.create_unit(unit_type=units.Protoss.Archon, owner=1, pos=(20, 30))
    self.create_unit(unit_type=units.Protoss.Observer, owner=1, pos=(40, 30))

    self.step()
    obs = self.observe()

    archon = utils.get_unit(obs[0], unit_type=units.Protoss.Archon)
    observer = utils.get_unit(obs[0], unit_type=units.Protoss.Observer)

    self.assert_point(archon.pos, (20, 30))
    self.assert_point(observer.pos, (40, 30))
    self.assertLess(archon.pos.z, observer.pos.z)  # The observer flies.
    self.assertGreater(archon.radius, observer.radius)

    # Move them towards the center, make sure they move.
    self.raw_unit_command(0, "Move_screen", (archon.tag, observer.tag),
                          (30, 25))

    self.step(40)
    obs2 = self.observe()

    archon2 = utils.get_unit(obs2[0], unit_type=units.Protoss.Archon)
    observer2 = utils.get_unit(obs2[0], unit_type=units.Protoss.Observer)

    self.assertGreater(archon2.pos.x, 20)
    self.assertLess(observer2.pos.x, 40)
    self.assertLess(archon2.pos.z, observer2.pos.z)

  @utils.GameReplayTestCase.setup()
  def test_fog(self):
    obs = self.observe()

    def assert_visible(unit, display_type, alliance, cloak):
      self.assert_unit(unit, display_type=display_type, alliance=alliance,
                       cloak=cloak)

    self.create_unit(unit_type=units.Protoss.Sentry, owner=1, pos=(30, 32))
    self.create_unit(unit_type=units.Protoss.DarkTemplar, owner=1, pos=(32, 32))

    self.step()
    obs = self.observe()

    assert_visible(utils.get_unit(obs[0], unit_type=units.Protoss.Sentry),
                   sc_raw.Visible, sc_raw.Self, sc_raw.NotCloaked)
    assert_visible(utils.get_unit(obs[0], unit_type=units.Protoss.DarkTemplar),
                   sc_raw.Visible, sc_raw.Self, sc_raw.CloakedAllied)
    self.assertIsNone(utils.get_unit(obs[1], unit_type=units.Protoss.Sentry))
    self.assertIsNone(utils.get_unit(obs[1],
                                     unit_type=units.Protoss.DarkTemplar))

    obs = self.observe(disable_fog=True)

    assert_visible(utils.get_unit(obs[0], unit_type=units.Protoss.Sentry),
                   sc_raw.Visible, sc_raw.Self, sc_raw.NotCloaked)
    assert_visible(utils.get_unit(obs[0], unit_type=units.Protoss.DarkTemplar),
                   sc_raw.Visible, sc_raw.Self, sc_raw.CloakedAllied)
    assert_visible(utils.get_unit(obs[1], unit_type=units.Protoss.Sentry),
                   sc_raw.Hidden, sc_raw.Enemy, sc_raw.CloakedUnknown)
    assert_visible(utils.get_unit(obs[1], unit_type=units.Protoss.DarkTemplar),
                   sc_raw.Hidden, sc_raw.Enemy, sc_raw.CloakedUnknown)

  @utils.GameReplayTestCase.setup()
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
    self.create_unit(unit_type=units.Protoss.Sentry, owner=1, pos=(30, 30))
    self.create_unit(unit_type=units.Protoss.Stalker, owner=1, pos=(28, 30))
    self.create_unit(unit_type=units.Protoss.Phoenix, owner=2, pos=(30, 28))

    self.step()
    obs = self.observe()

    # Give enough energy.
    sentry = utils.get_unit(obs[0], unit_type=units.Protoss.Sentry)
    stalker = utils.get_unit(obs[0], unit_type=units.Protoss.Stalker)
    pheonix = utils.get_unit(obs[0], unit_type=units.Protoss.Phoenix)
    self.set_energy(sentry.tag, 200)
    self.set_energy(pheonix.tag, 200)

    self.step()
    obs = self.observe()

    self.raw_unit_command(0, "Effect_GuardianShield_quick", sentry.tag)

    self.step(16)
    obs = self.observe()

    self.assertIn(buffs.Buffs.GuardianShield,
                  utils.get_unit(obs[0], tag=sentry.tag).buff_ids)
    self.assertIn(buffs.Buffs.GuardianShield,
                  utils.get_unit(obs[1], tag=sentry.tag).buff_ids)
    self.assertIn(buffs.Buffs.GuardianShield,
                  utils.get_unit(obs[0], tag=stalker.tag).buff_ids)
    self.assertIn(buffs.Buffs.GuardianShield,
                  utils.get_unit(obs[1], tag=stalker.tag).buff_ids)
    self.assertNotIn(buffs.Buffs.GuardianShield,
                     utils.get_unit(obs[0], tag=pheonix.tag).buff_ids)
    self.assertNotIn(buffs.Buffs.GuardianShield,
                     utils.get_unit(obs[1], tag=pheonix.tag).buff_ids)

    # Both players should see the shield.
    e = get_effect_proto(obs[0], features.Effects.GuardianShield)
    self.assertIsNotNone(e)
    self.assert_point(e.pos[0], (30, 30))
    self.assertEqual(e.alliance, sc_raw.Self)
    self.assertEqual(e.owner, 1)
    self.assertGreater(e.radius, 3)

    e = get_effect_proto(obs[1], features.Effects.GuardianShield)
    self.assertIsNotNone(e)
    self.assert_point(e.pos[0], (30, 30))
    self.assertEqual(e.alliance, sc_raw.Enemy)
    self.assertEqual(e.owner, 1)
    self.assertGreater(e.radius, 3)

    # Should show up on the feature layers too.
    transformed_obs1 = self._features.transform_obs(obs[0])
    transformed_obs2 = self._features.transform_obs(obs[1])
    screen1 = transformed_obs1["feature_screen"]
    screen2 = transformed_obs2["feature_screen"]
    sentry_pos = utils.xy_locs(screen1.unit_type == units.Protoss.Sentry)[0]
    self.assert_layers(screen1, sentry_pos, unit_type=units.Protoss.Sentry,
                       effects=features.Effects.GuardianShield,
                       buffs=buffs.Buffs.GuardianShield)
    self.assert_layers(screen2, sentry_pos, unit_type=units.Protoss.Sentry,
                       effects=features.Effects.GuardianShield,
                       buffs=buffs.Buffs.GuardianShield)
    phoenix_pos = utils.xy_locs(screen1.unit_type == units.Protoss.Phoenix)[0]
    self.assert_layers(screen1, phoenix_pos, unit_type=units.Protoss.Phoenix,
                       effects=features.Effects.GuardianShield, buffs=0)
    self.assert_layers(screen2, phoenix_pos, unit_type=units.Protoss.Phoenix,
                       effects=features.Effects.GuardianShield, buffs=0)

    # Also in the raw_effects.
    raw1 = transformed_obs1["raw_effects"]
    e = get_effect_obs(raw1, features.Effects.GuardianShield)
    self.assertIsNotNone(e)
    # Not located at (30, 30) due to map shape and minimap coords.
    self.assertGreater(e.x, 20)
    self.assertGreater(e.y, 20)
    self.assertEqual(e.alliance, sc_raw.Self)
    self.assertEqual(e.owner, 1)
    self.assertGreater(e.radius, 3)

    self.raw_unit_command(1, "Effect_GravitonBeam_screen", pheonix.tag,
                          target=stalker.tag)

    self.step(32)
    obs = self.observe()

    self.assertIn(buffs.Buffs.GravitonBeam,
                  utils.get_unit(obs[0], tag=stalker.tag).buff_ids)
    self.assertIn(buffs.Buffs.GravitonBeam,
                  utils.get_unit(obs[1], tag=stalker.tag).buff_ids)
    self.assertNotIn(buffs.Buffs.GravitonBeam,
                     utils.get_unit(obs[0], tag=sentry.tag).buff_ids)
    self.assertNotIn(buffs.Buffs.GravitonBeam,
                     utils.get_unit(obs[1], tag=sentry.tag).buff_ids)
    self.assertNotIn(buffs.Buffs.GravitonBeam,
                     utils.get_unit(obs[0], tag=pheonix.tag).buff_ids)
    self.assertNotIn(buffs.Buffs.GravitonBeam,
                     utils.get_unit(obs[1], tag=pheonix.tag).buff_ids)

  @utils.GameReplayTestCase.setup()
  def test_active(self):
    obs = self.observe()

    # P1 can see P2.
    self.create_unit(
        unit_type=units.Protoss.Observer, owner=1,
        pos=utils.get_unit(obs[1], unit_type=units.Protoss.Nexus).pos)

    self.step(32)  # Make sure visibility updates.
    obs = self.observe()

    for i, o in enumerate(obs):
      # Probes are active gathering
      for u in utils.get_units(o, unit_type=units.Protoss.Probe).values():
        self.assert_unit(u, display_type=sc_raw.Visible, is_active=True)

      # Own Nexus is idle
      nexus = utils.get_unit(o, unit_type=units.Protoss.Nexus, owner=i+1)
      self.assert_unit(nexus, display_type=sc_raw.Visible, is_active=False)
      self.assertEmpty(nexus.orders)

      # Give it an action.
      self.raw_unit_command(i, "Train_Probe_quick", nexus.tag)

    # P1 can tell P2's Nexus is idle.
    nexus = utils.get_unit(obs[0], unit_type=units.Protoss.Nexus, owner=2)
    self.assert_unit(nexus, display_type=sc_raw.Visible, is_active=False)

    # Observer is idle.
    self.assert_unit(utils.get_unit(obs[0], unit_type=units.Protoss.Observer),
                     display_type=sc_raw.Visible, is_active=False)
    self.assert_unit(utils.get_unit(obs[1], unit_type=units.Protoss.Observer),
                     display_type=sc_raw.Hidden, is_active=False)

    self.step(32)
    obs = self.observe()

    # All Nexus are now active
    nexus0 = utils.get_unit(obs[0], unit_type=units.Protoss.Nexus, owner=1)
    nexus1 = utils.get_unit(obs[0], unit_type=units.Protoss.Nexus, owner=2)
    nexus2 = utils.get_unit(obs[1], unit_type=units.Protoss.Nexus)
    self.assert_unit(nexus0, display_type=sc_raw.Visible, is_active=True)
    self.assert_unit(nexus1, display_type=sc_raw.Visible, is_active=True)
    self.assert_unit(nexus2, display_type=sc_raw.Visible, is_active=True)
    self.assertLen(nexus0.orders, 1)
    self.assertLen(nexus2.orders, 1)
    self.assertEmpty(nexus1.orders)  # Can't see opponent's orders

    # Go back to a snapshot
    self.kill_unit(utils.get_unit(obs[0], unit_type=units.Protoss.Observer).tag)

    self.step(100)  # Make sure visibility updates.
    obs = self.observe()

    self.assertIsNone(utils.get_unit(obs[0], unit_type=units.Protoss.Observer))

    # Own Nexus is now active, snapshot isn't.
    nexus0 = utils.get_unit(obs[0], unit_type=units.Protoss.Nexus, owner=1)
    nexus1 = utils.get_unit(obs[0], unit_type=units.Protoss.Nexus, owner=2)
    nexus2 = utils.get_unit(obs[1], unit_type=units.Protoss.Nexus)
    self.assert_unit(nexus0, display_type=sc_raw.Visible, is_active=True)
    self.assert_unit(nexus1, display_type=sc_raw.Snapshot, is_active=False)
    self.assert_unit(nexus2, display_type=sc_raw.Visible, is_active=True)
    self.assertLen(nexus0.orders, 1)
    self.assertLen(nexus2.orders, 1)
    self.assertEmpty(nexus1.orders)  # Can't see opponent's orders

  @utils.GameReplayTestCase.setup(disable_fog=True)
  def test_disable_fog(self):
    obs = self.observe()

    for i, o in enumerate(obs):
      # Probes are active gathering
      for u in utils.get_units(o, unit_type=units.Protoss.Probe).values():
        self.assert_unit(u, display_type=sc_raw.Visible, is_active=True)

      # All Nexus are idle.
      own = utils.get_unit(o, unit_type=units.Protoss.Nexus, owner=i+1)
      other = utils.get_unit(o, unit_type=units.Protoss.Nexus, owner=2-i)
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
      own = utils.get_unit(o, unit_type=units.Protoss.Nexus, owner=i+1)
      other = utils.get_unit(o, unit_type=units.Protoss.Nexus, owner=2-i)
      self.assert_unit(own, display_type=sc_raw.Visible, is_active=True)
      self.assert_unit(other, display_type=sc_raw.Visible, is_active=True)
      self.assertLen(own.orders, 1)
      self.assertEmpty(other.orders)

  @utils.GameReplayTestCase.setup()
  def test_action_delay(self):
    self.observe()
    self.create_unit(unit_type=units.Protoss.Zealot, owner=1, pos=(32, 32))

    self.step(16)
    obs1 = self.observe()
    self.assertLen(obs1[0].actions, 0)

    zealot1 = utils.get_unit(obs1[0], unit_type=units.Protoss.Zealot, owner=1)
    self.assertLen(zealot1.orders, 0)

    self.raw_unit_command(0, "Move_screen", zealot1.tag, (30, 30))

    # If the delay is taken down to 1, remove this first step of verifying the
    # actions length is 0.
    self.assertEqual(EXPECTED_ACTION_DELAY, 2)

    self.step(1)
    obs2 = self.observe()
    self.assertLen(obs2[0].action_errors, 0)
    self.assertLen(obs2[0].actions, 0)

    self.step(1)
    obs2 = self.observe()
    self.assertLen(obs2[0].action_errors, 0)
    self.assertGreaterEqual(len(obs2[0].actions), 1)
    for action in obs2[0].actions:
      if action.HasField("action_raw"):
        break
    else:
      self.assertFalse("No raw action found")

    self.assertEqual(action.game_loop, obs1[0].observation.game_loop+1)  # pylint: disable=undefined-loop-variable
    unit_command = action.action_raw.unit_command  # pylint: disable=undefined-loop-variable
    self.assertEqual(unit_command.ability_id,
                     actions.FUNCTIONS.Move_Move_screen.ability_id)
    self.assert_point(unit_command.target_world_space_pos, (30, 30))
    self.assertEqual(unit_command.unit_tags[0], zealot1.tag)

    zealot2 = utils.get_unit(obs2[0], unit_type=units.Protoss.Zealot, owner=1)
    self.assertLen(zealot2.orders, 1)
    self.assertEqual(zealot2.orders[0].ability_id,
                     actions.FUNCTIONS.Move_Move_screen.ability_id)
    self.assert_point(zealot2.orders[0].target_world_space_pos, (30, 30))

  @utils.GameReplayTestCase.setup()
  def test_camera_movement_delay(self):
    obs1 = self.observe()
    screen1 = self._features.transform_obs(obs1[0])["feature_screen"]
    nexus1 = utils.xy_locs(screen1.unit_type == units.Protoss.Nexus)

    self.step(1)
    obs2 = self.observe()
    screen2 = self._features.transform_obs(obs2[0])["feature_screen"]
    nexus2 = utils.xy_locs(screen2.unit_type == units.Protoss.Nexus)

    self.assertEqual(nexus1, nexus2)  # Same place.

    loc = obs1[0].observation.raw_data.player.camera
    self.move_camera(loc.x + 3, loc.y + 3)

    self.step(EXPECTED_ACTION_DELAY + 1)

    obs3 = self.observe()
    screen3 = self._features.transform_obs(obs3[0])["feature_screen"]
    nexus3 = utils.xy_locs(screen3.unit_type == units.Protoss.Nexus)

    self.assertNotEqual(nexus1, nexus3)  # Different location due to camera.


if __name__ == "__main__":
  absltest.main()
