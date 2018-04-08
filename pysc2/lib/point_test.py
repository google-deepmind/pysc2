#!/usr/bin/python
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
"""Tests for the point library."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest
from future.builtins import int  # pylint: disable=redefined-builtin

from pysc2.lib import point


class FakePoint(object):

  def __init__(self):
    self.x = 5
    self.y = 8


class PointTest(absltest.TestCase):

  def testBuild(self):
    self.assertEqual(point.Point(5, 8), point.Point.build(FakePoint()))

  def testAssignTo(self):
    f = FakePoint()
    self.assertEqual(5, f.x)
    self.assertEqual(8, f.y)
    point.Point(1, 2).assign_to(f)
    self.assertEqual(1, f.x)
    self.assertEqual(2, f.y)

  def testDist(self):
    a = point.Point(1, 1)
    b = point.Point(4, 5)
    self.assertEqual(5, a.dist(b))

  def testDistSq(self):
    a = point.Point(1, 1)
    b = point.Point(4, 5)
    self.assertEqual(25, a.dist_sq(b))

  def testLen(self):
    p = point.Point(3, 4)
    self.assertEqual(5, p.len())

  def testScale(self):
    p = point.Point(3, 4)
    self.assertAlmostEqual(2, p.scale(2).len())

  def testScaleMaxSize(self):
    p = point.Point(3, 4)
    self.assertEqual(p, p.scale_max_size(p))
    self.assertEqual(point.Point(6, 8), p.scale_max_size(point.Point(8, 8)))
    self.assertEqual(point.Point(6, 8), p.scale_max_size(point.Point(100, 8)))
    self.assertEqual(point.Point(6, 8), p.scale_max_size(point.Point(6, 100)))

  def testScaleMinSize(self):
    p = point.Point(3, 4)
    self.assertEqual(p, p.scale_min_size(p))
    self.assertEqual(point.Point(6, 8), p.scale_min_size(point.Point(6, 6)))
    self.assertEqual(point.Point(6, 8), p.scale_min_size(point.Point(2, 8)))
    self.assertEqual(point.Point(6, 8), p.scale_min_size(point.Point(6, 2)))

  def testMinDim(self):
    self.assertEqual(5, point.Point(5, 10).min_dim())

  def testMaxDim(self):
    self.assertEqual(10, point.Point(5, 10).max_dim())

  def testTranspose(self):
    self.assertEqual(point.Point(4, 3), point.Point(3, 4).transpose())

  def testRound(self):
    p = point.Point(1.3, 2.6).round()
    self.assertEqual(point.Point(1, 3), p)
    self.assertIsInstance(p.x, int)
    self.assertIsInstance(p.y, int)

  def testCeil(self):
    p = point.Point(1.3, 2.6).ceil()
    self.assertEqual(point.Point(2, 3), p)
    self.assertIsInstance(p.x, int)
    self.assertIsInstance(p.y, int)

  def testFloor(self):
    p = point.Point(1.3, 2.6).floor()
    self.assertEqual(point.Point(1, 2), p)
    self.assertIsInstance(p.x, int)
    self.assertIsInstance(p.y, int)

  def testRotate(self):
    p = point.Point(0, 100)
    self.assertEqual(point.Point(-100, 0), p.rotate_deg(90).round())
    self.assertEqual(point.Point(100, 0), p.rotate_deg(-90).round())
    self.assertEqual(point.Point(0, -100), p.rotate_deg(180).round())

  def testContainedCircle(self):
    self.assertTrue(point.Point(2, 2).contained_circle(point.Point(1, 1), 2))
    self.assertFalse(point.Point(2, 2).contained_circle(point.Point(1, 1), 0.5))

  def testBound(self):
    tl = point.Point(1, 2)
    br = point.Point(3, 4)
    self.assertEqual(tl, point.Point(0, 0).bound(tl, br))
    self.assertEqual(br, point.Point(10, 10).bound(tl, br))
    self.assertEqual(point.Point(1.5, 2), point.Point(1.5, 0).bound(tl, br))


class RectTest(absltest.TestCase):

  def testInit(self):
    r = point.Rect(1, 2, 3, 4)
    self.assertEqual(r.t, 1)
    self.assertEqual(r.l, 2)
    self.assertEqual(r.b, 3)
    self.assertEqual(r.r, 4)
    self.assertEqual(r.tl, point.Point(2, 1))
    self.assertEqual(r.tr, point.Point(4, 1))
    self.assertEqual(r.bl, point.Point(2, 3))
    self.assertEqual(r.br, point.Point(4, 3))

  def testInitBad(self):
    with self.assertRaises(TypeError):
      point.Rect(4, 3, 2, 1)  # require t <= b, l <= r
    with self.assertRaises(TypeError):
      point.Rect(1)
    with self.assertRaises(TypeError):
      point.Rect(1, 2, 3)
    with self.assertRaises(TypeError):
      point.Rect()

  def testInitOnePoint(self):
    r = point.Rect(point.Point(1, 2))
    self.assertEqual(r.t, 0)
    self.assertEqual(r.l, 0)
    self.assertEqual(r.b, 2)
    self.assertEqual(r.r, 1)
    self.assertEqual(r.tl, point.Point(0, 0))
    self.assertEqual(r.tr, point.Point(1, 0))
    self.assertEqual(r.bl, point.Point(0, 2))
    self.assertEqual(r.br, point.Point(1, 2))
    self.assertEqual(r.size, point.Point(1, 2))
    self.assertEqual(r.center, point.Point(1, 2) / 2)
    self.assertEqual(r.area, 2)

  def testInitTwoPoints(self):
    r = point.Rect(point.Point(1, 2), point.Point(3, 4))
    self.assertEqual(r.t, 2)
    self.assertEqual(r.l, 1)
    self.assertEqual(r.b, 4)
    self.assertEqual(r.r, 3)
    self.assertEqual(r.tl, point.Point(1, 2))
    self.assertEqual(r.tr, point.Point(3, 2))
    self.assertEqual(r.bl, point.Point(1, 4))
    self.assertEqual(r.br, point.Point(3, 4))
    self.assertEqual(r.size, point.Point(2, 2))
    self.assertEqual(r.center, point.Point(2, 3))
    self.assertEqual(r.area, 4)

  def testInitTwoPointsReversed(self):
    r = point.Rect(point.Point(3, 4), point.Point(1, 2))
    self.assertEqual(r.t, 2)
    self.assertEqual(r.l, 1)
    self.assertEqual(r.b, 4)
    self.assertEqual(r.r, 3)
    self.assertEqual(r.tl, point.Point(1, 2))
    self.assertEqual(r.tr, point.Point(3, 2))
    self.assertEqual(r.bl, point.Point(1, 4))
    self.assertEqual(r.br, point.Point(3, 4))
    self.assertEqual(r.size, point.Point(2, 2))
    self.assertEqual(r.center, point.Point(2, 3))
    self.assertEqual(r.area, 4)

  def testArea(self):
    r = point.Rect(point.Point(1, 1), point.Point(3, 4))
    self.assertEqual(r.area, 6)

  def testContains(self):
    r = point.Rect(point.Point(1, 1), point.Point(3, 3))
    self.assertTrue(r.contains_point(point.Point(2, 2)))
    self.assertFalse(r.contains_circle(point.Point(2, 2), 5))
    self.assertFalse(r.contains_point(point.Point(4, 4)))
    self.assertFalse(r.contains_circle(point.Point(4, 4), 5))

  def testIntersectsCircle(self):
    r = point.Rect(point.Point(1, 1), point.Point(3, 3))
    self.assertFalse(r.intersects_circle(point.Point(0, 0), 0.5))
    self.assertFalse(r.intersects_circle(point.Point(0, 0), 1))
    self.assertTrue(r.intersects_circle(point.Point(0, 0), 1.5))
    self.assertTrue(r.intersects_circle(point.Point(0, 0), 2))


if __name__ == '__main__':
  absltest.main()
