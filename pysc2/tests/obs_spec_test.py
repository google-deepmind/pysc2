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
"""Verify that the observations match the observation spec."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest
from future.builtins import range  # pylint: disable=redefined-builtin
import six

from pysc2.agents import random_agent
from pysc2.env import sc2_env
from pysc2.tests import utils


class TestObservationSpec(utils.TestCase):

  def test_observation_matches_obs_spec(self):
    with sc2_env.SC2Env(
        map_name="Simple64",
        feature_screen_width=84,
        feature_screen_height=87,
        feature_minimap_width=64,
        feature_minimap_height=67) as env:

      multiplayer_obs_spec = env.observation_spec()
      self.assertIsInstance(multiplayer_obs_spec, tuple)
      self.assertLen(multiplayer_obs_spec, 1)
      obs_spec = multiplayer_obs_spec[0]

      multiplayer_action_spec = env.action_spec()
      self.assertIsInstance(multiplayer_action_spec, tuple)
      self.assertLen(multiplayer_action_spec, 1)
      action_spec = multiplayer_action_spec[0]

      agent = random_agent.RandomAgent()
      agent.setup(obs_spec, action_spec)

      multiplayer_obs = env.reset()
      agent.reset()
      for _ in range(100):
        self.assertIsInstance(multiplayer_obs, tuple)
        self.assertLen(multiplayer_obs, 1)
        raw_obs = multiplayer_obs[0]

        obs = raw_obs.observation
        self.assertItemsEqual(obs_spec.keys(), obs.keys())
        for k, o in six.iteritems(obs):
          descr = "%s: spec: %s != obs: %s" % (k, obs_spec[k], o.shape)

          if o.shape == (0,):  # Empty tensor can't have a shape.
            self.assertIn(0, obs_spec[k], descr)
          else:
            self.assertEqual(len(obs_spec[k]), len(o.shape), descr)
            for a, b in zip(obs_spec[k], o.shape):
              if a != 0:
                self.assertEqual(a, b, descr)

        act = agent.step(raw_obs)
        multiplayer_act = (act,)
        multiplayer_obs = env.step(multiplayer_act)


if __name__ == "__main__":
  absltest.main()
