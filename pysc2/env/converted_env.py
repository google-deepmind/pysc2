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

"""Environment which uses converters to transform an underlying environment."""

import functools
import threading
from typing import Any, Mapping, NamedTuple, Sequence

import dm_env
from pysc2.env.converter import converter as converter_lib
from pysc2.env.converter.proto import converter_pb2
from pysc2.lib import actions as sc2_actions
import typing_extensions

from s2clientprotocol import common_pb2
from s2clientprotocol import raw_pb2
from s2clientprotocol import sc2api_pb2

_BARRIER_TIMEOUT = 30.0


class ConverterFactory(typing_extensions.Protocol):

  def __call__(self, game_info: sc2api_pb2.ResponseGameInfo) -> Any:
    """Returns an environment converter given a game info."""


class ConvertedEnvironment(dm_env.Environment):
  """Env which uses converters to transform an underlying environment.

  Note that this is a multiplayer environment. The returned timesteps contain
  lists for their reward and observation fields, with entries in those lists
  corresponding to the players in the game. A list of actions must be passed
  to step - an action per player. Note, however, that this is expected to
  be None where the player isn't expected to act on the current game loop
  because their previous action delay hasn't expired yet.

  If you would prefer to access the environment in a singleplayer fashion,
  see `make_streams`, below.
  """

  def __init__(self,
               env,
               converter_factories: Sequence[ConverterFactory],
               allow_out_of_turn_actions=False):
    """Initializes the environment.

    Args:
      env: The underlying environment which is being converted.
      converter_factories: One for each agent player in the game.
      allow_out_of_turn_actions: Whether to allow agents to act when it's not
        their turns. Used for testing.
    """
    self._env = env
    self._num_players = len(converter_factories)
    self._converter_factories = converter_factories
    self._initialized = False
    converters = [f(_dummy_game_info()) for f in converter_factories]
    self._action_specs = [c.action_spec() for c in converters]
    self._obs_specs = [c.observation_spec() for c in converters]
    self._target_game_loops = [0] * self._num_players
    self._converters = [None] * self._num_players
    self._game_loop = None
    self._allow_out_of_turn_actions = allow_out_of_turn_actions

  def reset(self) -> dm_env.TimeStep:
    """Resets the environment."""
    self._initialized = True
    self._game_loop = 0
    self._target_game_loops = [0] * self._num_players
    self._converters = [
        f(g) for f, g in zip(self._converter_factories, self._env.game_info)
    ]
    return self._convert_timesteps(self._env.reset())

  def step(self, actions) -> dm_env.TimeStep:
    """Steps the environment."""
    if not self._initialized:
      return self.reset()

    converted_actions = []
    for i, (action, converter) in enumerate(zip(actions, self._converters)):
      if action is None:
        if self._target_game_loops[i] <= self._game_loop:
          raise RuntimeError('No action specified when its your turn.')
        converted_actions.append(sc2_actions.FUNCTIONS.no_op())
      else:
        if (self._target_game_loops[i] > self._game_loop and
            not self._allow_out_of_turn_actions):
          raise RuntimeError('Can\'t act when not your turn.')
        action_with_delay = converter.convert_action(action)
        self._target_game_loops[i] = self._game_loop + action_with_delay.delay
        num_actions = len(action_with_delay.request_action.actions)
        if not num_actions:
          converted_actions.append(sc2api_pb2.Action())
        else:
          converted_actions.append(
              [action_with_delay.request_action.actions[0]] * num_actions)

    min_delay = min(g for g in self._target_game_loops) - self._game_loop
    timestep = self._convert_timesteps(
        self._env.step(converted_actions, min_delay))

    self._game_loop = max(int(obs['game_loop']) for obs in timestep.observation)

    if timestep.last():
      self._initialized = False
      self._target_game_loops = [0] * len(self._target_game_loops)
    return timestep

  def observation_spec(self):
    return self._obs_specs

  def action_spec(self):
    return self._action_specs

  def close(self):
    self._env.close()
    self._env = None

  def send_chat_messages(self, messages: Sequence[str], broadcast: bool = True):
    fn = getattr(self._env, 'send_chat_messages', None)
    if fn:
      # Make sure that chat messages are less than 255 characters
      messages = [x[:254] for x in messages]
      fn(messages, broadcast)

  def save_replay(self, replay_dir, prefix=None):
    return self._env.save_replay(replay_dir, prefix)

  def action_delays(self):
    return self._env.action_delays()

  def num_players(self):
    return self._num_players

  def is_player_turn(self):
    return [t <= self._game_loop for t in self._target_game_loops]

  def _convert_timesteps(self, timesteps):

    def _convert_obs(obs, converter):
      if not isinstance(obs, sc2api_pb2.ResponseObservation):
        obs = obs['_response_observation']()
      env_obs = converter_pb2.Observation(player=obs)
      return converter.convert_observation(observation=env_obs)

    # Merge the timesteps from a sequence to a single timestep
    return dm_env.TimeStep(
        step_type=dm_env.StepType(timesteps[0].step_type),
        reward=[timestep.reward for timestep in timesteps],
        discount=timesteps[0].discount,
        observation=[
            _convert_obs(ts.observation, t)
            for ts, t in zip(timesteps, self._converters)
        ])


class _Stream(dm_env.Environment):
  """A stream for a single player interacting with a multiplayer environment."""

  def __init__(self, player: int, environment: '_StreamedEnvironment'):
    self._player = player
    self._environment = environment

  def reset(self) -> dm_env.TimeStep:
    return self._environment.reset(self._player)

  def step(self, action) -> dm_env.TimeStep:
    return self._environment.step(action, self._player)

  def action_spec(self):
    return self._environment.action_spec(self._player)

  def observation_spec(self):
    return self._environment.observation_spec(self._player)

  def close(self):
    self._environment.close(self._player)

  def save_replay(self, replay_dir, prefix=None):
    return self._environment.save_replay(replay_dir, prefix)


class _StreamedEnvironment:
  """Env presenting ConvertedEnvironment as multiple single player streams."""

  def __init__(self, underlying_env: ConvertedEnvironment):
    if not 1 <= underlying_env.num_players() <= 2:
      raise ValueError(
          f'Unsupported number of players: {underlying_env.num_players()}')

    self._underlying_env = underlying_env
    self._num_players = underlying_env.num_players()
    self._barrier = threading.Barrier(parties=2)
    self._lock = threading.Lock()
    self._timestep = None
    self._actions = [None] * self._num_players
    self._closed = [False] * self._num_players
    self._closed_lock = threading.Lock()

  def reset(self, player: int) -> dm_env.TimeStep:
    """Resets the underlying environment, syncing players."""
    self._wait_for_other_player()
    if player == 0:
      self._timestep = self._underlying_env.reset()
    self._wait_for_other_player()
    return self._player_timestep(player)

  def step(self, action, player: int) -> dm_env.TimeStep:
    """Steps the underlying environment, syncing players."""
    self._actions[player] = action

    while True:
      self._wait_for_other_player()
      if player == 0:
        self._timestep = self._underlying_env.step(self._actions)
        self._actions = [None] * self._num_players
      self._wait_for_other_player()
      if self._underlying_env.is_player_turn()[player]:
        break

    return self._player_timestep(player)

  def action_spec(self, player: int):
    return self._underlying_env.action_spec()[player]

  def observation_spec(self, player: int):
    return self._underlying_env.observation_spec()[player]

  def close(self, player: int):
    with self._closed_lock:
      self._closed[player] = True
      if all(self._closed):
        self._underlying_env.close()

  def save_replay(self, replay_dir, prefix=None):
    with self._lock:
      return self._underlying_env.save_replay(replay_dir, prefix)

  def _wait_for_other_player(self):
    """Waits for the other player (if there is one) to reach this point."""
    if self._num_players == 1:
      return
    try:
      self._barrier.wait(_BARRIER_TIMEOUT)
    except threading.BrokenBarrierError:
      raise TimeoutError('Timed out waiting for other player')

  def _player_timestep(self, player: int):
    first_step = self._timestep.step_type is dm_env.StepType.FIRST
    return dm_env.TimeStep(
        step_type=self._timestep.step_type,
        reward=float(self._timestep.reward[player]) if not first_step else None,
        discount=self._timestep.discount if not first_step else None,
        observation=self._timestep.observation[player])


def make_streams(converted_environment: ConvertedEnvironment):
  """Makes single player environment streams out of a ConvertedEnvironment.

  Each stream is expected to be run in a separate thread as steps involving
  multiple player must be executed concurrently. Where multiple players are
  expected to act but don't within _BARRIER_TIMEOUT, an exception will be
  raised.

  Args:
    converted_environment: A converted environment configured for 1 or 2
      players.

  Returns:
    A dm_env.Environment for each player.
  """
  environment = _StreamedEnvironment(converted_environment)
  return [
      _Stream(p, environment)
      for p in range(converted_environment.num_players())
  ]


def _dummy_game_info() -> sc2api_pb2.ResponseGameInfo:
  """Returns a dummy game info object.

  The converter *specs* don't depend on the game info (this is not true for
  the converted data). So, rather than instantiating the game to have the
  converter generate specs, we can supply this dummy game info instead.
  """
  return sc2api_pb2.ResponseGameInfo(
      start_raw=raw_pb2.StartRaw(map_size=common_pb2.Size2DI(x=256, y=256)),
      player_info=[
          sc2api_pb2.PlayerInfo(race_requested=common_pb2.Protoss),
          sc2api_pb2.PlayerInfo(race_requested=common_pb2.Protoss)
      ])


class EnvironmentSpec(NamedTuple):
  obs_spec: Mapping[str, Any]
  action_spec: Mapping[str, Any]


def get_environment_spec(
    converter_settings: converter_pb2.ConverterSettings,) -> EnvironmentSpec:
  """Gets observation and action spec for the specified converter settings.

  Args:
    converter_settings: The converter settings to get specs for.

  Returns:
    (observation spec, action spec).
  """
  env_info = converter_pb2.EnvironmentInfo(game_info=_dummy_game_info())
  cvr = converter_lib.Converter(converter_settings, env_info)
  return EnvironmentSpec(cvr.observation_spec(), cvr.action_spec())


def make_converter_factories(
    all_converter_settings: Sequence[converter_pb2.ConverterSettings]):
  """Makes converter factories from converter settings."""

  def converter_factory(settings: converter_pb2.ConverterSettings,
                        game_info: sc2api_pb2.ResponseGameInfo):
    return converter_lib.Converter(
        settings, converter_pb2.EnvironmentInfo(game_info=game_info))

  return [
      functools.partial(converter_factory, s) for s in all_converter_settings
  ]
