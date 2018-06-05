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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest

from pysc2.lib import actions
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import units
from pysc2.tests import dummy_observation

from s2clientprotocol import common_pb2


_PROBE = dummy_observation.Unit(
    units.Protoss.Probe, features.PlayerRelative.SELF, 20, 20, 0, 0, 1.0)

_ZEALOT = dummy_observation.Unit(
    units.Protoss.Zealot, features.PlayerRelative.SELF, 100, 50, 0, 0, 1.0)

_MOTHERSHIP = dummy_observation.Unit(
    units.Protoss.Mothership, features.PlayerRelative.SELF, 350, 7, 200, 0, 1.0)


class DummyObservationTest(absltest.TestCase):

  def setUp(self):
    self._features = features.Features(
        features.AgentInterfaceFormat(
            feature_dimensions=features.Dimensions(
                screen=(64, 60), minimap=(32, 28)),
            rgb_dimensions=features.Dimensions(
                screen=(128, 124), minimap=(64, 60)),
            action_space=actions.ActionSpace.FEATURES,
            use_feature_units=True
        ),
        map_size=point.Point(256, 256)
    )
    self._obs_spec = self._features.observation_spec()
    self._builder = dummy_observation.Builder(self._obs_spec)

  def testFeatureScreenMatchesSpec(self):
    obs = self._get_obs()
    for f in features.SCREEN_FEATURES:
      self._check_layer(
          getattr(obs.feature_layer_data.renders, f.name), 64, 60, 8)

  def testFeatureMinimapMatchesSpec(self):
    obs = self._get_obs()
    for f in features.MINIMAP_FEATURES:
      self._check_layer(
          getattr(obs.feature_layer_data.minimap_renders, f.name), 32, 28, 8)

  def testRgbScreenMatchesSpec(self):
    obs = self._get_obs()
    self._check_layer(obs.render_data.map, 128, 124, 24)

  def testRgbMinimapMatchesSpec(self):
    obs = self._get_obs()
    self._check_layer(obs.render_data.minimap, 64, 60, 24)

  def testNoSingleSelect(self):
    obs = self._get_obs()
    self.assertFalse(obs.ui_data.HasField("single"))

  def testWithSingleSelect(self):
    self._builder.single_select(_PROBE)
    obs = self._get_obs()
    self._check_unit(obs.ui_data.single.unit, _PROBE)

  def testNoMultiSelect(self):
    obs = self._get_obs()
    self.assertFalse(obs.ui_data.HasField("multi"))

  def testWithMultiSelect(self):
    nits = [_MOTHERSHIP, _PROBE, _PROBE, _ZEALOT]
    self._builder.multi_select(nits)
    obs = self._get_obs()
    for proto, builder in zip(obs.ui_data.multi.units, nits):
      self._check_unit(proto, builder)

  def testFeatureUnitsAreAdded(self):
    feature_units = [
        dummy_observation.FeatureUnit(
            units.Protoss.Probe,
            features.PlayerRelative.SELF,
            owner=1,
            pos=common_pb2.Point(x=10, y=10, z=0),
            radius=1.0,
            health=10,
            health_max=20,
            is_on_screen=True,
            shield=0,
            shield_max=20
        ),
        dummy_observation.FeatureUnit(
            units.Terran.Marine,
            features.PlayerRelative.SELF,
            owner=1,
            pos=common_pb2.Point(x=11, y=12, z=0),
            radius=1.0,
            health=35,
            health_max=45,
            is_on_screen=True,
            shield=0,
            shield_max=0
        )
    ]

    self._builder.feature_units(feature_units)

    obs = self._get_obs()
    for proto, builder in zip(obs.raw_data.units, feature_units):
      self._check_feature_unit(proto, builder)

  def _get_obs(self):
    return self._builder.build().observation

  def _check_layer(self, layer, x, y, bits):
    self.assertEqual(layer.size.x, x)
    self.assertEqual(layer.size.y, y)
    self.assertEqual(layer.bits_per_pixel, bits)

  def _check_attributes_match(self, a, b, attributes):
    for attribute in attributes:
      self.assertEqual(getattr(a, attribute), getattr(b, attribute))

  def _check_unit(self, proto, builder):
    return self._check_attributes_match(proto, builder, vars(builder).keys())

  def _check_feature_unit(self, proto, builder):
    return self._check_attributes_match(proto, builder, [
        "unit_type",
        "alliance",
        "owner",
        "pos",
        "radius",
        "health",
        "health_max",
        "is_on_screen",
        "shield",
        "shield_max"
    ])


if __name__ == "__main__":
  absltest.main()
