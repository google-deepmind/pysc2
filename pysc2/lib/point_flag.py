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
"""Define a flag type for points."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import flags
import six

from pysc2.lib import point


class PointParser(flags.ArgumentParser):
  """Parse a flag into a point."""

  def parse(self, argument):
    if not argument or argument == "0":
      return None

    if isinstance(argument, int):
      args = [argument]
    elif isinstance(argument, (list, tuple)):
      args = argument
    elif isinstance(argument, six.string_types):
      args = argument.split(",")
    else:
      raise ValueError(
          "Invalid point: '%r'. Valid: '<int>' or '<int>,<int>'." % argument)

    args = [int(v) for v in args]

    if len(args) == 1:
      args *= 2
    if len(args) == 2:
      return point.Point(args[0], args[1])
    raise ValueError(
        "Invalid point: '%s'. Valid: '<int>' or '<int>,<int>'." % argument)

  def flag_type(self):
    return "pysc2 point"


def DEFINE_point(name, default, help):  # pylint: disable=invalid-name,redefined-builtin
  """Registers a flag whose value parses as a point."""
  flags.DEFINE(PointParser(), name, default, help)
