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
"""A Starcraft II environment."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

from pysc2 import maps
from pysc2 import run_configs
from pysc2.env import environment
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import renderer_human
from pysc2.lib import stopwatch

from s2clientprotocol import sc2api_pb2 as sc_pb

sw = stopwatch.sw


_possible_results = {
    sc_pb.Victory: 1,
    sc_pb.Defeat: -1,
    sc_pb.Tie: 0,
    sc_pb.Undecided: 0,
}

races = {
    "R": sc_pb.Random,
    "P": sc_pb.Protoss,
    "T": sc_pb.Terran,
    "Z": sc_pb.Zerg,
}

difficulties = {
    "1": sc_pb.VeryEasy,
    "2": sc_pb.Easy,
    "3": sc_pb.Medium,
    "4": sc_pb.MediumHard,
    "5": sc_pb.Hard,
    "6": sc_pb.Harder,
    "7": sc_pb.VeryHard,
    "8": sc_pb.CheatVision,
    "9": sc_pb.CheatMoney,
    "A": sc_pb.CheatInsane,
}


class SC2Env(environment.Base):
  """A Starcraft II environment.

  The implementation details of the action and observation specs are in
  lib/features.py
  """

  def __init__(self,  # pylint: disable=invalid-name
               _only_use_kwargs=None,
               map_name=None,
               screen_size_px=(64, 64),
               minimap_size_px=(64, 64),
               camera_width_world_units=None,
               discount=1.,
               visualize=False,
               agent_race=None,
               bot_race=None,
               difficulty=None,
               step_mul=None,
               save_replay_steps=0,
               replay_dir=None,
               game_steps_per_episode=None,
               score_index=None,
               score_multiplier=None):
    """Create a SC2 Env.

    Args:
      _only_use_kwargs: Don't pass args, only kwargs.
      map_name: Name of a SC2 map. Run bin/map_list to get the full list of
          known maps. Alternatively, pass a Map instance. Take a look at the
          docs in maps/README.md for more information on available maps.
      screen_size_px: The size of your screen output in pixels.
      minimap_size_px: The size of your minimap output in pixels.
      camera_width_world_units: The width of your screen in world units. If your
          screen_size_px=(64, 48) and camera_width is 24, then each px
          represents 24 / 64 = 0.375 world units in each of x and y. It'll then
          represent a camera of size (24, 0.375 * 48) = (24, 18) world units.
      discount: Returned as part of the observation.
      visualize: Whether to pop up a window showing the camera and feature
          layers. This won't work without access to a window manager.
      agent_race: One of P,T,Z,R default random. This is the race you control.
      bot_race: One of P,T,Z,R default random. This is the race controlled by
          the built-in bot.
      difficulty: One of 1-9,A. How strong should the bot be?
      step_mul: How many game steps per agent step (action/observation). None
          means use the map default.
      save_replay_steps: How many game steps to wait before saving a replay.
          Default of 0 means don't save replays.
      replay_dir: Directory to save replays to. Required with save_replay_steps.
      game_steps_per_episode: Game steps per episode, independent of the
          step_mul. 0 means no limit. None means use the map default.
      score_index: -1 means use the win/loss reward, >=0 is the index into the
          score_cumulative with 0 being the curriculum score. None means use
          the map default.
      score_multiplier: How much to multiply the score by. Useful for negating.

    Raises:
      ValueError: if the agent_race, bot_race or difficulty are invalid.
    """
    if _only_use_kwargs:
      raise ValueError("All arguments must be passed as keyword arguments.")

    if save_replay_steps and not replay_dir:
      raise ValueError("Missing replay_dir")
    if agent_race and agent_race not in races:
      raise ValueError("Bad agent_race args")
    if bot_race and bot_race not in races:
      raise ValueError("Bad bot_race args")
    if difficulty and str(difficulty) not in difficulties:
      raise ValueError("Bad difficulty")
    self._map = maps.get(map_name)
    self._discount = discount
    self._step_mul = step_mul or self._map.step_mul
    self._save_replay_steps = save_replay_steps
    self._replay_dir = replay_dir
    self._total_steps = 0

    if score_index is None:
      self._score_index = self._map.score_index
    else:
      self._score_index = score_index
    if score_multiplier is None:
      self._score_multiplier = self._map.score_multiplier
    else:
      self._score_multiplier = score_multiplier
    self._last_score = None

    self._episode_length = (game_steps_per_episode or
                            self._map.game_steps_per_episode)
    self._episode_steps = 0

    self._run_config = run_configs.get()
    self._sc2_proc = self._run_config.start()
    self._controller = self._sc2_proc.controller

    screen_size_px = point.Point(*screen_size_px)
    minimap_size_px = point.Point(*minimap_size_px)
    interface = sc_pb.InterfaceOptions(
        raw=visualize, score=True,
        feature_layer=sc_pb.SpatialCameraSetup(
            width=camera_width_world_units or 24))
    screen_size_px.assign_to(interface.feature_layer.resolution)
    minimap_size_px.assign_to(interface.feature_layer.minimap_resolution)

    create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(
        map_path=self._map.path, map_data=self._map.data(self._run_config)))
    create.player_setup.add(type=sc_pb.Participant)
    create.player_setup.add(type=sc_pb.Computer,
                            race=races[bot_race or "R"],
                            difficulty=difficulties[difficulty or "1"])
    join = sc_pb.RequestJoinGame(race=races[agent_race or "R"],
                                 options=interface)

    self._controller.create_game(create)
    self._controller.join_game(join)

    game_info = self._controller.game_info()
    static_data = self._controller.data()

    self._features = features.Features(game_info)
    if visualize:
      self._renderer_human = renderer_human.RendererHuman()
      self._renderer_human.init(game_info, static_data)
    else:
      self._renderer_human = None

    self._episode_count = 0
    self._obs = None
    self._state = environment.StepType.LAST  # Want to jump to `reset`.
    logging.info("Environment is ready.")

  def observation_spec(self):
    """Look at Features for full specs."""
    return self._features.observation_spec()

  def action_spec(self):
    """Look at Features for full specs."""
    return self._features.action_spec()

  @sw.decorate
  def reset(self):
    """Start a new episode."""
    self._episode_steps = 0
    if self._episode_count:
      # No need to restart for the first episode.
      self._controller.restart()

    self._episode_count += 1
    logging.info("Starting episode: %s", self._episode_count)

    self._last_score = None
    self._state = environment.StepType.FIRST
    return self._step()

  @sw.decorate
  def step(self, actions):
    """Apply actions, step the world forward, and return observations."""
    if self._state == environment.StepType.LAST:
      return self.reset()

    assert len(actions) == 1  # No multiplayer yet.
    action = self._features.transform_action(self._obs.observation, actions[0])
    self._controller.act(action)
    self._state = environment.StepType.MID
    return self._step()

  def _step(self):
    self._controller.step(self._step_mul)
    self._obs = self._controller.observe()
    agent_obs = self._features.transform_obs(self._obs.observation)

    if self._obs.player_result:  # Episode over.
      self._state = environment.StepType.LAST
      outcome = _possible_results.get(self._obs.player_result[0].result, 0)
      discount = 0
    else:
      outcome = 0
      discount = self._discount

    if self._score_index >= 0:  # Game score, not win/loss reward.
      cur_score = agent_obs["score_cumulative"][self._score_index]
      # First reward is always 0.
      reward = cur_score - self._last_score if self._episode_steps > 0 else 0
      self._last_score = cur_score
    else:
      reward = outcome

    if self._renderer_human:
      self._renderer_human.render(self._obs)
      cmd = self._renderer_human.get_actions(self._run_config, self._controller)
      if cmd == renderer_human.ActionCmd.STEP:
        pass
      elif cmd == renderer_human.ActionCmd.RESTART:
        self._state = environment.StepType.LAST
      elif cmd == renderer_human.ActionCmd.QUIT:
        raise KeyboardInterrupt("Quit?")

    self._episode_steps += self._step_mul
    if self._episode_length > 0 and self._episode_steps >= self._episode_length:
      self._state = environment.StepType.LAST
      # No change to reward or discount since it's not actually terminal.

    self._total_steps += self._step_mul
    if (self._save_replay_steps > 0 and
        self._total_steps % self._save_replay_steps < self._step_mul):
      self.save_replay(self._replay_dir)

    if self._state == environment.StepType.LAST:
      logging.info("Episode finished. Outcome: %s, reward: %s, score: %s",
                   outcome, reward, agent_obs["score_cumulative"][0])

    return (environment.TimeStep(
        step_type=self._state, reward=reward * self._score_multiplier,
        discount=discount, observation=agent_obs),)  # A tuple for multiplayer.

  def save_replay(self, replay_dir):
    replay_path = self._run_config.save_replay(
        self._controller.save_replay(), replay_dir, self._map.name)
    print("Wrote replay to:", replay_path)

  @property
  def state(self):
    return self._state

  def close(self):
    logging.info("Environment Close")
    if hasattr(self, "_renderer_human") and self._renderer_human:
      self._renderer_human.close()
      self._renderer_human = None
    if hasattr(self, "_controller") and self._controller:
      self._controller.quit()
      self._controller = None
    if hasattr(self, "_sc2_proc") and self._sc2_proc:
      self._sc2_proc.close()
      self._sc2_proc = None
    logging.info(sw)
