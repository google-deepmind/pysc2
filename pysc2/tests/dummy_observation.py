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
"""For test code - build a dummy ResponseObservation proto.

This can then e.g. be passed to features.transform_obs.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math

import numpy as np
from pysc2.lib import features

from s2clientprotocol import raw_pb2
from s2clientprotocol import sc2api_pb2 as sc_pb


class Unit(object):
  """Class to hold unit data for the builder."""

  def __init__(
      self,
      unit_type,  # see lib/units.py
      player_relative,  # features.PlayerRelative,
      health,
      shields=0,
      energy=0,
      transport_slots_taken=0,
      build_progress=1.0):

    self.unit_type = unit_type
    self.player_relative = player_relative
    self.health = health
    self.shields = shields
    self.energy = energy
    self.transport_slots_taken = transport_slots_taken
    self.build_progress = build_progress

  def fill(self, unit_proto):
    """Fill a proto unit data object from this Unit."""
    unit_proto.unit_type = self.unit_type
    unit_proto.player_relative = self.player_relative
    unit_proto.health = self.health
    unit_proto.shields = self.shields
    unit_proto.energy = self.energy
    unit_proto.transport_slots_taken = self.transport_slots_taken
    unit_proto.build_progress = self.build_progress

  def as_array(self):
    """Return the unit represented as a numpy array."""
    return np.array([
        self.unit_type,
        self.player_relative,
        self.health,
        self.shields,
        self.energy,
        self.transport_slots_taken,
        int(self.build_progress * 100)
    ], dtype=np.int32)

  def as_dict(self):
    return vars(self)


class FeatureUnit(object):
  """Class to hold feature unit data for the builder."""

  def __init__(
      self,
      unit_type,  # see lib/units
      alliance,  # features.PlayerRelative,
      owner,  # 1-15, 16=neutral
      pos,  # common_pb2.Point,
      radius,
      health,
      health_max,
      is_on_screen,
      shield=0,
      shield_max=0,
      energy=0,
      energy_max=0,
      cargo_space_taken=0,
      cargo_space_max=0,
      build_progress=1.0,
      facing=0.0,
      display_type=raw_pb2.Visible,  # raw_pb.DisplayType
      cloak=raw_pb2.NotCloaked,  # raw_pb.CloakState
      is_selected=False,
      is_blip=False,
      is_powered=True,
      mineral_contents=0,
      vespene_contents=0,
      assigned_harvesters=0,
      ideal_harvesters=0,
      weapon_cooldown=0.0):

    self.unit_type = unit_type
    self.alliance = alliance
    self.owner = owner
    self.pos = pos
    self.radius = radius
    self.health = health
    self.health_max = health_max
    self.is_on_screen = is_on_screen
    self.shield = shield
    self.shield_max = shield_max
    self.energy = energy
    self.energy_max = energy_max
    self.cargo_space_taken = cargo_space_taken
    self.cargo_space_max = cargo_space_max
    self.build_progress = build_progress
    self.facing = facing
    self.display_type = display_type
    self.cloak = cloak
    self.is_selected = is_selected
    self.is_blip = is_blip
    self.is_powered = is_powered
    self.mineral_contents = mineral_contents
    self.vespene_contents = vespene_contents
    self.assigned_harvesters = assigned_harvesters
    self.ideal_harvesters = ideal_harvesters
    self.weapon_cooldown = weapon_cooldown

  def as_dict(self):
    return vars(self)


class Builder(object):
  """For test code - build a dummy ResponseObservation proto."""

  def __init__(self, obs_spec):
    self._obs_spec = obs_spec
    self._single_select = None
    self._multi_select = None
    self._feature_units = None

  def single_select(self, unit):
    self._single_select = unit
    return self

  def multi_select(self, units):
    self._multi_select = units
    return self

  def feature_units(self, feature_units):
    self._feature_units = feature_units
    return self

  def build(self):
    """Builds and returns a proto ResponseObservation."""
    response_observation = sc_pb.ResponseObservation()
    obs = response_observation.observation

    obs.game_loop = 1
    obs.player_common.player_id = 1
    obs.player_common.minerals = 20
    obs.player_common.vespene = 50
    obs.player_common.food_cap = 36
    obs.player_common.food_used = 21
    obs.player_common.food_army = 6
    obs.player_common.food_workers = 15
    obs.player_common.idle_worker_count = 2
    obs.player_common.army_count = 6
    obs.player_common.warp_gate_count = 0
    obs.player_common.larva_count = 0

    obs.abilities.add(ability_id=1, requires_point=True)  # Smart

    obs.score.score = 300
    score_details = obs.score.score_details
    score_details.idle_production_time = 0
    score_details.idle_worker_time = 0
    score_details.total_value_units = 190
    score_details.total_value_structures = 230
    score_details.killed_value_units = 0
    score_details.killed_value_structures = 0
    score_details.collected_minerals = 2130
    score_details.collected_vespene = 560
    score_details.collection_rate_minerals = 50
    score_details.collection_rate_vespene = 20
    score_details.spent_minerals = 2000
    score_details.spent_vespene = 500

    def fill(image_data, size, bits):
      image_data.bits_per_pixel = bits
      image_data.size.y = size[0]
      image_data.size.x = size[1]
      image_data.data = b'\0' * int(math.ceil(size[0] * size[1] * bits / 8))

    if 'feature_screen' in self._obs_spec:
      for feature in features.SCREEN_FEATURES:
        fill(getattr(obs.feature_layer_data.renders, feature.name),
             self._obs_spec['feature_screen'][1:], 8)

    if 'feature_minimap' in self._obs_spec:
      for feature in features.MINIMAP_FEATURES:
        fill(getattr(obs.feature_layer_data.minimap_renders, feature.name),
             self._obs_spec['feature_minimap'][1:], 8)

    if 'rgb_screen' in self._obs_spec:
      fill(obs.render_data.map, self._obs_spec['rgb_screen'][:2], 24)

    if 'rgb_minimap' in self._obs_spec:
      fill(obs.render_data.minimap, self._obs_spec['rgb_minimap'][:2], 24)

    if self._single_select:
      self._single_select.fill(obs.ui_data.single.unit)

    if self._multi_select:
      for unit in self._multi_select:
        obs.ui_data.multi.units.add(**unit.as_dict())

    if self._feature_units:
      for feature_unit in self._feature_units:
        obs.raw_data.units.add(**feature_unit.as_dict())

    return response_observation
