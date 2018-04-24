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
"""Transform coordinates for rendering in various ways.

It's best to name these as `a_to_b` for example `screen_to_world`. The
`fwd` methods take a point or distance in coordinate system `a` and
convert it to a point or distance in coordinate system `b`. The `back` methods
do the reverse going from `b` to `a`.

These can then be chained as b_to_c.fwd(a_to_b.fwd(pt)) which will take
something in `a` and return something in `c`. It's better to use the Chain
transform to create `a_to_c`.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numbers

from pysc2.lib import point


class Transform(object):
  """Base class for coordinate transforms."""

  def fwd_dist(self, dist):
    raise NotImplementedError()

  def fwd_pt(self, pt):
    raise NotImplementedError()

  def back_dist(self, dist):
    raise NotImplementedError()

  def back_pt(self, pt):
    raise NotImplementedError()


class Linear(Transform):
  """A linear transform with a scale and offset."""

  def __init__(self, scale=None, offset=None):
    if scale is None:
      self.scale = point.Point(1, 1)
    elif isinstance(scale, numbers.Number):
      self.scale = point.Point(scale, scale)
    else:
      self.scale = scale
    assert self.scale.x != 0 and self.scale.y != 0
    self.offset = offset or point.Point(0, 0)

  def fwd_dist(self, dist):
    return dist * self.scale.x

  def fwd_pt(self, pt):
    return pt * self.scale + self.offset

  def back_dist(self, dist):
    return dist / self.scale.x

  def back_pt(self, pt):
    return (pt - self.offset) / self.scale

  def __str__(self):
    return "Linear(scale=%s, offset=%s)" % (self.scale, self.offset)


class Chain(Transform):
  """Chain a set of transforms: Chain(a_to_b, b_to_c) => a_to_c."""

  def __init__(self, *args):
    self.transforms = args

  def fwd_dist(self, dist):
    for transform in self.transforms:
      dist = transform.fwd_dist(dist)
    return dist

  def fwd_pt(self, pt):
    for transform in self.transforms:
      pt = transform.fwd_pt(pt)
    return pt

  def back_dist(self, dist):
    for transform in reversed(self.transforms):
      dist = transform.back_dist(dist)
    return dist

  def back_pt(self, pt):
    for transform in reversed(self.transforms):
      pt = transform.back_pt(pt)
    return pt

  def __str__(self):
    return "Chain(%s)" % (self.transforms,)


class PixelToCoord(Transform):
  """Take a point within a pixel and use the tl, or tl to pixel center."""

  def fwd_dist(self, dist):
    return dist

  def fwd_pt(self, pt):
    return pt.floor()

  def back_dist(self, dist):
    return dist

  def back_pt(self, pt):
    return pt.floor() + 0.5

  def __str__(self):
    return "PixelToCoord()"

