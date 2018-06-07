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
"""Print the valid actions."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import app
from absl import flags

from pysc2.lib import actions
from pysc2.lib import features
from pysc2.lib import point_flag

FLAGS = flags.FLAGS
point_flag.DEFINE_point("screen_size", "84", "Resolution for screen actions.")
point_flag.DEFINE_point("minimap_size", "64", "Resolution for minimap actions.")
flags.DEFINE_bool("hide_specific", False, "Hide the specific actions")


def main(unused_argv):
  """Print the valid actions."""
  feats = features.Features(
      # Actually irrelevant whether it's feature or rgb size.
      features.AgentInterfaceFormat(
          feature_dimensions=features.Dimensions(
              screen=FLAGS.screen_size,
              minimap=FLAGS.minimap_size)))
  action_spec = feats.action_spec()
  flattened = 0
  count = 0
  for func in action_spec.functions:
    if FLAGS.hide_specific and actions.FUNCTIONS[func.id].general_id != 0:
      continue
    count += 1
    act_flat = 1
    for arg in func.args:
      for size in arg.sizes:
        act_flat *= size
    flattened += act_flat
    print(func.str(True))
  print("Total base actions:", count)
  print("Total possible actions (flattened):", flattened)


if __name__ == "__main__":
  app.run(main)
