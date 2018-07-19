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

  for i in range(1, scale):
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
  # Can specify a scale to match the api or to accept unknown unit types.
  palette_size = scale or max(static_data.UNIT_TYPES) + 1
  palette = shuffled_hue(palette_size)
  assert len(static_data.UNIT_TYPES) <= len(distinct_colors)
  for i, v in enumerate(static_data.UNIT_TYPES):
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
# 255 colors: H: 0-360, C: 0-100, L: 35-100; then shuffled.
distinct_colors = numpy.array([
    [85, 238, 255],
    [79, 84, 36],
    [227, 117, 255],
    [255, 86, 137],
    [210, 0, 141],
    [152, 51, 0],
    [255, 233, 174],
    [125, 149, 0],
    [198, 0, 57],
    [169, 26, 0],
    [0, 84, 234],
    [215, 255, 144],
    [0, 108, 123],
    [1, 150, 136],
    [185, 88, 255],
    [255, 49, 42],
    [137, 124, 255],
    [244, 84, 255],
    [231, 191, 255],
    [255, 171, 174],
    [229, 255, 231],
    [172, 0, 205],
    [198, 20, 0],
    [212, 159, 0],
    [0, 98, 46],
    [176, 102, 0],
    [203, 175, 255],
    [133, 49, 102],
    [195, 255, 124],
    [1, 224, 129],
    [151, 39, 51],
    [49, 81, 135],
    [249, 176, 0],
    [255, 203, 125],
    [0, 169, 192],
    [1, 59, 221],
    [165, 194, 255],
    [0, 164, 74],
    [99, 106, 0],
    [217, 200, 255],
    [255, 134, 79],
    [255, 150, 143],
    [147, 25, 115],
    [150, 0, 154],
    [122, 86, 0],
    [2, 143, 194],
    [255, 29, 80],
    [149, 32, 89],
    [1, 150, 227],
    [255, 153, 66],
    [40, 88, 88],
    [0, 125, 211],
    [0, 180, 84],
    [60, 53, 221],
    [219, 218, 255],
    [183, 103, 255],
    [0, 90, 160],
    [138, 103, 255],
    [208, 0, 94],
    [0, 189, 237],
    [90, 77, 91],
    [255, 83, 45],
    [121, 66, 51],
    [173, 254, 255],
    [130, 58, 66],
    [237, 117, 0],
    [2, 172, 234],
    [85, 81, 59],
    [78, 173, 255],
    [255, 147, 174],
    [255, 50, 155],
    [255, 170, 53],
    [0, 112, 242],
    [224, 79, 0],
    [1, 122, 129],
    [31, 210, 24],
    [127, 63, 31],
    [240, 255, 76],
    [112, 72, 31],
    [255, 93, 24],
    [117, 67, 69],
    [74, 84, 72],
    [253, 255, 222],
    [1, 253, 168],
    [255, 93, 89],
    [181, 0, 117],
    [58, 120, 0],
    [1, 83, 191],
    [141, 110, 0],
    [188, 164, 0],
    [180, 226, 0],
    [66, 83, 95],
    [1, 135, 28],
    [169, 255, 176],
    [16, 92, 75],
    [158, 26, 36],
    [255, 130, 253],
    [0, 199, 138],
    [229, 255, 107],
    [255, 104, 109],
    [93, 255, 235],
    [35, 91, 58],
    [0, 161, 255],
    [1, 85, 174],
    [2, 211, 246],
    [0, 122, 97],
    [156, 255, 140],
    [111, 196, 0],
    [0, 143, 2],
    [160, 3, 81],
    [255, 244, 154],
    [255, 66, 15],
    [255, 175, 114],
    [133, 225, 0],
    [255, 176, 98],
    [123, 70, 0],
    [120, 22, 187],
    [1, 199, 179],
    [236, 0, 13],
    [213, 151, 255],
    [160, 105, 0],
    [255, 114, 141],
    [255, 118, 193],
    [67, 138, 0],
    [114, 72, 5],
    [114, 50, 154],
    [167, 127, 0],
    [128, 65, 239],
    [101, 136, 255],
    [177, 209, 255],
    [143, 27, 211],
    [143, 0, 165],
    [1, 116, 178],
    [255, 247, 199],
    [255, 241, 244],
    [255, 202, 88],
    [237, 255, 151],
    [196, 1, 166],
    [199, 255, 199],
    [255, 185, 205],
    [1, 79, 210],
    [138, 53, 44],
    [250, 255, 249],
    [255, 233, 100],
    [255, 151, 123],
    [194, 76, 0],
    [72, 80, 106],
    [255, 106, 206],
    [132, 44, 125],
    [255, 109, 68],
    [98, 143, 0],
    [0, 156, 162],
    [255, 169, 218],
    [255, 219, 68],
    [79, 255, 177],
    [171, 85, 0],
    [184, 120, 255],
    [237, 255, 199],
    [214, 0, 80],
    [168, 213, 0],
    [98, 78, 38],
    [138, 54, 32],
    [106, 69, 94],
    [129, 43, 136],
    [116, 60, 115],
    [167, 252, 31],
    [255, 194, 92],
    [224, 233, 255],
    [0, 132, 69],
    [255, 247, 50],
    [255, 200, 216],
    [144, 145, 0],
    [97, 215, 255],
    [1, 212, 166],
    [254, 166, 255],
    [255, 29, 131],
    [84, 85, 0],
    [93, 79, 54],
    [200, 255, 160],
    [42, 92, 16],
    [1, 214, 106],
    [137, 207, 255],
    [183, 191, 0],
    [255, 132, 225],
    [210, 255, 106],
    [36, 248, 255],
    [1, 193, 196],
    [136, 255, 111],
    [0, 82, 241],
    [124, 169, 255],
    [0, 141, 237],
    [171, 255, 224],
    [255, 246, 134],
    [0, 92, 100],
    [145, 255, 170],
    [255, 172, 77],
    [0, 88, 119],
    [255, 194, 175],
    [0, 98, 21],
    [192, 195, 255],
    [61, 97, 0],
    [150, 255, 203],
    [71, 53, 202],
    [216, 67, 246],
    [120, 255, 208],
    [88, 82, 13],
    [210, 0, 115],
    [189, 119, 0],
    [255, 171, 157],
    [215, 171, 0],
    [238, 104, 0],
    [115, 104, 0],
    [160, 229, 255],
    [0, 166, 116],
    [0, 127, 147],
    [222, 1, 27],
    [85, 57, 181],
    [255, 178, 148],
    [100, 75, 70],
    [255, 81, 106],
    [39, 240, 75],
    [247, 0, 54],
    [27, 69, 189],
    [77, 146, 255],
    [255, 66, 206],
    [242, 0, 174],
    [255, 217, 216],
    [161, 255, 244],
    [159, 20, 58],
    [176, 143, 255],
    [255, 161, 39],
    [0, 214, 199],
    [163, 93, 255],
    [88, 68, 142],
    [131, 122, 0],
    [206, 0, 46],
    [224, 47, 230],
    [51, 89, 69],
    [50, 90, 41],
    [211, 227, 0],
    [255, 195, 238],
    [176, 255, 134],
    [196, 247, 255],
    [48, 78, 147],
    [79, 68, 156],
    [1, 105, 200],
    [255, 117, 230],
    [2, 225, 235],
    [255, 72, 230],
    [1, 132, 97],
    [255, 213, 155],
    [151, 33, 73],
    [1, 185, 30],
    [255, 159, 221],
    [0, 141, 86],
])
