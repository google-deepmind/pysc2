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
        agent_interface_format=sc2_env.AgentInterfaceFormat(
            feature_dimensions=sc2_env.Dimensions(
                screen=(84, 87),
                minimap=(64, 67)))) as env:

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
        self.check_observation_matches_spec(obs, obs_spec)

        act = agent.step(raw_obs)
        multiplayer_act = (act,)
        multiplayer_obs = env.step(multiplayer_act)

  def test_heterogeneous_observations(self):
    with sc2_env.SC2Env(
        map_name="Simple64",
        players=[
            sc2_env.Agent(sc2_env.Race.random),
            sc2_env.Agent(sc2_env.Race.random)
        ],
        agent_interface_format=[
            sc2_env.AgentInterfaceFormat(
                feature_dimensions=sc2_env.Dimensions(
                    screen=(84, 87),
                    minimap=(64, 67)
                )
            ),
            sc2_env.AgentInterfaceFormat(
                rgb_dimensions=sc2_env.Dimensions(
                    screen=128,
                    minimap=64
                )
            )
        ]) as env:

      obs_specs = env.observation_spec()
      self.assertIsInstance(obs_specs, tuple)
      self.assertLen(obs_specs, 2)

      actions_specs = env.action_spec()
      self.assertIsInstance(actions_specs, tuple)
      self.assertLen(actions_specs, 2)

      agents = []
      for obs_spec, action_spec in zip(obs_specs, actions_specs):
        agent = random_agent.RandomAgent()
        agent.setup(obs_spec, action_spec)
        agent.reset()
        agents.append(agent)

      time_steps = env.reset()
      for _ in range(100):
        self.assertIsInstance(time_steps, tuple)
        self.assertLen(time_steps, 2)

        actions = []
        for i, agent in enumerate(agents):
          time_step = time_steps[i]
          obs = time_step.observation
          self.check_observation_matches_spec(obs, obs_specs[i])
          actions.append(agent.step(time_step))

        time_steps = env.step(actions)

  def check_observation_matches_spec(self, obs, obs_spec):
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


if __name__ == "__main__":
  absltest.main()
