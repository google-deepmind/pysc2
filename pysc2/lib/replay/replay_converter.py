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
"""SC2 replay data -> converted observations."""

import collections
from typing import Any, Dict, Iterable, Sequence

import numpy as np
from pysc2.env.converter import converter as converter_lib
from pysc2.env.converter import derive_interface_options
from pysc2.env.converter.proto import converter_pb2
from pysc2.lib.replay import replay_observation_stream
from pysc2.lib.replay import sc2_replay
from pysc2.lib.replay import sc2_replay_utils
import tree

from s2clientprotocol import sc2api_pb2


def _unconverted_observation(observation, actions):
  return converter_pb2.Observation(
      player=observation[0],
      opponent=observation[1],
      force_action=sc2api_pb2.RequestAction(
          actions=actions
      ),
      # This will be populated when we look ahead.
      force_action_delay=0,
  )


def get_flat_action(obs: Dict[str, Any]) -> Dict[str, Any]:
  """Extracts action, with components starting action/, from an observation."""
  result = {
      k[len('action/'):]: v for k, v in obs.items() if k.startswith('action/')
  }
  if not result:
    raise ValueError(f'Failed to parse action from observation: {obs}')
  return result


def _convert_observation(converter, player_observation, force_action_delay,
                         force_action_fn):
  """Convert a raw observation proto and set action delay."""
  player_observation.force_action_delay = force_action_delay
  converted_observation = converter.convert_observation(player_observation)
  converter.convert_action(force_action_fn(converted_observation))

  def _squeeze_if_necessary(x):
    if x.shape == (1,):
      return np.squeeze(x)
    return x

  return tree.map_structure(_squeeze_if_necessary, converted_observation)


def converted_observations(observations_iterator, converter, accept_step_fn,
                           force_action_fn=get_flat_action):
  """Generator of transformed observations (incl. action and time delay)."""
  current_observation = next(observations_iterator)
  current_step = current_observation[0].observation.game_loop
  assert current_step == 0

  player_obs_queue = collections.deque()

  for next_observation in observations_iterator:
    step = next_observation[0].observation.game_loop

    if (step == 0 or (current_step > 0 and not accept_step_fn(step - 1))):
      # Save the observation even if it didn't have any actions. The step
      # stream also yields the observations immediately before the actions
      # are reported to capture the time the player actually issued the
      # action. If actions were reported at time steps t1 and t2
      # subsequently, we need to yield observation at step t2-1 instead of
      # t1 (this is also what is recorded in the action skips dataset).
      current_observation = next_observation
      continue

    player_obs_queue.append(_unconverted_observation(
        observation=current_observation,
        actions=next_observation[0].actions))

    while len(player_obs_queue) >= 2:
      # We have saved at least 2 observations in the queue, we can now
      # correctly calculate the true action delay.
      player_obs = player_obs_queue.popleft()
      player_obs_next = player_obs_queue[0]
      converted_observation = _convert_observation(
          converter,
          player_obs,
          force_action_delay=(player_obs_next.player.observation.game_loop -
                              player_obs.player.observation.game_loop),
          force_action_fn=force_action_fn)

      yield converted_observation

    current_step = step
    current_observation = next_observation

  # Always use last observation, it contains the player result.
  player_obs_queue.append(_unconverted_observation(
      observation=current_observation,
      actions=current_observation[0].actions))

  previous_delay = 1
  while player_obs_queue:
    player_obs = player_obs_queue.popleft()
    if len(player_obs_queue) >= 1:
      player_obs_next = player_obs_queue[0]
      force_action_delay = (player_obs_next.player.observation.game_loop -
                            player_obs.player.observation.game_loop)
    else:
      # Use previous force action delay, this is only done in the last step.
      # Preserve for reproducibility. In theory the actual delay value
      # shouldn't matter if we retrain checkpoints, since the actions from
      # the last step are never taken.
      force_action_delay = previous_delay
    converted_observation = _convert_observation(
        converter,
        player_obs,
        force_action_delay=force_action_delay,
        force_action_fn=force_action_fn)
    previous_delay = force_action_delay

    yield converted_observation


def converted_observation_stream(
    replay_data: bytes,
    player_id: int,
    converter_settings: converter_pb2.ConverterSettings,
    disable_fog: bool = False,
    max_steps: int = int(1e6)):
  """Generator of transformed observations (incl. action and time delay)."""

  with replay_observation_stream.ReplayObservationStream(
      step_mul=1,
      game_steps_per_episode=max_steps,
      add_opponent_observations=True,
      interface_options=derive_interface_options.from_settings(
          converter_settings),
      disable_fog=disable_fog,
  ) as replay_stream:
    replay_stream.start_replay_from_data(replay_data, player_id=player_id)

    obs_converter = converter_lib.Converter(
        converter_settings,
        environment_info=converter_pb2.EnvironmentInfo(
            game_info=replay_stream.game_info(),
            replay_info=replay_stream.replay_info()))

    replay_file = sc2_replay.SC2Replay(replay_data)
    action_skips = sc2_replay_utils.raw_action_skips(replay_file)
    player_action_skips = action_skips[player_id]
    step_sequence = get_step_sequence(player_action_skips)

    observations_iterator = replay_stream.observations(
        step_sequence=step_sequence)

    def _accept_step_fn(step):
      return step in player_action_skips

    yield from converted_observations(observations_iterator, obs_converter,
                                      _accept_step_fn)


# Current step sequence will yield observations right before
# the last camera move in a contiguous sequence of camera moves. Consider
# whether we want to change the observation at which the camera action is being
# reported.
def get_step_sequence(action_skips: Iterable[int]) -> Sequence[int]:
  """Generates a sequence of step muls for the replay stream.

  In SC2 we train on observations with actions but actions in replays are
  reported in frames after they were taken. We need a step sequence so we can
  advance the SC2 environment to the relevant observations before the action was
  taken and then step again with delta=1 to get the actual action on the next
  frame. A step sequence is key from a performance point of view since at the
  steps where no actions were taken we do not really need to render which is the
  expensive part of processing a replay. We can advance the simulation without
  rendering at a relatively low cost.

  An example stream looks like this:
  (obs_{0},)------(obs_{k-1},)---(obs_{k}, a_{k-1})---(obs_{k+1}, a_{k})...

  The first observation where an action was taken is `obs_{k-1}`, but the replay
  will not report the action until we request the next observation `obs_{k}`.
  In the above case we also have an action taken at timestep k, but it will be
  reported when we request `obs_{k+1}`. A step sequence would allow us to
  get a union of the observations that we want to report for training and
  those that have actions in them. An example step sequence for the above stream
  would be `[k-1, 1, 1]` where we first step k-1 times to get to the first
  observation where an action was taken, then step once to get the actual action
  as it is reported late.

  Args:
    action_skips: A sequence of game loops where actions were taken in the
      replay. This contains the game loops of the observations that happened
      before the action was reported by the replay to align it with the time
      step when the player took the action (replays report past actions). Note
      that the provided action skips sequence is assumed to have already been
      processed to include only relevant frames depending on the action types of
      interest (e.g., with or without camera moves).

  Returns:
    A sequence of step_muls to use in the replay stream.
  """
  prev_game_loop = 0
  steps = []
  for current_game_loop in action_skips:
    if prev_game_loop == 0:
      steps.append(current_game_loop)
    elif current_game_loop - prev_game_loop > 1:
      # We need to yield twice: to get the observation immediately before the
      # action (this is the game loop number we stored in the index), and to
      # get the replay observation that will return the actual actions. This
      # is needed because replays return actions that humans have taken on
      # previous frames.
      steps.append(1)
      steps.append(current_game_loop - prev_game_loop - 1)
    elif current_game_loop - prev_game_loop == 1:
      # Both previous and current observations had actions, step 1.
      steps.append(1)
    prev_game_loop = current_game_loop
  return steps
