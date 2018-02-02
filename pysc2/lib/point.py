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
"""Basic Point and Rect classes."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import math
import random


class Point(collections.namedtuple("Point", ["x", "y"])):
  """A basic Point class."""
  __slots__ = ()

  @classmethod
  def build(cls, obj):
    """Build a Point from an object that has properties `x` and `y`."""
    return cls(obj.x, obj.y)

  @classmethod
  def unit_rand(cls):
    """Return a Point with x, y chosen randomly with 0 <= x < 1, 0 <= y < 1."""
    return cls(random.random(), random.random())

  def assign_to(self, obj):
    """Assign `x` and `y` to an object that has properties `x` and `y`."""
    obj.x = self.x
    obj.y = self.y

  def dist(self, other):
    """Distance to some other point."""
    dx = self.x - other.x
    dy = self.y - other.y
    return math.sqrt(dx**2 + dy**2)

  def dist_sq(self, other):
    """Distance squared to some other point."""
    dx = self.x - other.x
    dy = self.y - other.y
    return dx**2 + dy**2

  def round(self):
    """Round `x` and `y` to integers."""
    return Point(int(round(self.x)), int(round(self.y)))

  def floor(self):
    """Round `x` and `y` down to integers."""
    return Point(int(math.floor(self.x)), int(math.floor(self.y)))

  def ceil(self):
    """Round `x` and `y` up to integers."""
    return Point(int(math.ceil(self.x)), int(math.ceil(self.y)))

  def abs(self):
    """Take the absolute value of `x` and `y`."""
    return Point(abs(self.x), abs(self.y))

  def len(self):
    """Length of the vector to this point."""
    return math.sqrt(self.x**2 + self.y**2)

  def scale(self, target_len):
    """Scale the vector to have the target length."""
    return self * (target_len / self.len())

  def scale_max_size(self, max_size):
    """Scale this value, keeping aspect ratio, but fitting inside `max_size`."""
    return self * (max_size / self).min_dim()

  def scale_min_size(self, min_size):
    """Scale this value, keeping aspect ratio, but fitting around `min_size`."""
    return self * (min_size / self).max_dim()

  def min_dim(self):
    return min(self.x, self.y)

  def max_dim(self):
    return max(self.x, self.y)

  def transpose(self):
    """Flip x and y."""
    return Point(self.y, self.x)

  def rotate_deg(self, angle):
    return self.rotate_rad(math.radians(angle))

  def rotate_rad(self, angle):
    return Point(self.x * math.cos(angle) - self.y * math.sin(angle),
                 self.x * math.sin(angle) + self.y * math.cos(angle))

  def rotate_rand(self, angle=180):
    return self.rotate_deg(random.uniform(-angle, angle))

  def contained_circle(self, pt, radius):
    """Is this point inside the circle defined by (`pt`, `radius`)?"""
    return self.dist(pt) < radius

  def bound(self, p1, p2=None):
    """Bound this point within the rect defined by (`p1`, `p2`)."""
    r = Rect(p1, p2)
    return Point(min(max(self.x, r.l), r.r), min(max(self.y, r.t), r.b))

  def __str__(self):
    return "%.6f,%.6f" % self

  def __neg__(self):
    return Point(-self.x, -self.y)

  def __add__(self, pt_or_val):
    if isinstance(pt_or_val, Point):
      return Point(self.x + pt_or_val.x, self.y + pt_or_val.y)
    else:
      return Point(self.x + pt_or_val, self.y + pt_or_val)

  def __sub__(self, pt_or_val):
    if isinstance(pt_or_val, Point):
      return Point(self.x - pt_or_val.x, self.y - pt_or_val.y)
    else:
      return Point(self.x - pt_or_val, self.y - pt_or_val)

  def __mul__(self, pt_or_val):
    if isinstance(pt_or_val, Point):
      return Point(self.x * pt_or_val.x, self.y * pt_or_val.y)
    else:
      return Point(self.x * pt_or_val, self.y * pt_or_val)

  def __truediv__(self, pt_or_val):
    if isinstance(pt_or_val, Point):
      return Point(self.x / pt_or_val.x, self.y / pt_or_val.y)
    else:
      return Point(self.x / pt_or_val, self.y / pt_or_val)

  def __floordiv__(self, pt_or_val):
    if isinstance(pt_or_val, Point):
      return Point(int(self.x // pt_or_val.x), int(self.y // pt_or_val.y))
    else:
      return Point(int(self.x // pt_or_val), int(self.y // pt_or_val))

  __div__ = __truediv__


origin = Point(0, 0)


class Rect(collections.namedtuple("Rect", ["t", "l", "b", "r"])):
  """A basic Rect class. Assumes tl <= br."""
  __slots__ = ()

  def __new__(cls, *args):
    if len(args) == 1 or (len(args) == 2 and args[1] is None):
      args = (origin, args[0])
    if len(args) == 2:
      p1, p2 = args
      if not isinstance(p1, Point) or not isinstance(p2, Point):
        raise TypeError("Rect expected Points")
      return super(Rect, cls).__new__(
          cls,
          min(p1.y, p2.y),
          min(p1.x, p2.x),
          max(p1.y, p2.y),
          max(p1.x, p2.x))
    if len(args) == 4:
      if args[0] > args[2] or args[1] > args[3]:
        raise TypeError("Rect requires: t <= b and l <= r")
      return super(Rect, cls).__new__(cls, *args)
    raise TypeError(
        "Unexpected arguments to Rect. Takes 1 or 2 Points, or 4 coords.")

  def __str__(self):
    return "%.6f,%.6f,%.6f,%.6f" % self

  @property
  def center(self):
    return Point(self.l + self.r, self.t + self.b) / 2

  @property
  def top(self):
    return self.t

  @property
  def left(self):
    return self.l

  @property
  def bottom(self):
    return self.b

  @property
  def right(self):
    return self.r

  @property
  def width(self):
    return self.r - self.l

  @property
  def height(self):
    return self.b - self.t

  @property
  def tl(self):
    return Point(self.l, self.t)

  @property
  def br(self):
    return Point(self.r, self.b)

  @property
  def tr(self):
    return Point(self.r, self.t)

  @property
  def bl(self):
    return Point(self.l, self.b)

  @property
  def size(self):
    return self.br - self.tl

  @property
  def area(self):
    size = self.size
    return size.x * size.y

  def contains_point(self, pt):
    """Is the point inside this rect?"""
    return (self.l < pt.x and self.r > pt.x and
            self.t < pt.y and self.b > pt.y)

  def contains_circle(self, pt, radius):
    """Is the circle completely inside this rect?"""
    return (self.l < pt.x - radius and self.r > pt.x + radius and
            self.t < pt.y - radius and self.b > pt.y + radius)

  def intersects_circle(self, pt, radius):
    """Does the circle intersect with this rect?"""
    # How this works: http://stackoverflow.com/a/402010
    rect_corner = self.size / 2  # relative to the rect center
    circle_center = (pt - self.center).abs()  # relative to the rect center

    # Is the circle far from the rect?
    if (circle_center.x > rect_corner.x + radius or
        circle_center.y > rect_corner.y + radius):
      return False

    # Is the circle center inside the rect or near one of the edges?
    if (circle_center.x <= rect_corner.x or
        circle_center.y <= rect_corner.y):
      return True

    # Does the circle contain the corner of the rect?
    return circle_center.dist_sq(rect_corner) <= radius**2
