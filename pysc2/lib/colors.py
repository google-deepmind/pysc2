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

import collections
import math
import random

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
  random.seed(21) # provide a fixed seed (modify as necessary) to support Python 3.9+
  random.shuffle(palette)  # Return a fixed shuffle
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
# 350 colors: H: 0-360, C: 0-100, L: 35-100; then shuffled.
distinct_colors = numpy.array([
    [99, 91, 0],
    [195, 211, 0],
    [57, 206, 255],
    [255, 172, 106],
    [255, 187, 77],
    [255, 195, 114],
    [0, 102, 201],
    [3, 249, 197],
    [79, 84, 81],
    [255, 252, 198],
    [0, 132, 134],
    [255, 155, 144],
    [255, 211, 140],
    [41, 91, 83],
    [101, 77, 73],
    [0, 144, 124],
    [146, 41, 97],
    [2, 223, 228],
    [173, 77, 0],
    [255, 93, 193],
    [54, 92, 36],
    [119, 255, 202],
    [154, 0, 183],
    [0, 156, 121],
    [144, 173, 0],
    [255, 254, 173],
    [62, 90, 54],
    [144, 54, 5],
    [2, 169, 191],
    [132, 255, 249],
    [196, 158, 255],
    [187, 8, 0],
    [138, 255, 99],
    [236, 163, 255],
    [78, 255, 187],
    [128, 64, 56],
    [255, 195, 148],
    [0, 101, 209],
    [149, 193, 255],
    [0, 239, 125],
    [134, 65, 240],
    [0, 222, 123],
    [255, 249, 146],
    [0, 247, 164],
    [8, 169, 0],
    [156, 36, 46],
    [255, 174, 81],
    [0, 102, 84],
    [139, 213, 0],
    [142, 87, 0],
    [215, 255, 55],
    [203, 255, 124],
    [0, 96, 93],
    [63, 78, 147],
    [227, 255, 115],
    [160, 0, 131],
    [69, 148, 0],
    [142, 149, 0],
    [255, 72, 70],
    [0, 229, 224],
    [127, 63, 76],
    [248, 139, 255],
    [2, 188, 206],
    [0, 128, 203],
    [113, 151, 0],
    [255, 203, 103],
    [0, 178, 172],
    [128, 53, 122],
    [163, 4, 83],
    [2, 79, 204],
    [235, 128, 0],
    [0, 106, 247],
    [164, 156, 255],
    [179, 173, 0],
    [255, 124, 221],
    [115, 209, 0],
    [62, 249, 255],
    [240, 118, 0],
    [45, 84, 135],
    [106, 96, 255],
    [39, 89, 109],
    [0, 86, 192],
    [255, 133, 151],
    [90, 192, 0],
    [156, 0, 154],
    [127, 51, 133],
    [216, 255, 82],
    [160, 255, 212],
    [106, 43, 191],
    [224, 255, 221],
    [167, 47, 227],
    [255, 217, 85],
    [251, 173, 255],
    [92, 55, 185],
    [162, 28, 1],
    [126, 102, 255],
    [212, 140, 255],
    [113, 66, 111],
    [216, 0, 205],
    [70, 242, 69],
    [120, 109, 255],
    [0, 132, 180],
    [122, 67, 62],
    [255, 166, 54],
    [140, 173, 255],
    [105, 79, 0],
    [39, 227, 55],
    [255, 71, 238],
    [112, 75, 18],
    [149, 83, 255],
    [255, 130, 205],
    [255, 138, 39],
    [0, 184, 21],
    [202, 154, 0],
    [145, 52, 41],
    [185, 255, 85],
    [151, 46, 8],
    [255, 215, 128],
    [2, 192, 148],
    [80, 81, 101],
    [255, 166, 114],
    [0, 161, 80],
    [255, 56, 89],
    [2, 223, 146],
    [98, 246, 255],
    [150, 251, 255],
    [255, 125, 56],
    [144, 51, 53],
    [83, 133, 255],
    [1, 82, 173],
    [122, 118, 0],
    [255, 86, 174],
    [67, 87, 78],
    [131, 65, 4],
    [170, 255, 204],
    [0, 108, 66],
    [248, 96, 255],
    [212, 101, 255],
    [99, 230, 34],
    [140, 41, 121],
    [173, 0, 175],
    [255, 190, 175],
    [186, 179, 255],
    [171, 221, 255],
    [78, 255, 135],
    [220, 0, 32],
    [255, 217, 192],
    [46, 58, 215],
    [68, 255, 230],
    [96, 81, 53],
    [1, 174, 246],
    [72, 70, 166],
    [255, 233, 77],
    [255, 166, 197],
    [255, 208, 241],
    [183, 255, 62],
    [255, 226, 226],
    [107, 255, 119],
    [148, 122, 0],
    [171, 255, 143],
    [255, 109, 232],
    [156, 142, 255],
    [124, 148, 255],
    [178, 236, 255],
    [168, 91, 0],
    [255, 255, 248],
    [255, 92, 91],
    [132, 238, 255],
    [225, 131, 0],
    [255, 149, 111],
    [171, 157, 0],
    [255, 133, 181],
    [196, 158, 0],
    [2, 162, 246],
    [193, 110, 0],
    [255, 243, 244],
    [255, 180, 181],
    [255, 79, 221],
    [255, 211, 109],
    [0, 99, 118],
    [255, 167, 214],
    [89, 81, 83],
    [147, 255, 120],
    [2, 210, 200],
    [255, 244, 113],
    [255, 197, 248],
    [0, 122, 37],
    [255, 194, 57],
    [130, 130, 255],
    [107, 77, 29],
    [255, 153, 56],
    [178, 104, 255],
    [17, 98, 0],
    [0, 119, 128],
    [146, 106, 0],
    [117, 255, 186],
    [255, 155, 232],
    [1, 87, 232],
    [61, 83, 120],
    [200, 255, 187],
    [196, 221, 255],
    [100, 73, 112],
    [115, 218, 255],
    [85, 114, 0],
    [208, 142, 0],
    [255, 30, 147],
    [156, 0, 200],
    [239, 0, 122],
    [255, 43, 170],
    [0, 87, 241],
    [237, 255, 248],
    [0, 151, 44],
    [255, 155, 161],
    [218, 0, 107],
    [139, 57, 29],
    [148, 255, 174],
    [100, 69, 131],
    [195, 0, 29],
    [177, 64, 0],
    [93, 81, 60],
    [2, 162, 172],
    [205, 0, 134],
    [255, 168, 135],
    [225, 93, 0],
    [125, 39, 165],
    [187, 255, 126],
    [2, 196, 237],
    [234, 119, 255],
    [240, 0, 182],
    [115, 181, 0],
    [255, 125, 125],
    [67, 90, 26],
    [242, 255, 69],
    [185, 81, 255],
    [255, 195, 130],
    [32, 95, 35],
    [215, 0, 153],
    [197, 125, 0],
    [46, 104, 0],
    [72, 73, 155],
    [177, 183, 0],
    [149, 40, 81],
    [255, 145, 88],
    [164, 16, 58],
    [215, 187, 255],
    [119, 204, 255],
    [198, 255, 237],
    [255, 92, 65],
    [197, 244, 255],
    [0, 146, 22],
    [118, 179, 255],
    [255, 94, 144],
    [208, 1, 182],
    [28, 200, 0],
    [0, 121, 97],
    [167, 0, 111],
    [25, 84, 143],
    [2, 191, 98],
    [175, 0, 127],
    [48, 92, 57],
    [119, 71, 31],
    [255, 169, 186],
    [2, 115, 247],
    [111, 74, 50],
    [255, 82, 41],
    [41, 94, 11],
    [42, 155, 255],
    [235, 52, 0],
    [243, 167, 0],
    [255, 96, 134],
    [61, 255, 216],
    [220, 255, 177],
    [3, 162, 206],
    [183, 0, 90],
    [255, 237, 208],
    [86, 153, 0],
    [207, 255, 220],
    [255, 194, 229],
    [255, 93, 34],
    [3, 95, 57],
    [0, 160, 99],
    [1, 89, 165],
    [167, 128, 0],
    [1, 215, 245],
    [167, 255, 97],
    [187, 0, 77],
    [173, 0, 32],
    [0, 101, 130],
    [58, 90, 66],
    [255, 102, 112],
    [0, 120, 89],
    [240, 182, 255],
    [125, 90, 0],
    [216, 210, 255],
    [244, 0, 78],
    [88, 85, 18],
    [228, 181, 0],
    [169, 207, 0],
    [24, 134, 0],
    [217, 255, 255],
    [216, 255, 147],
    [133, 55, 93],
    [205, 90, 255],
    [255, 119, 97],
    [255, 227, 164],
    [50, 129, 0],
    [1, 138, 243],
    [0, 134, 68],
    [98, 255, 245],
    [255, 94, 158],
    [186, 204, 255],
    [0, 191, 163],
    [1, 141, 207],
    [2, 228, 103],
    [255, 208, 171],
    [207, 78, 0],
    [0, 147, 86],
    [217, 32, 0],
    [194, 0, 50],
    [0, 122, 68],
    [255, 235, 48],
    [183, 28, 217],
    [193, 167, 0],
    [250, 0, 200],
    [154, 36, 64],
    [126, 58, 107],
    [103, 127, 0],
    [210, 106, 0],
    [220, 0, 49],
    [0, 107, 143],
    [255, 181, 242],
    [166, 255, 183],
    [95, 66, 149],
    [0, 210, 151],
    [1, 217, 81],
    [255, 238, 184],
    [253, 255, 0],
    [201, 0, 75],
    [0, 170, 49],
    [255, 215, 209],
    [94, 61, 168],
    [117, 54, 151],
    [91, 83, 37],
    [190, 1, 209],
    [216, 241, 0],
    [243, 230, 255],
    [233, 255, 193],
    [169, 141, 0],
    [80, 96, 0],
    [0, 101, 34],
])
