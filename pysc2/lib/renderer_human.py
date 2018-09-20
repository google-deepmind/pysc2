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
import ctypes
import functools
import itertools
from absl import logging
import math
import os
import platform
import re
import subprocess
import threading
import time

import enum
from future.builtins import range  # pylint: disable=redefined-builtin
import numpy as np
import pygame
import queue
from pysc2.lib import colors
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import remote_controller
from pysc2.lib import stopwatch
from pysc2.lib import transform

from pysc2.lib import video_writer
from s2clientprotocol import error_pb2 as sc_err
from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import spatial_pb2 as sc_spatial
from s2clientprotocol import ui_pb2 as sc_ui

# Disable attribute-error because of the multiple stages of initialization for
# RendererHuman.
# pytype: disable=attribute-error

sw = stopwatch.sw

render_lock = threading.Lock()  # Serialize all window/render operations.


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


class MouseButtons(enum.IntEnum):
  # https://www.pygame.org/docs/ref/mouse.html
  LEFT = 1
  MIDDLE = 2
  RIGHT = 3
  WHEEL_UP = 4
  WHEEL_DOWN = 5


class SurfType(enum.IntEnum):
  """Used to tell what a mouse click refers to."""
  CHROME = 1  # ie help, feature layer titles, etc
  SCREEN = 2
  MINIMAP = 4
  FEATURE = 8
  RGB = 16


class ActionCmd(enum.Enum):
  STEP = 1
  RESTART = 2
  QUIT = 3


class _Ability(collections.namedtuple("_Ability", [
    "ability_id", "name", "footprint_radius", "requires_point", "hotkey"])):
  """Hold the specifics of available abilities."""

  def __new__(cls, ability, static_data):
    specific_data = static_data[ability.ability_id]
    if specific_data.remaps_to_ability_id:
      general_data = static_data[specific_data.remaps_to_ability_id]
    else:
      general_data = specific_data
    return super(_Ability, cls).__new__(
        cls,
        ability_id=general_data.ability_id,
        name=(general_data.friendly_name or general_data.button_name or
              general_data.link_name),
        footprint_radius=general_data.footprint_radius,
        requires_point=ability.requires_point,
        hotkey=specific_data.hotkey)


class _Surface(object):
  """A surface to display on screen."""

  def __init__(self, surf, surf_type, surf_rect, world_to_surf, world_to_obs,
               draw):
    """A surface to display on screen.

    Args:
      surf: The actual pygame.Surface (or subsurface).
      surf_type: A SurfType, used to tell how to treat clicks in that area.
      surf_rect: Rect of the surface relative to the window.
      world_to_surf: Convert a world point to a pixel on the surface.
      world_to_obs: Convert a world point to a pixel in the observation.
      draw: A function that draws onto the surface.
    """
    self.surf = surf
    self.surf_type = surf_type
    self.surf_rect = surf_rect
    self.world_to_surf = world_to_surf
    self.world_to_obs = world_to_obs
    self.draw = draw

  def draw_arc(self, color, world_loc, world_radius, start_angle, stop_angle,
               thickness=1):
    """Draw an arc using world coordinates, radius, start and stop angles."""
    center = self.world_to_surf.fwd_pt(world_loc).round()
    radius = max(1, int(self.world_to_surf.fwd_dist(world_radius)))
    rect = pygame.Rect(center - radius, (radius * 2, radius * 2))
    pygame.draw.arc(self.surf, color, rect, start_angle, stop_angle,
                    thickness if thickness < radius else 0)

  def draw_circle(self, color, world_loc, world_radius, thickness=0):
    """Draw a circle using world coordinates and radius."""
    if world_radius > 0:
      center = self.world_to_surf.fwd_pt(world_loc).round()
      radius = max(1, int(self.world_to_surf.fwd_dist(world_radius)))
      pygame.draw.circle(self.surf, color, center, radius,
                         thickness if thickness < radius else 0)

  def draw_rect(self, color, world_rect, thickness=0):
    """Draw a rectangle using world coordinates."""
    tl = self.world_to_surf.fwd_pt(world_rect.tl).round()
    br = self.world_to_surf.fwd_pt(world_rect.br).round()
    rect = pygame.Rect(tl, br - tl)
    pygame.draw.rect(self.surf, color, rect, thickness)

  def blit_np_array(self, array):
    """Fill this surface using the contents of a numpy array."""
    with sw("make_surface"):
      raw_surface = pygame.surfarray.make_surface(array.transpose([1, 0, 2]))
    with sw("draw"):
      pygame.transform.scale(raw_surface, self.surf.get_size(), self.surf)

  def write_screen(self, font, color, screen_pos, text, align="left",
                   valign="top"):
    """Write to the screen in font.size relative coordinates."""
    pos = point.Point(*screen_pos) * point.Point(0.75, 1) * font.get_linesize()
    text_surf = font.render(str(text), True, color)
    rect = text_surf.get_rect()
    if pos.x >= 0:
      setattr(rect, align, pos.x)
    else:
      setattr(rect, align, self.surf.get_width() + pos.x)
    if pos.y >= 0:
      setattr(rect, valign, pos.y)
    else:
      setattr(rect, valign, self.surf.get_height() + pos.y)
    self.surf.blit(text_surf, rect)


class MousePos(collections.namedtuple("MousePos", ["world_pos", "surf"])):
  """Holds the mouse position in world coordinates and the surf it came from."""
  __slots__ = ()

  @property
  def surf_pos(self):
    return self.surf.world_to_surf.fwd_pt(self.world_pos)

  @property
  def obs_pos(self):
    return self.surf.world_to_obs.fwd_pt(self.world_pos)

  def action_spatial(self, action):
    """Given an Action, return the right spatial action."""
    if self.surf.surf_type & SurfType.FEATURE:
      return action.action_feature_layer
    elif self.surf.surf_type & SurfType.RGB:
      return action.action_render
    else:
      assert self.surf.surf_type & (SurfType.RGB | SurfType.FEATURE)


class PastAction(collections.namedtuple("PastAction", [
    "ability", "color", "pos", "time", "deadline"])):
  """Holds a past action for drawing over time."""


def _get_desktop_size():
  """Get the desktop size."""
  if platform.system() == "Linux":
    try:
      xrandr_query = subprocess.check_output(["xrandr", "--query"])
      sizes = re.findall(r"\bconnected primary (\d+)x(\d+)", str(xrandr_query))
      if sizes[0]:
        return point.Point(int(sizes[0][0]), int(sizes[0][1]))
    except:  # pylint: disable=bare-except
      logging.error("Failed to get the resolution from xrandr.")

  # Most general, but doesn't understand multiple monitors.
  display_info = pygame.display.Info()
  return point.Point(display_info.current_w, display_info.current_h)


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

  cmd_group_keys = {
      pygame.K_0: 0,
      pygame.K_1: 1,
      pygame.K_2: 2,
      pygame.K_3: 3,
      pygame.K_4: 4,
      pygame.K_5: 5,
      pygame.K_6: 6,
      pygame.K_7: 7,
      pygame.K_8: 8,
      pygame.K_9: 9,
  }

  shortcuts = [
      ("F1", "Select idle worker"),
      ("F2", "Select army"),
      ("F3", "Select larva (zerg) or warp gates (protoss)"),
      ("F4", "Quit the game"),
      ("F5", "Restart the map"),
      ("F7", "Toggle RGB rendering"),
      ("F8", "Toggle synchronous rendering"),
      ("F9", "Save a replay"),
      ("Ctrl++", "Zoom in"),
      ("Ctrl+-", "Zoom out"),
      ("PgUp/PgDn", "Increase/decrease the max game speed"),
      ("Ctrl+PgUp/PgDn", "Increase/decrease the step multiplier"),
      ("Pause", "Pause the game"),
      ("?", "This help screen"),
  ]

  def __init__(self, fps=22.4, step_mul=1, render_sync=False,
               render_feature_grid=True, video=None):
    """Create a renderer for use by humans.

    Make sure to call `init` with the game info, or just use `run`.

    Args:
      fps: How fast should the game be run.
      step_mul: How many game steps to take per observation.
      render_sync: Whether to wait for the obs to render before continuing.
      render_feature_grid: When RGB and feature layers are available, whether
          to render the grid of feature layers.
      video: A filename to write the video to. Implicitly enables render_sync.
    """
    self._fps = fps
    self._step_mul = step_mul
    self._render_sync = render_sync or bool(video)
    self._render_rgb = None
    self._render_feature_grid = render_feature_grid
    self._window = None
    self._desktop_size = None
    self._window_scale = 0.75
    self._obs_queue = queue.Queue()
    self._render_thread = threading.Thread(target=self.render_thread,
                                           name="Renderer")
    self._render_thread.start()
    self._game_times = collections.deque(maxlen=100)  # Avg FPS over 100 frames.  # pytype: disable=wrong-keyword-args
    self._render_times = collections.deque(maxlen=100)  # pytype: disable=wrong-keyword-args
    self._last_time = time.time()
    self._last_game_loop = 0
    self._name_lengths = {}
    self._video_writer = video_writer.VideoWriter(video, fps) if video else None

  def close(self):
    if self._obs_queue:
      self._obs_queue.put(None)
      self._render_thread.join()
      self._obs_queue = None
      self._render_thread = None
    if self._video_writer:
      self._video_writer.close()
      self._video_writer = None

  def init(self, game_info, static_data):
    """Take the game info and the static data needed to set up the game.

    This must be called before render or get_actions for each game or restart.

    Args:
      game_info: A `sc_pb.ResponseGameInfo` object for this game.
      static_data: A `StaticData` object for this game.

    Raises:
      ValueError: if there is nothing to render.
    """
    self._game_info = game_info
    self._static_data = static_data

    if not game_info.HasField("start_raw"):
      raise ValueError("Raw observations are required for the renderer.")

    self._map_size = point.Point.build(game_info.start_raw.map_size)

    if game_info.options.HasField("feature_layer"):
      fl_opts = game_info.options.feature_layer
      self._feature_screen_px = point.Point.build(fl_opts.resolution)
      self._feature_minimap_px = point.Point.build(fl_opts.minimap_resolution)
      self._feature_camera_width_world_units = fl_opts.width
      self._render_rgb = False
    else:
      self._feature_screen_px = self._feature_minimap_px = None
    if game_info.options.HasField("render"):
      render_opts = game_info.options.render
      self._rgb_screen_px = point.Point.build(render_opts.resolution)
      self._rgb_minimap_px = point.Point.build(render_opts.minimap_resolution)
      self._render_rgb = True
    else:
      self._rgb_screen_px = self._rgb_minimap_px = None

    if not self._feature_screen_px and not self._rgb_screen_px:
      raise ValueError("Nothing to render.")

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
    self._queued_action = None
    self._queued_hotkey = ""
    self._select_start = None
    self._alerts = {}
    self._past_actions = []
    self._help = False

  @with_lock(render_lock)
  @sw.decorate
  def init_window(self):
    """Initialize the pygame window and lay out the surfaces."""
    if platform.system() == "Windows":
      # Enable DPI awareness on Windows to give the correct window size.
      ctypes.windll.user32.SetProcessDPIAware()  # pytype: disable=module-attr

    pygame.init()

    if self._desktop_size is None:
      self._desktop_size = _get_desktop_size()

    if self._render_rgb and self._rgb_screen_px:
      main_screen_px = self._rgb_screen_px
    else:
      main_screen_px = self._feature_screen_px

    window_size_ratio = main_screen_px
    if self._feature_screen_px and self._render_feature_grid:
      # Want a roughly square grid of feature layers, each being roughly square.
      num_feature_layers = (len(features.SCREEN_FEATURES) +
                            len(features.MINIMAP_FEATURES))
      feature_cols = math.ceil(math.sqrt(num_feature_layers))
      feature_rows = math.ceil(num_feature_layers / feature_cols)
      features_layout = point.Point(feature_cols,
                                    feature_rows * 1.05)  # make room for titles

      # Scale features_layout to main_screen_px height so we know its width.
      features_aspect_ratio = (features_layout * main_screen_px.y /
                               features_layout.y)
      window_size_ratio += point.Point(features_aspect_ratio.x, 0)

    window_size_px = window_size_ratio.scale_max_size(
        self._desktop_size * self._window_scale).ceil()

    # Create the actual window surface. This should only be blitted to from one
    # of the sub-surfaces defined below.
    self._window = pygame.display.set_mode(window_size_px, 0, 32)
    pygame.display.set_caption("Starcraft Viewer")

    # The sub-surfaces that the various draw functions will draw to.
    self._surfaces = []
    def add_surface(surf_type, surf_loc, world_to_surf, world_to_obs, draw_fn):
      """Add a surface. Drawn in order and intersect in reverse order."""
      sub_surf = self._window.subsurface(
          pygame.Rect(surf_loc.tl, surf_loc.size))
      self._surfaces.append(_Surface(
          sub_surf, surf_type, surf_loc, world_to_surf, world_to_obs, draw_fn))

    self._scale = window_size_px.y // 32
    self._font_small = pygame.font.Font(None, int(self._scale * 0.5))
    self._font_large = pygame.font.Font(None, self._scale)

    def check_eq(a, b):
      """Used to run unit tests on the transforms."""
      assert (a - b).len() < 0.0001, "%s != %s" % (a, b)

    # World has origin at bl, world_tl has origin at tl.
    self._world_to_world_tl = transform.Linear(
        point.Point(1, -1), point.Point(0, self._map_size.y))

    check_eq(self._world_to_world_tl.fwd_pt(point.Point(0, 0)),
             point.Point(0, self._map_size.y))
    check_eq(self._world_to_world_tl.fwd_pt(point.Point(5, 10)),
             point.Point(5, self._map_size.y - 10))

    # Move the point to be relative to the camera. This gets updated per frame.
    self._world_tl_to_world_camera_rel = transform.Linear(
        offset=-self._map_size / 4)

    check_eq(self._world_tl_to_world_camera_rel.fwd_pt(self._map_size / 4),
             point.Point(0, 0))
    check_eq(
        self._world_tl_to_world_camera_rel.fwd_pt(
            (self._map_size / 4) + point.Point(5, 10)),
        point.Point(5, 10))

    if self._feature_screen_px:
      # Feature layer locations in continuous space.
      feature_world_per_pixel = (self._feature_screen_px /
                                 self._feature_camera_width_world_units)
      world_camera_rel_to_feature_screen = transform.Linear(
          feature_world_per_pixel, self._feature_screen_px / 2)

      check_eq(world_camera_rel_to_feature_screen.fwd_pt(point.Point(0, 0)),
               self._feature_screen_px / 2)
      check_eq(
          world_camera_rel_to_feature_screen.fwd_pt(
              point.Point(-0.5, -0.5) * self._feature_camera_width_world_units),
          point.Point(0, 0))

      self._world_to_feature_screen = transform.Chain(
          self._world_to_world_tl,
          self._world_tl_to_world_camera_rel,
          world_camera_rel_to_feature_screen)
      self._world_to_feature_screen_px = transform.Chain(
          self._world_to_feature_screen,
          transform.PixelToCoord())

      world_tl_to_feature_minimap = transform.Linear(
          self._feature_minimap_px / self._map_size.max_dim())

      check_eq(world_tl_to_feature_minimap.fwd_pt(point.Point(0, 0)),
               point.Point(0, 0))
      check_eq(world_tl_to_feature_minimap.fwd_pt(self._map_size),
               self._map_size.scale_max_size(self._feature_minimap_px))

      self._world_to_feature_minimap = transform.Chain(
          self._world_to_world_tl,
          world_tl_to_feature_minimap)
      self._world_to_feature_minimap_px = transform.Chain(
          self._world_to_feature_minimap,
          transform.PixelToCoord())

    if self._rgb_screen_px:
      # RGB pixel locations in continuous space.

      # TODO(tewalds): Use a real 3d projection instead of orthogonal.
      rgb_world_per_pixel = (self._rgb_screen_px / 24)
      world_camera_rel_to_rgb_screen = transform.Linear(
          rgb_world_per_pixel, self._rgb_screen_px / 2)

      check_eq(world_camera_rel_to_rgb_screen.fwd_pt(point.Point(0, 0)),
               self._rgb_screen_px / 2)
      check_eq(
          world_camera_rel_to_rgb_screen.fwd_pt(
              point.Point(-0.5, -0.5) * 24),
          point.Point(0, 0))

      self._world_to_rgb_screen = transform.Chain(
          self._world_to_world_tl,
          self._world_tl_to_world_camera_rel,
          world_camera_rel_to_rgb_screen)
      self._world_to_rgb_screen_px = transform.Chain(
          self._world_to_rgb_screen,
          transform.PixelToCoord())

      world_tl_to_rgb_minimap = transform.Linear(
          self._rgb_minimap_px / self._map_size.max_dim())

      check_eq(world_tl_to_rgb_minimap.fwd_pt(point.Point(0, 0)),
               point.Point(0, 0))
      check_eq(world_tl_to_rgb_minimap.fwd_pt(self._map_size),
               self._map_size.scale_max_size(self._rgb_minimap_px))

      self._world_to_rgb_minimap = transform.Chain(
          self._world_to_world_tl,
          world_tl_to_rgb_minimap)
      self._world_to_rgb_minimap_px = transform.Chain(
          self._world_to_rgb_minimap,
          transform.PixelToCoord())

    # Renderable space for the screen.
    screen_size_px = main_screen_px.scale_max_size(window_size_px)
    minimap_size_px = self._map_size.scale_max_size(screen_size_px / 4)
    minimap_offset = point.Point(0, (screen_size_px.y - minimap_size_px.y))

    if self._render_rgb:
      rgb_screen_to_main_screen = transform.Linear(
          screen_size_px / self._rgb_screen_px)
      add_surface(SurfType.RGB | SurfType.SCREEN,
                  point.Rect(point.origin, screen_size_px),
                  transform.Chain(  # surf
                      self._world_to_rgb_screen,
                      rgb_screen_to_main_screen),
                  self._world_to_rgb_screen_px,
                  self.draw_screen)
      rgb_minimap_to_main_minimap = transform.Linear(
          minimap_size_px / self._rgb_minimap_px)
      add_surface(SurfType.RGB | SurfType.MINIMAP,
                  point.Rect(minimap_offset,
                             minimap_offset + minimap_size_px),
                  transform.Chain(  # surf
                      self._world_to_rgb_minimap,
                      rgb_minimap_to_main_minimap),
                  self._world_to_rgb_minimap_px,
                  self.draw_mini_map)
    else:
      feature_screen_to_main_screen = transform.Linear(
          screen_size_px / self._feature_screen_px)
      add_surface(SurfType.FEATURE | SurfType.SCREEN,
                  point.Rect(point.origin, screen_size_px),
                  transform.Chain(  # surf
                      self._world_to_feature_screen,
                      feature_screen_to_main_screen),
                  self._world_to_feature_screen_px,
                  self.draw_screen)
      feature_minimap_to_main_minimap = transform.Linear(
          minimap_size_px / self._feature_minimap_px)
      add_surface(SurfType.FEATURE | SurfType.MINIMAP,
                  point.Rect(minimap_offset,
                             minimap_offset + minimap_size_px),
                  transform.Chain(  # surf
                      self._world_to_feature_minimap,
                      feature_minimap_to_main_minimap),
                  self._world_to_feature_minimap_px,
                  self.draw_mini_map)

    if self._feature_screen_px and self._render_feature_grid:
      # Add the feature layers
      features_loc = point.Point(screen_size_px.x, 0)
      feature_pane = self._window.subsurface(
          pygame.Rect(features_loc, window_size_px - features_loc))
      feature_pane.fill(colors.white / 2)
      feature_pane_size = point.Point(*feature_pane.get_size())
      feature_grid_size = feature_pane_size / point.Point(feature_cols,
                                                          feature_rows)
      feature_layer_area = self._feature_screen_px.scale_max_size(
          feature_grid_size)
      feature_layer_padding = feature_layer_area // 20
      feature_layer_size = feature_layer_area - feature_layer_padding * 2

      feature_font_size = int(feature_grid_size.y * 0.09)
      feature_font = pygame.font.Font(None, feature_font_size)

      feature_counter = itertools.count()
      def add_feature_layer(feature, surf_type, world_to_surf, world_to_obs):
        """Add a feature layer surface."""
        i = next(feature_counter)
        grid_offset = point.Point(i % feature_cols,
                                  i // feature_cols) * feature_grid_size
        text = feature_font.render(feature.full_name, True, colors.white)
        rect = text.get_rect()
        rect.center = grid_offset + point.Point(feature_grid_size.x / 2,
                                                feature_font_size)
        feature_pane.blit(text, rect)
        surf_loc = (features_loc + grid_offset + feature_layer_padding +
                    point.Point(0, feature_font_size))
        add_surface(surf_type,
                    point.Rect(surf_loc, surf_loc + feature_layer_size),
                    world_to_surf, world_to_obs,
                    lambda surf: self.draw_feature_layer(surf, feature))

      # Add the minimap feature layers
      feature_minimap_to_feature_minimap_surf = transform.Linear(
          feature_layer_size / self._feature_minimap_px)
      world_to_feature_minimap_surf = transform.Chain(
          self._world_to_feature_minimap,
          feature_minimap_to_feature_minimap_surf)
      for feature in features.MINIMAP_FEATURES:
        add_feature_layer(feature, SurfType.FEATURE | SurfType.MINIMAP,
                          world_to_feature_minimap_surf,
                          self._world_to_feature_minimap_px)

      # Add the screen feature layers
      feature_screen_to_feature_screen_surf = transform.Linear(
          feature_layer_size / self._feature_screen_px)
      world_to_feature_screen_surf = transform.Chain(
          self._world_to_feature_screen,
          feature_screen_to_feature_screen_surf)
      for feature in features.SCREEN_FEATURES:
        add_feature_layer(feature, SurfType.FEATURE | SurfType.SCREEN,
                          world_to_feature_screen_surf,
                          self._world_to_feature_screen_px)

    # Add the help screen
    help_size = point.Point(
        (max(len(s) for s, _ in self.shortcuts) +
         max(len(s) for _, s in self.shortcuts)) * 0.4 + 4,
        len(self.shortcuts) + 3) * self._scale
    help_rect = point.Rect(window_size_px / 2 - help_size / 2,
                           window_size_px / 2 + help_size / 2)
    add_surface(SurfType.CHROME, help_rect, None, None, self.draw_help)

    # Arbitrarily set the initial camera to the center of the map.
    self._update_camera(self._map_size / 2)

  def _update_camera(self, camera_center):
    """Update the camera transform based on the new camera center."""
    self._world_tl_to_world_camera_rel.offset = (
        -self._world_to_world_tl.fwd_pt(camera_center) *
        self._world_tl_to_world_camera_rel.scale)

    if self._feature_screen_px:
      camera_radius = (self._feature_screen_px / self._feature_screen_px.x *
                       self._feature_camera_width_world_units / 2)
      center = camera_center.bound(camera_radius,
                                   self._map_size - camera_radius)
      self._camera = point.Rect(
          (center - camera_radius).bound(self._map_size),
          (center + camera_radius).bound(self._map_size))

  def zoom(self, factor):
    """Zoom the window in/out."""
    self._window_scale *= factor
    self.init_window()

  def get_mouse_pos(self, window_pos=None):
    """Return a MousePos filled with the world position and surf it hit."""
    window_pos = window_pos or pygame.mouse.get_pos()
    # +0.5 to center the point on the middle of the pixel.
    window_pt = point.Point(*window_pos) + 0.5
    for surf in reversed(self._surfaces):
      if (surf.surf_type != SurfType.CHROME and
          surf.surf_rect.contains_point(window_pt)):
        surf_rel_pt = window_pt - surf.surf_rect.tl
        world_pt = surf.world_to_surf.back_pt(surf_rel_pt)
        return MousePos(world_pt, surf)

  def clear_queued_action(self):
    self._queued_hotkey = ""
    self._queued_action = None

  def save_replay(self, run_config, controller):
    prefix, _ = os.path.splitext(
        os.path.basename(self._game_info.local_map_path))
    replay_path = run_config.save_replay(
        controller.save_replay(), "local", prefix)
    print("Wrote replay to:", replay_path)

  @sw.decorate
  def get_actions(self, run_config, controller):
    """Get actions from the UI, apply to controller, and return an ActionCmd."""
    if not self._initialized:
      return ActionCmd.STEP

    for event in pygame.event.get():
      ctrl = pygame.key.get_mods() & pygame.KMOD_CTRL
      shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
      alt = pygame.key.get_mods() & pygame.KMOD_ALT
      if event.type == pygame.QUIT:
        return ActionCmd.QUIT
      elif event.type == pygame.KEYDOWN:
        if self._help:
          self._help = False
        elif event.key in (pygame.K_QUESTION, pygame.K_SLASH):
          self._help = True
        elif event.key == pygame.K_PAUSE:
          pause = True
          while pause:
            time.sleep(0.1)
            for event2 in pygame.event.get():
              if event2.type == pygame.KEYDOWN:
                if event2.key in (pygame.K_PAUSE, pygame.K_ESCAPE):
                  pause = False
                elif event2.key == pygame.K_F4:
                  return ActionCmd.QUIT
                elif event2.key == pygame.K_F5:
                  return ActionCmd.RESTART
        elif event.key == pygame.K_F4:
          return ActionCmd.QUIT
        elif event.key == pygame.K_F5:
          return ActionCmd.RESTART
        elif event.key == pygame.K_F7:  # Toggle rgb rendering.
          if self._rgb_screen_px and self._feature_screen_px:
            self._render_rgb = not self._render_rgb
            print("Rendering", self._render_rgb and "RGB" or "Feature Layers")
            self.init_window()
        elif event.key == pygame.K_F8:  # Toggle synchronous rendering.
          self._render_sync = not self._render_sync
          print("Rendering", self._render_sync and "Sync" or "Async")
        elif event.key == pygame.K_F9:  # Save a replay.
          self.save_replay(run_config, controller)
        elif event.key in (pygame.K_PLUS, pygame.K_EQUALS) and ctrl:
          self.zoom(1.1)  # zoom in
        elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE) and ctrl:
          self.zoom(1 / 1.1)  # zoom out
        elif event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
          if ctrl:
            if event.key == pygame.K_PAGEUP:
              self._step_mul += 1
            elif self._step_mul > 1:
              self._step_mul -= 1
            print("New step mul:", self._step_mul)
          else:
            self._fps *= 1.25 if event.key == pygame.K_PAGEUP else 1 / 1.25
            print("New max game speed: %.1f" % self._fps)
        elif event.key == pygame.K_F1:
          if self._obs.observation.player_common.idle_worker_count > 0:
            controller.act(self.select_idle_worker(ctrl, shift))
        elif event.key == pygame.K_F2:
          if self._obs.observation.player_common.army_count > 0:
            controller.act(self.select_army(shift))
        elif event.key == pygame.K_F3:
          if self._obs.observation.player_common.warp_gate_count > 0:
            controller.act(self.select_warp_gates(shift))
          if self._obs.observation.player_common.larva_count > 0:
            controller.act(self.select_larva())
        elif event.key in self.cmd_group_keys:
          controller.act(self.control_group(self.cmd_group_keys[event.key],
                                            ctrl, shift, alt))
        elif event.key in self.camera_actions:
          if self._obs:
            controller.act(self.camera_action_raw(
                point.Point.build(
                    self._obs.observation.raw_data.player.camera) +
                self.camera_actions[event.key]))
        elif event.key == pygame.K_ESCAPE:
          if self._queued_action:
            self.clear_queued_action()
          else:
            cmds = self._abilities(lambda cmd: cmd.hotkey == "escape")  # Cancel
            for cmd in cmds:  # There could be multiple cancels.
              assert not cmd.requires_point
              controller.act(self.unit_action(cmd, None, shift))
        else:
          if not self._queued_action:
            key = pygame.key.name(event.key).lower()
            new_cmd = self._queued_hotkey + key
            cmds = self._abilities(lambda cmd, n=new_cmd: (  # pylint: disable=g-long-lambda
                cmd.hotkey != "escape" and cmd.hotkey.startswith(n)))
            if cmds:
              self._queued_hotkey = new_cmd
              if len(cmds) == 1:
                cmd = cmds[0]
                if cmd.hotkey == self._queued_hotkey:
                  if cmd.requires_point:
                    self.clear_queued_action()
                    self._queued_action = cmd
                  else:
                    controller.act(self.unit_action(cmd, None, shift))
      elif event.type == pygame.MOUSEBUTTONDOWN:
        mouse_pos = self.get_mouse_pos(event.pos)
        if event.button == MouseButtons.LEFT and mouse_pos:
          if self._queued_action:
            controller.act(self.unit_action(
                self._queued_action, mouse_pos, shift))
          elif mouse_pos.surf.surf_type & SurfType.MINIMAP:
            controller.act(self.camera_action(mouse_pos))
          else:
            self._select_start = mouse_pos
        elif event.button == MouseButtons.RIGHT:
          if self._queued_action:
            self.clear_queued_action()
          cmds = self._abilities(lambda cmd: cmd.name == "Smart")
          if cmds:
            controller.act(self.unit_action(cmds[0], mouse_pos, shift))
      elif event.type == pygame.MOUSEBUTTONUP:
        mouse_pos = self.get_mouse_pos(event.pos)
        if event.button == MouseButtons.LEFT and self._select_start:
          if (mouse_pos and mouse_pos.surf.surf_type & SurfType.SCREEN and
              mouse_pos.surf.surf_type == self._select_start.surf.surf_type):
            controller.act(self.select_action(
                self._select_start, mouse_pos, ctrl, shift))
          self._select_start = None
    return ActionCmd.STEP

  def camera_action(self, mouse_pos):
    """Return a `sc_pb.Action` with the camera movement filled."""
    action = sc_pb.Action()
    action_spatial = mouse_pos.action_spatial(action)
    mouse_pos.obs_pos.assign_to(action_spatial.camera_move.center_minimap)
    return action

  def camera_action_raw(self, world_pos):
    """Return a `sc_pb.Action` with the camera movement filled."""
    action = sc_pb.Action()
    world_pos.assign_to(action.action_raw.camera_move.center_world_space)
    return action

  def select_action(self, pos1, pos2, ctrl, shift):
    """Return a `sc_pb.Action` with the selection filled."""
    assert pos1.surf.surf_type == pos2.surf.surf_type
    assert pos1.surf.world_to_obs == pos2.surf.world_to_obs

    action = sc_pb.Action()
    action_spatial = pos1.action_spatial(action)

    if pos1.world_pos == pos2.world_pos:  # select a point
      select = action_spatial.unit_selection_point
      pos1.obs_pos.assign_to(select.selection_screen_coord)
      mod = sc_spatial.ActionSpatialUnitSelectionPoint
      if ctrl:
        select.type = mod.AddAllType if shift else mod.AllType
      else:
        select.type = mod.Toggle if shift else mod.Select
    else:
      select = action_spatial.unit_selection_rect
      rect = select.selection_screen_coord.add()
      pos1.obs_pos.assign_to(rect.p0)
      pos2.obs_pos.assign_to(rect.p1)
      select.selection_add = shift

    # Clear the queued action if something will be selected. An alternative
    # implementation may check whether the selection changed next frame.
    units = self._units_in_area(point.Rect(pos1.world_pos, pos2.world_pos))
    if units:
      self.clear_queued_action()

    return action

  def select_idle_worker(self, ctrl, shift):
    """Select an idle worker."""
    action = sc_pb.Action()
    mod = sc_ui.ActionSelectIdleWorker
    if ctrl:
      select_worker = mod.AddAll if shift else mod.All
    else:
      select_worker = mod.Add if shift else mod.Set
    action.action_ui.select_idle_worker.type = select_worker
    return action

  def select_army(self, shift):
    """Select the entire army."""
    action = sc_pb.Action()
    action.action_ui.select_army.selection_add = shift
    return action

  def select_warp_gates(self, shift):
    """Select all warp gates."""
    action = sc_pb.Action()
    action.action_ui.select_warp_gates.selection_add = shift
    return action

  def select_larva(self):
    """Select all larva."""
    action = sc_pb.Action()
    action.action_ui.select_larva.SetInParent()  # Adds the empty proto field.
    return action

  def control_group(self, control_group_id, ctrl, shift, alt):
    """Act on a control group, selecting, setting, etc."""
    action = sc_pb.Action()
    select = action.action_ui.control_group

    mod = sc_ui.ActionControlGroup
    if not ctrl and not shift and not alt:
      select.action = mod.Recall
    elif ctrl and not shift and not alt:
      select.action = mod.Set
    elif not ctrl and shift and not alt:
      select.action = mod.Append
    elif not ctrl and not shift and alt:
      select.action = mod.SetAndSteal
    elif not ctrl and shift and alt:
      select.action = mod.AppendAndSteal
    else:
      return  # unknown
    select.control_group_index = control_group_id
    return action

  def unit_action(self, cmd, pos, shift):
    """Return a `sc_pb.Action` filled with the cmd and appropriate target."""
    action = sc_pb.Action()
    if pos:
      action_spatial = pos.action_spatial(action)
      unit_command = action_spatial.unit_command
      unit_command.ability_id = cmd.ability_id
      unit_command.queue_command = shift
      if pos.surf.surf_type & SurfType.SCREEN:
        pos.obs_pos.assign_to(unit_command.target_screen_coord)
      elif pos.surf.surf_type & SurfType.MINIMAP:
        pos.obs_pos.assign_to(unit_command.target_minimap_coord)
    else:
      if self._feature_screen_px:
        action.action_feature_layer.unit_command.ability_id = cmd.ability_id
      else:
        action.action_render.unit_command.ability_id = cmd.ability_id

    self.clear_queued_action()
    return action

  def _abilities(self, fn=None):
    """Return the list of abilities filtered by `fn`."""
    out = {}
    for cmd in self._obs.observation.abilities:
      ability = _Ability(cmd, self._static_data.abilities)
      if not fn or fn(ability):
        out[ability.ability_id] = ability
    return list(out.values())

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
        if self._font_small.size(name[:i + 1])[0] > max_len:
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

        if u.shield and u.shield_max:
          surf.draw_arc(colors.blue, p, u.radius, 0,
                        2 * math.pi * u.shield / u.shield_max)
        if u.energy and u.energy_max:
          surf.draw_arc(colors.purple * 0.75, p, u.radius - 0.05, 0,
                        2 * math.pi * u.energy / u.energy_max)

        name = self.get_unit_name(
            surf, self._static_data.units.get(u.unit_type, "<none>"), u.radius)
        if name:
          text = self._font_small.render(name, True, colors.white)
          rect = text.get_rect()
          rect.center = surf.world_to_surf.fwd_pt(p)
          surf.surf.blit(text, rect)

        if u.is_selected:
          surf.draw_circle(colors.green, p, u.radius + 0.1, 1)

  @sw.decorate
  def draw_selection(self, surf):
    """Draw the selection rectange."""
    select_start = self._select_start  # Cache to avoid a race condition.
    if select_start:
      mouse_pos = self.get_mouse_pos()
      if (mouse_pos and mouse_pos.surf.surf_type & SurfType.SCREEN and
          mouse_pos.surf.surf_type == select_start.surf.surf_type):
        rect = point.Rect(select_start.world_pos, mouse_pos.world_pos)
        surf.draw_rect(colors.green, rect, 1)

  @sw.decorate
  def draw_build_target(self, surf):
    """Draw the build target."""
    round_half = lambda v, cond: round(v - 0.5) + 0.5 if cond else round(v)

    queued_action = self._queued_action
    if queued_action:
      radius = queued_action.footprint_radius
      if radius:
        pos = self.get_mouse_pos()
        if pos:
          pos = point.Point(round_half(pos.world_pos.x, (radius * 2) % 2),
                            round_half(pos.world_pos.y, (radius * 2) % 2))
          surf.draw_circle(
              colors.PLAYER_ABSOLUTE_PALETTE[
                  self._obs.observation.player_common.player_id],
              pos, radius)

  @sw.decorate
  def draw_overlay(self, surf):
    """Draw the overlay describing resources."""
    obs = self._obs.observation
    player = obs.player_common
    surf.write_screen(
        self._font_large, colors.green, (0.2, 0.2),
        "Minerals: %s, Vespene: %s, Food: %s / %s" % (
            player.minerals, player.vespene, player.food_used, player.food_cap))
    times, steps = zip(*self._game_times)
    sec = obs.game_loop // 22.4  # http://liquipedia.net/starcraft2/Game_Speed
    surf.write_screen(
        self._font_large, colors.green, (-0.2, 0.2),
        "Score: %s, Step: %s, %.1f/s, Time: %d:%02d" % (
            obs.score.score, obs.game_loop, sum(steps) / (sum(times) or 1),
            sec // 60, sec % 60),
        align="right")
    surf.write_screen(
        self._font_large, colors.green * 0.8, (-0.2, 1.2),
        "FPS: O:%.1f, R:%.1f" % (
            len(times) / (sum(times) or 1),
            len(self._render_times) / (sum(self._render_times) or 1)),
        align="right")
    line = 3
    for alert, ts in sorted(self._alerts.items(), key=lambda item: item[1]):
      if time.time() < ts + 3:  # Show for 3 seconds.
        surf.write_screen(self._font_large, colors.red, (20, line), alert)
        line += 1
      else:
        del self._alerts[alert]

  @sw.decorate
  def draw_help(self, surf):
    """Draw the help dialog."""
    if not self._help:
      return

    def write(loc, text):
      surf.write_screen(self._font_large, colors.black, loc, text)

    surf.surf.fill(colors.white * 0.8)
    write((1, 1), "Shortcuts:")

    max_len = max(len(s) for s, _ in self.shortcuts)
    for i, (hotkey, description) in enumerate(self.shortcuts, start=2):
      write((2, i), hotkey)
      write((3 + max_len * 0.7, i), description)

  @sw.decorate
  def draw_commands(self, surf):
    """Draw the list of available commands."""
    past_abilities = {act.ability for act in self._past_actions if act.ability}
    for y, cmd in enumerate(sorted(self._abilities(
        lambda c: c.name != "Smart"), key=lambda c: c.name), start=2):
      if self._queued_action and cmd == self._queued_action:
        color = colors.green
      elif self._queued_hotkey and cmd.hotkey.startswith(self._queued_hotkey):
        color = colors.green * 0.75
      elif cmd.ability_id in past_abilities:
        color = colors.red
      else:
        color = colors.yellow
      hotkey = cmd.hotkey[0:3]  # truncate "escape" -> "esc"
      surf.write_screen(self._font_large, color, (0.2, y), hotkey)
      surf.write_screen(self._font_large, color, (3, y), cmd.name)

  @sw.decorate
  def draw_panel(self, surf):
    """Draw the unit selection or build queue."""

    left = -12  # How far from the right border

    def unit_name(unit_type):
      return self._static_data.units.get(unit_type, "<unknown>")

    def write(loc, text, color=colors.yellow):
      surf.write_screen(self._font_large, color, loc, text)

    def write_single(unit, line):
      write((left + 1, next(line)), unit_name(unit.unit_type))
      write((left + 1, next(line)), "Health: %s" % unit.health)
      write((left + 1, next(line)), "Shields: %s" % unit.shields)
      write((left + 1, next(line)), "Energy: %s" % unit.energy)
      if unit.build_progress > 0:
        write((left + 1, next(line)),
              "Progress: %d%%" % (unit.build_progress * 100))
      if unit.transport_slots_taken > 0:
        write((left + 1, next(line)), "Slots: %s" % unit.transport_slots_taken)

    def write_multi(units, line):
      counts = collections.defaultdict(int)
      for unit in units:
        counts[unit_name(unit.unit_type)] += 1
      for name, count in sorted(counts.items()):
        y = next(line)
        write((left + 1, y), count)
        write((left + 3, y), name)

    ui = self._obs.observation.ui_data
    line = itertools.count(3)

    if ui.groups:
      write((left, next(line)), "Control Groups:", colors.green)
      for group in ui.groups:
        y = next(line)
        write((left + 1, y), "%s:" % group.control_group_index, colors.green)
        write((left + 3, y), "%s %s" % (group.count,
                                        unit_name(group.leader_unit_type)))
      next(line)

    if ui.HasField("single"):
      write((left, next(line)), "Selection:", colors.green)
      write_single(ui.single.unit, line)
    elif ui.HasField("multi"):
      write((left, next(line)), "Selection:", colors.green)
      write_multi(ui.multi.units, line)
    elif ui.HasField("cargo"):
      write((left, next(line)), "Selection:", colors.green)
      write_single(ui.cargo.unit, line)
      next(line)
      write((left, next(line)), "Cargo:", colors.green)
      write((left + 1, next(line)),
            "Empty slots: %s" % ui.cargo.slots_available)
      write_multi(ui.cargo.passengers, line)
    elif ui.HasField("production"):
      write((left, next(line)), "Selection:", colors.green)
      write_single(ui.production.unit, line)
      next(line)
      write((left, next(line)), "Build Queue:", colors.green)
      for unit in ui.production.build_queue:
        s = unit_name(unit.unit_type)
        if unit.build_progress > 0:
          s += ": %d%%" % (unit.build_progress * 100)
        write((left + 1, next(line)), s)

  @sw.decorate
  def draw_actions(self):
    """Draw the actions so that they can be inspected for accuracy."""
    now = time.time()
    for act in self._past_actions:
      if act.pos and now < act.deadline:
        remain = (act.deadline - now) / (act.deadline - act.time)
        if isinstance(act.pos, point.Point):
          size = remain / 3
          self.all_surfs(_Surface.draw_circle, act.color, act.pos, size, 1)
        else:
          # Fade with alpha would be nice, but doesn't seem to work.
          self.all_surfs(_Surface.draw_rect, act.color, act.pos, 1)

  @sw.decorate
  def prepare_actions(self, obs):
    """Keep a list of the past actions so they can be drawn."""
    now = time.time()
    while self._past_actions and self._past_actions[0].deadline < now:
      self._past_actions.pop(0)

    def add_act(ability_id, color, pos, timeout=1):
      if ability_id:
        ability = self._static_data.abilities[ability_id]
        if ability.remaps_to_ability_id:  # Prefer general abilities.
          ability_id = ability.remaps_to_ability_id
      self._past_actions.append(
          PastAction(ability_id, color, pos, now, now + timeout))

    for act in obs.actions:
      if (act.HasField("action_raw") and
          act.action_raw.HasField("unit_command") and
          act.action_raw.unit_command.HasField("target_world_space_pos")):
        pos = point.Point.build(
            act.action_raw.unit_command.target_world_space_pos)
        add_act(act.action_raw.unit_command.ability_id, colors.yellow, pos)
      if act.HasField("action_feature_layer"):
        act_fl = act.action_feature_layer
        if act_fl.HasField("unit_command"):
          if act_fl.unit_command.HasField("target_screen_coord"):
            pos = self._world_to_feature_screen_px.back_pt(
                point.Point.build(act_fl.unit_command.target_screen_coord))
            add_act(act_fl.unit_command.ability_id, colors.cyan, pos)
          elif act_fl.unit_command.HasField("target_minimap_coord"):
            pos = self._world_to_feature_minimap_px.back_pt(
                point.Point.build(act_fl.unit_command.target_minimap_coord))
            add_act(act_fl.unit_command.ability_id, colors.cyan, pos)
          else:
            add_act(act_fl.unit_command.ability_id, None, None)
        if (act_fl.HasField("unit_selection_point") and
            act_fl.unit_selection_point.HasField("selection_screen_coord")):
          pos = self._world_to_feature_screen_px.back_pt(point.Point.build(
              act_fl.unit_selection_point.selection_screen_coord))
          add_act(None, colors.cyan, pos)
        if act_fl.HasField("unit_selection_rect"):
          for r in act_fl.unit_selection_rect.selection_screen_coord:
            rect = point.Rect(
                self._world_to_feature_screen_px.back_pt(
                    point.Point.build(r.p0)),
                self._world_to_feature_screen_px.back_pt(
                    point.Point.build(r.p1)))
            add_act(None, colors.cyan, rect, 0.3)
      if act.HasField("action_render"):
        act_rgb = act.action_render
        if act_rgb.HasField("unit_command"):
          if act_rgb.unit_command.HasField("target_screen_coord"):
            pos = self._world_to_rgb_screen_px.back_pt(
                point.Point.build(act_rgb.unit_command.target_screen_coord))
            add_act(act_rgb.unit_command.ability_id, colors.red, pos)
          elif act_rgb.unit_command.HasField("target_minimap_coord"):
            pos = self._world_to_rgb_minimap_px.back_pt(
                point.Point.build(act_rgb.unit_command.target_minimap_coord))
            add_act(act_rgb.unit_command.ability_id, colors.red, pos)
          else:
            add_act(act_rgb.unit_command.ability_id, None, None)
        if (act_rgb.HasField("unit_selection_point") and
            act_rgb.unit_selection_point.HasField("selection_screen_coord")):
          pos = self._world_to_rgb_screen_px.back_pt(point.Point.build(
              act_rgb.unit_selection_point.selection_screen_coord))
          add_act(None, colors.red, pos)
        if act_rgb.HasField("unit_selection_rect"):
          for r in act_rgb.unit_selection_rect.selection_screen_coord:
            rect = point.Rect(
                self._world_to_rgb_screen_px.back_pt(
                    point.Point.build(r.p0)),
                self._world_to_rgb_screen_px.back_pt(
                    point.Point.build(r.p1)))
            add_act(None, colors.red, rect, 0.3)

  @sw.decorate
  def draw_base_map(self, surf):
    """Draw the base map."""
    hmap_feature = features.SCREEN_FEATURES.height_map
    hmap = hmap_feature.unpack(self._obs.observation)
    if not hmap.any():
      hmap = hmap + 100  # pylint: disable=g-no-augmented-assignment
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
    if (self._render_rgb and self._obs.observation.HasField("render_data") and
        self._obs.observation.render_data.HasField("minimap")):
      # Draw the rendered version.
      surf.blit_np_array(features.Feature.unpack_rgb_image(
          self._obs.observation.render_data.minimap))
    else:  # Render it manually from feature layer data.
      hmap_feature = features.MINIMAP_FEATURES.height_map
      hmap = hmap_feature.unpack(self._obs.observation)
      if not hmap.any():
        hmap = hmap + 100  # pylint: disable=g-no-augmented-assignment
      hmap_color = hmap_feature.color(hmap)

      creep_feature = features.MINIMAP_FEATURES.creep
      creep = creep_feature.unpack(self._obs.observation)
      creep_mask = creep > 0
      creep_color = creep_feature.color(creep)

      if self._obs.observation.player_common.player_id in (0, 16):  # observer
        # If we're the observer, show the absolute since otherwise all player
        # units are friendly, making it pretty boring.
        player_feature = features.MINIMAP_FEATURES.player_id
      else:
        player_feature = features.MINIMAP_FEATURES.player_relative
      player_data = player_feature.unpack(self._obs.observation)
      player_mask = player_data > 0
      player_color = player_feature.color(player_data)

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
          self._feature_minimap_px).floor()
      surf.blit_np_array(out[:shape.y, :shape.x, :])

      surf.draw_rect(colors.white * 0.8, self._camera, 1)  # Camera
      pygame.draw.rect(surf.surf, colors.red, surf.surf.get_rect(), 1)  # Border

  def check_valid_queued_action(self):
    # Make sure the existing command is still valid
    if (self._queued_hotkey and not self._abilities(
        lambda cmd: cmd.hotkey.startswith(self._queued_hotkey))):
      self._queued_hotkey = ""
    if (self._queued_action and not self._abilities(
        lambda cmd: self._queued_action == cmd)):
      self._queued_action = None

  @sw.decorate
  def draw_rendered_map(self, surf):
    """Draw the rendered pixels."""
    surf.blit_np_array(features.Feature.unpack_rgb_image(
        self._obs.observation.render_data.map))

  def draw_screen(self, surf):
    """Draw the screen area."""
    # surf.fill(colors.black)
    if (self._render_rgb and self._obs.observation.HasField("render_data") and
        self._obs.observation.render_data.HasField("map")):
      self.draw_rendered_map(surf)
    else:
      self.draw_base_map(surf)
      self.draw_units(surf)
    self.draw_selection(surf)
    self.draw_build_target(surf)
    self.draw_overlay(surf)
    self.draw_commands(surf)
    self.draw_panel(surf)

  @sw.decorate
  def draw_feature_layer(self, surf, feature):
    """Draw a feature layer."""
    layer = feature.unpack(self._obs.observation)
    if layer is not None:
      surf.blit_np_array(feature.color(layer))
    else:  # Ignore layers that aren't in this version of SC2.
      surf.surf.fill(colors.black)

  def all_surfs(self, fn, *args, **kwargs):
    for surf in self._surfaces:
      if surf.world_to_surf:
        fn(surf, *args, **kwargs)

  @sw.decorate
  def render(self, obs):
    """Push an observation onto the queue to be rendered."""
    if not self._initialized:
      return
    now = time.time()
    self._game_times.append(
        (now - self._last_time,
         max(1, obs.observation.game_loop - self._obs.observation.game_loop)))
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
      if obs:
        for alert in obs.observation.alerts:
          self._alerts[sc_pb.Alert.Name(alert)] = time.time()
        for err in obs.action_errors:
          if err.result != sc_err.Success:
            self._alerts[sc_err.ActionResult.Name(err.result)] = time.time()
        self.prepare_actions(obs)
        if self._obs_queue.empty():
          # Only render the latest observation so we keep up with the game.
          self.render_obs(obs)
        if self._video_writer:
          self._video_writer.add(np.transpose(
              pygame.surfarray.pixels3d(self._window), axes=(1, 0, 2)))
      self._obs_queue.task_done()

  @with_lock(render_lock)
  @sw.decorate
  def render_obs(self, obs):
    """Render a frame given an observation."""
    start_time = time.time()
    self._obs = obs
    self.check_valid_queued_action()
    self._update_camera(point.Point.build(
        self._obs.observation.raw_data.player.camera))

    for surf in self._surfaces:
      # Render that surface.
      surf.draw(surf)

    mouse_pos = self.get_mouse_pos()
    if mouse_pos:
      # Draw a small mouse cursor
      self.all_surfs(_Surface.draw_circle, colors.green, mouse_pos.world_pos,
                     0.1)

    self.draw_actions()

    with sw("flip"):
      pygame.display.flip()

    self._render_times.append(time.time() - start_time)

  def run(self, run_config, controller, max_game_steps=0, max_episodes=0,
          game_steps_per_episode=0, save_replay=False):
    """Run loop that gets observations, renders them, and sends back actions."""
    is_replay = (controller.status == remote_controller.Status.in_replay)
    total_game_steps = 0
    start_time = time.time()
    num_episodes = 0

    try:
      while True:
        self.init(controller.game_info(), controller.data())
        episode_steps = 0
        num_episodes += 1

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

        if max_episodes and num_episodes >= max_episodes:
          break

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
