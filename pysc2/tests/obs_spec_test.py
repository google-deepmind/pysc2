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

from future.builtins import range  # pylint: disable=redefined-builtin
import six

from pysc2.agents import random_agent
from pysc2.env import sc2_env
from pysc2.tests import utils

from absl.testing import absltest as basetest


class TestObservationSpec(utils.TestCase):

  def test_observation_matches_obs_spec(self):
    with sc2_env.SC2Env(map_name="Simple64") as env:
      spec = env.observation_spec()

      agent = random_agent.RandomAgent()
      agent.setup(spec, env.action_spec())

      raw_obs = env.reset()[0]
      agent.reset()
      for _ in range(100):
        obs = raw_obs.observation

        self.assertItemsEqual(spec.keys(), obs.keys())
        for k, o in six.iteritems(obs):
          descr = "%s: spec: %s != obs: %s" % (k, spec[k], o.shape)

          if o.shape == (0,):  # Empty tensor can't have a shape.
            self.assertIn(0, spec[k], descr)
          else:
            self.assertEqual(len(spec[k]), len(o.shape), descr)
            for a, b in zip(spec[k], o.shape):
              if a != 0:
                self.assertEqual(a, b, descr)

        act = agent.step(raw_obs)
        raw_obs = env.step([act])[0]

if __name__ == "__main__":
  basetest.main()
