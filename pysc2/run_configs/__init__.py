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
"""Configs for various ways to run starcraft."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import flags

from pysc2.lib import sc_process
from pysc2.run_configs import platforms
from pysc2.run_configs import lib

flags.DEFINE_string("sc2_run_config", None,
                    "Which run_config to use to spawn the binary.")
FLAGS = flags.FLAGS


def get():
  """Get the config chosen by the flags."""
  configs = {c.name(): c
             for c in lib.RunConfig.all_subclasses() if c.priority()}

  if not configs:
    raise sc_process.SC2LaunchError("No valid run_configs found.")

  if FLAGS.sc2_run_config is None:  # Find the highest priority as default.
    return max(configs.values(), key=lambda c: c.priority())()

  try:
    return configs[FLAGS.sc2_run_config]()
  except KeyError:
    raise sc_process.SC2LaunchError(
        "Invalid run_config. Valid configs are: %s" % (
            ", ".join(sorted(configs.keys()))))
