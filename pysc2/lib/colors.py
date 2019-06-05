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
"""A basic Color class."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import math
import random

from future.builtins import range  # pylint: disable=redefined-builtin
import numpy

from pysc2.lib import static_data


class Color(collections.namedtuple("Color", ["r", "g", "b"])):
  """A basic Color class."""
  __slots__ = ()

  def set(self, r=None, g=None, b=None):
    return Color(r or self.r, b or self.b, g or self.g)

  def round(self):
    return Color(int(round(self.r)), int(round(self.g)), int(round(self.b)))

  def floor(self):
    return Color(int(math.floor(self.r)), int(math.floor(self.g)),
                 int(math.floor(self.b)))

  def ceil(self):
    return Color(int(math.ceil(self.r)), int(math.ceil(self.g)),
                 int(math.ceil(self.b)))

  def __str__(self):
    return "%d,%d,%d" % self

  def __add__(self, o):
    return Color(self.r + o.r, self.g + o.g, self.b + o.b)

  def __sub__(self, o):
    return Color(self.r - o.r, self.g - o.g, self.b - o.b)

  def __mul__(self, val):
    return Color(self.r * val, self.g * val, self.b * val)

  def __truediv__(self, val):
    return Color(self.r / val, self.g / val, self.b / val)

  def __floordiv__(self, val):
    return Color(self.r // val, self.g // val, self.b // val)

  __div__ = __truediv__

black = Color(0, 0, 0)
white = Color(255, 255, 255)
red = Color(255, 0, 0)
green = Color(0, 255, 0)
blue = Color(0, 0, 255)
cyan = Color(0, 255, 255)
yellow = Color(255, 255, 0)
purple = Color(255, 0, 255)


def smooth_hue_palette(scale):
  """Takes an array of ints and returns a corresponding colored rgb array."""
  # http://en.wikipedia.org/wiki/HSL_and_HSV#From_HSL
  # Based on http://stackoverflow.com/a/17382854 , with simplifications and
  # optimizations. Assumes S=1, L=0.5, meaning C=1 and m=0.
  # 0 stays black, everything else moves into a hue.

  # Some initial values and scaling. Check wikipedia for variable meanings.
  array = numpy.arange(scale)
  h = array * (6 / scale)  # range of [0,6)
  x = 255 * (1 - numpy.absolute(numpy.mod(h, 2) - 1))
  c = 255

  # Initialize outputs to zero/black
  out = numpy.zeros(h.shape + (3,), float)
  r = out[..., 0]
  g = out[..., 1]
  b = out[..., 2]

  mask = (0 < h) & (h < 1)
  r[mask] = c
  g[mask] = x[mask]

  mask = (1 <= h) & (h < 2)
  r[mask] = x[mask]
  g[mask] = c

  mask = (2 <= h) & (h < 3)
  g[mask] = c
  b[mask] = x[mask]

  mask = (3 <= h) & (h < 4)
  g[mask] = x[mask]
  b[mask] = c

  mask = (4 <= h) & (h < 5)
  r[mask] = x[mask]
  b[mask] = c

  mask = 5 <= h
  r[mask] = c
  b[mask] = x[mask]

  return out


def shuffled_hue(scale):
  palette = list(smooth_hue_palette(scale))
  random.shuffle(palette, lambda: 0.5)  # Return a fixed shuffle
  return numpy.array(palette)


def piece_wise_linear(scale, points):
  """Create a palette that is piece-wise linear given some colors at points."""
  assert len(points) >= 2
  assert points[0][0] == 0
  assert points[-1][0] == 1
  assert all(i < j for i, j in zip(points[:-1], points[1:]))
  out = numpy.zeros((scale, 3))
  p1, c1 = points[0]
  p2, c2 = points[1]
  next_pt = 2

  for i in range(1, scale):  # Leave 0 as black.
    v = i / scale
    if v > p2:
      p1, c1 = p2, c2
      p2, c2 = points[next_pt]
      next_pt += 1
    frac = (v - p1) / (p2 - p1)
    out[i, :] = c1 * (1 - frac) + c2 * frac
  return out


def winter(scale):
  return piece_wise_linear(scale, [(0, Color(0, 0.5, 0.4) * 255),
                                   (1, Color(1, 1, 0.4) * 255)])


def hot(scale):
  return piece_wise_linear(scale, [(0, Color(0.5, 0, 0) * 255),
                                   (0.2, Color(1, 0, 0) * 255),
                                   (0.6, Color(1, 1, 0) * 255),
                                   (1, Color(1, 1, 1) * 255)])


def height_map(scale):
  return piece_wise_linear(scale, [
      (0, Color(0, 0, 0)),  # Abyss
      (40/255, Color(67, 109, 95)),  # Water, little below this height.
      (50/255, Color(168, 152, 129)),  # Beach
      (60/255, Color(154, 124, 90)),  # Sand, the mode height.
      (70/255, Color(117, 150, 96)),  # Grass
      (80/255, Color(166, 98, 97)),  # Dirt, should be the top.
      (1, Color(255, 255, 100)),  # Heaven. Shouldn't be seen.
  ])

# Palette used to color player_relative features.
PLAYER_RELATIVE_PALETTE = numpy.array([
    black,                 # Background.
    Color(0, 142, 0),      # Self. (Green).
    yellow,                # Ally.
    Color(129, 166, 196),  # Neutral. (Cyan.)
    Color(113, 25, 34),    # Enemy. (Red).
])

PLAYER_ABSOLUTE_PALETTE = numpy.array([
    black,                 # Background
    Color(0, 142, 0),      # 1: Green
    Color(113, 25, 34),    # 2: Red
    Color(223, 215, 67),   # 3: Yellow
    Color(66, 26, 121),    # 4: Purple
    Color(222, 144, 50),   # 5: Orange
    Color(46, 72, 237),    # 6: Blue
    Color(207, 111, 176),  # 7: Pink
    Color(189, 251, 157),  # 8: Light green
    white * 0.1,           # 9: Does the game ever have more than 8 players?
    white * 0.1,           # 10: Does the game ever have more than 8 players?
    white * 0.1,           # 11: Does the game ever have more than 8 players?
    white * 0.1,           # 12: Does the game ever have more than 8 players?
    white * 0.1,           # 13: Does the game ever have more than 8 players?
    white * 0.1,           # 14: Does the game ever have more than 8 players?
    white * 0.1,           # 15: Does the game ever have more than 8 players?
    Color(129, 166, 196),  # 16 Neutral: Cyan
])

VISIBILITY_PALETTE = numpy.array([
    black,         # Hidden
    white * 0.25,  # Fogged
    white * 0.6,   # Visible
])

CAMERA_PALETTE = numpy.array([black, white * 0.6])
CREEP_PALETTE = numpy.array([black, purple * 0.4])
POWER_PALETTE = numpy.array([black, cyan * 0.7])
SELECTED_PALETTE = numpy.array([black, green * 0.7])


def unit_type(scale=None):
  """Returns a palette that maps unit types to rgb colors."""
  return categorical(static_data.UNIT_TYPES, scale)


def buffs(scale=None):
  """Returns a palette that maps buffs to rgb colors."""
  return categorical(static_data.BUFFS, scale)


def categorical(options, scale=None):
  # Can specify a scale to match the api or to accept unknown unit types.
  palette_size = scale or max(options) + 1
  palette = shuffled_hue(palette_size)
  assert len(options) <= len(distinct_colors)
  for i, v in enumerate(options):
    palette[v] = distinct_colors[i]
  return palette


effects = numpy.array([
    [0, 0, 0],
    [72, 173, 207],
    [203, 76, 49],
    [122, 98, 209],
    [109, 183, 67],
    [192, 80, 181],
    [86, 185, 138],
    [211, 63, 115],
    [81, 128, 60],
    [182, 135, 208],
    [182, 174, 73],
    [95, 123, 196],
    [220, 146, 71],
    [187, 102, 147],
    [138, 109, 48],
    [197, 103, 99],
])


# Generated with http://tools.medialab.sciences-po.fr/iwanthue/
# 280 colors: H: 0-360, C: 0-100, L: 35-100; then shuffled.
distinct_colors = numpy.array([
    [255, 165, 150],
    [255, 255, 138],
    [0, 82, 232],
    [196, 141, 0],
    [7, 94, 71],
    [1, 138, 253],
    [152, 255, 143],
    [39, 95, 4],
    [209, 207, 0],
    [52, 255, 213],
    [89, 84, 31],
    [90, 77, 113],
    [255, 102, 141],
    [78, 184, 0],
    [96, 82, 1],
    [238, 42, 0],
    [101, 45, 194],
    [255, 57, 114],
    [1, 248, 160],
    [87, 127, 255],
    [74, 69, 167],
    [153, 255, 86],
    [0, 173, 108],
    [168, 0, 126],
    [255, 230, 75],
    [2, 195, 226],
    [120, 70, 42],
    [138, 166, 0],
    [255, 191, 133],
    [165, 0, 191],
    [0, 162, 104],
    [255, 192, 88],
    [145, 255, 161],
    [1, 247, 184],
    [162, 27, 18],
    [115, 251, 255],
    [255, 157, 168],
    [1, 129, 186],
    [228, 0, 198],
    [2, 164, 126],
    [191, 3, 0],
    [1, 108, 241],
    [255, 149, 208],
    [152, 49, 0],
    [0, 137, 99],
    [255, 244, 181],
    [1, 208, 245],
    [110, 57, 152],
    [0, 104, 91],
    [255, 203, 51],
    [255, 33, 205],
    [0, 115, 135],
    [135, 136, 255],
    [130, 199, 0],
    [115, 214, 0],
    [149, 173, 255],
    [0, 137, 117],
    [220, 255, 158],
    [3, 230, 191],
    [255, 72, 235],
    [122, 66, 72],
    [70, 82, 114],
    [159, 243, 8],
    [255, 105, 35],
    [2, 110, 200],
    [42, 94, 255],
    [254, 123, 255],
    [43, 57, 218],
    [255, 144, 85],
    [111, 75, 55],
    [132, 68, 0],
    [0, 110, 58],
    [138, 56, 67],
    [227, 245, 255],
    [255, 123, 171],
    [206, 145, 255],
    [79, 86, 46],
    [1, 205, 73],
    [0, 87, 162],
    [179, 146, 0],
    [63, 139, 0],
    [1, 140, 22],
    [1, 235, 254],
    [47, 87, 113],
    [133, 255, 237],
    [227, 193, 0],
    [139, 114, 0],
    [137, 15, 169],
    [244, 255, 187],
    [240, 163, 255],
    [166, 0, 78],
    [255, 72, 32],
    [86, 84, 60],
    [87, 255, 124],
    [210, 70, 0],
    [255, 175, 185],
    [0, 205, 203],
    [120, 66, 87],
    [255, 143, 236],
    [255, 248, 243],
    [0, 226, 110],
    [255, 230, 135],
    [255, 59, 163],
    [247, 0, 179],
    [117, 235, 255],
    [219, 96, 0],
    [255, 140, 172],
    [210, 255, 201],
    [78, 84, 78],
    [188, 255, 181],
    [129, 255, 173],
    [255, 154, 21],
    [255, 42, 126],
    [255, 159, 95],
    [200, 0, 175],
    [95, 223, 14],
    [77, 76, 138],
    [157, 255, 186],
    [1, 184, 192],
    [115, 124, 0],
    [167, 255, 121],
    [255, 216, 240],
    [0, 169, 235],
    [145, 50, 46],
    [144, 43, 100],
    [234, 255, 242],
    [117, 176, 255],
    [154, 65, 241],
    [62, 88, 77],
    [125, 46, 150],
    [131, 57, 91],
    [205, 0, 60],
    [255, 169, 45],
    [177, 111, 0],
    [0, 215, 154],
    [61, 108, 0],
    [246, 255, 162],
    [145, 29, 131],
    [138, 85, 255],
    [255, 138, 131],
    [112, 188, 255],
    [244, 154, 0],
    [255, 226, 222],
    [2, 191, 165],
    [166, 205, 0],
    [237, 77, 254],
    [1, 131, 204],
    [251, 0, 34],
    [178, 0, 21],
    [141, 222, 255],
    [1, 168, 204],
    [61, 207, 0],
    [46, 89, 95],
    [100, 170, 0],
    [255, 115, 75],
    [255, 199, 111],
    [255, 184, 252],
    [41, 157, 0],
    [155, 255, 100],
    [1, 199, 181],
    [105, 72, 97],
    [231, 0, 96],
    [213, 0, 142],
    [149, 47, 28],
    [255, 226, 102],
    [255, 52, 144],
    [56, 87, 99],
    [155, 22, 106],
    [179, 82, 0],
    [213, 255, 109],
    [236, 255, 99],
    [227, 0, 40],
    [86, 98, 0],
    [131, 249, 51],
    [1, 118, 89],
    [255, 209, 172],
    [171, 50, 0],
    [245, 81, 0],
    [136, 202, 255],
    [0, 110, 25],
    [227, 128, 255],
    [255, 190, 169],
    [0, 178, 39],
    [230, 255, 63],
    [255, 217, 133],
    [182, 238, 0],
    [182, 255, 209],
    [0, 172, 47],
    [94, 117, 0],
    [210, 0, 123],
    [244, 184, 0],
    [216, 160, 255],
    [134, 255, 207],
    [45, 84, 132],
    [240, 255, 132],
    [0, 147, 143],
    [199, 0, 45],
    [15, 154, 255],
    [49, 255, 249],
    [255, 159, 189],
    [255, 200, 213],
    [105, 114, 255],
    [255, 99, 228],
    [0, 180, 134],
    [212, 178, 255],
    [159, 29, 59],
    [244, 243, 0],
    [198, 164, 255],
    [1, 134, 146],
    [0, 121, 9],
    [137, 131, 0],
    [255, 178, 223],
    [122, 42, 218],
    [0, 143, 83],
    [255, 105, 120],
    [0, 134, 160],
    [164, 116, 0],
    [255, 135, 96],
    [165, 151, 0],
    [159, 96, 0],
    [255, 228, 204],
    [225, 0, 208],
    [255, 165, 135],
    [12, 68, 203],
    [90, 158, 255],
    [1, 102, 174],
    [127, 57, 112],
    [105, 55, 168],
    [203, 95, 255],
    [159, 0, 145],
    [193, 106, 0],
    [255, 131, 207],
    [200, 223, 255],
    [100, 255, 185],
    [1, 102, 116],
    [178, 255, 240],
    [1, 209, 39],
    [236, 205, 255],
    [18, 247, 88],
    [118, 72, 15],
    [1, 153, 55],
    [183, 209, 0],
    [255, 139, 42],
    [171, 125, 255],
    [1, 85, 210],
    [227, 135, 0],
    [183, 0, 96],
    [16, 202, 255],
    [194, 0, 209],
    [255, 232, 168],
    [255, 75, 149],
    [106, 63, 140],
    [101, 79, 41],
    [92, 79, 93],
    [181, 101, 255],
    [0, 235, 234],
    [92, 242, 61],
    [1, 122, 159],
    [224, 0, 173],
    [155, 185, 1],
    [127, 84, 0],
    [0, 101, 148],
    [255, 213, 42],
    [188, 255, 115],
    [255, 53, 184],
    [183, 210, 255],
    [234, 224, 255],
    [76, 88, 17],
    [253, 26, 16],
    [169, 0, 59],
    [0, 163, 81],
    [255, 173, 96],
    [210, 255, 236],
    [1, 182, 242],
    [136, 60, 30],
    [53, 92, 34],
    [1, 103, 210],
    [255, 90, 83],
    [126, 54, 124],
    [193, 249, 255],
])
