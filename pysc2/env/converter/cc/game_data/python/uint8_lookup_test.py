# Copyright 2021 DeepMind Technologies Ltd. All rights reserved.
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

from absl.testing import absltest
from pysc2.env.converter.cc.game_data.proto import buffs_pb2
from pysc2.env.converter.cc.game_data.proto import units_pb2
from pysc2.env.converter.cc.game_data.proto import upgrades_pb2
from pysc2.env.converter.cc.game_data.python import uint8_lookup


class Uint8LookupTest(absltest.TestCase):

  def test_pysc2_to_uint8(self):
    self.assertEqual(
        uint8_lookup.PySc2ToUint8(units_pb2.Zerg.InfestedTerran), 4)

  def test_pysc2_to_uint8_buffs(self):
    self.assertEqual(
        uint8_lookup.PySc2ToUint8Buffs(buffs_pb2.Buffs.BlindingCloudStructure),
        3)

  def test_pysc2_to_uint8_upgrades(self):
    self.assertEqual(
        uint8_lookup.PySc2ToUint8Upgrades(upgrades_pb2.Upgrades.Blink), 5)

  def test_uint8_to_pysc2(self):
    self.assertEqual(
        uint8_lookup.Uint8ToPySc2(4), units_pb2.Zerg.InfestedTerran)

  def test_uint8_to_pysc2_upgrades(self):
    self.assertEqual(
        uint8_lookup.Uint8ToPySc2Upgrades(5), upgrades_pb2.Upgrades.Blink)

  def test_effect_id_identity(self):
    self.assertEqual(uint8_lookup.EffectIdIdentity(17), 17)


if __name__ == '__main__':
  absltest.main()
