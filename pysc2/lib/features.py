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
from pysc2.lib import point
from pysc2.lib import stopwatch

from s2clientprotocol import sc2api_pb2 as sc_pb

sw = stopwatch.sw


class FeatureType(enum.Enum):
  SCALAR = 1
  CATEGORICAL = 2


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
    data = np.fromstring(plane.data, dtype=Feature.dtypes[plane.bits_per_pixel])
    if plane.bits_per_pixel == 1:
      data = np.unpackbits(data)
    return data.reshape(size.transpose())

  @staticmethod
  @sw.decorate
  def unpack_rgb_image(plane):
    """Return a correctly shaped numpy array given the image bytes."""
    assert plane.bits_per_pixel == 24
    size = point.Point.build(plane.size)
    data = np.fromstring(plane.data, dtype=np.uint8)
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
    return super(ScreenFeatures, cls).__new__(cls, **feats)


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
    return super(MinimapFeatures, cls).__new__(cls, **feats)


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
    unit_type=(1850, FeatureType.CATEGORICAL, colors.unit_type, False),
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


class Features(object):
  """Render feature layers from SC2 Observation protos into numpy arrays.

  This has the implementation details of how to render a starcraft environment.
  It translates between agent action/observation formats and starcraft
  action/observation formats, which should not be seen by agent authors. The
  starcraft protos contain more information than they should have access to.

  This is outside of the environment so that it can also be used in other
  contexts, eg a supervised dataset pipeline.
  """

  def __init__(self, game_info=None, screen_size_px=None, minimap_size_px=None,
               hide_specific_actions=True):
    """Initialize a Features instance.

    Args:
      game_info: A `sc_pb.ResponseGameInfo` from the game. Can be None if you
          instead set `screen_size_px` and `minimap_size_px`.
      screen_size_px: The screen resolution.
      minimap_size_px: The minimap resolution.
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
      ValueError: if game_info is None and screen or minimap sizes are missing.
    """
    if game_info:
      fl_opts = game_info.options.feature_layer
      screen_size_px = point.Point.build(fl_opts.resolution)
      minimap_size_px = point.Point.build(fl_opts.minimap_resolution)
    elif not (screen_size_px and minimap_size_px):
      raise ValueError(
          "Must provide either game_info or screen and minimap sizes")
    self._screen_size_px = point.Point(*screen_size_px)
    self._minimap_size_px = point.Point(*minimap_size_px)
    self._hide_specific_actions = hide_specific_actions
    self._valid_functions = self._init_valid_functions()

  def observation_spec(self):
    """The observation spec for the SC2 environment.

    Returns:
      The dict of observation names to their tensor shapes. Shapes with a 0 can
      vary in length, for example the number of valid actions depends on which
      units you have selected.
    """
    return {
        "screen": (len(SCREEN_FEATURES),
                   self._screen_size_px.y,
                   self._screen_size_px.x),
        "minimap": (len(MINIMAP_FEATURES),
                    self._minimap_size_px.y,
                    self._minimap_size_px.x),
        "player": (11,),
        "game_loop": (1,),
        "score_cumulative": (13,),
        "available_actions": (0,),
        "single_select": (0, 7),  # Actually only (n, 7) for n in (0, 1)
        "multi_select": (0, 7),
        "cargo": (0, 7),
        "cargo_slots_available": (1,),
        "build_queue": (0, 7),
        "control_groups": (10, 2),
    }

  def action_spec(self):
    """The action space pretty complicated and fills the ValidFunctions."""
    return self._valid_functions

  @sw.decorate
  def transform_obs(self, obs):
    """Render some SC2 observations into something an agent can handle."""
    empty = np.array([], dtype=np.int32).reshape((0, 7))
    out = {  # Fill out some that are sometimes empty.
        "single_select": empty,
        "multi_select": empty,
        "build_queue": empty,
        "cargo": empty,
        "cargo_slots_available": np.array([0], dtype=np.int32),
    }

    def or_zeros(layer, size):
      if layer is not None:
        return layer.astype(np.int32, copy=False)
      else:
        return np.zeros(size.transpose(), dtype=np.int32)

    with sw("feature_layers"):
      out["screen"] = np.stack(or_zeros(f.unpack(obs), self._screen_size_px)
                               for f in SCREEN_FEATURES)
      out["minimap"] = np.stack(or_zeros(f.unpack(obs), self._minimap_size_px)
                                for f in MINIMAP_FEATURES)

    out["game_loop"] = np.array([obs.game_loop], dtype=np.int32)
    out["score_cumulative"] = np.array([
        obs.score.score,
        obs.score.score_details.idle_production_time,
        obs.score.score_details.idle_worker_time,
        obs.score.score_details.total_value_units,
        obs.score.score_details.total_value_structures,
        obs.score.score_details.killed_value_units,
        obs.score.score_details.killed_value_structures,
        obs.score.score_details.collected_minerals,
        obs.score.score_details.collected_vespene,
        obs.score.score_details.collection_rate_minerals,
        obs.score.score_details.collection_rate_vespene,
        obs.score.score_details.spent_minerals,
        obs.score.score_details.spent_vespene,
    ], dtype=np.int32)
    out["player"] = np.array([
        obs.player_common.player_id,
        obs.player_common.minerals,
        obs.player_common.vespene,
        obs.player_common.food_used,
        obs.player_common.food_cap,
        obs.player_common.food_army,
        obs.player_common.food_workers,
        obs.player_common.idle_worker_count,
        obs.player_common.army_count,
        obs.player_common.warp_gate_count,
        obs.player_common.larva_count,
    ], dtype=np.int32)

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

    ui = obs.ui_data

    with sw("ui"):
      groups = np.zeros((10, 2), dtype=np.int32)
      for g in ui.groups:
        groups[g.control_group_index, :] = (g.leader_unit_type, g.count)
      out["control_groups"] = groups

      if ui.single:
        out["single_select"] = np.array([unit_vec(ui.single.unit)])

      if ui.multi and ui.multi.units:
        out["multi_select"] = np.stack(unit_vec(u) for u in ui.multi.units)

      if ui.cargo and ui.cargo.passengers:
        out["single_select"] = np.array([unit_vec(ui.single.unit)])
        out["cargo"] = np.stack(unit_vec(u) for u in ui.cargo.passengers)
        out["cargo_slots_available"] = np.array([ui.cargo.slots_available],
                                                dtype=np.int32)

      if ui.production and ui.production.build_queue:
        out["single_select"] = np.array([unit_vec(ui.production.unit)])
        out["build_queue"] = np.stack(unit_vec(u)
                                      for u in ui.production.build_queue)

    out["available_actions"] = np.array(self.available_actions(obs),
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
        sizes = self._screen_size_px
      elif t.name == "minimap":
        sizes = self._minimap_size_px
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
    def func_call(func_id, args):
      return actions.FunctionCall(func_id, [[int(v) for v in a] for a in args])

    def func_call_ability(ability_id, cmd_type, args):
      """Get the function id for a specific ability id and action type."""
      if ability_id not in actions.ABILITY_IDS:
        logging.warning("Unknown ability_id: %s. This is probably dance or "
                        "cheer, or some unknown new or map specific ability. "
                        "Treating it as a no-op.", ability_id)
        return func_call_name("no_op", [])

      if self._hide_specific_actions:
        general_id = next(iter(actions.ABILITY_IDS[ability_id])).general_id
        if general_id:
          ability_id = general_id

      for func in actions.ABILITY_IDS[ability_id]:
        if func.function_type is cmd_type:
          return func_call(func.id, args)
      raise ValueError("Unknown ability_id: %s, type: %s. Likely a bug." % (
          ability_id, cmd_type.__name__))

    def func_call_name(name, args):
      return func_call(actions.FUNCTIONS[name].id, args)

    if action.HasField("action_ui"):
      act_ui = action.action_ui
      if act_ui.HasField("multi_panel"):
        return func_call_name("select_unit", [[act_ui.multi_panel.type - 1],
                                              [act_ui.multi_panel.unit_index]])
      if act_ui.HasField("control_group"):
        return func_call_name("select_control_group",
                              [[act_ui.control_group.action - 1],
                               [act_ui.control_group.control_group_index]])
      if act_ui.HasField("select_idle_worker"):
        return func_call_name("select_idle_worker",
                              [[act_ui.select_idle_worker.type - 1]])
      if act_ui.HasField("select_army"):
        return func_call_name("select_army",
                              [[act_ui.select_army.selection_add]])
      if act_ui.HasField("select_warp_gates"):
        return func_call_name("select_warp_gates",
                              [[act_ui.select_warp_gates.selection_add]])
      if act_ui.HasField("select_larva"):
        return func_call_name("select_larva", [])
      if act_ui.HasField("cargo_panel"):
        return func_call_name("unload", [[act_ui.cargo_panel.unit_index]])
      if act_ui.HasField("production_panel"):
        return func_call_name("build_queue",
                              [[act_ui.production_panel.unit_index]])
      if act_ui.HasField("toggle_autocast"):
        return func_call_ability(act_ui.toggle_autocast.ability_id,
                                 actions.autocast, [])

    if action.HasField("action_feature_layer"):
      act_fl = action.action_feature_layer
      if act_fl.HasField("camera_move"):
        coord = point.Point.build(act_fl.camera_move.center_minimap)
        return func_call_name("move_camera", [coord])
      if act_fl.HasField("unit_selection_point"):
        select_point = act_fl.unit_selection_point
        coord = point.Point.build(select_point.selection_screen_coord)
        return func_call_name("select_point", [[select_point.type - 1], coord])
      if act_fl.HasField("unit_selection_rect"):
        select_rect = act_fl.unit_selection_rect
        if len(select_rect.selection_screen_coord) > 1:
          # TODO(tewalds): After looking at some replays we should decide if
          # this is good enough. Maybe we need to simulate multiple actions or
          # merge the selection rects into a bigger one.
          logging.info("Multi-rect selection, just using the first one:\n%s",
                       select_rect.selection_screen_coord)
        tl = point.Point.build(select_rect.selection_screen_coord[0].p0)
        br = point.Point.build(select_rect.selection_screen_coord[0].p1)
        return func_call_name("select_rect", [[select_rect.selection_add],
                                              [tl.x, tl.y], [br.x, br.y]])
      if act_fl.HasField("unit_command"):
        cmd = act_fl.unit_command
        queue = [int(cmd.queue_command)]
        if cmd.HasField("target_screen_coord"):
          coord = point.Point.build(cmd.target_screen_coord)
          return func_call_ability(cmd.ability_id, actions.cmd_screen,
                                   [queue, coord])
        elif cmd.HasField("target_minimap_coord"):
          coord = point.Point.build(cmd.target_minimap_coord)
          return func_call_ability(cmd.ability_id, actions.cmd_minimap,
                                   [queue, coord])
        else:
          return func_call_ability(cmd.ability_id, actions.cmd_quick, [queue])

    if action.HasField("action_raw") or action.HasField("action_render"):
      raise ValueError("Unknown action:\n%s" % action)

    return func_call_name("no_op", [])  # No-op

  def _init_valid_functions(self):
    """Initialize ValidFunctions and set up the callbacks."""
    sizes = {
        "screen": tuple(int(i) for i in self._screen_size_px),
        "minimap": tuple(int(i) for i in self._minimap_size_px),
        "screen2": tuple(int(i) for i in self._screen_size_px),
    }

    types = actions.Arguments(*[
        actions.ArgumentType.spec(t.id, t.name, sizes.get(t.name, t.sizes))
        for t in actions.TYPES])

    functions = actions.Functions([
        actions.Function.spec(f.id, f.name, tuple(types[t.id] for t in f.args))
        for f in actions.FUNCTIONS])

    return actions.ValidActions(types, functions)
