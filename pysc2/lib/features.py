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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
from absl import logging

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
    "unit_shields_ratio", "unit_density", "unit_density_aa", "effects"])):
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
    "player_relative", "selected"])):
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
    height_map=(256, FeatureType.SCALAR, colors.winter, False),
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
)

MINIMAP_FEATURES = MinimapFeatures(
    height_map=(256, FeatureType.SCALAR, colors.winter),
    visibility_map=(4, FeatureType.CATEGORICAL, colors.VISIBILITY_PALETTE),
    creep=(2, FeatureType.CATEGORICAL, colors.CREEP_PALETTE),
    camera=(2, FeatureType.CATEGORICAL, colors.CAMERA_PALETTE),
    player_id=(17, FeatureType.CATEGORICAL, colors.PLAYER_ABSOLUTE_PALETTE),
    player_relative=(5, FeatureType.CATEGORICAL,
                     colors.PLAYER_RELATIVE_PALETTE),
    selected=(2, FeatureType.CATEGORICAL, colors.winter),
)


def point_from_size_width_height(size, width, height):
  """Get a point from size, width and height."""
  if not size and not width and not height:
    return None
  if size:
    if width or height:
      raise ValueError("Either specify size or width and height, not both.")
    return point.Point(size, size)
  if width and height:
    return point.Point(width, height)
  else:
    raise ValueError("Specify both width and height.")


class Features(object):
  """Render feature layers from SC2 Observation protos into numpy arrays.

  This has the implementation details of how to render a starcraft environment.
  It translates between agent action/observation formats and starcraft
  action/observation formats, which should not be seen by agent authors. The
  starcraft protos contain more information than they should have access to.

  This is outside of the environment so that it can also be used in other
  contexts, eg a supervised dataset pipeline.
  """

  def __init__(self,
               _only_use_kwargs=None,
               game_info=None,
               feature_screen_size=None,
               feature_screen_width=None,
               feature_screen_height=None,
               feature_minimap_size=None,
               feature_minimap_width=None,
               feature_minimap_height=None,
               rgb_screen_size=None,
               rgb_screen_width=None,
               rgb_screen_height=None,
               rgb_minimap_size=None,
               rgb_minimap_width=None,
               rgb_minimap_height=None,
               use_feature_units=False,
               map_size=None,
               camera_width_world_units=None,
               action_space=None,
               hide_specific_actions=True):
    """Initialize a Features instance.

    You must specify the resolutions. This can come from a game_info object from
    the game, or you can specify them directly. If you specify size then both
    width and height will take that value.

    Args:
      _only_use_kwargs: Don't pass args, only kwargs.
      game_info: A `sc_pb.ResponseGameInfo` from the game. Can be None if you
          instead set the sizes explicitly.
      feature_screen_size: Sets feature_screen_width and feature_screen_width.
      feature_screen_width: The width of the feature layer screen observation.
      feature_screen_height: The height of the feature layer screen observation.
      feature_minimap_size: Sets feature_minimap_width and
          feature_minimap_height.
      feature_minimap_width: The width of the feature layer minimap observation.
      feature_minimap_height: The height of the feature layer minimap
          observation.
      rgb_screen_size: Sets rgb_screen_width and rgb_screen_height.
      rgb_screen_width: The width of the rgb screen observation.
      rgb_screen_height: The height of the rgb screen observation.
      rgb_minimap_size: Sets rgb_minimap_width and rgb_minimap_height.
      rgb_minimap_width: The width of the rgb minimap observation.
      rgb_minimap_height: The height of the rgb minimap observation.
      use_feature_units: Whether to include the feature unit observation.
      map_size: The size of the map in world units, needed for feature_units.
      camera_width_world_units: The width of the feature layer camera in world
          units. This is needed for feature_units.
      action_space: If you pass both feature and rgb sizes, then you must also
          specify which you want to use for your actions as an ActionSpace enum.
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

    Raises:
      ValueError: if game_info is None and the resolutions aren't well
          specified.
      ValueError: if the action_space is poorly specified or doesn't match the
          observations.
    """
    if _only_use_kwargs:
      raise ValueError("All arguments must be passed as keyword arguments.")

    if game_info:
      if any(
          (feature_screen_size, feature_screen_width, feature_screen_height,
           feature_minimap_size, feature_minimap_width, feature_minimap_height,
           rgb_screen_size, rgb_screen_width, rgb_screen_height,
           rgb_minimap_size, rgb_minimap_width, rgb_minimap_height)):
        raise ValueError(
            "Either pass the game_info or explicit sizes, not both.")

      if game_info.options.HasField("feature_layer"):
        fl_opts = game_info.options.feature_layer
        self._feature_screen_px = point.Point.build(fl_opts.resolution)
        self._feature_minimap_px = point.Point.build(fl_opts.minimap_resolution)
      else:
        self._feature_screen_px = self._feature_minimap_px = None
      if game_info.options.HasField("render"):
        render_opts = game_info.options.render
        self._rgb_screen_px = point.Point.build(render_opts.resolution)
        self._rgb_minimap_px = point.Point.build(render_opts.minimap_resolution)
      else:
        self._rgb_screen_px = self._rgb_minimap_px = None
      if use_feature_units:
        self._init_camera(game_info.start_raw.map_size,
                          game_info.options.feature_layer.width)
    else:
      self._feature_screen_px = point_from_size_width_height(
          feature_screen_size, feature_screen_width, feature_screen_height)
      self._feature_minimap_px = point_from_size_width_height(
          feature_minimap_size, feature_minimap_width, feature_minimap_height)
      self._rgb_screen_px = point_from_size_width_height(
          rgb_screen_size, rgb_screen_width, rgb_screen_height)
      self._rgb_minimap_px = point_from_size_width_height(
          rgb_minimap_size, rgb_minimap_width, rgb_minimap_height)
      if use_feature_units:
        self._init_camera(map_size, camera_width_world_units)

    if bool(self._feature_screen_px) != bool(self._feature_minimap_px):
      raise ValueError("Must set all the feature layer sizes.")
    if bool(self._rgb_screen_px) != bool(self._rgb_minimap_px):
      raise ValueError("Must set all the rgb sizes.")
    if not self._feature_screen_px and not self._rgb_screen_px:
      raise ValueError("Must set either the feature layer or rgb sizes.")

    if action_space:
      if not isinstance(action_space, actions.ActionSpace):
        raise ValueError("action_space must be of type ActionSpace.")
      if ((action_space == actions.ActionSpace.FEATURES and
           not self._feature_screen_px) or
          (action_space == actions.ActionSpace.RGB and
           not self._rgb_screen_px)):
        raise ValueError("Action space must match the observations.")
      self._action_space = action_space
    else:
      if self._feature_screen_px and self._rgb_screen_px:
        raise ValueError(
            "You must specify the action space if you have both observations.")
      if self._feature_screen_px:
        self._action_space = actions.ActionSpace.FEATURES
      else:
        self._action_space = actions.ActionSpace.RGB

    if self._action_space == actions.ActionSpace.FEATURES:
      self._action_screen_px = self._feature_screen_px
      self._action_minimap_px = self._feature_minimap_px
    else:
      self._action_screen_px = self._rgb_screen_px
      self._action_minimap_px = self._rgb_minimap_px

    self._feature_units = use_feature_units
    self._hide_specific_actions = hide_specific_actions
    self._valid_functions = self._init_valid_functions()

  def _init_camera(self, map_size, camera_width_world_units):
    """Initialize the feature_units camera."""
    if not map_size or not camera_width_world_units:
      raise ValueError(
          "Either pass the game_info with raw enabled, or map_size and "
          "camera_width_world_units in order to use feature_units.")
    map_size = point.Point.build(map_size)
    self._world_to_world_tl = transform.Linear(point.Point(1, -1),
                                               point.Point(0, map_size.y))
    self._world_tl_to_world_camera_rel = transform.Linear(offset=-map_size / 4)
    world_camera_rel_to_feature_screen = transform.Linear(
        self._feature_screen_px / camera_width_world_units,
        self._feature_screen_px / 2)
    self._world_to_feature_screen_px = transform.Chain(
        self._world_to_world_tl,
        self._world_tl_to_world_camera_rel,
        world_camera_rel_to_feature_screen,
        transform.PixelToCoord())

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
    obs_spec = named_array.NamedDict({
        "action_result": (0,),  # See error.proto: ActionResult.
        "alerts": (0,),  # See sc2api.proto: Alert.
        "available_actions": (0,),
        "build_queue": (0, len(UnitLayer)),  # pytype: disable=wrong-arg-types
        "cargo": (0, len(UnitLayer)),  # pytype: disable=wrong-arg-types
        "cargo_slots_available": (1,),
        "control_groups": (10, 2),
        "game_loop": (1,),
        "last_actions": (0,),
        "multi_select": (0, len(UnitLayer)),  # pytype: disable=wrong-arg-types
        "player": (len(Player),),  # pytype: disable=wrong-arg-types
        "score_cumulative": (len(ScoreCumulative),),  # pytype: disable=wrong-arg-types
        "single_select": (0, len(UnitLayer)),  # Only (n, 7) for n in (0, 1).  # pytype: disable=wrong-arg-types
    })
    if self._feature_screen_px:
      obs_spec["feature_screen"] = (len(SCREEN_FEATURES),
                                    self._feature_screen_px.y,
                                    self._feature_screen_px.x)
    if self._feature_minimap_px:
      obs_spec["feature_minimap"] = (len(MINIMAP_FEATURES),
                                     self._feature_minimap_px.y,
                                     self._feature_minimap_px.x)
    if self._rgb_screen_px:
      obs_spec["rgb_screen"] = (self._rgb_screen_px.y,
                                self._rgb_screen_px.x,
                                3)
    if self._rgb_minimap_px:
      obs_spec["rgb_minimap"] = (self._rgb_minimap_px.y,
                                 self._rgb_minimap_px.x,
                                 3)
    if self._feature_units:
      obs_spec["feature_units"] = (0, len(FeatureUnit))  # pytype: disable=wrong-arg-types
    return obs_spec

  def action_spec(self):
    """The action space pretty complicated and fills the ValidFunctions."""
    return self._valid_functions

  @sw.decorate
  def transform_obs(self, obs):
    """Render some SC2 observations into something an agent can handle."""
    empty = np.array([], dtype=np.int32).reshape((0, 7))
    out = named_array.NamedDict({  # Fill out some that are sometimes empty.
        "single_select": empty,
        "multi_select": empty,
        "build_queue": empty,
        "cargo": empty,
        "cargo_slots_available": np.array([0], dtype=np.int32),
    })

    def or_zeros(layer, size):
      if layer is not None:
        return layer.astype(np.int32, copy=False)
      else:
        return np.zeros((size.y, size.x), dtype=np.int32)

    if self._feature_screen_px:
      out["feature_screen"] = named_array.NamedNumpyArray(
          np.stack(or_zeros(f.unpack(obs.observation), self._feature_screen_px)
                   for f in SCREEN_FEATURES),
          names=[ScreenFeatures, None, None])
    if self._feature_minimap_px:
      out["feature_minimap"] = named_array.NamedNumpyArray(
          np.stack(or_zeros(f.unpack(obs.observation), self._feature_minimap_px)
                   for f in MINIMAP_FEATURES),
          names=[MinimapFeatures, None, None])
    if self._rgb_screen_px:
      out["rgb_screen"] = Feature.unpack_rgb_image(
          obs.observation.render_data.map).astype(np.int32)
    if self._rgb_minimap_px:
      out["rgb_minimap"] = Feature.unpack_rgb_image(
          obs.observation.render_data.minimap).astype(np.int32)

    out["last_actions"] = np.array(
        [self.reverse_action(a).function for a in obs.actions],
        dtype=np.int32)

    out["action_result"] = np.array([o.result for o in obs.action_errors],
                                    dtype=np.int32)

    out["alerts"] = np.array(obs.observation.alerts, dtype=np.int32)

    out["game_loop"] = np.array([obs.observation.game_loop], dtype=np.int32)

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

      if ui.single:
        out["single_select"] = named_array.NamedNumpyArray(
            [unit_vec(ui.single.unit)], [None, UnitLayer])

      if ui.multi and ui.multi.units:
        out["multi_select"] = named_array.NamedNumpyArray(
            [unit_vec(u) for u in ui.multi.units], [None, UnitLayer])

      if ui.cargo and ui.cargo.passengers:
        out["single_select"] = named_array.NamedNumpyArray(
            [unit_vec(ui.single.unit)], [None, UnitLayer])
        out["cargo"] = named_array.NamedNumpyArray(
            [unit_vec(u) for u in ui.cargo.passengers], [None, UnitLayer])
        out["cargo_slots_available"] = np.array([ui.cargo.slots_available],
                                                dtype=np.int32)

      if ui.production and ui.production.build_queue:
        out["single_select"] = named_array.NamedNumpyArray(
            [unit_vec(ui.production.unit)], [None, UnitLayer])
        out["build_queue"] = named_array.NamedNumpyArray(
            [unit_vec(u) for u in ui.production.build_queue],
            [None, UnitLayer])

    def feature_unit_vec(u):
      screen_pos = self._world_to_feature_screen_px.fwd_pt(
          point.Point.build(u.pos))
      screen_radius = self._world_to_feature_screen_px.fwd_dist(u.radius)
      return np.array((
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
      ), dtype=np.int32)

    raw = obs.observation.raw_data

    if self._feature_units:
      with sw("feature_units"):
        # Update the camera location so we can calculate world to screen pos
        self._update_camera(point.Point.build(raw.player.camera))
        feature_units = []
        for u in raw.units:
          if u.is_on_screen and u.display_type != sc_raw.Hidden:
            feature_units.append(feature_unit_vec(u))
        out["feature_units"] = named_array.NamedNumpyArray(
            feature_units, [None, FeatureUnit], dtype=np.int32)

    out["available_actions"] = np.array(self.available_actions(obs.observation),
                                        dtype=np.int32)

    return out

  @sw.decorate
  def available_actions(self, obs):
    """Return the list of available action ids."""
    available_actions = set()
    for i, func in six.iteritems(actions.FUNCTIONS_AVAILABLE):
      if func.avail_fn(obs):
        available_actions.add(i)
    for a in obs.abilities:
      if a.ability_id not in actions.ABILITY_IDS:
        logging.warning("Unknown ability %s seen as available.", a.ability_id)
        continue
      for func in actions.ABILITY_IDS[a.ability_id]:
        if func.function_type in actions.POINT_REQUIRED_FUNCS[a.requires_point]:
          if func.general_id == 0 or not self._hide_specific_actions:
            available_actions.add(func.id)
          if func.general_id != 0:  # Always offer generic actions.
            for general_func in actions.ABILITY_IDS[func.general_id]:
              if general_func.function_type is func.function_type:
                # Only the right type. Don't want to expose the general action
                # to minimap if only the screen version is available.
                available_actions.add(general_func.id)
                break
    return list(available_actions)

  @sw.decorate
  def transform_action(self, obs, func_call, skip_available=False):
    """Tranform an agent-style action to one that SC2 can consume.

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
    func_id = func_call.function
    try:
      func = actions.FUNCTIONS[func_id]
    except KeyError:
      raise ValueError("Invalid function id: %s." % func_id)

    # Available?
    if not (skip_available or func_id in self.available_actions(obs)):
      raise ValueError("Function %s/%s is currently not available" % (
          func_id, func.name))

    # Right number of args?
    if len(func_call.arguments) != len(func.args):
      raise ValueError(
          "Wrong number of arguments for function: %s, got: %s" % (
              func, func_call.arguments))

    # Args are valid?
    for t, arg in zip(func.args, func_call.arguments):
      if t.name in ("screen", "screen2"):
        sizes = self._action_screen_px
      elif t.name == "minimap":
        sizes = self._action_minimap_px
      else:
        sizes = t.sizes

      if len(sizes) != len(arg):
        raise ValueError(
            "Wrong number of values for argument of %s, got: %s" % (
                func, func_call.arguments))

      for s, a in zip(sizes, arg):
        if not 0 <= a < s:
          raise ValueError("Argument is out of range for %s, got: %s" % (
              func, func_call.arguments))

    # Convert them to python types.
    kwargs = {type_.name: type_.fn(a)
              for type_, a in zip(func.args, func_call.arguments)}

    # Call the right callback to get an SC2 action proto.
    sc2_action = sc_pb.Action()
    kwargs["action"] = sc2_action
    kwargs["action_space"] = self._action_space
    if func.ability_id:
      kwargs["ability_id"] = func.ability_id
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

    def func_call_ability(ability_id, cmd_type, *args):
      """Get the function id for a specific ability id and action type."""
      if ability_id not in actions.ABILITY_IDS:
        logging.warning("Unknown ability_id: %s. This is probably dance or "
                        "cheer, or some unknown new or map specific ability. "
                        "Treating it as a no-op.", ability_id)
        return FUNCTIONS.no_op()

      if self._hide_specific_actions:
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
      act_sp = actions.spatial(action, self._action_space)
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

  def _init_valid_functions(self):
    """Initialize ValidFunctions and set up the callbacks."""
    sizes = {
        "screen": tuple(int(i) for i in self._action_screen_px),
        "screen2": tuple(int(i) for i in self._action_screen_px),
        "minimap": tuple(int(i) for i in self._action_minimap_px),
    }

    types = actions.Arguments(*[
        actions.ArgumentType.spec(t.id, t.name, sizes.get(t.name, t.sizes))
        for t in actions.TYPES])

    functions = actions.Functions([
        actions.Function.spec(f.id, f.name, tuple(types[t.id] for t in f.args))
        for f in actions.FUNCTIONS])

    return actions.ValidActions(types, functions)
