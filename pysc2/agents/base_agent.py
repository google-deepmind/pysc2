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
"""A base agent to write custom scripted agents."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2.lib import actions


class BaseAgent(object):
  """A base agent to write custom scripted agents.

  It can also act as a passive agent that does nothing but no-ops.
  """

  def __init__(self):
    self.reward = 0
    self.episodes = 0
    self.steps = 0
    self.obs_spec = None
    self.action_spec = None

  def setup(self, obs_spec, action_spec):
    self.obs_spec = obs_spec
    self.action_spec = action_spec

  def reset(self):
    self.episodes += 1

  def step(self, obs):
    self.steps += 1
    self.reward += obs.reward
    return actions.FunctionCall(actions.FUNCTIONS.no_op.id, [])
