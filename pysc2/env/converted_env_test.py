# Copyright 2021 DeepMind Technologies Ltd. All rights reserved.
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

import concurrent.futures
import random

from absl.testing import absltest
import dm_env
from dm_env import test_utils
import numpy as np
from pysc2.env import converted_env
from pysc2.env import mock_sc2_env
from pysc2.env import sc2_env
from pysc2.env.converter import converter
from pysc2.env.converter.proto import converter_pb2
from pysc2.lib import features

from s2clientprotocol import common_pb2
from s2clientprotocol import sc2api_pb2


def _action(delay: int):
  return {
      'function': np.int32(1),
      'world': np.int32(2949),
      'queued': np.int32(0),
      'unit_tags': np.array([1] + [255] * 63, dtype=np.int32),
      'target_unit_tag': np.int32(0),
      'repeat': np.int32(0),
      'delay': np.int32(delay)
  }


def _converter_factory(game_info: sc2api_pb2.ResponseGameInfo):
  return converter.Converter(
      converter_pb2.ConverterSettings(
          raw_settings=converter_pb2.ConverterSettings.RawSettings(
              num_unit_features=40,
              max_unit_selection_size=64,
              max_unit_count=512,
              resolution=common_pb2.Size2DI(x=128, y=128)),
          num_action_types=540,
          num_unit_types=217,
          num_upgrade_types=86,
          max_num_upgrades=40),
      environment_info=converter_pb2.EnvironmentInfo(game_info=game_info))


def _agent_interface_format():
  return features.AgentInterfaceFormat(
      use_raw_units=True, use_raw_actions=True, send_observation_proto=True)


class StreamedEnvTest(absltest.TestCase):

  def _check_episode(self, stream):
    timestep = stream.reset()
    self.assertIsNotNone(timestep)

    while True:
      timestep = stream.step(_action(random.randint(1, 5)))
      if timestep.step_type == dm_env.StepType.LAST:
        break
    self.assertIsNotNone(timestep)

  def test_single_player(self):
    env = converted_env.ConvertedEnvironment(
        converter_factories=[_converter_factory],
        env=mock_sc2_env.SC2TestEnv(
            players=[
                sc2_env.Agent(race=sc2_env.Race.protoss),
                sc2_env.Bot(
                    race=sc2_env.Race.zerg,
                    difficulty=sc2_env.Difficulty.very_easy)
            ],
            agent_interface_format=_agent_interface_format(),
            game_steps_per_episode=30,
        ),
    )

    with converted_env.make_streams(env)[0] as stream:
      self._check_episode(stream)

  def test_two_player(self):
    env = converted_env.ConvertedEnvironment(
        converter_factories=[_converter_factory, _converter_factory],
        env=mock_sc2_env.SC2TestEnv(
            players=[
                sc2_env.Agent(race=sc2_env.Race.protoss),
                sc2_env.Agent(race=sc2_env.Race.zerg),
            ],
            agent_interface_format=[
                _agent_interface_format() for _ in range(2)
            ],
            game_steps_per_episode=30,
        ),
    )

    s0, s1 = converted_env.make_streams(env)
    with s0, s1:
      fs = []
      with concurrent.futures.ThreadPoolExecutor() as executor:
        fs.append(executor.submit(self._check_episode, s0))
        fs.append(executor.submit(self._check_episode, s1))

        concurrent.futures.wait(fs)
        for f in fs:
          f.result()


class StreamedEnvConformanceTest(test_utils.EnvironmentTestMixin,
                                 absltest.TestCase):

  def make_object_under_test(self):
    env = converted_env.ConvertedEnvironment(
        env=mock_sc2_env.SC2TestEnv(
            players=[
                sc2_env.Agent(race=sc2_env.Race.protoss),
                sc2_env.Bot(
                    race=sc2_env.Race.zerg,
                    difficulty=sc2_env.Difficulty.very_easy)
            ],
            agent_interface_format=_agent_interface_format(),
            game_steps_per_episode=10,
        ),
        converter_factories=[_converter_factory])

    return converted_env.make_streams(env)[0]


if __name__ == '__main__':
  absltest.main()
