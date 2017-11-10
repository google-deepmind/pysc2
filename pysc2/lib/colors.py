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
distinct_colors = numpy.array([
    [128, 72, 135],
    [82, 219, 53],
    [152, 62, 231],
    [141, 206, 35],
    [95, 62, 218],
    [62, 196, 61],
    [202, 69, 237],
    [124, 215, 88],
    [169, 39, 195],
    [47, 155, 36],
    [224, 74, 230],
    [104, 184, 58],
    [60, 80, 221],
    [243, 192, 17],
    [124, 102, 247],
    [198, 193, 32],
    [36, 90, 218],
    [158, 199, 56],
    [134, 40, 179],
    [76, 206, 114],
    [232, 75, 209],
    [27, 225, 159],
    [226, 52, 182],
    [118, 165, 26],
    [171, 83, 218],
    [83, 147, 34],
    [148, 103, 234],
    [233, 195, 56],
    [80, 115, 247],
    [210, 175, 31],
    [95, 74, 194],
    [182, 193, 66],
    [124, 62, 186],
    [233, 175, 42],
    [60, 77, 187],
    [235, 149, 25],
    [68, 134, 246],
    [239, 93, 21],
    [68, 101, 211],
    [161, 160, 35],
    [184, 57, 181],
    [69, 156, 63],
    [235, 53, 166],
    [38, 168, 99],
    [213, 114, 236],
    [100, 141, 42],
    [141, 39, 152],
    [76, 207, 146],
    [248, 54, 125],
    [71, 215, 192],
    [231, 37, 37],
    [60, 205, 228],
    [239, 70, 32],
    [78, 180, 243],
    [195, 35, 17],
    [81, 205, 205],
    [240, 52, 69],
    [89, 207, 162],
    [233, 39, 92],
    [127, 202, 118],
    [175, 38, 142],
    [46, 109, 28],
    [157, 134, 249],
    [216, 182, 68],
    [132, 125, 235],
    [246, 189, 83],
    [140, 97, 205],
    [174, 196, 98],
    [112, 65, 162],
    [195, 185, 80],
    [82, 76, 162],
    [224, 169, 63],
    [116, 131, 226],
    [226, 122, 34],
    [94, 144, 233],
    [207, 75, 28],
    [49, 160, 222],
    [213, 56, 45],
    [105, 204, 237],
    [194, 22, 42],
    [74, 181, 163],
    [220, 28, 67],
    [42, 140, 92],
    [244, 74, 149],
    [82, 146, 78],
    [212, 34, 115],
    [157, 205, 125],
    [152, 64, 159],
    [136, 171, 76],
    [198, 121, 223],
    [121, 140, 48],
    [175, 133, 237],
    [186, 136, 26],
    [120, 98, 189],
    [170, 145, 42],
    [152, 95, 188],
    [85, 105, 18],
    [198, 90, 185],
    [119, 186, 127],
    [215, 31, 99],
    [71, 163, 128],
    [217, 65, 144],
    [55, 100, 42],
    [238, 131, 221],
    [134, 119, 24],
    [64, 146, 223],
    [241, 83, 72],
    [60, 170, 200],
    [167, 57, 22],
    [121, 193, 239],
    [207, 54, 74],
    [46, 140, 129],
    [238, 84, 98],
    [48, 112, 75],
    [180, 32, 115],
    [105, 165, 115],
    [240, 102, 171],
    [74, 138, 99],
    [220, 103, 181],
    [123, 151, 95],
    [177, 32, 96],
    [139, 203, 173],
    [173, 19, 75],
    [134, 203, 209],
    [195, 48, 93],
    [94, 168, 168],
    [211, 64, 105],
    [47, 96, 70],
    [245, 101, 153],
    [80, 108, 61],
    [219, 161, 243],
    [187, 125, 39],
    [62, 102, 178],
    [231, 152, 70],
    [124, 165, 236],
    [188, 97, 37],
    [126, 132, 208],
    [221, 169, 85],
    [98, 88, 153],
    [199, 179, 100],
    [164, 114, 190],
    [155, 102, 20],
    [149, 187, 239],
    [241, 117, 76],
    [50, 112, 164],
    [203, 83, 55],
    [89, 152, 188],
    [219, 90, 83],
    [58, 134, 151],
    [234, 85, 123],
    [29, 104, 110],
    [248, 117, 116],
    [57, 98, 129],
    [237, 144, 106],
    [121, 144, 197],
    [171, 43, 59],
    [144, 184, 215],
    [172, 65, 53],
    [174, 166, 231],
    [94, 95, 29],
    [247, 165, 229],
    [118, 123, 59],
    [215, 72, 127],
    [177, 199, 148],
    [168, 64, 130],
    [174, 180, 123],
    [147, 47, 92],
    [132, 170, 135],
    [226, 114, 170],
    [82, 125, 103],
    [237, 116, 150],
    [90, 98, 61],
    [211, 131, 194],
    [134, 107, 41],
    [198, 144, 210],
    [112, 82, 22],
    [201, 186, 237],
    [157, 78, 43],
    [88, 91, 135],
    [218, 169, 105],
    [145, 121, 175],
    [164, 129, 63],
    [171, 112, 167],
    [148, 141, 83],
    [162, 81, 133],
    [219, 189, 141],
    [119, 80, 115],
    [235, 167, 120],
    [113, 122, 161],
    [212, 115, 91],
    [172, 149, 188],
    [144, 86, 42],
    [233, 163, 209],
    [116, 99, 50],
    [201, 82, 111],
    [134, 137, 99],
    [174, 75, 110],
    [192, 160, 119],
    [153, 51, 70],
    [223, 184, 155],
    [138, 71, 86],
    [235, 185, 199],
    [100, 79, 51],
    [212, 169, 195],
    [135, 99, 65],
    [200, 120, 157],
    [189, 130, 84],
    [162, 107, 135],
    [214, 98, 102],
    [233, 173, 159],
    [136, 77, 66],
    [235, 157, 175],
    [179, 82, 89],
    [194, 142, 145],
    [230, 131, 151],
    [177, 127, 104],
    [232, 135, 134],
    [164, 102, 103],
    [233, 149, 136],
    [192, 114, 106],
])
