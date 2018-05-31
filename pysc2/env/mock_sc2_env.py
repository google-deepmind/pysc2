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
"""Mocking the Starcraft II environment."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math

import numpy as np
from pysc2.env import environment
from pysc2.env import sc2_env
from pysc2.lib import features
from pysc2.lib import point

from s2clientprotocol import sc2api_pb2 as sc_pb

DUMMY_MAP_SIZE = point.Point(256, 256)


class _TestEnvironment(environment.Base):
  """A simple generic test environment.

  This class is a lightweight implementation of `environment.Base` that returns
  the same timesteps on every observation call. By default, each returned
  timestep (one per agent) is reward 0., discount 1., and the observations are
  zero `np.ndarrays` of dtype `np.int32` and the shape specified by the
  environment's spec.

  However, the behavior of the `TestEnvironment` can be configured using the
  object's attributes.

  Attributes:
    next_timestep: The `environment.TimeStep`s to return on the next call to
      `step`. When necessary, some fields will be overridden to ensure the
      `step_type` contract.
    episode_length: if the episode length (number of transitions) exceeds
      `episode_length` on a call to `step`, the `step-type` will be set to
      `environment.StepType.LAST`, forcing an end of episode. This allows a
      stub of a production environment to have end_episodes. Will be ignored if
      set to `float('inf')` (the default).
  """

  def __init__(self, num_agents, observation_spec, action_spec):
    """Initializes the TestEnvironment.

    The `next_observation` is initialized to be reward = 0., discount = 1.,
    and an appropriately sized observation of all zeros. `episode_length` is set
    to `float('inf')`.

    Args:
      num_agents: The number of agents.
      observation_spec: The observation specs for each player.
      action_spec: The action specs for each player.
    """
    self._num_agents = num_agents
    self._observation_spec = observation_spec
    self._action_spec = action_spec
    self._episode_steps = 0

    self.next_timestep = [
        environment.TimeStep(
            step_type=environment.StepType.MID,
            reward=0.,
            discount=1.,
            observation=self._default_observation(obs_spec, agent_index))
        for agent_index, obs_spec in enumerate(observation_spec)]

    self.episode_length = float('inf')

  def reset(self):
    """Restarts episode and returns `next_observation` with `StepType.FIRST`."""
    self._episode_steps = 0
    return self.step([None] * self._num_agents)

  def step(self, actions):
    """Returns `next_observation` modifying its `step_type` if necessary."""
    if len(actions) != self._num_agents:
      raise ValueError(
          'Expected %d actions, received %d.' % (
              self._num_agents, len(actions)))

    if self._episode_steps == 0:
      step_type = environment.StepType.FIRST
    elif self._episode_steps >= self.episode_length:
      step_type = environment.StepType.LAST
    else:
      step_type = environment.StepType.MID

    timesteps = []
    for timestep in self.next_timestep:
      if step_type is environment.StepType.FIRST:
        timesteps.append(timestep._replace(
            step_type=step_type,
            reward=0.,
            discount=1.))
      elif step_type is environment.StepType.LAST:
        timesteps.append(timestep._replace(
            step_type=step_type))
      else:
        timesteps.append(timestep)

    if timesteps[0].step_type is environment.StepType.LAST:
      self._episode_steps = 0
    else:
      self._episode_steps += 1

    return timesteps

  def action_spec(self):
    """See base class."""
    return self._action_spec

  def observation_spec(self):
    """See base class."""
    return self._observation_spec

  def _default_observation(self, obs_spec, agent_index):
    """Returns an observation based on the observation spec."""
    observation = {}
    for key, spec in obs_spec.items():
      observation[key] = np.zeros(shape=spec, dtype=np.int32)
    return observation


class SC2TestEnv(_TestEnvironment):
  """A TestEnvironment to swap in for `starcraft2.env.sc2_env.SC2Env`.

  Repeatedly returns a mock observation for 10 calls to `step` whereupon it
  sets discount to 0. and changes state to READY_TO_END_EPISODE.

  Example:

  ```
  @mock.patch(
      'starcraft2.env.sc2_env.SC2Env',
      mock_sc2_env.SC2TestEnv)
  def test_method(self):
    env = sc2_env.SC2Env('nonexisting map')  # Really a SC2TestEnv.
    ...
  ```

  See base class for more details.
  """

  def __init__(self,
               _only_use_kwargs=None,
               map_name=None,
               players=None,
               agent_interface_format=None,
               discount=1.,
               visualize=False,
               step_mul=None,
               save_replay_episodes=0,
               replay_dir=None,
               game_steps_per_episode=None,
               score_index=None,
               score_multiplier=None,
               random_seed=None,
               disable_fog=False):
    """Initializes an SC2TestEnv.

    Args:
      _only_use_kwargs: Don't pass args, only kwargs.
      map_name: Map name. Ignored.
      players: A list of Agent and Bot instances that specify who will play.
      agent_interface_format: A sequence containing one AgentInterfaceFormat
        per agent, matching the order of agents specified in the players list.
        Or a single AgentInterfaceFormat to be used for all agents.
      discount: Unused.
      visualize: Unused.
      step_mul: Unused.
      save_replay_episodes: Unused.
      replay_dir: Unused.
      game_steps_per_episode: Unused.
      score_index: Unused.
      score_multiplier: Unused.
      random_seed: Unused.
      disable_fog: Unused.

    Raises:
      ValueError: if args are passed.
    """
    del map_name  # Unused.
    del discount  # Unused.
    del visualize  # Unused.
    del step_mul  # Unused.
    del save_replay_episodes  # Unused.
    del replay_dir  # Unused.
    del game_steps_per_episode  # Unused.
    del score_index  # Unused.
    del score_multiplier  # Unused.
    del random_seed  # Unused.
    del disable_fog  # Unused.

    if _only_use_kwargs:
      raise ValueError('All arguments must be passed as keyword arguments.')

    if not players:
      num_agents = 1
    else:
      num_agents = sum(1 for p in players if isinstance(p, sc2_env.Agent))

    if agent_interface_format is None:
      raise ValueError('Please specify agent_interface_format.')

    if isinstance(agent_interface_format, sc2_env.AgentInterfaceFormat):
      agent_interface_format = [agent_interface_format] * num_agents

    if len(agent_interface_format) != num_agents:
      raise ValueError(
          'The number of entries in agent_interface_format should '
          'correspond 1-1 with the number of agents.')

    self._features = [
        features.Features(interface_format, map_size=DUMMY_MAP_SIZE)
        for interface_format in agent_interface_format]

    super(SC2TestEnv, self).__init__(
        num_agents=num_agents,
        action_spec=tuple(f.action_spec() for f in self._features),
        observation_spec=tuple(f.observation_spec() for f in self._features))
    self.episode_length = 10

  def save_replay(self, *args, **kwargs):
    """Does nothing."""

  def _default_observation(self, obs_spec, agent_index):
    """Returns a mock observation from an SC2Env."""

    response_observation = sc_pb.ResponseObservation()
    obs = response_observation.observation

    obs.game_loop = 1
    obs.player_common.player_id = 1
    obs.player_common.minerals = 20
    obs.player_common.vespene = 50
    obs.player_common.food_cap = 36
    obs.player_common.food_used = 21
    obs.player_common.food_army = 6
    obs.player_common.food_workers = 15
    obs.player_common.idle_worker_count = 2
    obs.player_common.army_count = 6
    obs.player_common.warp_gate_count = 0
    obs.player_common.larva_count = 0

    obs.abilities.add(ability_id=1, requires_point=True)  # Smart

    obs.score.score = 300
    score_details = obs.score.score_details
    score_details.idle_production_time = 0
    score_details.idle_worker_time = 0
    score_details.total_value_units = 190
    score_details.total_value_structures = 230
    score_details.killed_value_units = 0
    score_details.killed_value_structures = 0
    score_details.collected_minerals = 2130
    score_details.collected_vespene = 560
    score_details.collection_rate_minerals = 50
    score_details.collection_rate_vespene = 20
    score_details.spent_minerals = 2000
    score_details.spent_vespene = 500

    def fill(image_data, size, bits):
      image_data.bits_per_pixel = bits
      image_data.size.y = size[0]
      image_data.size.x = size[1]
      image_data.data = b'\0' * int(math.ceil(size[0] * size[1] * bits / 8))

    if 'feature_screen' in obs_spec:
      for feature in features.SCREEN_FEATURES:
        fill(getattr(obs.feature_layer_data.renders, feature.name),
             obs_spec['feature_screen'][1:], 8)
    if 'feature_minimap' in obs_spec:
      for feature in features.MINIMAP_FEATURES:
        fill(getattr(obs.feature_layer_data.minimap_renders, feature.name),
             obs_spec['feature_minimap'][1:], 8)
    if 'rgb_screen' in obs_spec:
      fill(obs.render_data.map, obs_spec['rgb_screen'][:2], 24)
    if 'rgb_screen' in obs_spec:
      fill(obs.render_data.minimap, obs_spec['rgb_minimap'][:2], 24)

    features_ = self._features[agent_index]
    observation = features_.transform_obs(response_observation)

    # Add bounding box for the minimap camera in top left of feature screen.
    if 'feature_minimap' in observation:
      minimap_camera = observation.feature_minimap.camera
      minimap_camera.fill(0)
      height, width = [dim // 2 for dim in minimap_camera.shape]
      minimap_camera[:height, :width].fill(1)

    return observation
