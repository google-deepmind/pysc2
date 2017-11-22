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
"""Tests for lib.run_parallel."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import threading

from absl.testing import absltest
from pysc2.lib import run_parallel


class Barrier(object):

  def __init__(self, n):
    self.n = n
    self.count = 0
    self.cond = threading.Condition()

  def wait(self):
    self.cond.acquire()
    me = self.count
    self.count += 1
    if self.count < self.n:
      self.cond.wait()
    else:
      self.count = 0
      self.cond.notify_all()
    self.cond.release()
    return me

  def clear(self):
    self.cond.acquire()
    self.cond.notify_all()
    self.cond.release()


def bad():
  raise ValueError()


class RunParallelTest(absltest.TestCase):

  def test_returns_expected_values(self):
    pool = run_parallel.RunParallel()
    out = pool.run([int])
    self.assertListEqual(out, [0])
    out = pool.run([lambda: 1, lambda: 2, lambda: "asdf", lambda: {1: 2}])
    self.assertListEqual(out, [1, 2, "asdf", {1: 2}])

  def test_run_in_parallel(self):
    b = Barrier(3)
    pool = run_parallel.RunParallel()
    out = pool.run([b.wait, b.wait, b.wait])
    self.assertItemsEqual(out, [0, 1, 2])

  def test_avoids_deadlock(self):
    b = Barrier(2)
    pool = run_parallel.RunParallel(timeout=2)
    with self.assertRaises(ValueError):
      pool.run([int, b.wait, bad])
    # Release the thread waiting on the barrier so the process can exit cleanly.
    b.clear()

  def test_exception(self):
    pool = run_parallel.RunParallel()
    out = pool.run([lambda: 1, ValueError])
    self.assertEqual(out[0], 1)
    self.assertIsInstance(out[1], ValueError)
    with self.assertRaises(ValueError):
      pool.run([bad])
    with self.assertRaises(ValueError):
      pool.run([int, bad])

  def test_partial(self):
    pool = run_parallel.RunParallel()
    out = pool.run((max, 0, i - 2) for i in range(5))
    self.assertListEqual(out, [0, 0, 0, 1, 2])


if __name__ == "__main__":
  absltest.main()
