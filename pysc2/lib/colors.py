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

import numpy


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

  mask0 = h == 0
  mask1 = h < 1
  mask2 = h < 2
  mask3 = h < 3
  mask4 = h < 4
  mask5 = h < 5

  mask = mask1 - mask0  # h in (0, 1)
  r[mask] = c
  g[mask] = x[mask]

  mask = mask2 - mask1  # h in [1, 2)
  r[mask] = x[mask]
  g[mask] = c

  mask = mask3 - mask2  # h in [2, 3)
  g[mask] = c
  b[mask] = x[mask]

  mask = mask4 - mask3  # h in [3, 4)
  g[mask] = x[mask]
  b[mask] = c

  mask = mask5 - mask4  # h in [4, 5)
  r[mask] = x[mask]
  b[mask] = c

  mask = ~mask5  # [5, 6)
  r[mask] = c
  b[mask] = x[mask]

  return out


# Palette used to color player_relative features.
PLAYER_RELATIVE_PALETTE = numpy.array([
    black,         # Background.
    green * 0.5,   # Self.
    yellow,        # Ally.
    cyan,          # Neutral.
    red * 0.8,     # Enemy.
])

VISIBILITY_PALETTE = numpy.array([
    black,         # Hidden
    white * 0.25,  # Fogged
    white * 0.6,   # Visible
])

CREEP_PALETTE = numpy.array([black, purple * 0.4])
POWER_PALETTE = numpy.array([black, cyan])
