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
"""A viewer for starcraft observations/replays."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import functools
import itertools
from absl import logging
import math
import threading
import time

import enum
from future.builtins import range  # pylint: disable=redefined-builtin
import numpy as np
import pygame
from six.moves import queue
from pysc2.lib import colors
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import remote_controller
from pysc2.lib import stopwatch
from pysc2.lib import transform

from s2clientprotocol import data_pb2 as sc_data
from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import spatial_pb2 as sc_spatial

sw = stopwatch.sw

render_lock = threading.Lock()  # Serialize all window/render operations.
obs_lock = threading.Lock()  # Protect the observations.


def with_lock(lock):
  """Make sure the lock is held while in this function."""
  def decorator(func):
    @functools.wraps(func)
    def _with_lock(*args, **kwargs):
      with lock:
        return func(*args, **kwargs)
    return _with_lock
  return decorator


def clamp(n, smallest, largest):
  return max(smallest, min(n, largest))


class MouseButtons(object):
  LEFT = 1
  MIDDLE = 2
  RIGHT = 3
  WHEEL_UP = 4
  WHEEL_DOWN = 5


class SurfType(enum.Enum):
  """Used to tell what a mouse click refers to."""
  CHROME = 1  # ie help, feature layer titles, etc
  SCREEN = 2
  MINIMAP = 3


class ActionCmd(enum.Enum):
  STEP = 1
  RESTART = 2
  QUIT = 3


class _Surface(object):
  """A surface to display on screen."""

  def __init__(self, surf, surf_type, surf_rect, world_to_surf, draw):
    """A surface to display on screen.

    Args:
      surf: The actual pygame.Surface (or subsurface).
      surf_type: A SurfType, used to tell how to treat clicks in that area.
      surf_rect: Rect of the surface relative to the window.
      world_to_surf: Convert a point relative to the surface to a world point.
      draw: A function that draws onto the surface.
    """
    self.surf = surf
    self.surf_type = surf_type
    self.surf_rect = surf_rect
    self.world_to_surf = world_to_surf
    self.draw = draw

  def draw_circle(self, color, world_loc, world_radius, thickness=0):
    """Draw a circle using world coordinates and radius."""
    if world_radius > 0:
      radius = max(1, int(self.world_to_surf.fwd_dist(world_radius)))
      pygame.draw.circle(self.surf, color,
                         self.world_to_surf.fwd_pt(world_loc).floor(),
                         radius, thickness if thickness < radius else 0)

  def draw_rect(self, color, world_rect, thickness=0):
    """Draw a rectangle using world coordinates."""
    tl = self.world_to_surf.fwd_pt(world_rect.tl).floor()
    br = self.world_to_surf.fwd_pt(world_rect.br).floor()
    rect = pygame.Rect(tl, br - tl)
    pygame.draw.rect(self.surf, color, rect, thickness)

  def blit_np_array(self, array):
    """Fill this surface using the contents of a numpy array."""
    with sw("make_surface"):
      raw_surface = pygame.surfarray.make_surface(array.transpose([1, 0, 2]))
    with sw("draw"):
      pygame.transform.scale(raw_surface, self.surf.get_size(), self.surf)


class MousePos(collections.namedtuple("MousePos", ["pos", "type"])):
  """Holds the mouse position in world coordinates and a SurfType."""
  __slots__ = ()


max_window_size = None
def _get_max_window_size():  # pylint: disable=g-wrong-blank-lines
  global max_window_size
  if max_window_size is None:
    display_info = pygame.display.Info()
    desktop_size = point.Point(display_info.current_w, display_info.current_h)
    max_window_size = desktop_size * 0.75
  return max_window_size


def circle_mask(shape, pt, radius):
  # ogrid is confusing but seems to be the best way to generate a circle mask.
  # http://docs.scipy.org/doc/numpy/reference/generated/numpy.ogrid.html
  # http://stackoverflow.com/questions/8647024/how-to-apply-a-disc-shaped-mask-to-a-numpy-array
  y, x = np.ogrid[-pt.y:shape.y - pt.y, -pt.x:shape.x - pt.x]
  # <= is important as radius will often come in as 0 due to rounding.
  return x**2 + y**2 <= radius**2


class RendererHuman(object):
  """Render starcraft obs with pygame such that it's playable by humans."""
  camera_actions = {  # camera moves by 3 world units.
      pygame.K_LEFT: point.Point(-3, 0),
      pygame.K_RIGHT: point.Point(3, 0),
      pygame.K_UP: point.Point(0, 3),
      pygame.K_DOWN: point.Point(0, -3),
  }

  shortcuts = [
      ("F4", "Quit the game"),
      ("F5", "Restart the map"),
      ("F8", "Toggle synchronous rendering"),
      ("F9", "Save a replay"),
      ("Ctrl++", "Zoom in"),
      ("Ctrl+-", "Zoom out"),
      ("PgUp/PgDn", "Increase/decrease the max game speed"),
      ("Ctrl+PgUp/PgDn", "Increase/decrease the step multiplier"),
      ("Pause", "Pause the game"),
      ("?", "This help screen"),
  ]

  def __init__(self, fps=22.4, step_mul=1, render_sync=False):
    """Create a renderer for use by humans.

    Make sure to call `init` with the game info, or just use `run`.

    Args:
      fps: How fast should the game be run.
      step_mul: How many game steps to take per observation.
      render_sync: Whether to wait for the obs to render before continuing.
    """
    self._fps = fps
    self._step_mul = step_mul
    self._render_sync = render_sync
    self._obs_queue = queue.Queue()
    self._render_thread = threading.Thread(target=self.render_thread,
                                           name="Renderer")
    self._render_thread.start()
    self._game_times = collections.deque(maxlen=100)  # Avg FPS over 100 frames.
    self._render_times = collections.deque(maxlen=100)
    self._last_time = time.time()
    self._last_game_loop = 0
    self._name_lengths = {}

  def close(self):
    if self._obs_queue:
      self._obs_queue.put(None)
      self._render_thread.join()
      self._obs_queue = None
      self._render_thread = None

  def init(self, game_info, static_data):
    """Take the game info and the static data needed to set up the game.

    This must be called before render or get_actions for each game or restart.

    Args:
      game_info: A `sc_pb.ResponseGameInfo` object for this game.
      static_data: A `StaticData` object for this game.
    """
    self._game_info = game_info
    self._static_data = static_data
    self._map_size = point.Point.build(game_info.start_raw.map_size)
    fl_opts = game_info.options.feature_layer
    self._feature_layer_screen_size = point.Point.build(fl_opts.resolution)
    self._feature_layer_minimap_size = point.Point.build(
        fl_opts.minimap_resolution)
    self._camera_width_world_units = fl_opts.width
    try:
      self.init_window()
      self._initialized = True
    except pygame.error as e:
      self._initialized = False
      logging.error("-" * 60)
      logging.error("Failed to initialize pygame: %s", e)
      logging.error("Continuing without pygame.")
      logging.error("If you're using ssh and have an X server, try ssh -X.")
      logging.error("-" * 60)

    self._obs = sc_pb.ResponseObservation()
    self.queued_action = None
    self.queued_hotkey = ""
    self.select_start = None
    self.help = False

  @with_lock(render_lock)
  @sw.decorate
  def init_window(self):
    """Initialize the pygame window and lay out the surfaces."""
    pygame.init()

    # Want a roughly square grid of feature layers, each being roughly square.
    num_feature_layers = (len(features.SCREEN_FEATURES) +
                          len(features.MINIMAP_FEATURES))
    cols = math.ceil(math.sqrt(num_feature_layers))
    rows = math.ceil(num_feature_layers / cols)
    features_layout = point.Point(cols, rows * 1.05)  # make room for titles

    # Scale such that features_layout and screen_aspect ratio have the same
    # height so that we can figure out the max window size and ratio of widths.
    screen_aspect_ratio = (self._feature_layer_screen_size *
                           (rows / self._feature_layer_screen_size.y))
    total = features_layout + point.Point(screen_aspect_ratio.x, 0)
    window_size_px = total.scale_max_size(_get_max_window_size()).ceil()

    # Create the actual window surface. This should only be blitted to from one
    # of the sub-surfaces defined below.
    self._window = pygame.display.set_mode(window_size_px, 0, 32)
    pygame.display.set_caption("Starcraft Viewer")

    # The sub-surfaces that the various draw functions will draw to.
    self.surfaces = []
    def add_surface(surf_type, surf_loc, world_to_surf, draw_fn):
      """Add a surface. Drawn in order and intersect in reverse order."""
      sub_surf = self._window.subsurface(
          pygame.Rect(surf_loc.tl, surf_loc.size))
      self.surfaces.append(_Surface(
          sub_surf, surf_type, surf_loc, world_to_surf, draw_fn))

    self.scale = window_size_px.y // 30
    self.font_small = pygame.font.Font(None, int(self.scale * 0.5))
    self.font_large = pygame.font.Font(None, self.scale)

    # Just flip so the base minimap is TL origin
    self._world_to_minimap = transform.Linear(point.Point(1, -1),
                                              point.Point(0, self._map_size.y))
    max_map_dim = self._map_size.max_dim()
    self._minimap_to_fl_minimap = transform.Linear(
        self._feature_layer_minimap_size / max_map_dim)
    self._world_to_fl_minimap = transform.Chain(
        self._world_to_minimap,
        self._minimap_to_fl_minimap,
        transform.Floor())

    # Flip and zoom to the camera area. Update the offset as the camera moves.
    self._world_to_screen = transform.Linear(point.Point(1, -1),
                                             point.Point(0, self._map_size.y))
    self._screen_to_fl_screen = transform.Linear(
        self._feature_layer_screen_size / self._camera_width_world_units)
    self._world_to_fl_screen = transform.Chain(
        self._world_to_screen,
        self._screen_to_fl_screen,
        transform.Floor())

    # Renderable space for the screen.
    self.screen_size_px = self._feature_layer_screen_size.scale_max_size(
        window_size_px)
    screen_to_visual_screen = transform.Linear(
        self.screen_size_px.x / self._camera_width_world_units)
    add_surface(SurfType.SCREEN,
                point.Rect(point.origin, self.screen_size_px),
                transform.Chain(
                    self._world_to_screen,
                    screen_to_visual_screen),
                self.draw_screen)

    # Renderable space for the minimap.
    self.minimap_size_px = self._map_size.scale_max_size(
        self.screen_size_px / 4)
    minimap_to_visual_minimap = transform.Linear(
        self.minimap_size_px.max_dim() / max_map_dim)
    minimap_offset = point.Point(0, (self.screen_size_px.y -
                                     self.minimap_size_px.y))
    add_surface(SurfType.MINIMAP,
                point.Rect(minimap_offset,
                           minimap_offset + self.minimap_size_px),
                transform.Chain(
                    self._world_to_minimap,
                    minimap_to_visual_minimap),
                self.draw_mini_map)

    # Add the feature layers
    features_loc = point.Point(self.screen_size_px.x, 0)
    feature_pane = self._window.subsurface(
        pygame.Rect(features_loc, window_size_px - features_loc))
    feature_pane.fill(colors.white / 2)
    feature_pane_size = point.Point(*feature_pane.get_size())
    feature_grid_size = feature_pane_size / point.Point(cols, rows)
    feature_layer_area = self._feature_layer_screen_size.scale_max_size(
        feature_grid_size)
    feature_layer_size = feature_layer_area * 0.9
    feature_layer_padding = (feature_layer_area - feature_layer_size) / 2

    feature_font_size = int(feature_grid_size.y * 0.09)
    feature_font = pygame.font.Font(None, feature_font_size)

    feature_counter = itertools.count()
    def add_feature_layer(feature, surf_type, world_to_surf):
      """Add a feature layer surface."""
      i = next(feature_counter)
      grid_offset = point.Point(i % cols, i // cols) * feature_grid_size
      text = feature_font.render(feature.full_name, True, colors.white)
      rect = text.get_rect()
      rect.center = grid_offset + point.Point(feature_grid_size.x / 2,
                                              feature_font_size)
      feature_pane.blit(text, rect)
      surf_loc = (features_loc + grid_offset + feature_layer_padding +
                  point.Point(0, feature_font_size))
      add_surface(surf_type,
                  point.Rect(surf_loc, surf_loc + feature_layer_size),
                  world_to_surf,
                  lambda surf: self.draw_feature_layer(surf, feature))

    # Add the minimap feature layers
    fl_minimap_to_fl_surf = transform.Linear(
        feature_layer_size / self._feature_layer_minimap_size)
    world_to_fl_minimap_surf = transform.Chain(
        self._world_to_minimap,
        self._minimap_to_fl_minimap,
        transform.Center(),
        fl_minimap_to_fl_surf)
    for feature in features.MINIMAP_FEATURES:
      add_feature_layer(feature, SurfType.MINIMAP, world_to_fl_minimap_surf)

    # Add the screen feature layers
    fl_screen_to_fl_surf = transform.Linear(
        feature_layer_size / self._feature_layer_screen_size)
    world_to_fl_screen_surf = transform.Chain(
        self._world_to_screen,
        self._screen_to_fl_screen,
        transform.Center(),
        fl_screen_to_fl_surf)
    for feature in features.SCREEN_FEATURES:
      add_feature_layer(feature, SurfType.SCREEN, world_to_fl_screen_surf)

    # Add the help screen
    add_surface(SurfType.CHROME,
                point.Rect(window_size_px / 4, window_size_px * 3 / 4),
                None,
                self.draw_help)

    # Arbitrarily set the initial camera to the center of the map.
    self._update_camera(self._map_size / 2)

  def _update_camera(self, camera_center):
    """Update the camera transform based on the new camera center."""
    camera_radius = (self._feature_layer_screen_size /
                     self._feature_layer_screen_size.x *
                     self._camera_width_world_units / 2)
    center = camera_center.bound(camera_radius, self._map_size - camera_radius)
    self._camera = point.Rect(
        (center - camera_radius).bound(self._map_size),
        (center + camera_radius).bound(self._map_size))
    self._world_to_screen.offset = (-self._camera.bl *
                                    self._world_to_screen.scale)

  def zoom(self, factor):
    """Zoom the window in/out."""
    global max_window_size
    max_window_size *= factor
    self.init_window()

  def get_mouse_pos(self, window_pos=None):
    """Return a MousePos filled with the world and screen/minimap positions."""
    window_pos = window_pos or pygame.mouse.get_pos()
    # +0.5 to center the point on the middle of the pixel.
    window_pt = point.Point(*window_pos) + 0.5
    for surf in reversed(self.surfaces):
      if (surf.surf_type != SurfType.CHROME and
          surf.surf_rect.contains_point(window_pt)):
        surf_rel_pt = window_pt - surf.surf_rect.tl
        world_pt = surf.world_to_surf.back_pt(surf_rel_pt)
        return MousePos(world_pt, surf.surf_type)

  def clear_queued_action(self):
    self.queued_hotkey = ""
    self.queued_action = None

  def save_replay(self, run_config, controller):
    replay_path = run_config.save_replay(
        controller.save_replay(), "local", self._game_info.local_map_path)
    print("Wrote replay to:", replay_path)

  @with_lock(obs_lock)
  @sw.decorate
  def get_actions(self, run_config, controller):
    """Get actions from the UI, apply to controller, and return an ActionCmd."""
    if not self._initialized:
      return ActionCmd.STEP

    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        return ActionCmd.QUIT
      elif event.type == pygame.KEYDOWN:
        if self.help:
          self.help = False
        elif event.key in (pygame.K_QUESTION, pygame.K_SLASH):
          self.help = True
        elif event.key == pygame.K_PAUSE:
          pause = True
          while pause:
            time.sleep(0.1)
            for event in pygame.event.get():
              if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_PAUSE, pygame.K_ESCAPE):
                  pause = False
                elif event.key == pygame.K_F4:
                  return ActionCmd.QUIT
                elif event.key == pygame.K_F5:
                  return ActionCmd.RESTART
        elif event.key == pygame.K_F4:
          return ActionCmd.QUIT
        elif event.key == pygame.K_F5:
          return ActionCmd.RESTART
        elif event.key == pygame.K_F8:  # Toggle synchronous rendering.
          self._render_sync = not self._render_sync
          print("Rendering", self._render_sync and "Sync" or "Async")
        elif event.key == pygame.K_F9:  # Save a replay.
          self.save_replay(run_config, controller)
        elif (event.key in (pygame.K_PLUS, pygame.K_EQUALS) and
              pygame.key.get_mods() & pygame.KMOD_CTRL):  # zoom in
          self.zoom(1.1)
        elif (event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE) and
              pygame.key.get_mods() & pygame.KMOD_CTRL):  # zoom out
          self.zoom(1 / 1.1)
        elif event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
          if pygame.key.get_mods() & pygame.KMOD_CTRL:
            if event.key == pygame.K_PAGEUP:
              self._step_mul += 1
            elif self._step_mul > 1:
              self._step_mul -= 1
            print("New step mul:", self._step_mul)
          else:
            self._fps *= 1.25 if event.key == pygame.K_PAGEUP else 1 / 1.25
            print("New max game speed: %.1f" % self._fps)
        elif event.key in self.camera_actions:
          controller.act(self.camera_action_raw(
              self._camera.center + self.camera_actions[event.key]))
        elif event.key == pygame.K_ESCAPE:
          cmds = self._abilities(lambda cmd: cmd.hotkey == "escape")
          if cmds:
            assert len(cmds) == 1
            cmd = cmds[0]
            assert cmd.target == sc_data.AbilityData.Target.Value("None")
            controller.act(self.unit_action(cmd))
          else:
            self.clear_queued_action()
        else:
          if not self.queued_action:
            key = pygame.key.name(event.key).lower()
            new_cmd = self.queued_hotkey + key
            cmds = self._abilities(lambda cmd, n=new_cmd: (  # pylint: disable=g-long-lambda
                cmd.hotkey != "escape" and cmd.hotkey.startswith(n)))
            if cmds:
              self.queued_hotkey = new_cmd
              if len(cmds) == 1:
                cmd = cmds[0]
                if cmd.hotkey == self.queued_hotkey:
                  if cmd.target != sc_data.AbilityData.Target.Value("None"):
                    self.clear_queued_action()
                    self.queued_action = cmd
                  else:
                    controller.act(self.unit_action(cmd))
      elif event.type == pygame.MOUSEBUTTONDOWN:
        mouse_pos = self.get_mouse_pos(event.pos)
        if event.button == MouseButtons.LEFT and mouse_pos:
          if self.queued_action:
            controller.act(self.unit_action(self.queued_action, mouse_pos))
          elif mouse_pos.type == SurfType.MINIMAP:
            controller.act(self.camera_action(mouse_pos.pos))
          else:
            self.select_start = mouse_pos.pos
        elif event.button == MouseButtons.RIGHT:
          if self.queued_action:
            self.clear_queued_action()
          else:
            cmds = self._abilities(lambda cmd: cmd.button_name == "Smart")
            if cmds:
              controller.act(self.unit_action(cmds[0], mouse_pos))
      elif event.type == pygame.MOUSEBUTTONUP:
        mouse_pos = self.get_mouse_pos(event.pos)
        if event.button == MouseButtons.LEFT and self.select_start:
          if mouse_pos and mouse_pos.type == SurfType.SCREEN:
            controller.act(self.select_action(point.Rect(self.select_start,
                                                         mouse_pos.pos)))
          self.select_start = None
    return ActionCmd.STEP

  def camera_action(self, world_pos):
    """Return a `sc_pb.Action` with the camera movement filled."""
    action = sc_pb.Action()
    self._world_to_fl_minimap.fwd_pt(world_pos).assign_to(
        action.action_feature_layer.camera_move.center_minimap)
    return action

  def camera_action_raw(self, world_pos):
    """Return a `sc_pb.Action` with the camera movement filled."""
    action = sc_pb.Action()
    world_pos.assign_to(action.action_raw.camera_move.center_world_space)
    return action

  def select_action(self, select_rect):
    """Return a `sc_pb.Action` with the selection filled."""
    action = sc_pb.Action()

    if select_rect.tl == select_rect.br:  # select a point
      select = action.action_feature_layer.unit_selection_point
      self._world_to_fl_screen.fwd_pt(select_rect.tl).assign_to(
          select.selection_screen_coord)
      select.type = sc_spatial.ActionSpatialUnitSelectionPoint.Select
    else:
      select = action.action_feature_layer.unit_selection_rect
      rect = select.selection_screen_coord.add()
      self._world_to_fl_screen.fwd_pt(select_rect.bl).assign_to(rect.p0)
      self._world_to_fl_screen.fwd_pt(select_rect.tr).assign_to(rect.p1)
      select.selection_add = False

    # Clear the queued action if something will be selected. An alternative
    # implementation may check whether the selection changed next frame.
    units = self._units_in_area(select_rect)
    if units:
      self.clear_queued_action()

    return action

  def unit_action(self, cmd, pos=None):
    """Return a `sc_pb.Action` filled with the cmd and appropriate target."""
    action = sc_pb.Action()
    unit_command = action.action_feature_layer.unit_command
    unit_command.ability_id = cmd.ability_id
    if pos:
      if pos.type == SurfType.SCREEN:
        self._world_to_fl_screen.fwd_pt(pos.pos).assign_to(
            unit_command.target_screen_coord)
      elif pos.type == SurfType.MINIMAP:
        self._world_to_fl_minimap.fwd_pt(pos.pos).assign_to(
            unit_command.target_minimap_coord)
    self.clear_queued_action()
    return action

  def _abilities(self, fn=None):
    """Return the list of abilities filtered by `fn`."""
    return list(filter(fn, (self._static_data.abilities[cmd.ability_id]
                            for cmd in self._obs.observation.abilities)))

  def _visible_units(self):
    """A generator of visible units and their positions as `Point`s, sorted."""
    # Sort the units by elevation, then owned (eg refinery) above world (ie 16)
    # (eg geiser), small above big, and otherwise arbitrary but stable.
    for u in sorted(self._obs.observation.raw_data.units,
                    key=lambda u: (u.pos.z, u.owner != 16, -u.radius, u.tag)):
      yield u, point.Point.build(u.pos)

  def _units_in_area(self, rect):
    """Return the list of units that intersect the rect."""
    player_id = self._obs.observation.player_common.player_id
    return [u for u, p in self._visible_units()
            if rect.intersects_circle(p, u.radius) and u.owner == player_id]

  def get_unit_name(self, surf, name, radius):
    """Get a length limited unit name for drawing units."""
    key = (name, radius)
    if key not in self._name_lengths:
      max_len = surf.world_to_surf.fwd_dist(radius * 1.6)
      for i in range(len(name)):
        if self.font_small.size(name[:i + 1])[0] > max_len:
          self._name_lengths[key] = name[:i]
          break
      else:
        self._name_lengths[key] = name
    return self._name_lengths[key]

  @sw.decorate
  def draw_units(self, surf):
    """Draw the units and buildings."""
    for u, p in self._visible_units():
      if self._camera.intersects_circle(p, u.radius):
        fraction_damage = clamp((u.health_max - u.health) / (u.health_max or 1),
                                0, 1)
        surf.draw_circle(colors.PLAYER_ABSOLUTE_PALETTE[u.owner], p, u.radius)

        if fraction_damage > 0:
          surf.draw_circle(colors.PLAYER_ABSOLUTE_PALETTE[u.owner] // 2,
                           p, u.radius * fraction_damage)

        name = self.get_unit_name(
            surf, self._static_data.units.get(u.unit_type, "<none>"), u.radius)
        if name:
          text = self.font_small.render(name, True, colors.white)
          rect = text.get_rect()
          rect.center = surf.world_to_surf.fwd_pt(p)
          surf.surf.blit(text, rect)

        if u.is_selected:
          surf.draw_circle(colors.green, p, u.radius + 0.05, 1)

  @sw.decorate
  def draw_selection(self, surf):
    """Draw the selection rectange."""
    if self.select_start:
      mouse_pos = self.get_mouse_pos()
      if mouse_pos and mouse_pos.type == SurfType.SCREEN:
        surf.draw_rect(
            colors.green, point.Rect(self.select_start, mouse_pos.pos), 1)

  @sw.decorate
  def draw_build_target(self, surf):
    """Draw the build target."""
    round_half = lambda v, cond: round(v - 0.5) + 0.5 if cond else round(v)

    if self.queued_action:
      radius = self.queued_action.footprint_radius
      if radius:
        pos = self.get_mouse_pos()
        if pos:
          pos = point.Point(round_half(pos.pos.x, (radius * 2) % 2),
                            round_half(pos.pos.y, (radius * 2) % 2))
          surf.draw_circle(
              colors.PLAYER_ABSOLUTE_PALETTE[
                  self._obs.observation.player_common.player_id],
              pos, radius)

  @sw.decorate
  def draw_overlay(self, surf):
    """Draw the overlay describing resources."""
    player = self._obs.observation.player_common
    text = self.font_large.render(
        "Minerals: %s, Vespene: %s, Food: %s / %s; Score: %s, Frame: %s, "
        "FPS: G:%.1f, R:%.1f" % (
            player.minerals, player.vespene,
            player.food_used, player.food_cap,
            self._obs.observation.score.score, self._obs.observation.game_loop,
            len(self._game_times) / (sum(self._game_times) or 1),
            len(self._render_times) / (sum(self._render_times) or 1)),
        True, colors.green)
    surf.surf.blit(text, (3, 3))

  @sw.decorate
  def draw_help(self, surf):
    """Draw the help dialog."""
    if not self.help:
      return

    def write(line, loc):
      surf.surf.blit(self.font_large.render(line, True, colors.black), loc)

    surf.surf.fill(colors.white * 0.8)
    write("Shortcuts:", point.Point(self.scale, self.scale))

    for i, (hotkey, description) in enumerate(self.shortcuts, start=2):
      write(hotkey, point.Point(self.scale * 2, self.scale * i))
      write(description, point.Point(self.scale * 8, self.scale * i))

  @sw.decorate
  def draw_commands(self, surf):
    """Draw the list of available commands."""
    y = self.scale * 2

    for cmd in sorted(self._abilities(), key=lambda c: c.hotkey):
      if cmd.button_name != "Smart":
        if self.queued_action and cmd == self.queued_action:
          color = colors.green
        elif self.queued_hotkey and cmd.hotkey.startswith(self.queued_hotkey):
          color = colors.green / 2
        else:
          color = colors.yellow
        text = self.font_large.render(
            "%s - %s" % (cmd.hotkey, cmd.button_name), True, color)
        surf.surf.blit(text, (3, y))
        y += self.scale

  @sw.decorate
  def draw_actions(self):
    """Draw the actions so that they can be inspected for accuracy."""
    for act in self._obs.actions:
      if (act.HasField("action_raw") and
          act.action_raw.HasField("unit_command") and
          act.action_raw.unit_command.HasField("target_world_space_pos")):
        pos = point.Point.build(
            act.action_raw.unit_command.target_world_space_pos)
        self.all_surfs(_Surface.draw_circle, colors.yellow, pos, 0.1)
      if act.HasField("action_feature_layer"):
        act_fl = act.action_feature_layer
        if act_fl.HasField("unit_command"):
          if act_fl.unit_command.HasField("target_screen_coord"):
            pos = self._world_to_fl_screen.back_pt(
                point.Point.build(act_fl.unit_command.target_screen_coord))
            self.all_surfs(_Surface.draw_circle, colors.cyan, pos, 0.1)
          if act_fl.unit_command.HasField("target_minimap_coord"):
            pos = self._world_to_fl_minimap.back_pt(
                point.Point.build(act_fl.unit_command.target_minimap_coord))
            self.all_surfs(_Surface.draw_circle, colors.cyan, pos, 0.1)
        if (act_fl.HasField("unit_selection_point") and
            act_fl.unit_selection_point.HasField("selection_screen_coord")):
          pos = self._world_to_fl_screen.back_pt(point.Point.build(
              act_fl.unit_selection_point.selection_screen_coord))
          self.all_surfs(_Surface.draw_circle, colors.cyan, pos, 0.1)
        if act_fl.HasField("unit_selection_rect"):
          for r in act_fl.unit_selection_rect.selection_screen_coord:
            rect = point.Rect(
                self._world_to_fl_screen.back_pt(point.Point.build(r.p0)),
                self._world_to_fl_screen.back_pt(point.Point.build(r.p1)))
            self.all_surfs(_Surface.draw_rect, colors.cyan, rect, 1)

  @sw.decorate
  def draw_base_map(self, surf):
    """Draw the base map."""
    hmap_feature = features.SCREEN_FEATURES.height_map
    hmap = hmap_feature.unpack(self._obs.observation)
    if not hmap.any():
      hmap += 100
    hmap_color = hmap_feature.color(hmap)

    creep_feature = features.SCREEN_FEATURES.creep
    creep = creep_feature.unpack(self._obs.observation)
    creep_mask = creep > 0
    creep_color = creep_feature.color(creep)

    power_feature = features.SCREEN_FEATURES.power
    power = power_feature.unpack(self._obs.observation)
    power_mask = power > 0
    power_color = power_feature.color(power)

    visibility = features.SCREEN_FEATURES.visibility_map.unpack(
        self._obs.observation)
    visibility_fade = np.array([[0.5] * 3, [0.75]*3, [1]*3])

    out = hmap_color * 0.6
    out[creep_mask, :] = (0.4 * out[creep_mask, :] +
                          0.6 * creep_color[creep_mask, :])
    out[power_mask, :] = (0.7 * out[power_mask, :] +
                          0.3 * power_color[power_mask, :])
    out *= visibility_fade[visibility]

    surf.blit_np_array(out)

  @sw.decorate
  def draw_mini_map(self, surf):
    """Draw the minimap."""
    if (self._obs.observation.HasField("render_data") and
        self._obs.observation.render_data.HasField("minimap")):
      # Draw the rendered version.
      surf.blit_np_array(features.Feature.unpack_rgb_image(
          self._obs.observation.render_data.minimap))
    else:  # Render it manually from feature layer data.
      hmap_feature = features.MINIMAP_FEATURES.height_map
      hmap = hmap_feature.unpack(self._obs.observation)
      if not hmap.any():
        hmap += 100
      hmap_color = hmap_feature.color(hmap)

      creep_feature = features.MINIMAP_FEATURES.creep
      creep = creep_feature.unpack(self._obs.observation)
      creep_mask = creep > 0
      creep_color = creep_feature.color(creep)

      player_feature = features.MINIMAP_FEATURES.player_relative
      player_relative = player_feature.unpack(self._obs.observation)
      player_mask = player_relative > 0
      player_color = player_feature.color(player_relative)

      visibility = features.MINIMAP_FEATURES.visibility_map.unpack(
          self._obs.observation)
      visibility_fade = np.array([[0.5] * 3, [0.75]*3, [1]*3])

      # Compose and color the different layers.
      out = hmap_color * 0.6
      out[creep_mask, :] = (0.4 * out[creep_mask, :] +
                            0.6 * creep_color[creep_mask, :])
      out[player_mask, :] = player_color[player_mask, :]
      out *= visibility_fade[visibility]

      # Render the bit of the composited layers that actually correspond to the
      # map. This isn't all of it on non-square maps.
      shape = self._map_size.scale_max_size(
          self._feature_layer_minimap_size).floor()
      surf.blit_np_array(out[:shape.y, :shape.x, :])

      surf.draw_rect(colors.white * 0.8, self._camera, 1)  # Camera
      pygame.draw.rect(surf.surf, colors.red, surf.surf.get_rect(), 1)  # Border

  def check_valid_queued_action(self):
    # Make sure the existing command is still valid
    if (self.queued_hotkey and not self._abilities(
        lambda cmd: cmd.hotkey.startswith(self.queued_hotkey))):
      self.queued_hotkey = ""
    if (self.queued_action and not self._abilities(
        lambda cmd: self.queued_action == cmd)):
      self.queued_action = None

  @sw.decorate
  def draw_rendered_map(self, surf):
    """Draw the rendered pixels."""
    surf.blit_np_array(features.Feature.unpack_rgb_image(
        self._obs.observation.render_data.map))

  def draw_screen(self, surf):
    """Draw the screen area."""
    # surf.fill(colors.black)
    if (self._obs.observation.HasField("render_data") and
        self._obs.observation.render_data.HasField("map")):
      self.draw_rendered_map(surf)
    else:
      self.draw_base_map(surf)
      self.draw_units(surf)
    self.draw_selection(surf)
    self.draw_build_target(surf)
    self.draw_overlay(surf)
    self.draw_commands(surf)

  @sw.decorate
  def draw_feature_layer(self, surf, feature):
    """Draw a feature layer."""
    layer = feature.unpack(self._obs.observation)
    if layer is not None:
      surf.blit_np_array(feature.color(layer))
    else:  # Ignore layers that aren't in this version of SC2.
      surf.surf.fill(colors.black)

  def all_surfs(self, fn, *args, **kwargs):
    for surf in self.surfaces:
      if surf.world_to_surf:
        fn(surf, *args, **kwargs)

  @sw.decorate
  def render(self, obs):
    """Push an observation onto the queue to be rendered."""
    if not self._initialized:
      return
    now = time.time()
    self._game_times.append((now - self._last_time) /
                            max(1, (obs.observation.game_loop -
                                    self._obs.observation.game_loop)))
    self._last_time = now
    self._last_game_loop = self._obs.observation.game_loop
    self._obs_queue.put(obs)
    if self._render_sync:
      self._obs_queue.join()

  def render_thread(self):
    """A render loop that pulls observations off the queue to render."""
    obs = True
    while obs:  # Send something falsy through the queue to shut down.
      obs = self._obs_queue.get()
      if obs and self._obs_queue.empty():
        # Only render the latest observation so we keep up with the game.
        self.render_obs(obs)
      self._obs_queue.task_done()

  @with_lock(render_lock)
  @sw.decorate
  def render_obs(self, obs):
    """Render a frame given an observation."""
    start_time = time.time()
    with obs_lock:
      self._obs = obs
    self.check_valid_queued_action()
    self._update_camera(point.Point.build(
        self._obs.observation.raw_data.player.camera))

    for surf in self.surfaces:
      # Render that surface.
      surf.draw(surf)

    mouse_pos = self.get_mouse_pos()
    if mouse_pos:
      # Draw a small mouse cursor
      self.all_surfs(_Surface.draw_circle, colors.green, mouse_pos.pos, 0.1)

    self.draw_actions()

    with sw("flip"):
      pygame.display.flip()

    self._render_times.append(time.time() - start_time)

  def run(self, run_config, controller, max_game_steps=0,
          game_steps_per_episode=0, save_replay=False):
    """Run loop that gets observations, renders them, and sends back actions."""
    is_replay = (controller.status == remote_controller.Status.in_replay)
    total_game_steps = 0
    start_time = time.time()

    try:
      while True:
        self.init(controller.game_info(), controller.data())
        episode_steps = 0

        controller.step()

        while True:
          total_game_steps += self._step_mul
          episode_steps += self._step_mul
          frame_start_time = time.time()

          obs = controller.observe()
          self.render(obs)

          if obs.player_result:
            break

          cmd = self.get_actions(run_config, controller)
          if cmd == ActionCmd.STEP:
            pass
          elif cmd == ActionCmd.QUIT:
            if not is_replay and save_replay:
              self.save_replay(run_config, controller)
            return
          elif cmd == ActionCmd.RESTART:
            break
          else:
            raise Exception("Unexpected command: %s" % cmd)

          controller.step(self._step_mul)

          if max_game_steps and total_game_steps >= max_game_steps:
            return

          if game_steps_per_episode and episode_steps >= game_steps_per_episode:
            break

          with sw("sleep"):
            elapsed_time = time.time() - frame_start_time
            time.sleep(max(0, 1 / self._fps - elapsed_time))

        if is_replay:
          break

        if save_replay:
          self.save_replay(run_config, controller)

        print("Restarting")
        controller.restart()
    except KeyboardInterrupt:
      pass
    finally:
      self.close()
      elapsed_time = time.time() - start_time
      print("took %.3f seconds for %s steps: %.3f fps" %
            (elapsed_time, total_game_steps, total_game_steps / elapsed_time))

  def __del__(self):
    self.close()
