#!/usr/bin/python
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Tests for lib.named_array."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import pickle

from absl.testing import absltest
from absl.testing import parameterized
import enum
import numpy as np

from pysc2.lib import named_array


class NamedDictTest(absltest.TestCase):

  def test_named_dict(self):
    a = named_array.NamedDict(a=2, b=(1, 2))
    self.assertEqual(a["a"], a.a)
    self.assertEqual(a["b"], a.b)
    self.assertIs(a["b"], a.b)
    self.assertNotEqual(a["a"], a.b)
    a.c = 3
    self.assertEqual(a["c"], 3)


class TestEnum(enum.IntEnum):
  a = 0
  b = 1
  c = 2


class BadEnum(enum.IntEnum):
  a = 1
  b = 2
  c = 3


class TestNamedTuple(collections.namedtuple("TestNamedTuple", ["a", "b", "c"])):
  pass


class BadNamedTuple(collections.namedtuple("BadNamedTuple", ["a", "b"])):
  pass


class NamedArrayTest(parameterized.TestCase):

  def assertArrayEqual(self, a, b):
    np.testing.assert_array_equal(a, b)

  @parameterized.named_parameters(
      ("none", None),
      ("none2", [None]),
      ("short_list", ["a"]),
      ("long_list", ["a", "b", "c", "d"]),
      ("long_list2", [["a", "b", "c", "d"]]),
      ("ints", [[1, "b", 3]]),
      ("bad_enum", [BadEnum]),
      ("bad_namedtuple", [BadNamedTuple]),
      ("dict", [{"a": 0, "b": 1, "c": 2}]),
      ("set", [{"a", "b", "c"}]),
  )
  def test_bad_names(self, names):
    with self.assertRaises(ValueError):
      named_array.NamedNumpyArray([1, 3, 6], names)

  @parameterized.named_parameters(
      ("list", ["a", "b", "c"]),
      ("tuple", ("a", "b", "c")),
      ("list2", [["a", "b", "c"]]),
      ("tuple2", (("a", "b", "c"))),
      ("list_tuple", [("a", "b", "c")]),
      ("named_tuple", TestNamedTuple),
      ("named_tuple2", [TestNamedTuple]),
      ("int_enum", TestEnum),
      ("int_enum2", [TestEnum]),
  )
  def test_single_dimension(self, names):
    a = named_array.NamedNumpyArray([1, 3, 6], names)
    self.assertEqual(a[0], 1)
    self.assertEqual(a[1], 3)
    self.assertEqual(a[2], 6)
    self.assertEqual(a[-1], 6)
    self.assertEqual(a.a, 1)
    self.assertEqual(a.b, 3)
    self.assertEqual(a.c, 6)
    with self.assertRaises(AttributeError):
      a.d  # pylint: disable=pointless-statement
    self.assertEqual(a["a"], 1)
    self.assertEqual(a["b"], 3)
    self.assertEqual(a["c"], 6)
    with self.assertRaises(KeyError):
      a["d"]  # pylint: disable=pointless-statement

    # range slicing
    self.assertArrayEqual(a[0:2], [1, 3])
    self.assertArrayEqual(a[1:3], [3, 6])
    self.assertArrayEqual(a[0:2:], [1, 3])
    self.assertArrayEqual(a[0:2:1], [1, 3])
    self.assertArrayEqual(a[::2], [1, 6])
    self.assertArrayEqual(a[::-1], [6, 3, 1])
    self.assertEqual(a[1:3][0], 3)
    self.assertEqual(a[1:3].b, 3)
    self.assertEqual(a[1:3].c, 6)

    # list slicing
    self.assertArrayEqual(a[[0, 0]], [1, 1])
    self.assertArrayEqual(a[[0, 1]], [1, 3])
    self.assertArrayEqual(a[[1, 0]], [3, 1])
    self.assertArrayEqual(a[[1, 2]], [3, 6])
    self.assertArrayEqual(a[np.array([0, 2])], [1, 6])
    self.assertEqual(a[[1, 2]].b, 3)
    self.assertEqual(a[[2, 0]].c, 6)

    a[1] = 4
    self.assertEqual(a[1], 4)
    self.assertEqual(a.b, 4)
    self.assertEqual(a["b"], 4)

    a[1:2] = 2
    self.assertEqual(a[1], 2)
    self.assertEqual(a.b, 2)
    self.assertEqual(a["b"], 2)

    a[[1]] = 3
    self.assertEqual(a[1], 3)
    self.assertEqual(a.b, 3)
    self.assertEqual(a["b"], 3)

    a.b = 5
    self.assertEqual(a[1], 5)
    self.assertEqual(a.b, 5)
    self.assertEqual(a["b"], 5)

  def test_empty_array(self):
    named_array.NamedNumpyArray([], [None, ["a", "b"]])
    with self.assertRaises(ValueError):
      # Must be the right length.
      named_array.NamedNumpyArray([], [["a", "b"]])
    with self.assertRaises(ValueError):
      # Returning an empty slice is not supported, and it's not clear how or
      # even if it should be supported.
      named_array.NamedNumpyArray([], [["a", "b"], None])
    with self.assertRaises(ValueError):
      # Scalar arrays are unsupported.
      named_array.NamedNumpyArray(1, [])

  def test_named_array_multi_first(self):
    a = named_array.NamedNumpyArray([[1, 3], [6, 8]], [["a", "b"], None])
    self.assertArrayEqual(a.a, [1, 3])
    self.assertArrayEqual(a[1], [6, 8])
    self.assertArrayEqual(a["b"], [6, 8])
    self.assertArrayEqual(a[::-1], [[6, 8], [1, 3]])
    self.assertArrayEqual(a[::-1][::-1], [[1, 3], [6, 8]])
    self.assertArrayEqual(a[::-1, ::-1], [[8, 6], [3, 1]])
    self.assertArrayEqual(a[::-1][0], [6, 8])
    self.assertArrayEqual(a[::-1, 0], [6, 1])
    self.assertArrayEqual(a[::-1, 1], [8, 3])
    self.assertArrayEqual(a[::-1].a, [1, 3])
    self.assertArrayEqual(a[::-1].a[0], 1)
    self.assertArrayEqual(a[::-1].b, [6, 8])
    self.assertArrayEqual(a[[0, 0]], [[1, 3], [1, 3]])
    self.assertArrayEqual(a[[0, 0]].a, [1, 3])
    self.assertEqual(a[0, 1], 3)
    self.assertEqual(a[(0, 1)], 3)
    self.assertEqual(a["a", 0], 1)
    self.assertEqual(a["b", 0], 6)
    self.assertEqual(a["b", 1], 8)
    self.assertEqual(a.a[0], 1)
    with self.assertRaises(TypeError):
      a[0].a  # pylint: disable=pointless-statement

  def test_named_array_multi_second(self):
    a = named_array.NamedNumpyArray([[1, 3], [6, 8]], [None, ["a", "b"]])
    self.assertArrayEqual(a[0], [1, 3])
    self.assertEqual(a[0, 1], 3)
    self.assertEqual(a[0, "a"], 1)
    self.assertEqual(a[0, "b"], 3)
    self.assertEqual(a[1, "b"], 8)
    self.assertEqual(a[0].a, 1)
    with self.assertRaises(TypeError):
      a.a  # pylint: disable=pointless-statement

  def test_slicing(self):
    a = named_array.NamedNumpyArray([1, 2, 3, 4, 5], list("abcde"))
    self.assertArrayEqual(a[:], [1, 2, 3, 4, 5])
    self.assertArrayEqual(a[::], [1, 2, 3, 4, 5])
    self.assertArrayEqual(a[::2], [1, 3, 5])
    self.assertArrayEqual(a[::-1], [5, 4, 3, 2, 1])
    self.assertEqual(a[:].a, 1)
    self.assertEqual(a[::].b, 2)
    self.assertEqual(a[::2].c, 3)
    with self.assertRaises(AttributeError):
      a[::2].d  # pylint: disable=pointless-statement
    self.assertEqual(a[::-1].e, 5)
    self.assertArrayEqual(a[a % 2 == 0], [2, 4])
    self.assertEqual(a[a % 2 == 0].b, 2)

    a = named_array.NamedNumpyArray([[1, 2, 3, 4], [5, 6, 7, 8]],
                                    [None, list("abcd")])
    self.assertArrayEqual(a[:], [[1, 2, 3, 4], [5, 6, 7, 8]])
    self.assertArrayEqual(a[::], [[1, 2, 3, 4], [5, 6, 7, 8]])
    self.assertArrayEqual(a[:, :], [[1, 2, 3, 4], [5, 6, 7, 8]])
    self.assertArrayEqual(a[:, ...], [[1, 2, 3, 4], [5, 6, 7, 8]])
    self.assertArrayEqual(a[..., ::], [[1, 2, 3, 4], [5, 6, 7, 8]])
    self.assertArrayEqual(a[:, ::2], [[1, 3], [5, 7]])

    self.assertArrayEqual(a[::-1], [[5, 6, 7, 8], [1, 2, 3, 4]])
    self.assertArrayEqual(a[..., ::-1], [[4, 3, 2, 1], [8, 7, 6, 5]])
    self.assertArrayEqual(a[:, ::-1], [[4, 3, 2, 1], [8, 7, 6, 5]])
    self.assertArrayEqual(a[:, ::-2], [[4, 2], [8, 6]])
    self.assertArrayEqual(a[:, -2::-2], [[3, 1], [7, 5]])
    self.assertArrayEqual(a[::-1, -2::-2], [[7, 5], [3, 1]])
    self.assertArrayEqual(a[..., 0, 0], 1)  # weird scalar arrays...

    a = named_array.NamedNumpyArray(
        [[[[0, 1], [2, 3]], [[4, 5], [6, 7]]],
         [[[8, 9], [10, 11]], [[12, 13], [14, 15]]]],
        [["a", "b"], ["c", "d"], ["e", "f"], ["g", "h"]])
    self.assertEqual(a.a.c.e.g, 0)
    self.assertEqual(a.b.c.f.g, 10)
    self.assertEqual(a.b.d.f.h, 15)
    self.assertArrayEqual(a[0, ..., 0], [[0, 2], [4, 6]])
    self.assertArrayEqual(a[0, ..., 1], [[1, 3], [5, 7]])
    self.assertArrayEqual(a[0, 0, ..., 1], [1, 3])
    self.assertArrayEqual(a[0, ..., 1, 1], [3, 7])
    self.assertArrayEqual(a[..., 1, 1], [[3, 7], [11, 15]])
    self.assertArrayEqual(a[1, 0, ...], [[8, 9], [10, 11]])

    self.assertArrayEqual(a["a", ..., "g"], [[0, 2], [4, 6]])
    self.assertArrayEqual(a["a", ...], [[[0, 1], [2, 3]], [[4, 5], [6, 7]]])
    self.assertArrayEqual(a[..., "g"], [[[0, 2], [4, 6]], [[8, 10], [12, 14]]])
    self.assertArrayEqual(a["a", "c"], [[0, 1], [2, 3]])
    self.assertArrayEqual(a["a", ...].c, [[0, 1], [2, 3]])
    self.assertArrayEqual(a["a", ..., "g"].c, [0, 2])

    with self.assertRaises(TypeError):
      a[np.array([[0, 1], [0, 1]])]  # pylint: disable=pointless-statement, expression-not-assigned

    with self.assertRaises(IndexError):
      a[..., 0, ...]  # pylint: disable=pointless-statement

  def test_string(self):
    a = named_array.NamedNumpyArray([1, 3, 6], ["a", "b", "c"], dtype=np.int32)
    self.assertEqual(str(a), "[1 3 6]")
    self.assertEqual(repr(a), ("NamedNumpyArray([1, 3, 6], ['a', 'b', 'c'], "
                               "dtype=int32)"))

    a = named_array.NamedNumpyArray([[1, 3], [6, 8]], [None, ["a", "b"]])
    self.assertEqual(str(a), "[[1 3]\n [6 8]]")
    self.assertEqual(repr(a), ("NamedNumpyArray([[1, 3],\n"
                               "                 [6, 8]], [None, ['a', 'b']])"))

    a = named_array.NamedNumpyArray([[1, 3], [6, 8]], [["a", "b"], None])
    self.assertEqual(str(a), "[[1 3]\n [6 8]]")
    self.assertEqual(repr(a), ("NamedNumpyArray([[1, 3],\n"
                               "                 [6, 8]], [['a', 'b'], None])"))

    a = named_array.NamedNumpyArray([list(range(50))] * 50,
                                    [None, ["a%s" % i for i in range(50)]])
    self.assertIn("49", str(a))
    self.assertIn("49", repr(a))

    a = named_array.NamedNumpyArray([list(range(50))] * 50,
                                    [["a%s" % i for i in range(50)], None])
    self.assertIn("49", str(a))
    self.assertIn("49", repr(a))

  def test_pickle(self):
    arr = named_array.NamedNumpyArray([1, 3, 6], ["a", "b", "c"])
    pickled = pickle.loads(pickle.dumps(arr))
    self.assertTrue(np.all(arr == pickled))
    self.assertEqual(repr(pickled),
                     "NamedNumpyArray([1, 3, 6], ['a', 'b', 'c'])")

if __name__ == "__main__":
  absltest.main()
