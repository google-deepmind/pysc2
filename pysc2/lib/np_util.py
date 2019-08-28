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
"""Diff proto objects returning paths to changed attributes."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np


def summarize_array_diffs(lhs, rhs):
  """Output value differences, with index for each, between two arrays."""
  result = []
  indices = np.transpose(np.nonzero(lhs - rhs))
  for row in indices:
    index = tuple(np.array([e]) for e in row.tolist())
    lhs_element = lhs[index]
    rhs_element = rhs[index]
    result.append("{}: {} -> {}".format(
        "".join("[{}]".format(i) for i in row), lhs_element[0], rhs_element[0]))

  if indices.size:
    return "{} element(s) changed - ".format(len(indices)) + "; ".join(result)
  else:
    return ""
