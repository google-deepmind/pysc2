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

from absl import logging

from pysc2 import maps
from pysc2 import run_configs
from pysc2.env import environment
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import renderer_human
from pysc2.lib import run_parallel
from pysc2.lib import stopwatch

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb

sw = stopwatch.sw


_possible_results = {
    sc_pb.Victory: 1,
    sc_pb.Defeat: -1,
    sc_pb.Tie: 0,
    sc_pb.Undecided: 0,
}

races = {
    "R": sc_common.Random,
    "P": sc_common.Protoss,
    "T": sc_common.Terran,
    "Z": sc_common.Zerg,
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
               agent_race=None,
               bot_race=None,
               difficulty=None,
               **kwargs):
    # pylint: disable=g-doc-args
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
      save_replay_episodes: Save a replay after this many episodes. Default of 0
          means don't save replays.
      replay_dir: Directory to save replays. Required with save_replay_episodes.
      game_steps_per_episode: Game steps per episode, independent of the
          step_mul. 0 means no limit. None means use the map default.
      score_index: -1 means use the win/loss reward, >=0 is the index into the
          score_cumulative with 0 being the curriculum score. None means use
          the map default.
      score_multiplier: How much to multiply the score by. Useful for negating.

    Raises:
      ValueError: if the agent_race, bot_race or difficulty are invalid.
    """
    # pylint: enable=g-doc-args
    if _only_use_kwargs:
      raise ValueError("All arguments must be passed as keyword arguments.")

    agent_race = agent_race or "R"
    if agent_race not in races:
      raise ValueError("Bad agent_race args")

    bot_race = bot_race or "R"
    if bot_race not in races:
      raise ValueError("Bad bot_race args")

    difficulty = difficulty and str(difficulty) or "1"
    if difficulty not in difficulties:
      raise ValueError("Bad difficulty")

    self._num_players = 1

    self._setup((agent_race, bot_race, difficulty), **kwargs)

  def _setup(self,
             player_setup,
             map_name,
             screen_size_px=(64, 64),
             minimap_size_px=(64, 64),
             camera_width_world_units=None,
             discount=1.,
             visualize=False,
             step_mul=None,
             save_replay_episodes=0,
             replay_dir=None,
             game_steps_per_episode=None,
             score_index=None,
             score_multiplier=None):

    if save_replay_episodes and not replay_dir:
      raise ValueError("Missing replay_dir")

    self._map = maps.get(map_name)
    self._discount = discount
    self._step_mul = step_mul or self._map.step_mul
    self._save_replay_episodes = save_replay_episodes
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
    self._parallel = run_parallel.RunParallel()  # Needed for multiplayer.

    screen_size_px = point.Point(*screen_size_px)
    minimap_size_px = point.Point(*minimap_size_px)
    interface = sc_pb.InterfaceOptions(
        raw=visualize, score=True,
        feature_layer=sc_pb.SpatialCameraSetup(
            width=camera_width_world_units or 24))
    screen_size_px.assign_to(interface.feature_layer.resolution)
    minimap_size_px.assign_to(interface.feature_layer.minimap_resolution)

    self._launch(interface, player_setup)

    game_info = self._controllers[0].game_info()
    static_data = self._controllers[0].data()

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

  def _launch(self, interface, player_setup):
    agent_race, bot_race, difficulty = player_setup

    self._sc2_procs = [self._run_config.start()]
    self._controllers = [p.controller for p in self._sc2_procs]

    # Create the game.
    create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(
        map_path=self._map.path,
        map_data=self._run_config.map_data(self._map.path)))
    create.player_setup.add(type=sc_pb.Participant)
    create.player_setup.add(type=sc_pb.Computer, race=races[bot_race],
                            difficulty=difficulties[difficulty])
    self._controllers[0].create_game(create)

    join = sc_pb.RequestJoinGame(race=races[agent_race], options=interface)
    self._controllers[0].join_game(join)

  def observation_spec(self):
    """Look at Features for full specs."""
    return self._features.observation_spec()

  def action_spec(self):
    """Look at Features for full specs."""
    return self._features.action_spec()

  def _restart(self):
    self._controllers[0].restart()

  @sw.decorate
  def reset(self):
    """Start a new episode."""
    self._episode_steps = 0
    if self._episode_count:
      # No need to restart for the first episode.
      self._restart()

    self._episode_count += 1
    logging.info("Starting episode: %s", self._episode_count)

    self._last_score = [0] * self._num_players
    self._state = environment.StepType.FIRST
    return self._step()

  @sw.decorate
  def step(self, actions):
    """Apply actions, step the world forward, and return observations."""
    if self._state == environment.StepType.LAST:
      return self.reset()

    self._parallel.run(
        (c.act, self._features.transform_action(o.observation, a))
        for c, o, a in zip(self._controllers, self._obs, actions))

    self._state = environment.StepType.MID
    return self._step()

  def _step(self):
    self._parallel.run((c.step, self._step_mul) for c in self._controllers)
    self._obs = self._parallel.run(c.observe for c in self._controllers)
    agent_obs = [self._features.transform_obs(o.observation) for o in self._obs]

    # TODO(tewalds): How should we handle more than 2 agents and the case where
    # the episode can end early for some agents?
    outcome = [0] * self._num_players
    discount = self._discount
    if any(o.player_result for o in self._obs):  # Episode over.
      self._state = environment.StepType.LAST
      discount = 0
      for i, o in enumerate(self._obs):
        player_id = o.observation.player_common.player_id
        for result in o.player_result:
          if result.player_id == player_id:
            outcome[i] = _possible_results.get(result.result, 0)

    if self._score_index >= 0:  # Game score, not win/loss reward.
      cur_score = [o["score_cumulative"][self._score_index] for o in agent_obs]
      if self._episode_steps == 0:  # First reward is always 0.
        reward = [0] * self._num_players
      else:
        reward = [cur - last for cur, last in zip(cur_score, self._last_score)]
      self._last_score = cur_score
    else:
      reward = outcome

    if self._renderer_human:
      self._renderer_human.render(self._obs[0])
      cmd = self._renderer_human.get_actions(
          self._run_config, self._controllers[0])
      if cmd == renderer_human.ActionCmd.STEP:
        pass
      elif cmd == renderer_human.ActionCmd.RESTART:
        self._state = environment.StepType.LAST
      elif cmd == renderer_human.ActionCmd.QUIT:
        raise KeyboardInterrupt("Quit?")

    self._total_steps += self._step_mul
    self._episode_steps += self._step_mul
    if self._episode_length > 0 and self._episode_steps >= self._episode_length:
      self._state = environment.StepType.LAST
      # No change to reward or discount since it's not actually terminal.

    if self._state == environment.StepType.LAST:
      if (self._save_replay_episodes > 0 and
          self._episode_count % self._save_replay_episodes == 0):
        self.save_replay(self._replay_dir)
      logging.info(
          "Episode finished. Outcome: %s, reward: %s, score: %s",
          outcome, reward, [o["score_cumulative"][0] for o in agent_obs])

    return tuple(environment.TimeStep(step_type=self._state,
                                      reward=r * self._score_multiplier,
                                      discount=discount, observation=o)
                 for r, o in zip(reward, agent_obs))

  def save_replay(self, replay_dir):
    replay_path = self._run_config.save_replay(
        self._controllers[0].save_replay(), replay_dir, self._map.name)
    logging.info("Wrote replay to: %s", replay_path)

  @property
  def state(self):
    return self._state

  def close(self):
    logging.info("Environment Close")
    if hasattr(self, "_renderer_human") and self._renderer_human:
      self._renderer_human.close()
      self._renderer_human = None

    # Don't use parallel since it might be broken by an exception.
    if hasattr(self, "_controller") and self._controller:
      for c in self._controllers:
        c.quit()
      self._controllers = None
    if hasattr(self, "_sc2_proc") and self._sc2_proc:
      for p in self._sc2_procs:
        p.close()
      self._sc2_procs = None

    logging.info(sw)
