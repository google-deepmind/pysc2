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
"""An env wrapper to print the available actions."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2.env import base_env_wrapper


class AvailableActionsPrinter(base_env_wrapper.BaseEnvWrapper):
  """An env wrapper to print the available actions."""

  def __init__(self, env):
    super(AvailableActionsPrinter, self).__init__(env)
    self._seen = set()
    self._action_spec = self.action_spec()[0]

  def step(self, *args, **kwargs):
    all_obs = super(AvailableActionsPrinter, self).step(*args, **kwargs)
    for obs in all_obs:
      for avail in obs.observation["available_actions"]:
        if avail not in self._seen:
          self._seen.add(avail)
          self._print(self._action_spec.functions[avail].str(True))
    return all_obs

  def _print(self, s):
    print(s)
