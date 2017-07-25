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
"""A base env wrapper so we don't need to override everything every time."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2.env import environment


class BaseEnvWrapper(environment.Base):
  """A base env wrapper so we don't need to override everything every time."""

  def __init__(self, env):
    self._env = env

  def close(self, *args, **kwargs):
    return self._env.close(*args, **kwargs)

  def action_spec(self, *args, **kwargs):
    return self._env.action_spec(*args, **kwargs)

  def observation_spec(self, *args, **kwargs):
    return self._env.observation_spec(*args, **kwargs)

  def reset(self, *args, **kwargs):
    return self._env.reset(*args, **kwargs)

  def step(self, *args, **kwargs):
    return self._env.step(*args, **kwargs)

  def save_replay(self, *args, **kwargs):
    return self._env.save_replay(*args, **kwargs)

  @property
  def state(self):
    return self._env.state
