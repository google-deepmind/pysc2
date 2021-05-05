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
"""Test that various actions do what you'd expect."""


from absl.testing import absltest

from pysc2.lib import actions
from pysc2.lib import units
from pysc2.tests import utils


def raw_ability_ids(obs):
  return list(filter(None, (a.action_raw.unit_command.ability_id
                            for a in obs.actions)))


class ActionsTest(utils.GameReplayTestCase):

  @utils.GameReplayTestCase.setup()
  def test_general_attack(self):
    self.create_unit(unit_type=units.Protoss.Zealot, owner=1, pos=(30, 30))
    self.create_unit(unit_type=units.Protoss.Observer, owner=1, pos=(30, 30))

    self.step()
    obs = self.observe()

    zealot = utils.get_unit(obs[0], unit_type=units.Protoss.Zealot)
    observer = utils.get_unit(obs[0], unit_type=units.Protoss.Observer)

    self.raw_unit_command(0, "Attack_screen", (zealot.tag, observer.tag),
                          (32, 32))

    self.step(64)
    obs = self.observe()

    zealot = utils.get_unit(obs[0], unit_type=units.Protoss.Zealot)
    observer = utils.get_unit(obs[0], unit_type=units.Protoss.Observer)
    self.assert_point(zealot.pos, (32, 32))
    self.assert_point(observer.pos, (32, 32))
    self.assertEqual(
        raw_ability_ids(obs[0]),
        [actions.FUNCTIONS.Attack_Attack_screen.ability_id])

    self.raw_unit_command(0, "Attack_screen", zealot.tag, (34, 34))

    self.step(64)
    obs = self.observe()

    zealot = utils.get_unit(obs[0], unit_type=units.Protoss.Zealot)
    observer = utils.get_unit(obs[0], unit_type=units.Protoss.Observer)
    self.assert_point(zealot.pos, (34, 34))
    self.assert_point(observer.pos, (32, 32))
    self.assertEqual(
        raw_ability_ids(obs[0]),
        [actions.FUNCTIONS.Attack_Attack_screen.ability_id])

    self.raw_unit_command(0, "Attack_screen", observer.tag, (34, 34))

    self.step(64)
    obs = self.observe()
    zealot = utils.get_unit(obs[0], unit_type=units.Protoss.Zealot)
    observer = utils.get_unit(obs[0], unit_type=units.Protoss.Observer)
    self.assert_point(zealot.pos, (34, 34))
    self.assert_point(observer.pos, (34, 34))
    self.assertEqual(
        raw_ability_ids(obs[0]),
        [actions.FUNCTIONS.Scan_Move_screen.ability_id])


if __name__ == "__main__":
  absltest.main()
