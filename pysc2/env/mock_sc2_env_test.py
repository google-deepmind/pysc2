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
"""Tests of the StarCraft2 mock environment."""

from absl.testing import absltest
import mock
import numpy as np

from pysc2.env import enums
from pysc2.env import environment
from pysc2.env import mock_sc2_env
from pysc2.env import sc2_env
from pysc2.lib import features

from s2clientprotocol import common_pb2
from s2clientprotocol import raw_pb2
from s2clientprotocol import sc2api_pb2


class _TestMixin(object):

  def assert_spec(self, array, shape, dtype):
    self.assertSequenceEqual(array.shape, shape)
    self.assertEqual(array.dtype, dtype)

  def assert_equal(self, actual, expected):
    np.testing.assert_equal(actual, expected)

  def assert_reset(self, env):
    expected = env.next_timestep[0]._replace(
        step_type=environment.StepType.FIRST, reward=0, discount=0)
    timestep = env.reset()
    self.assert_equal(timestep, [expected])

  def assert_first_step(self, env):
    expected = env.next_timestep[0]._replace(
        step_type=environment.StepType.FIRST, reward=0, discount=0)
    timestep = env.step([mock.sentinel.action])
    self.assert_equal(timestep, [expected])

  def assert_mid_step(self, env):
    expected = env.next_timestep[0]._replace(
        step_type=environment.StepType.MID)
    timestep = env.step([mock.sentinel.action])
    self.assert_equal(timestep, [expected])

  def assert_last_step(self, env):
    expected = env.next_timestep[0]._replace(
        step_type=environment.StepType.LAST,
        discount=0.)
    timestep = env.step([mock.sentinel.action])
    self.assert_equal(timestep, [expected])

  def _test_episode(self, env):
    env.next_timestep = [env.next_timestep[0]._replace(
        step_type=environment.StepType.MID)]
    self.assert_first_step(env)

    for step in range(1, 10):
      env.next_timestep = [env.next_timestep[0]._replace(
          reward=step, discount=step / 10)]
      self.assert_mid_step(env)

    env.next_timestep = [env.next_timestep[0]._replace(
        step_type=environment.StepType.LAST, reward=10, discount=0.0)]
    self.assert_last_step(env)

  def _test_episode_length(self, env, length):
    self.assert_reset(env)
    for _ in range(length - 1):
      self.assert_mid_step(env)
    self.assert_last_step(env)

    self.assert_first_step(env)
    for _ in range(length - 1):
      self.assert_mid_step(env)
    self.assert_last_step(env)


class TestTestEnvironment(_TestMixin, absltest.TestCase):

  def setUp(self):
    super(TestTestEnvironment, self).setUp()
    self._env = mock_sc2_env._TestEnvironment(
        num_agents=1,
        observation_spec=({'mock': [10, 1]},),
        action_spec=(mock.sentinel.action_spec,))

  def test_observation_spec(self):
    self.assertEqual(self._env.observation_spec(), ({'mock': [10, 1]},))

  def test_action_spec(self):
    self.assertEqual(self._env.action_spec(), (mock.sentinel.action_spec,))

  def test_default_observation(self):
    observation = self._env._default_observation(
        self._env.observation_spec()[0], 0)
    self.assert_equal(observation, {'mock': np.zeros([10, 1], dtype=np.int32)})

  def test_episode(self):
    self._env.episode_length = float('inf')
    self._test_episode(self._env)

  def test_two_episodes(self):
    self._env.episode_length = float('inf')
    self._test_episode(self._env)
    self._test_episode(self._env)

  def test_episode_length(self):
    self._env.episode_length = 16
    self._test_episode_length(self._env, length=16)


class TestSC2TestEnv(_TestMixin, absltest.TestCase):

  def test_episode(self):
    env = mock_sc2_env.SC2TestEnv(
        map_name='nonexistant map',
        agent_interface_format=features.AgentInterfaceFormat(
            feature_dimensions=features.Dimensions(screen=64, minimap=32)))
    env.episode_length = float('inf')
    self._test_episode(env)

  def test_episode_length(self):
    env = mock_sc2_env.SC2TestEnv(
        map_name='nonexistant map',
        agent_interface_format=features.AgentInterfaceFormat(
            feature_dimensions=features.Dimensions(screen=64, minimap=32)))
    self.assertEqual(env.episode_length, 10)
    self._test_episode_length(env, length=10)

  def test_screen_minimap_size(self):
    env = mock_sc2_env.SC2TestEnv(
        map_name='nonexistant map',
        agent_interface_format=features.AgentInterfaceFormat(
            feature_dimensions=features.Dimensions(
                screen=(84, 87),
                minimap=(64, 67))))
    timestep = env.reset()
    self.assertLen(timestep, 1)
    self.assert_spec(timestep[0].observation['feature_screen'],
                     [len(features.SCREEN_FEATURES), 87, 84], np.int32)
    self.assert_spec(timestep[0].observation['feature_minimap'],
                     [len(features.MINIMAP_FEATURES), 67, 64], np.int32)

  def test_feature_units_are_supported(self):
    env = mock_sc2_env.SC2TestEnv(
        map_name='nonexistant map',
        agent_interface_format=features.AgentInterfaceFormat(
            feature_dimensions=features.Dimensions(screen=64, minimap=32),
            use_feature_units=True))

    self.assertIn('feature_units', env.observation_spec()[0])

  def test_game_info(self):
    env = mock_sc2_env.SC2TestEnv(
        agent_interface_format=features.AgentInterfaceFormat(
            feature_dimensions=features.Dimensions(screen=64, minimap=32),
            use_feature_units=True),
        players=[sc2_env.Agent(sc2_env.Race.protoss, 'player'),
                 sc2_env.Bot(sc2_env.Race.random, sc2_env.Difficulty.easy,
                             sc2_env.BotBuild.random)])

    self.assertLen(env.game_info, 2)
    for i in range(2):
      self.assertEqual(
          env.game_info[i],
          sc2api_pb2.ResponseGameInfo(
              start_raw=raw_pb2.StartRaw(
                  map_size=common_pb2.Size2DI(
                      x=mock_sc2_env.DUMMY_MAP_SIZE,
                      y=mock_sc2_env.DUMMY_MAP_SIZE)),
              player_info=[
                  sc2api_pb2.PlayerInfo(
                      player_id=1,
                      type=sc2api_pb2.PlayerType.Participant,
                      race_requested=enums.Race.protoss,
                      player_name='player'),
                  sc2api_pb2.PlayerInfo(
                      player_id=2,
                      type=sc2api_pb2.PlayerType.Computer,
                      race_requested=enums.Race.random,
                      difficulty=enums.Difficulty.easy,
                      ai_build=enums.BotBuild.random,
                      player_name='easy')
              ]))


if __name__ == '__main__':
  absltest.main()
