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
"""Render feature layers from SC2 Observation protos into numpy arrays."""
# pylint: disable=g-complex-comprehension

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
from absl import logging
import random

import enum
import numpy as np
import six
from pysc2.lib import actions
from pysc2.lib import colors
from pysc2.lib import named_array
from pysc2.lib import point
from pysc2.lib import static_data
from pysc2.lib import stopwatch
from pysc2.lib import transform

from s2clientprotocol import raw_pb2 as sc_raw
from s2clientprotocol import sc2api_pb2 as sc_pb

sw = stopwatch.sw

EPSILON = 1e-5


class FeatureType(enum.Enum):
  SCALAR = 1
  CATEGORICAL = 2


class PlayerRelative(enum.IntEnum):
  """The values for the `player_relative` feature layers."""
  NONE = 0
  SELF = 1
  ALLY = 2
  NEUTRAL = 3
  ENEMY = 4


class Visibility(enum.IntEnum):
  """Values for the `visibility` feature layers."""
  HIDDEN = 0
  SEEN = 1
  VISIBLE = 2


class Effects(enum.IntEnum):
  """Values for the `effects` feature layer."""
  # pylint: disable=invalid-name
  none = 0
  PsiStorm = 1
  GuardianShield = 2
  TemporalFieldGrowing = 3
  TemporalField = 4
  ThermalLance = 5
  ScannerSweep = 6
  NukeDot = 7
  LiberatorDefenderZoneSetup = 8
  LiberatorDefenderZone = 9
  BlindingCloud = 10
  CorrosiveBile = 11
  LurkerSpines = 12
  # pylint: enable=invalid-name


class ScoreCumulative(enum.IntEnum):
  """Indices into the `score_cumulative` observation."""
  score = 0
  idle_production_time = 1
  idle_worker_time = 2
  total_value_units = 3
  total_value_structures = 4
  killed_value_units = 5
  killed_value_structures = 6
  collected_minerals = 7
  collected_vespene = 8
  collection_rate_minerals = 9
  collection_rate_vespene = 10
  spent_minerals = 11
  spent_vespene = 12


class ScoreByCategory(enum.IntEnum):
  """Indices for the `score_by_category` observation's first dimension."""
  food_used = 0
  killed_minerals = 1
  killed_vespene = 2
  lost_minerals = 3
  lost_vespene = 4
  friendly_fire_minerals = 5
  friendly_fire_vespene = 6
  used_minerals = 7
  used_vespene = 8
  total_used_minerals = 9
  total_used_vespene = 10


class ScoreCategories(enum.IntEnum):
  """Indices for the `score_by_category` observation's second dimension."""
  none = 0
  army = 1
  economy = 2
  technology = 3
  upgrade = 4


class ScoreByVital(enum.IntEnum):
  """Indices for the `score_by_vital` observation's first dimension."""
  total_damage_dealt = 0
  total_damage_taken = 1
  total_healed = 2


class ScoreVitals(enum.IntEnum):
  """Indices for the `score_by_vital` observation's second dimension."""
  life = 0
  shields = 1
  energy = 2


class Player(enum.IntEnum):
  """Indices into the `player` observation."""
  player_id = 0
  minerals = 1
  vespene = 2
  food_used = 3
  food_cap = 4
  food_army = 5
  food_workers = 6
  idle_worker_count = 7
  army_count = 8
  warp_gate_count = 9
  larva_count = 10


class UnitLayer(enum.IntEnum):
  """Indices into the unit layers in the observations."""
  unit_type = 0
  player_relative = 1
  health = 2
  shields = 3
  energy = 4
  transport_slots_taken = 5
  build_progress = 6


class UnitCounts(enum.IntEnum):
  """Indices into the `unit_counts` observations."""
  unit_type = 0
  count = 1


class FeatureUnit(enum.IntEnum):
  """Indices for the `feature_unit` observations."""
  unit_type = 0
  alliance = 1
  health = 2
  shield = 3
  energy = 4
  cargo_space_taken = 5
  build_progress = 6
  health_ratio = 7
  shield_ratio = 8
  energy_ratio = 9
  display_type = 10
  owner = 11
  x = 12
  y = 13
  facing = 14
  radius = 15
  cloak = 16
  is_selected = 17
  is_blip = 18
  is_powered = 19
  mineral_contents = 20
  vespene_contents = 21
  cargo_space_max = 22
  assigned_harvesters = 23
  ideal_harvesters = 24
  weapon_cooldown = 25
  order_length = 26  # If zero, the unit is idle.
  order_id_0 = 27
  order_id_1 = 28
  tag = 29  # Unique identifier for a unit (only populated for raw units).
  hallucination = 30
  buff_id_0 = 31
  buff_id_1 = 32
  addon_unit_type = 33
  active = 34
  is_on_screen = 35
  order_progress_0 = 36
  order_progress_1 = 37
  order_id_2 = 38
  order_id_3 = 39
  is_in_cargo = 40
  buff_duration_remain = 41
  buff_duration_max = 42
  attack_upgrade_level = 43
  armor_upgrade_level = 44
  shield_upgrade_level = 45


class EffectPos(enum.IntEnum):
  """Positions of the active effects."""
  effect = 0
  alliance = 1
  owner = 2
  radius = 3
  x = 4
  y = 5


class Radar(enum.IntEnum):
  """Positions of the Sensor towers."""
  x = 0
  y = 1
  radius = 2


class ProductionQueue(enum.IntEnum):
  """Indices for the `production_queue` observations."""
  ability_id = 0
  build_progress = 1


class Feature(collections.namedtuple(
    "Feature", ["index", "name", "layer_set", "full_name", "scale", "type",
                "palette", "clip"])):
  """Define properties of a feature layer.

  Attributes:
    index: Index of this layer into the set of layers.
    name: The name of the layer within the set.
    layer_set: Which set of feature layers to look at in the observation proto.
    full_name: The full name including for visualization.
    scale: Max value (+1) of this layer, used to scale the values.
    type: A FeatureType for scalar vs categorical.
    palette: A color palette for rendering.
    clip: Whether to clip the values for coloring.
  """
  __slots__ = ()

  dtypes = {
      1: np.uint8,
      8: np.uint8,
      16: np.uint16,
      32: np.int32,
  }

  def unpack(self, obs):
    """Return a correctly shaped numpy array for this feature."""
    planes = getattr(obs.feature_layer_data, self.layer_set)
    plane = getattr(planes, self.name)
    return self.unpack_layer(plane)

  @staticmethod
  @sw.decorate
  def unpack_layer(plane):
    """Return a correctly shaped numpy array given the feature layer bytes."""
    size = point.Point.build(plane.size)
    if size == (0, 0):
      # New layer that isn't implemented in this SC2 version.
      return None
    data = np.frombuffer(plane.data, dtype=Feature.dtypes[plane.bits_per_pixel])
    if plane.bits_per_pixel == 1:
      data = np.unpackbits(data)
      if data.shape[0] != size.x * size.y:
        # This could happen if the correct length isn't a multiple of 8, leading
        # to some padding bits at the end of the string which are incorrectly
        # interpreted as data.
        data = data[:size.x * size.y]
    return data.reshape(size.y, size.x)

  @staticmethod
  @sw.decorate
  def unpack_rgb_image(plane):
    """Return a correctly shaped numpy array given the image bytes."""
    assert plane.bits_per_pixel == 24, "{} != 24".format(plane.bits_per_pixel)
    size = point.Point.build(plane.size)
    data = np.frombuffer(plane.data, dtype=np.uint8)
    return data.reshape(size.y, size.x, 3)

  @sw.decorate
  def color(self, plane):
    if self.clip:
      plane = np.clip(plane, 0, self.scale - 1)
    return self.palette[plane]


class ScreenFeatures(collections.namedtuple("ScreenFeatures", [
    "height_map", "visibility_map", "creep", "power", "player_id",
    "player_relative", "unit_type", "selected", "unit_hit_points",
    "unit_hit_points_ratio", "unit_energy", "unit_energy_ratio", "unit_shields",
    "unit_shields_ratio", "unit_density", "unit_density_aa", "effects",
    "hallucinations", "cloaked", "blip", "buffs", "buff_duration", "active",
    "build_progress", "pathable", "buildable", "placeholder"])):
  """The set of screen feature layers."""
  __slots__ = ()

  def __new__(cls, **kwargs):
    feats = {}
    for name, (scale, type_, palette, clip) in six.iteritems(kwargs):
      feats[name] = Feature(
          index=ScreenFeatures._fields.index(name),
          name=name,
          layer_set="renders",
          full_name="screen " + name,
          scale=scale,
          type=type_,
          palette=palette(scale) if callable(palette) else palette,
          clip=clip)
    return super(ScreenFeatures, cls).__new__(cls, **feats)  # pytype: disable=missing-parameter


class MinimapFeatures(collections.namedtuple("MinimapFeatures", [
    "height_map", "visibility_map", "creep", "camera", "player_id",
    "player_relative", "selected", "unit_type", "alerts", "pathable",
    "buildable"])):
  """The set of minimap feature layers."""
  __slots__ = ()

  def __new__(cls, **kwargs):
    feats = {}
    for name, (scale, type_, palette) in six.iteritems(kwargs):
      feats[name] = Feature(
          index=MinimapFeatures._fields.index(name),
          name=name,
          layer_set="minimap_renders",
          full_name="minimap " + name,
          scale=scale,
          type=type_,
          palette=palette(scale) if callable(palette) else palette,
          clip=False)
    return super(MinimapFeatures, cls).__new__(cls, **feats)  # pytype: disable=missing-parameter


SCREEN_FEATURES = ScreenFeatures(
    height_map=(256, FeatureType.SCALAR, colors.height_map, False),
    visibility_map=(4, FeatureType.CATEGORICAL,
                    colors.VISIBILITY_PALETTE, False),
    creep=(2, FeatureType.CATEGORICAL, colors.CREEP_PALETTE, False),
    power=(2, FeatureType.CATEGORICAL, colors.POWER_PALETTE, False),
    player_id=(17, FeatureType.CATEGORICAL,
               colors.PLAYER_ABSOLUTE_PALETTE, False),
    player_relative=(5, FeatureType.CATEGORICAL,
                     colors.PLAYER_RELATIVE_PALETTE, False),
    unit_type=(max(static_data.UNIT_TYPES) + 1, FeatureType.CATEGORICAL,
               colors.unit_type, False),
    selected=(2, FeatureType.CATEGORICAL, colors.SELECTED_PALETTE, False),
    unit_hit_points=(1600, FeatureType.SCALAR, colors.hot, True),
    unit_hit_points_ratio=(256, FeatureType.SCALAR, colors.hot, False),
    unit_energy=(1000, FeatureType.SCALAR, colors.hot, True),
    unit_energy_ratio=(256, FeatureType.SCALAR, colors.hot, False),
    unit_shields=(1000, FeatureType.SCALAR, colors.hot, True),
    unit_shields_ratio=(256, FeatureType.SCALAR, colors.hot, False),
    unit_density=(16, FeatureType.SCALAR, colors.hot, True),
    unit_density_aa=(256, FeatureType.SCALAR, colors.hot, False),
    effects=(16, FeatureType.CATEGORICAL, colors.effects, False),
    hallucinations=(2, FeatureType.CATEGORICAL, colors.POWER_PALETTE, False),
    cloaked=(2, FeatureType.CATEGORICAL, colors.POWER_PALETTE, False),
    blip=(2, FeatureType.CATEGORICAL, colors.POWER_PALETTE, False),
    buffs=(max(static_data.BUFFS) + 1, FeatureType.CATEGORICAL,
           colors.buffs, False),
    buff_duration=(256, FeatureType.SCALAR, colors.hot, False),
    active=(2, FeatureType.CATEGORICAL, colors.POWER_PALETTE, False),
    build_progress=(256, FeatureType.SCALAR, colors.hot, False),
    pathable=(2, FeatureType.CATEGORICAL, colors.winter, False),
    buildable=(2, FeatureType.CATEGORICAL, colors.winter, False),
    placeholder=(2, FeatureType.CATEGORICAL, colors.winter, False),
)

MINIMAP_FEATURES = MinimapFeatures(
    height_map=(256, FeatureType.SCALAR, colors.height_map),
    visibility_map=(4, FeatureType.CATEGORICAL, colors.VISIBILITY_PALETTE),
    creep=(2, FeatureType.CATEGORICAL, colors.CREEP_PALETTE),
    camera=(2, FeatureType.CATEGORICAL, colors.CAMERA_PALETTE),
    player_id=(17, FeatureType.CATEGORICAL, colors.PLAYER_ABSOLUTE_PALETTE),
    player_relative=(5, FeatureType.CATEGORICAL,
                     colors.PLAYER_RELATIVE_PALETTE),
    selected=(2, FeatureType.CATEGORICAL, colors.winter),
    unit_type=(max(static_data.UNIT_TYPES) + 1, FeatureType.CATEGORICAL,
               colors.unit_type),
    alerts=(2, FeatureType.CATEGORICAL, colors.winter),
    pathable=(2, FeatureType.CATEGORICAL, colors.winter),
    buildable=(2, FeatureType.CATEGORICAL, colors.winter),
)


def _to_point(dims):
  """Convert (width, height) or size -> point.Point."""
  assert dims

  if isinstance(dims, (tuple, list)):
    if len(dims) != 2:
      raise ValueError(
          "A two element tuple or list is expected here, got {}.".format(dims))
    else:
      width = int(dims[0])
      height = int(dims[1])
      if width <= 0 or height <= 0:
        raise ValueError("Must specify +ve dims, got {}.".format(dims))
      else:
        return point.Point(width, height)
  else:
    size = int(dims)
    if size <= 0:
      raise ValueError(
          "Must specify a +ve value for size, got {}.".format(dims))
    else:
      return point.Point(size, size)


class Dimensions(object):
  """Screen and minimap dimensions configuration.

  Both screen and minimap must be specified. Sizes must be positive.
  Screen size must be greater than or equal to minimap size in both dimensions.

  Attributes:
    screen: A (width, height) int tuple or a single int to be used for both.
    minimap: A (width, height) int tuple or a single int to be used for both.
  """

  def __init__(self, screen=None, minimap=None):
    if not screen or not minimap:
      raise ValueError(
          "screen and minimap must both be set, screen={}, minimap={}".format(
              screen, minimap))

    self._screen = _to_point(screen)
    self._minimap = _to_point(minimap)

  @property
  def screen(self):
    return self._screen

  @property
  def minimap(self):
    return self._minimap

  def __repr__(self):
    return "Dimensions(screen={}, minimap={})".format(self.screen, self.minimap)

  def __eq__(self, other):
    return (isinstance(other, Dimensions) and self.screen == other.screen and
            self.minimap == other.minimap)

  def __ne__(self, other):
    return not self == other


class AgentInterfaceFormat(object):
  """Observation and action interface format specific to a particular agent."""

  def __init__(
      self,
      feature_dimensions=None,
      rgb_dimensions=None,
      raw_resolution=None,
      action_space=None,
      camera_width_world_units=None,
      use_feature_units=False,
      use_raw_units=False,
      use_raw_actions=False,
      max_raw_actions=512,
      max_selected_units=30,
      use_unit_counts=False,
      use_camera_position=False,
      show_cloaked=False,
      show_burrowed_shadows=False,
      show_placeholders=False,
      hide_specific_actions=True,
      action_delay_fn=None,
      send_observation_proto=False,
      crop_to_playable_area=False,
      raw_crop_to_playable_area=False,
      allow_cheating_layers=False,
      add_cargo_to_units=False):
    """Initializer.

    Args:
      feature_dimensions: Feature layer `Dimension`s. Either this or
          rgb_dimensions (or both) must be set.
      rgb_dimensions: RGB `Dimension`. Either this or feature_dimensions
          (or both) must be set.
      raw_resolution: Discretize the `raw_units` observation's x,y to this
          resolution. Default is the map_size.
      action_space: If you pass both feature and rgb sizes, then you must also
          specify which you want to use for your actions as an ActionSpace enum.
      camera_width_world_units: The width of your screen in world units. If your
          feature_dimensions.screen=(64, 48) and camera_width is 24, then each
          px represents 24 / 64 = 0.375 world units in each of x and y.
          It'll then represent a camera of size (24, 0.375 * 48) = (24, 18)
          world units.
      use_feature_units: Whether to include feature_unit observations.
      use_raw_units: Whether to include raw unit data in observations. This
          differs from feature_units because it includes units outside the
          screen and hidden units, and because unit positions are given in
          terms of world units instead of screen units.
      use_raw_actions: [bool] Whether to use raw actions as the interface.
          Same as specifying action_space=ActionSpace.RAW.
      max_raw_actions: [int] Maximum number of raw actions
      max_selected_units: [int] The maximum number of selected units in the
          raw interface.
      use_unit_counts: Whether to include unit_counts observation. Disabled by
          default since it gives information outside the visible area.
      use_camera_position: Whether to include the camera's position (in minimap
          coordinates) in the observations.
      show_cloaked: Whether to show limited information for cloaked units.
      show_burrowed_shadows: Whether to show limited information for burrowed
          units that leave a shadow on the ground (ie widow mines and moving
          roaches and infestors).
      show_placeholders: Whether to show buildings that are queued for
          construction.
      hide_specific_actions: [bool] Some actions (eg cancel) have many
          specific versions (cancel this building, cancel that spell) and can
          be represented in a more general form. If a specific action is
          available, the general will also be available. If you set
          `hide_specific_actions` to False, the specific versions will also be
          available, but if it's True, the specific ones will be hidden.
          Similarly, when transforming back, a specific action will be returned
          as the general action. This simplifies the action space, though can
          lead to some actions in replays not being exactly representable using
          only the general actions.
      action_delay_fn: A callable which when invoked returns a delay in game
          loops to apply to a requested action. Defaults to None, meaning no
          delays are added (actions will be executed on the next game loop,
          hence with the minimum delay of 1).
      send_observation_proto: Whether or not to send the raw observation
          response proto in the observations.
      crop_to_playable_area: Crop the feature layer minimap observations down
          from the full map area to just the playable area. Also improves the
          heightmap rendering.
      raw_crop_to_playable_area: Crop the raw units to the playable area. This
          means units will show up closer to the origin with less dead space
          around their valid locations.
      allow_cheating_layers: Show the unit types and potentially other cheating
          layers on the minimap.
      add_cargo_to_units: Whether to add the units that are currently in cargo
          to the feature_units and raw_units lists.

    Raises:
      ValueError: if the parameters are inconsistent.
    """

    if not (feature_dimensions or rgb_dimensions or use_raw_units):
      raise ValueError("Must set either the feature layer or rgb dimensions, "
                       "or use raw units.")

    if action_space:
      if not isinstance(action_space, actions.ActionSpace):
        raise ValueError("action_space must be of type ActionSpace.")

      if action_space == actions.ActionSpace.RAW:
        use_raw_actions = True
      elif ((action_space == actions.ActionSpace.FEATURES and
             not feature_dimensions) or
            (action_space == actions.ActionSpace.RGB and
             not rgb_dimensions)):
        raise ValueError(
            "Action space must match the observations, action space={}, "
            "feature_dimensions={}, rgb_dimensions={}".format(
                action_space, feature_dimensions, rgb_dimensions))
    else:
      if use_raw_actions:
        action_space = actions.ActionSpace.RAW
      elif feature_dimensions and rgb_dimensions:
        raise ValueError(
            "You must specify the action space if you have both screen and "
            "rgb observations.")
      elif feature_dimensions:
        action_space = actions.ActionSpace.FEATURES
      else:
        action_space = actions.ActionSpace.RGB

    if raw_resolution:
      raw_resolution = _to_point(raw_resolution)

    if use_raw_actions:
      if not use_raw_units:
        raise ValueError(
            "You must set use_raw_units if you intend to use_raw_actions")
      if action_space != actions.ActionSpace.RAW:
        raise ValueError(
            "Don't specify both an action_space and use_raw_actions.")

    if (rgb_dimensions and
        (rgb_dimensions.screen.x < rgb_dimensions.minimap.x or
         rgb_dimensions.screen.y < rgb_dimensions.minimap.y)):
      raise ValueError(
          "RGB Screen (%s) can't be smaller than the minimap (%s)." % (
              rgb_dimensions.screen, rgb_dimensions.minimap))

    self._feature_dimensions = feature_dimensions
    self._rgb_dimensions = rgb_dimensions
    self._action_space = action_space
    self._camera_width_world_units = camera_width_world_units or 24
    self._use_feature_units = use_feature_units
    self._use_raw_units = use_raw_units
    self._raw_resolution = raw_resolution
    self._use_raw_actions = use_raw_actions
    self._max_raw_actions = max_raw_actions
    self._max_selected_units = max_selected_units
    self._use_unit_counts = use_unit_counts
    self._use_camera_position = use_camera_position
    self._show_cloaked = show_cloaked
    self._show_burrowed_shadows = show_burrowed_shadows
    self._show_placeholders = show_placeholders
    self._hide_specific_actions = hide_specific_actions
    self._action_delay_fn = action_delay_fn
    self._send_observation_proto = send_observation_proto
    self._add_cargo_to_units = add_cargo_to_units
    self._crop_to_playable_area = crop_to_playable_area
    self._raw_crop_to_playable_area = raw_crop_to_playable_area
    self._allow_cheating_layers = allow_cheating_layers

    if action_space == actions.ActionSpace.FEATURES:
      self._action_dimensions = feature_dimensions
    else:
      self._action_dimensions = rgb_dimensions

  @property
  def feature_dimensions(self):
    return self._feature_dimensions

  @property
  def rgb_dimensions(self):
    return self._rgb_dimensions

  @property
  def action_space(self):
    return self._action_space

  @property
  def camera_width_world_units(self):
    return self._camera_width_world_units

  @property
  def use_feature_units(self):
    return self._use_feature_units

  @property
  def use_raw_units(self):
    return self._use_raw_units

  @property
  def raw_resolution(self):
    return self._raw_resolution

  @raw_resolution.setter
  def raw_resolution(self, value):
    self._raw_resolution = value

  @property
  def use_raw_actions(self):
    return self._use_raw_actions

  @property
  def max_raw_actions(self):
    return self._max_raw_actions

  @property
  def max_selected_units(self):
    return self._max_selected_units

  @property
  def use_unit_counts(self):
    return self._use_unit_counts

  @property
  def use_camera_position(self):
    return self._use_camera_position

  @property
  def show_cloaked(self):
    return self._show_cloaked

  @property
  def show_burrowed_shadows(self):
    return self._show_burrowed_shadows

  @property
  def show_placeholders(self):
    return self._show_placeholders

  @property
  def hide_specific_actions(self):
    return self._hide_specific_actions

  @property
  def action_delay_fn(self):
    return self._action_delay_fn

  @property
  def send_observation_proto(self):
    return self._send_observation_proto

  @property
  def add_cargo_to_units(self):
    return self._add_cargo_to_units

  @property
  def action_dimensions(self):
    return self._action_dimensions

  @property
  def crop_to_playable_area(self):
    return self._crop_to_playable_area

  @property
  def raw_crop_to_playable_area(self):
    return self._raw_crop_to_playable_area

  @property
  def allow_cheating_layers(self):
    return self._allow_cheating_layers


def parse_agent_interface_format(
    feature_screen=None,
    feature_minimap=None,
    rgb_screen=None,
    rgb_minimap=None,
    action_space=None,
    action_delays=None,
    **kwargs):
  """Creates an AgentInterfaceFormat object from keyword args.

  Convenient when using dictionaries or command-line arguments for config.

  Note that the feature_* and rgb_* properties define the respective spatial
  observation dimensions and accept:
      * None or 0 to disable that spatial observation.
      * A single int for a square observation with that side length.
      * A (int, int) tuple for a rectangular (width, height) observation.

  Args:
    feature_screen: If specified, so must feature_minimap be.
    feature_minimap: If specified, so must feature_screen be.
    rgb_screen: If specified, so must rgb_minimap be.
    rgb_minimap: If specified, so must rgb_screen be.
    action_space: ["FEATURES", "RGB", "RAW"].
    action_delays: List of relative frequencies for each of [1, 2, 3, ...]
      game loop delays on executed actions. Only used when the environment
      is non-realtime. Intended to simulate the delays which can be
      experienced when playing in realtime. Note that 1 is the minimum
      possible delay; as actions can only ever be executed on a subsequent
      game loop.
    **kwargs: Anything else is passed through to AgentInterfaceFormat.

  Returns:
    An `AgentInterfaceFormat` object.

  Raises:
    ValueError: If an invalid parameter is specified.
  """
  if feature_screen or feature_minimap:
    feature_dimensions = Dimensions(feature_screen, feature_minimap)
  else:
    feature_dimensions = None

  if rgb_screen or rgb_minimap:
    rgb_dimensions = Dimensions(rgb_screen, rgb_minimap)
  else:
    rgb_dimensions = None

  def _action_delay_fn(delays):
    """Delay frequencies per game loop delay -> fn returning game loop delay."""
    if not delays:
      return None
    else:
      total = sum(delays)
      cumulative_sum = np.cumsum([delay / total for delay in delays])
      def fn():
        sample = random.uniform(0, 1) - EPSILON
        for i, cumulative in enumerate(cumulative_sum):
          if sample <= cumulative:
            return i + 1
        raise ValueError("Failed to sample action delay??")
      return fn

  return AgentInterfaceFormat(
      feature_dimensions=feature_dimensions,
      rgb_dimensions=rgb_dimensions,
      action_space=(action_space and actions.ActionSpace[action_space.upper()]),
      action_delay_fn=_action_delay_fn(action_delays),
      **kwargs)


def features_from_game_info(game_info, agent_interface_format=None,
                            map_name=None, **kwargs):
  """Construct a Features object using data extracted from game info.

  Args:
    game_info: A `sc_pb.ResponseGameInfo` from the game.
    agent_interface_format: an optional AgentInterfaceFormat.
    map_name: an optional map name, which overrides the one in game_info.
    **kwargs: Anything else is passed through to AgentInterfaceFormat. It's an
        error to send any kwargs if you pass an agent_interface_format.

  Returns:
    A features object matching the specified parameterisation.

  Raises:
    ValueError: if you pass both agent_interface_format and kwargs.
    ValueError: if you pass an agent_interface_format that doesn't match
        game_info's resolutions.
  """
  if not map_name:
    map_name = game_info.map_name

  if game_info.options.HasField("feature_layer"):
    fl_opts = game_info.options.feature_layer
    feature_dimensions = Dimensions(
        screen=(fl_opts.resolution.x, fl_opts.resolution.y),
        minimap=(fl_opts.minimap_resolution.x, fl_opts.minimap_resolution.y))
    camera_width_world_units = game_info.options.feature_layer.width
  else:
    feature_dimensions = None
    camera_width_world_units = None

  if game_info.options.HasField("render"):
    rgb_opts = game_info.options.render
    rgb_dimensions = Dimensions(
        screen=(rgb_opts.resolution.x, rgb_opts.resolution.y),
        minimap=(rgb_opts.minimap_resolution.x, rgb_opts.minimap_resolution.y))
  else:
    rgb_dimensions = None

  map_size = game_info.start_raw.map_size

  requested_races = {
      info.player_id: info.race_requested for info in game_info.player_info
      if info.type != sc_pb.Observer}

  if agent_interface_format:
    if kwargs:
      raise ValueError(
          "Either give an agent_interface_format or kwargs, not both.")
    aif = agent_interface_format
    if (aif.rgb_dimensions != rgb_dimensions or
        aif.feature_dimensions != feature_dimensions or
        (feature_dimensions and
         aif.camera_width_world_units != camera_width_world_units)):
      raise ValueError("""
The supplied agent_interface_format doesn't match the resolutions computed from
the game_info:
  rgb_dimensions: %s != %s
  feature_dimensions: %s != %s
  camera_width_world_units: %s != %s
""" % (aif.rgb_dimensions, rgb_dimensions,
       aif.feature_dimensions, feature_dimensions,
       aif.camera_width_world_units, camera_width_world_units))
  else:
    agent_interface_format = AgentInterfaceFormat(
        feature_dimensions=feature_dimensions,
        rgb_dimensions=rgb_dimensions,
        camera_width_world_units=camera_width_world_units,
        **kwargs)

  return Features(
      agent_interface_format=agent_interface_format,
      map_size=map_size,
      map_name=map_name,
      requested_races=requested_races)


def _init_valid_functions(action_dimensions):
  """Initialize ValidFunctions and set up the callbacks."""
  sizes = {
      "screen": tuple(int(i) for i in action_dimensions.screen),
      "screen2": tuple(int(i) for i in action_dimensions.screen),
      "minimap": tuple(int(i) for i in action_dimensions.minimap),
  }

  types = actions.Arguments(*[
      actions.ArgumentType.spec(t.id, t.name, sizes.get(t.name, t.sizes))
      for t in actions.TYPES])

  functions = actions.Functions([
      actions.Function.spec(f.id, f.name, tuple(types[t.id] for t in f.args))
      for f in actions.FUNCTIONS])

  return actions.ValidActions(types, functions)


def _init_valid_raw_functions(raw_resolution, max_selected_units):
  """Initialize ValidFunctions and set up the callbacks."""
  sizes = {
      "world": tuple(int(i) for i in raw_resolution),
      "unit_tags": (max_selected_units,),
  }
  types = actions.RawArguments(*[
      actions.ArgumentType.spec(t.id, t.name, sizes.get(t.name, t.sizes))
      for t in actions.RAW_TYPES])

  functions = actions.Functions([
      actions.Function.spec(f.id, f.name, tuple(types[t.id] for t in f.args))
      for f in actions.RAW_FUNCTIONS])

  return actions.ValidActions(types, functions)


class Features(object):
  """Render feature layers from SC2 Observation protos into numpy arrays.

  This has the implementation details of how to render a starcraft environment.
  It translates between agent action/observation formats and starcraft
  action/observation formats, which should not be seen by agent authors. The
  starcraft protos contain more information than they should have access to.

  This is outside of the environment so that it can also be used in other
  contexts, eg a supervised dataset pipeline.
  """

  def __init__(self, agent_interface_format=None, map_size=None,
               requested_races=None, map_name="unknown"):
    """Initialize a Features instance matching the specified interface format.

    Args:
      agent_interface_format: See the documentation for `AgentInterfaceFormat`.
      map_size: The size of the map in world units, needed for feature_units.
      requested_races: Optional. Dict mapping `player_id`s to that player's
          requested race. If present, will send player races in observation.
      map_name: Optional name of the map, to be added to the observation.

    Raises:
      ValueError: if agent_interface_format isn't specified.
      ValueError: if map_size isn't specified when use_feature_units or
          use_camera_position is.
    """
    if not agent_interface_format:
      raise ValueError("Please specify agent_interface_format")

    self._agent_interface_format = agent_interface_format
    aif = self._agent_interface_format
    if not aif.raw_resolution and map_size:
      aif.raw_resolution = point.Point.build(map_size)
    self._map_size = map_size
    self._map_name = map_name

    if (aif.use_feature_units
        or aif.use_camera_position
        or aif.use_raw_units):
      self.init_camera(
          aif.feature_dimensions,
          map_size,
          aif.camera_width_world_units,
          aif.raw_resolution)

    self._send_observation_proto = aif.send_observation_proto
    self._raw = aif.use_raw_actions
    if self._raw:
      self._valid_functions = _init_valid_raw_functions(
          aif.raw_resolution, aif.max_selected_units)
      self._raw_tags = []
    else:
      self._valid_functions = _init_valid_functions(aif.action_dimensions)
    self._requested_races = requested_races
    if requested_races is not None:
      assert len(requested_races) <= 2

  def init_camera(
      self, feature_dimensions, map_size, camera_width_world_units,
      raw_resolution):
    """Initialize the camera (especially for feature_units).

    This is called in the constructor and may be called repeatedly after
    `Features` is constructed, since it deals with rescaling coordinates and not
    changing environment/action specs.

    Args:
      feature_dimensions: See the documentation in `AgentInterfaceFormat`.
      map_size: The size of the map in world units.
      camera_width_world_units: See the documentation in `AgentInterfaceFormat`.
      raw_resolution: See the documentation in `AgentInterfaceFormat`.

    Raises:
      ValueError: If map_size or camera_width_world_units are falsey (which
          should mainly happen if called by the constructor).
    """
    if not map_size or not camera_width_world_units:
      raise ValueError(
          "Either pass the game_info with raw enabled, or map_size and "
          "camera_width_world_units in order to use feature_units or camera"
          "position.")
    map_size = point.Point.build(map_size)
    self._world_to_world_tl = transform.Linear(point.Point(1, -1),
                                               point.Point(0, map_size.y))
    self._world_tl_to_world_camera_rel = transform.Linear(offset=-map_size / 4)
    if feature_dimensions:
      world_camera_rel_to_feature_screen = transform.Linear(
          feature_dimensions.screen / camera_width_world_units,
          feature_dimensions.screen / 2)
      self._world_to_feature_screen_px = transform.Chain(
          self._world_to_world_tl,
          self._world_tl_to_world_camera_rel,
          world_camera_rel_to_feature_screen,
          transform.PixelToCoord())

    # If we don't have a specified raw resolution, we do no transform.
    world_tl_to_feature_minimap = transform.Linear(
        scale=raw_resolution / map_size.max_dim() if raw_resolution else None)
    self._world_to_minimap_px = transform.Chain(
        self._world_to_world_tl,
        world_tl_to_feature_minimap,
        transform.PixelToCoord())
    self._camera_size = (
        raw_resolution / map_size.max_dim() * camera_width_world_units)

  def _update_camera(self, camera_center):
    """Update the camera transform based on the new camera center."""
    self._world_tl_to_world_camera_rel.offset = (
        -self._world_to_world_tl.fwd_pt(camera_center) *
        self._world_tl_to_world_camera_rel.scale)

  def observation_spec(self):
    """The observation spec for the SC2 environment.

    It's worth noting that the image-like observations are in y,x/row,column
    order which is different than the actions which are in x,y order. This is
    due to conflicting conventions, and to facilitate printing of the images.

    Returns:
      The dict of observation names to their tensor shapes. Shapes with a 0 can
      vary in length, for example the number of valid actions depends on which
      units you have selected.
    """
    # pytype: disable=wrong-arg-types
    obs_spec = named_array.NamedDict({
        "action_result": (0,),  # See error.proto: ActionResult.
        "alerts": (0,),  # See sc2api.proto: Alert.
        "build_queue": (0, len(UnitLayer)),
        "cargo": (0, len(UnitLayer)),
        "cargo_slots_available": (1,),
        "control_groups": (10, 2),
        "game_loop": (1,),
        "last_actions": (0,),
        "map_name": (0,),
        "multi_select": (0, len(UnitLayer)),
        "player": (len(Player),),
        "production_queue": (0, len(ProductionQueue)),
        "score_cumulative": (len(ScoreCumulative),),
        "score_by_category": (len(ScoreByCategory), len(ScoreCategories)),
        "score_by_vital": (len(ScoreByVital), len(ScoreVitals)),
        "single_select": (0, len(UnitLayer)),  # Only (n, 7) for n in (0, 1).
    })
    # pytype: enable=wrong-arg-types

    if not self._raw:
      obs_spec["available_actions"] = (0,)

    aif = self._agent_interface_format

    if aif.feature_dimensions:
      obs_spec["feature_screen"] = (len(SCREEN_FEATURES),
                                    aif.feature_dimensions.screen.y,
                                    aif.feature_dimensions.screen.x)

      obs_spec["feature_minimap"] = (len(MINIMAP_FEATURES),
                                     aif.feature_dimensions.minimap.y,
                                     aif.feature_dimensions.minimap.x)
    if aif.rgb_dimensions:
      obs_spec["rgb_screen"] = (aif.rgb_dimensions.screen.y,
                                aif.rgb_dimensions.screen.x,
                                3)
      obs_spec["rgb_minimap"] = (aif.rgb_dimensions.minimap.y,
                                 aif.rgb_dimensions.minimap.x,
                                 3)
    if aif.use_feature_units:
      obs_spec["feature_units"] = (0, len(FeatureUnit))  # pytype: disable=wrong-arg-types
      obs_spec["feature_effects"] = (0, len(EffectPos))

    if aif.use_raw_units:
      obs_spec["raw_units"] = (0, len(FeatureUnit))
      obs_spec["raw_effects"] = (0, len(EffectPos))

    if aif.use_feature_units or aif.use_raw_units:
      obs_spec["radar"] = (0, len(Radar))

    obs_spec["upgrades"] = (0,)

    if aif.use_unit_counts:
      obs_spec["unit_counts"] = (0, len(UnitCounts))

    if aif.use_camera_position:
      obs_spec["camera_position"] = (2,)
      obs_spec["camera_size"] = (2,)

    if self._send_observation_proto:
      obs_spec["_response_observation"] = (0,)

    obs_spec["home_race_requested"] = (1,)
    obs_spec["away_race_requested"] = (1,)
    return obs_spec

  def action_spec(self):
    """The action space pretty complicated and fills the ValidFunctions."""
    return self._valid_functions

  @property
  def map_size(self):
    return self._map_size

  @property
  def requested_races(self):
    return self._requested_races

  @sw.decorate
  def transform_obs(self, obs):
    """Render some SC2 observations into something an agent can handle."""
    empty_unit = np.array([], dtype=np.int32).reshape((0, len(UnitLayer)))
    out = named_array.NamedDict({  # Fill out some that are sometimes empty.
        "single_select": empty_unit,
        "multi_select": empty_unit,
        "build_queue": empty_unit,
        "cargo": empty_unit,
        "production_queue": np.array([], dtype=np.int32).reshape(
            (0, len(ProductionQueue))),
        "last_actions": np.array([], dtype=np.int32),
        "cargo_slots_available": np.array([0], dtype=np.int32),
        "home_race_requested": np.array([0], dtype=np.int32),
        "away_race_requested": np.array([0], dtype=np.int32),
        "map_name": self._map_name,
    })

    def or_zeros(layer, size):
      if layer is not None:
        return layer.astype(np.int32, copy=False)
      else:
        return np.zeros((size.y, size.x), dtype=np.int32)

    aif = self._agent_interface_format

    if aif.feature_dimensions:
      with sw("feature_screen"):
        out["feature_screen"] = named_array.NamedNumpyArray(
            np.stack([or_zeros(f.unpack(obs.observation),
                               aif.feature_dimensions.screen)
                      for f in SCREEN_FEATURES]),
            names=[ScreenFeatures, None, None])
      with sw("feature_minimap"):
        out["feature_minimap"] = named_array.NamedNumpyArray(
            np.stack([or_zeros(f.unpack(obs.observation),
                               aif.feature_dimensions.minimap)
                      for f in MINIMAP_FEATURES]),
            names=[MinimapFeatures, None, None])

    if aif.rgb_dimensions:
      with sw("rgb_screen"):
        out["rgb_screen"] = Feature.unpack_rgb_image(
            obs.observation.render_data.map).astype(np.int32)
      with sw("rgb_minimap"):
        out["rgb_minimap"] = Feature.unpack_rgb_image(
            obs.observation.render_data.minimap).astype(np.int32)

    if not self._raw:
      with sw("last_actions"):
        out["last_actions"] = np.array(
            [self.reverse_action(a).function for a in obs.actions],
            dtype=np.int32)

    out["action_result"] = np.array([o.result for o in obs.action_errors],
                                    dtype=np.int32)

    out["alerts"] = np.array(obs.observation.alerts, dtype=np.int32)

    out["game_loop"] = np.array([obs.observation.game_loop], dtype=np.int32)

    with sw("score"):
      score_details = obs.observation.score.score_details
      out["score_cumulative"] = named_array.NamedNumpyArray([
          obs.observation.score.score,
          score_details.idle_production_time,
          score_details.idle_worker_time,
          score_details.total_value_units,
          score_details.total_value_structures,
          score_details.killed_value_units,
          score_details.killed_value_structures,
          score_details.collected_minerals,
          score_details.collected_vespene,
          score_details.collection_rate_minerals,
          score_details.collection_rate_vespene,
          score_details.spent_minerals,
          score_details.spent_vespene,
      ], names=ScoreCumulative, dtype=np.int32)

      def get_score_details(key, details, categories):
        row = getattr(details, key.name)
        return [getattr(row, category.name) for category in categories]

      out["score_by_category"] = named_array.NamedNumpyArray([
          get_score_details(key, score_details, ScoreCategories)
          for key in ScoreByCategory
      ], names=[ScoreByCategory, ScoreCategories], dtype=np.int32)

      out["score_by_vital"] = named_array.NamedNumpyArray([
          get_score_details(key, score_details, ScoreVitals)
          for key in ScoreByVital
      ], names=[ScoreByVital, ScoreVitals], dtype=np.int32)

    player = obs.observation.player_common
    out["player"] = named_array.NamedNumpyArray([
        player.player_id,
        player.minerals,
        player.vespene,
        player.food_used,
        player.food_cap,
        player.food_army,
        player.food_workers,
        player.idle_worker_count,
        player.army_count,
        player.warp_gate_count,
        player.larva_count,
    ], names=Player, dtype=np.int32)

    def unit_vec(u):
      return np.array((
          u.unit_type,
          u.player_relative,
          u.health,
          u.shields,
          u.energy,
          u.transport_slots_taken,
          int(u.build_progress * 100),  # discretize
      ), dtype=np.int32)

    ui = obs.observation.ui_data

    with sw("ui"):
      groups = np.zeros((10, 2), dtype=np.int32)
      for g in ui.groups:
        groups[g.control_group_index, :] = (g.leader_unit_type, g.count)
      out["control_groups"] = groups

      if ui.HasField("single"):
        out["single_select"] = named_array.NamedNumpyArray(
            [unit_vec(ui.single.unit)], [None, UnitLayer])
      elif ui.HasField("multi"):
        out["multi_select"] = named_array.NamedNumpyArray(
            [unit_vec(u) for u in ui.multi.units], [None, UnitLayer])
      elif ui.HasField("cargo"):
        out["single_select"] = named_array.NamedNumpyArray(
            [unit_vec(ui.cargo.unit)], [None, UnitLayer])
        out["cargo"] = named_array.NamedNumpyArray(
            [unit_vec(u) for u in ui.cargo.passengers], [None, UnitLayer])
        out["cargo_slots_available"] = np.array([ui.cargo.slots_available],
                                                dtype=np.int32)
      elif ui.HasField("production"):
        out["single_select"] = named_array.NamedNumpyArray(
            [unit_vec(ui.production.unit)], [None, UnitLayer])
        if ui.production.build_queue:
          out["build_queue"] = named_array.NamedNumpyArray(
              [unit_vec(u) for u in ui.production.build_queue],
              [None, UnitLayer], dtype=np.int32)
        if ui.production.production_queue:
          out["production_queue"] = named_array.NamedNumpyArray(
              [(item.ability_id, item.build_progress * 100)
               for item in ui.production.production_queue],
              [None, ProductionQueue], dtype=np.int32)

    tag_types = {}  # Only populate the cache if it's needed.
    def get_addon_type(tag):
      if not tag_types:
        for u in raw.units:
          tag_types[u.tag] = u.unit_type
      return tag_types.get(tag, 0)

    def full_unit_vec(u, pos_transform, is_raw=False):
      """Compute unit features."""
      screen_pos = pos_transform.fwd_pt(
          point.Point.build(u.pos))
      screen_radius = pos_transform.fwd_dist(u.radius)
      def raw_order(i):
        if len(u.orders) > i:
          # TODO(tewalds): Return a generalized func id.
          return actions.RAW_ABILITY_ID_TO_FUNC_ID.get(
              u.orders[i].ability_id, 0)
        return 0
      features = [
          # Match unit_vec order
          u.unit_type,
          u.alliance,  # Self = 1, Ally = 2, Neutral = 3, Enemy = 4
          u.health,
          u.shield,
          u.energy,
          u.cargo_space_taken,
          int(u.build_progress * 100),  # discretize

          # Resume API order
          int(u.health / u.health_max * 255) if u.health_max > 0 else 0,
          int(u.shield / u.shield_max * 255) if u.shield_max > 0 else 0,
          int(u.energy / u.energy_max * 255) if u.energy_max > 0 else 0,
          u.display_type,  # Visible = 1, Snapshot = 2, Hidden = 3
          u.owner,  # 1-15, 16 = neutral
          screen_pos.x,
          screen_pos.y,
          u.facing,
          screen_radius,
          u.cloak,  # Cloaked = 1, CloakedDetected = 2, NotCloaked = 3
          u.is_selected,
          u.is_blip,
          u.is_powered,
          u.mineral_contents,
          u.vespene_contents,

          # Not populated for enemies or neutral
          u.cargo_space_max,
          u.assigned_harvesters,
          u.ideal_harvesters,
          u.weapon_cooldown,
          len(u.orders),
          raw_order(0),
          raw_order(1),
          u.tag if is_raw else 0,
          u.is_hallucination,
          u.buff_ids[0] if len(u.buff_ids) >= 1 else 0,
          u.buff_ids[1] if len(u.buff_ids) >= 2 else 0,
          get_addon_type(u.add_on_tag) if u.add_on_tag else 0,
          u.is_active,
          u.is_on_screen,
          int(u.orders[0].progress * 100) if len(u.orders) >= 1 else 0,
          int(u.orders[1].progress * 100) if len(u.orders) >= 2 else 0,
          raw_order(2),
          raw_order(3),
          0,
          u.buff_duration_remain,
          u.buff_duration_max,
          u.attack_upgrade_level,
          u.armor_upgrade_level,
          u.shield_upgrade_level,
      ]
      return features

    raw = obs.observation.raw_data

    if aif.use_feature_units:
      with sw("feature_units"):
        # Update the camera location so we can calculate world to screen pos
        self._update_camera(point.Point.build(raw.player.camera))
        feature_units = [full_unit_vec(u, self._world_to_feature_screen_px)
                         for u in raw.units if u.is_on_screen]
        out["feature_units"] = named_array.NamedNumpyArray(
            feature_units, [None, FeatureUnit], dtype=np.int64)

        feature_effects = []
        feature_screen_size = aif.feature_dimensions.screen
        for effect in raw.effects:
          for pos in effect.pos:
            screen_pos = self._world_to_feature_screen_px.fwd_pt(
                point.Point.build(pos))
            if (0 <= screen_pos.x < feature_screen_size.x and
                0 <= screen_pos.y < feature_screen_size.y):
              feature_effects.append([
                  effect.effect_id,
                  effect.alliance,
                  effect.owner,
                  effect.radius,
                  screen_pos.x,
                  screen_pos.y,
              ])
        out["feature_effects"] = named_array.NamedNumpyArray(
            feature_effects, [None, EffectPos], dtype=np.int32)

    if aif.use_raw_units:
      with sw("raw_units"):
        with sw("to_list"):
          raw_units = [full_unit_vec(u, self._world_to_minimap_px, is_raw=True)
                       for u in raw.units]
        with sw("to_numpy"):
          out["raw_units"] = named_array.NamedNumpyArray(
              raw_units, [None, FeatureUnit], dtype=np.int64)
        if raw_units:
          self._raw_tags = out["raw_units"][:, FeatureUnit.tag]
        else:
          self._raw_tags = np.array([])

        raw_effects = []
        for effect in raw.effects:
          for pos in effect.pos:
            raw_pos = self._world_to_minimap_px.fwd_pt(point.Point.build(pos))
            raw_effects.append([
                effect.effect_id,
                effect.alliance,
                effect.owner,
                effect.radius,
                raw_pos.x,
                raw_pos.y,
            ])
        out["raw_effects"] = named_array.NamedNumpyArray(
            raw_effects, [None, EffectPos], dtype=np.int32)

    out["upgrades"] = np.array(raw.player.upgrade_ids, dtype=np.int32)

    def cargo_units(u, pos_transform, is_raw=False):
      """Compute unit features."""
      screen_pos = pos_transform.fwd_pt(
          point.Point.build(u.pos))
      features = []
      for v in u.passengers:
        features.append([
            v.unit_type,
            u.alliance,  # Self = 1, Ally = 2, Neutral = 3, Enemy = 4
            v.health,
            v.shield,
            v.energy,
            0,  # cargo_space_taken
            0,  # build_progress
            int(v.health / v.health_max * 255) if v.health_max > 0 else 0,
            int(v.shield / v.shield_max * 255) if v.shield_max > 0 else 0,
            int(v.energy / v.energy_max * 255) if v.energy_max > 0 else 0,
            0,  # display_type
            u.owner,  # 1-15, 16 = neutral
            screen_pos.x,
            screen_pos.y,
            0,  # facing
            0,  # screen_radius
            0,  # cloak
            0,  # is_selected
            0,  # is_blip
            0,  # is powered
            0,  # mineral_contents
            0,  # vespene_contents
            0,  # cargo_space_max
            0,  # assigned_harvesters
            0,  # ideal_harvesters
            0,  # weapon_cooldown
            0,  # order_length
            0,  # order_id_0
            0,  # order_id_1
            v.tag if is_raw else 0,
            0,  # is hallucination
            0,  # buff_id_1
            0,  # buff_id_2
            0,  # addon_unit_type
            0,  # active
            0,  # is_on_screen
            0,  # order_progress_1
            0,  # order_progress_2
            0,  # order_id_2
            0,  # order_id_3
            1,  # is_in_cargo
            0,  # buff_duration_remain
            0,  # buff_duration_max
            0,  # attack_upgrade_level
            0,  # armor_upgrade_level
            0,  # shield_upgrade_level
        ])
      return features

    if aif.add_cargo_to_units:
      with sw("add_cargo_to_units"):
        if aif.use_feature_units:
          with sw("feature_units"):
            with sw("to_list"):
              feature_cargo_units = []
              for u in raw.units:
                if u.is_on_screen:
                  feature_cargo_units += cargo_units(
                      u, self._world_to_feature_screen_px)
            with sw("to_numpy"):
              if feature_cargo_units:
                all_feature_units = np.array(
                    feature_cargo_units, dtype=np.int64)
                all_feature_units = np.concatenate(
                    [out["feature_units"], feature_cargo_units], axis=0)
                out["feature_units"] = named_array.NamedNumpyArray(
                    all_feature_units, [None, FeatureUnit], dtype=np.int64)
        if aif.use_raw_units:
          with sw("raw_units"):
            with sw("to_list"):
              raw_cargo_units = []
              for u in raw.units:
                raw_cargo_units += cargo_units(
                    u, self._world_to_minimap_px, is_raw=True)
            with sw("to_numpy"):
              if raw_cargo_units:
                raw_cargo_units = np.array(raw_cargo_units, dtype=np.int64)
                all_raw_units = np.concatenate(
                    [out["raw_units"], raw_cargo_units], axis=0)
                out["raw_units"] = named_array.NamedNumpyArray(
                    all_raw_units, [None, FeatureUnit], dtype=np.int64)
                self._raw_tags = out["raw_units"][:, FeatureUnit.tag]

    if aif.use_unit_counts:
      with sw("unit_counts"):
        unit_counts = collections.defaultdict(int)
        for u in raw.units:
          if u.alliance == sc_raw.Self:
            unit_counts[u.unit_type] += 1
        out["unit_counts"] = named_array.NamedNumpyArray(
            sorted(unit_counts.items()), [None, UnitCounts], dtype=np.int32)

    if aif.use_camera_position:
      camera_position = self._world_to_minimap_px.fwd_pt(
          point.Point.build(raw.player.camera))
      out["camera_position"] = np.array((camera_position.x, camera_position.y),
                                        dtype=np.int32)
      out["camera_size"] = np.array((self._camera_size.x, self._camera_size.y),
                                    dtype=np.int32)

    if not self._raw:
      out["available_actions"] = np.array(
          self.available_actions(obs.observation), dtype=np.int32)

    if self._requested_races is not None:
      out["home_race_requested"] = np.array(
          (self._requested_races[player.player_id],), dtype=np.int32)
      for player_id, race in self._requested_races.items():
        if player_id != player.player_id:
          out["away_race_requested"] = np.array((race,), dtype=np.int32)

    if aif.use_feature_units or aif.use_raw_units:
      def transform_radar(radar):
        p = self._world_to_minimap_px.fwd_pt(point.Point.build(radar.pos))
        return p.x, p.y, radar.radius
      out["radar"] = named_array.NamedNumpyArray(
          list(map(transform_radar, obs.observation.raw_data.radar)),
          [None, Radar], dtype=np.int32)

    # Send the entire proto as well (in a function, so it isn't copied).
    if self._send_observation_proto:
      out["_response_observation"] = lambda: obs

    return out

  @sw.decorate
  def available_actions(self, obs):
    """Return the list of available action ids."""
    available_actions = set()
    hide_specific_actions = self._agent_interface_format.hide_specific_actions
    for i, func in six.iteritems(actions.FUNCTIONS_AVAILABLE):
      if func.avail_fn(obs):
        available_actions.add(i)
    for a in obs.abilities:
      if a.ability_id not in actions.ABILITY_IDS:
        logging.warning("Unknown ability %s seen as available.", a.ability_id)
        continue
      found_applicable = False
      for func in actions.ABILITY_IDS[a.ability_id]:
        if func.function_type in actions.POINT_REQUIRED_FUNCS[a.requires_point]:
          if func.general_id == 0 or not hide_specific_actions:
            available_actions.add(func.id)
            found_applicable = True
          if func.general_id != 0:  # Always offer generic actions.
            for general_func in actions.ABILITY_IDS[func.general_id]:
              if general_func.function_type is func.function_type:
                # Only the right type. Don't want to expose the general action
                # to minimap if only the screen version is available.
                available_actions.add(general_func.id)
                found_applicable = True
                break
      if not found_applicable:
        raise ValueError("Failed to find applicable action for {}".format(a))
    return list(available_actions)

  @sw.decorate
  def transform_action(self, obs, func_call, skip_available=False):
    """Transform an agent-style action to one that SC2 can consume.

    Args:
      obs: a `sc_pb.Observation` from the previous frame.
      func_call: a `FunctionCall` to be turned into a `sc_pb.Action`.
      skip_available: If True, assume the action is available. This should only
          be used for testing or if you expect to make actions that weren't
          valid at the last observation.

    Returns:
      a corresponding `sc_pb.Action`.

    Raises:
      ValueError: if the action doesn't pass validation.
    """
    # Ignore sc_pb.Action's to make the env more flexible, eg raw actions.
    if isinstance(func_call, sc_pb.Action):
      return func_call

    func_id = func_call.function
    try:
      if self._raw:
        func = actions.RAW_FUNCTIONS[func_id]
      else:
        func = actions.FUNCTIONS[func_id]
    except KeyError:
      raise ValueError("Invalid function id: %s." % func_id)

    # Available?
    if not (skip_available or self._raw or
            func_id in self.available_actions(obs)):
      raise ValueError("Function %s/%s is currently not available" % (
          func_id, func.name))

    # Right number of args?
    if len(func_call.arguments) != len(func.args):
      raise ValueError(
          "Wrong number of arguments for function: %s, got: %s" % (
              func, func_call.arguments))

    # Args are valid?
    aif = self._agent_interface_format
    for t, arg in zip(func.args, func_call.arguments):
      if t.count:
        if 1 <= len(arg) <= t.count:
          continue
        else:
          raise ValueError(
              "Wrong number of values for argument of %s, got: %s" % (
                  func, func_call.arguments))

      if t.name in ("screen", "screen2"):
        sizes = aif.action_dimensions.screen
      elif t.name == "minimap":
        sizes = aif.action_dimensions.minimap
      elif t.name == "world":
        sizes = aif.raw_resolution
      else:
        sizes = t.sizes

      if len(sizes) != len(arg):
        raise ValueError(
            "Wrong number of values for argument of %s, got: %s" % (
                func, func_call.arguments))

      for s, a in zip(sizes, arg):
        if not np.all(0 <= a) and np.all(a < s):
          raise ValueError("Argument is out of range for %s, got: %s" % (
              func, func_call.arguments))

    # Convert them to python types.
    kwargs = {type_.name: type_.fn(a)
              for type_, a in zip(func.args, func_call.arguments)}

    # Call the right callback to get an SC2 action proto.
    sc2_action = sc_pb.Action()
    kwargs["action"] = sc2_action
    if func.ability_id:
      kwargs["ability_id"] = func.ability_id

    if self._raw:
      if "world" in kwargs:
        kwargs["world"] = self._world_to_minimap_px.back_pt(kwargs["world"])
      def find_original_tag(position):
        if position >= len(self._raw_tags):  # Assume it's a real unit tag.
          return position
        original_tag = self._raw_tags[position]
        if original_tag == 0:
          logging.warning("Tag not found: %s", original_tag)
        return original_tag
      if "target_unit_tag" in kwargs:
        kwargs["target_unit_tag"] = find_original_tag(
            kwargs["target_unit_tag"][0])
      if "unit_tags" in kwargs:
        kwargs["unit_tags"] = [find_original_tag(t)
                               for t in kwargs["unit_tags"]]
      actions.RAW_FUNCTIONS[func_id].function_type(**kwargs)
    else:
      kwargs["action_space"] = aif.action_space
      actions.FUNCTIONS[func_id].function_type(**kwargs)
    return sc2_action

  @sw.decorate
  def reverse_action(self, action):
    """Transform an SC2-style action into an agent-style action.

    This should be the inverse of `transform_action`.

    Args:
      action: a `sc_pb.Action` to be transformed.

    Returns:
      A corresponding `actions.FunctionCall`.

    Raises:
      ValueError: if it doesn't know how to transform this action.
    """
    FUNCTIONS = actions.FUNCTIONS  # pylint: disable=invalid-name

    aif = self._agent_interface_format

    def func_call_ability(ability_id, cmd_type, *args):
      """Get the function id for a specific ability id and action type."""
      if ability_id not in actions.ABILITY_IDS:
        logging.warning("Unknown ability_id: %s. This is probably dance or "
                        "cheer, or some unknown new or map specific ability. "
                        "Treating it as a no-op.", ability_id)
        return FUNCTIONS.no_op()

      if aif.hide_specific_actions:
        general_id = next(iter(actions.ABILITY_IDS[ability_id])).general_id
        if general_id:
          ability_id = general_id

      for func in actions.ABILITY_IDS[ability_id]:
        if func.function_type is cmd_type:
          return FUNCTIONS[func.id](*args)
      raise ValueError("Unknown ability_id: %s, type: %s. Likely a bug." % (
          ability_id, cmd_type.__name__))

    if action.HasField("action_ui"):
      act_ui = action.action_ui
      if act_ui.HasField("multi_panel"):
        return FUNCTIONS.select_unit(act_ui.multi_panel.type - 1,
                                     act_ui.multi_panel.unit_index)
      if act_ui.HasField("control_group"):
        return FUNCTIONS.select_control_group(
            act_ui.control_group.action - 1,
            act_ui.control_group.control_group_index)
      if act_ui.HasField("select_idle_worker"):
        return FUNCTIONS.select_idle_worker(act_ui.select_idle_worker.type - 1)
      if act_ui.HasField("select_army"):
        return FUNCTIONS.select_army(act_ui.select_army.selection_add)
      if act_ui.HasField("select_warp_gates"):
        return FUNCTIONS.select_warp_gates(
            act_ui.select_warp_gates.selection_add)
      if act_ui.HasField("select_larva"):
        return FUNCTIONS.select_larva()
      if act_ui.HasField("cargo_panel"):
        return FUNCTIONS.unload(act_ui.cargo_panel.unit_index)
      if act_ui.HasField("production_panel"):
        return FUNCTIONS.build_queue(act_ui.production_panel.unit_index)
      if act_ui.HasField("toggle_autocast"):
        return func_call_ability(act_ui.toggle_autocast.ability_id,
                                 actions.autocast)

    if (action.HasField("action_feature_layer") or
        action.HasField("action_render")):
      act_sp = actions.spatial(action, aif.action_space)
      if act_sp.HasField("camera_move"):
        coord = point.Point.build(act_sp.camera_move.center_minimap)
        return FUNCTIONS.move_camera(coord)
      if act_sp.HasField("unit_selection_point"):
        select_point = act_sp.unit_selection_point
        coord = point.Point.build(select_point.selection_screen_coord)
        return FUNCTIONS.select_point(select_point.type - 1, coord)
      if act_sp.HasField("unit_selection_rect"):
        select_rect = act_sp.unit_selection_rect
        # TODO(tewalds): After looking at some replays we should decide if
        # this is good enough. Maybe we need to simulate multiple actions or
        # merge the selection rects into a bigger one.
        tl = point.Point.build(select_rect.selection_screen_coord[0].p0)
        br = point.Point.build(select_rect.selection_screen_coord[0].p1)
        return FUNCTIONS.select_rect(select_rect.selection_add, tl, br)
      if act_sp.HasField("unit_command"):
        cmd = act_sp.unit_command
        queue = int(cmd.queue_command)
        if cmd.HasField("target_screen_coord"):
          coord = point.Point.build(cmd.target_screen_coord)
          return func_call_ability(cmd.ability_id, actions.cmd_screen,
                                   queue, coord)
        elif cmd.HasField("target_minimap_coord"):
          coord = point.Point.build(cmd.target_minimap_coord)
          return func_call_ability(cmd.ability_id, actions.cmd_minimap,
                                   queue, coord)
        else:
          return func_call_ability(cmd.ability_id, actions.cmd_quick, queue)

    if action.HasField("action_raw") or action.HasField("action_render"):
      raise ValueError("Unknown action:\n%s" % action)

    return FUNCTIONS.no_op()

  @sw.decorate
  def reverse_raw_action(self, action, prev_obs):
    """Transform an SC2-style action into an agent-style action.

    This should be the inverse of `transform_action`.

    Args:
      action: a `sc_pb.Action` to be transformed.
      prev_obs: an obs to figure out tags.

    Returns:
      A corresponding `actions.FunctionCall`.

    Raises:
      ValueError: if it doesn't know how to transform this action.
    """
    aif = self._agent_interface_format
    raw_tags = prev_obs["raw_units"][:, FeatureUnit.tag]
    def find_tag_position(original_tag):
      for i, tag in enumerate(raw_tags):
        if tag == original_tag:
          return i
      logging.warning("Not found tag! %s", original_tag)
      return -1

    def func_call_ability(ability_id, cmd_type, *args):
      """Get the function id for a specific ability id and action type."""
      if ability_id not in actions.RAW_ABILITY_IDS:
        logging.warning("Unknown ability_id: %s. This is probably dance or "
                        "cheer, or some unknown new or map specific ability. "
                        "Treating it as a no-op.", ability_id)
        return actions.RAW_FUNCTIONS.no_op()

      if aif.hide_specific_actions:
        general_id = next(iter(actions.RAW_ABILITY_IDS[ability_id])).general_id
        if general_id:
          ability_id = general_id

      for func in actions.RAW_ABILITY_IDS[ability_id]:
        if func.function_type is cmd_type:
          return actions.RAW_FUNCTIONS[func.id](*args)
      raise ValueError("Unknown ability_id: %s, type: %s. Likely a bug." % (
          ability_id, cmd_type.__name__))

    if action.HasField("action_raw"):
      raw_act = action.action_raw
      if raw_act.HasField("unit_command"):
        uc = raw_act.unit_command
        ability_id = uc.ability_id
        queue_command = uc.queue_command
        unit_tags = (find_tag_position(t) for t in uc.unit_tags)
        # Remove invalid units.
        unit_tags = [t for t in unit_tags if t != -1]
        if not unit_tags:
          return actions.RAW_FUNCTIONS.no_op()

        if uc.HasField("target_unit_tag"):
          target_unit_tag = find_tag_position(uc.target_unit_tag)
          if target_unit_tag == -1:
            return actions.RAW_FUNCTIONS.no_op()
          return func_call_ability(ability_id, actions.raw_cmd_unit,
                                   queue_command, unit_tags, target_unit_tag)
        if uc.HasField("target_world_space_pos"):
          coord = point.Point.build(uc.target_world_space_pos)
          coord = self._world_to_minimap_px.fwd_pt(coord)
          return func_call_ability(ability_id, actions.raw_cmd_pt,
                                   queue_command, unit_tags, coord)
        else:
          return func_call_ability(ability_id, actions.raw_cmd,
                                   queue_command, unit_tags)

      if raw_act.HasField("toggle_autocast"):
        uc = raw_act.toggle_autocast
        ability_id = uc.ability_id
        unit_tags = (find_tag_position(t) for t in uc.unit_tags)
        # Remove invalid units.
        unit_tags = [t for t in unit_tags if t != -1]
        if not unit_tags:
          return actions.RAW_FUNCTIONS.no_op()
        return func_call_ability(ability_id, actions.raw_autocast, unit_tags)

      if raw_act.HasField("unit_command"):
        raise ValueError("Unknown action:\n%s" % action)

      if raw_act.HasField("camera_move"):
        coord = point.Point.build(raw_act.camera_move.center_world_space)
        coord = self._world_to_minimap_px.fwd_pt(coord)
        return actions.RAW_FUNCTIONS.raw_move_camera(coord)

    return actions.RAW_FUNCTIONS.no_op()
