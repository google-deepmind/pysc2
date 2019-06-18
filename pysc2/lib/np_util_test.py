#!/usr/bin/python
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Tests for np_util.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest
from absl.testing import parameterized
import numpy as np
from pysc2.lib import np_util


class NpUtilTest(parameterized.TestCase):

  @parameterized.named_parameters(
      ("no_diff_1d", [1, 2, 3, 4], [1, 2, 3, 4], ""),
      ("no_diff_2d", [[1, 2], [3, 4]], [[1, 2], [3, 4]], ""),
      ("diff_1d", [1, 2, 3, 4], [1, 3, 2, 4],
       "2 element(s) changed - [1]: 2 -> 3; [2]: 3 -> 2"),
      ("diff_2d", [[1, 2], [3, 4]], [[1, 3], [2, 4]],
       "2 element(s) changed - [0][1]: 2 -> 3; [1][0]: 3 -> 2"))
  def testSummarizeArrayDiffs(self, lhs, rhs, expected):
    a = np.array(lhs)
    b = np.array(rhs)
    result = np_util.summarize_array_diffs(a, b)
    self.assertEqual(result, expected)


if __name__ == "__main__":
  absltest.main()
