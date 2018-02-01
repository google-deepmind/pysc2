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

import collections
from absl import logging

import enum
import portpicker

from pysc2 import maps
from pysc2 import run_configs
from pysc2.env import environment
from pysc2.lib import actions as actions_lib
from pysc2.lib import features
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


class Race(enum.IntEnum):
  random = sc_common.Random
  protoss = sc_common.Protoss
  terran = sc_common.Terran
  zerg = sc_common.Zerg


class Difficulty(enum.IntEnum):
  """Bot difficulties."""
  very_easy = sc_pb.VeryEasy
  easy = sc_pb.Easy
  medium = sc_pb.Medium
  medium_hard = sc_pb.MediumHard
  hard = sc_pb.Hard
  harder = sc_pb.Harder
  very_hard = sc_pb.VeryHard
  cheat_vision = sc_pb.CheatVision
  cheat_money = sc_pb.CheatMoney
  cheat_insane = sc_pb.CheatInsane

# Re-export this enum to make it easy to construct the environment.
ActionSpace = actions_lib.ActionSpace  # pylint: disable=invalid-name


Agent = collections.namedtuple("Agent", ["race"])
Bot = collections.namedtuple("Bot", ["race", "difficulty"])


class SC2Env(environment.Base):
  """A Starcraft II environment.

  The implementation details of the action and observation specs are in
  lib/features.py
  """

  def __init__(self,  # pylint: disable=invalid-name
               _only_use_kwargs=None,
               map_name=None,
               players=None,
               agent_race=None,  # deprecated
               bot_race=None,  # deprecated
               difficulty=None,  # deprecated
               screen_size_px=None,  # deprecated
               minimap_size_px=None,  # deprecated
               feature_screen_size=None,
               feature_screen_width=None,
               feature_screen_height=None,
               feature_minimap_size=None,
               feature_minimap_width=None,
               feature_minimap_height=None,
               rgb_screen_size=None,
               rgb_screen_width=None,
               rgb_screen_height=None,
               rgb_minimap_size=None,
               rgb_minimap_width=None,
               rgb_minimap_height=None,
               action_space=None,
               camera_width_world_units=None,
               discount=1.,
               visualize=False,
               step_mul=None,
               save_replay_episodes=0,
               replay_dir=None,
               game_steps_per_episode=None,
               score_index=None,
               score_multiplier=None,
               use_feature_units=False,
               random_seed=None):
    """Create a SC2 Env.

    You must pass a resolution that you want to play at. You can send either
    feature layer resolution or rgb resolution or both. If you send both you
    must also choose which to use as your action space. Regardless of which you
    choose you must send both the screen and minimap resolutions.

    For each of the 4 resolutions, either specify size or both width and
    height. If you specify size then both width and height will take that value.

    Args:
      _only_use_kwargs: Don't pass args, only kwargs.
      map_name: Name of a SC2 map. Run bin/map_list to get the full list of
          known maps. Alternatively, pass a Map instance. Take a look at the
          docs in maps/README.md for more information on available maps.
      players: A list of Agent and Bot instances that specify who will play.
      agent_race: Deprecated. Use players instead.
      bot_race: Deprecated. Use players instead.
      difficulty: Deprecated. Use players instead.
      screen_size_px: Deprecated. Use feature_screen_... instead.
      minimap_size_px: Deprecated. Use feature_minimap_... instead.
      feature_screen_size: Sets feature_screen_width and feature_screen_width.
      feature_screen_width: The width of the feature layer screen observation.
      feature_screen_height: The height of the feature layer screen observation.
      feature_minimap_size: Sets feature_minimap_width and
          feature_minimap_height.
      feature_minimap_width: The width of the feature layer minimap observation.
      feature_minimap_height: The height of the feature layer minimap
          observation.
      rgb_screen_size: Sets rgb_screen_width and rgb_screen_height.
      rgb_screen_width: The width of the rgb screen observation.
      rgb_screen_height: The height of the rgb screen observation.
      rgb_minimap_size: Sets rgb_minimap_width and rgb_minimap_height.
      rgb_minimap_width: The width of the rgb minimap observation.
      rgb_minimap_height: The height of the rgb minimap observation.
      action_space: If you pass both feature and rgb sizes, then you must also
          specify which you want to use for your actions as an ActionSpace enum.
      camera_width_world_units: The width of your screen in world units. If your
          feature_screen=(64, 48) and camera_width is 24, then each px
          represents 24 / 64 = 0.375 world units in each of x and y. It'll then
          represent a camera of size (24, 0.375 * 48) = (24, 18) world units.
      discount: Returned as part of the observation.
      visualize: Whether to pop up a window showing the camera and feature
          layers. This won't work without access to a window manager.
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
      use_feature_units: Whether to include feature unit data in observations.
      random_seed: Random number seed to use when initializing the game. This
          lets you run repeatable games/tests.

    Raises:
      ValueError: if the agent_race, bot_race or difficulty are invalid.
      ValueError: if too many players are requested for a map.
      ValueError: if the resolutions aren't specified correctly.
      DeprecationWarning: if screen_size_px or minimap_size_px are sent.
      DeprecationWarning: if agent_race, bot_race or difficulty are sent.
    """
    if _only_use_kwargs:
      raise ValueError("All arguments must be passed as keyword arguments.")

    if screen_size_px or minimap_size_px:
      raise DeprecationWarning(
          "screen_size_px and minimap_size_px are deprecated. Use the feature "
          "or rgb variants instead. Make sure to check your observations too "
          "since they also switched from screen/minimap to feature and rgb "
          "variants.")

    if agent_race or bot_race or difficulty:
      raise DeprecationWarning(
          "Explicit agent and bot races are deprecated. Pass an array of "
          "sc2_env.Bot and sc2_env.Agent instances instead.")

    if not players:
      players = [Agent(Race.random), Bot(Race.random, Difficulty.very_easy)]

    for p in players:
      if not isinstance(p, (Agent, Bot)):
        raise ValueError(
            "Expected players to be of type Agent or Bot. Got: %s." % p)

    self._num_players = sum(1 for p in players if isinstance(p, Agent))
    self._players = players

    if not 1 <= len(players) <= 2 or not 1 <= self._num_players <= 2:
      raise ValueError("Only 1 or 2 players is supported at the moment.")

    feature_screen_px = features.point_from_size_width_height(
        feature_screen_size, feature_screen_width, feature_screen_height)
    feature_minimap_px = features.point_from_size_width_height(
        feature_minimap_size, feature_minimap_width, feature_minimap_height)
    rgb_screen_px = features.point_from_size_width_height(
        rgb_screen_size, rgb_screen_width, rgb_screen_height)
    rgb_minimap_px = features.point_from_size_width_height(
        rgb_minimap_size, rgb_minimap_width, rgb_minimap_height)

    if bool(feature_screen_px) != bool(feature_minimap_px):
      raise ValueError("Must set all the feature layer sizes.")
    if bool(rgb_screen_px) != bool(rgb_minimap_px):
      raise ValueError("Must set all the rgb sizes.")
    if not feature_screen_px and not rgb_screen_px:
      raise ValueError("Must set either the feature layer or rgb sizes.")

    if rgb_screen_px and (rgb_screen_px.x < rgb_minimap_px.x or
                          rgb_screen_px.y < rgb_minimap_px.y):
      raise ValueError("Screen (%s) can't be smaller than the minimap (%s)." % (
          rgb_screen_px, rgb_minimap_px))

    if feature_screen_px and rgb_screen_px and not action_space:
      raise ValueError(
          "You must specify the action space if you have both observations.")

    if save_replay_episodes and not replay_dir:
      raise ValueError("Missing replay_dir")

    self._map = maps.get(map_name)

    if self._map.players and self._num_players > self._map.players:
      raise ValueError(
          "Map only supports %s players, but trying to join with %s" % (
              self._map.players, self._num_players))

    self._discount = discount
    self._step_mul = step_mul or self._map.step_mul
    self._save_replay_episodes = save_replay_episodes
    self._replay_dir = replay_dir
    self._total_steps = 0
    self._random_seed = random_seed

    if score_index is None:
      self._score_index = self._map.score_index
    else:
      self._score_index = score_index
    if score_multiplier is None:
      self._score_multiplier = self._map.score_multiplier
    else:
      self._score_multiplier = score_multiplier
    self._last_score = None

    self._episode_length = game_steps_per_episode
    if self._episode_length is None:
      self._episode_length = self._map.game_steps_per_episode
    self._episode_steps = 0

    self._run_config = run_configs.get()
    self._parallel = run_parallel.RunParallel()  # Needed for multiplayer.

    interface = sc_pb.InterfaceOptions(raw=(visualize or use_feature_units),
                                       score=True)
    if feature_screen_px:
      interface.feature_layer.width = camera_width_world_units or 24
      feature_screen_px.assign_to(interface.feature_layer.resolution)
      feature_minimap_px.assign_to(interface.feature_layer.minimap_resolution)
    if rgb_screen_px:
      rgb_screen_px.assign_to(interface.render.resolution)
      rgb_minimap_px.assign_to(interface.render.minimap_resolution)

    if self._num_players == 1:
      self._launch_sp(interface)
    else:
      self._launch_mp(interface)

    game_info = self._controllers[0].game_info()
    static_data = self._controllers[0].data()

    if game_info.options.render != interface.render:
      logging.warning(
          "Actual interface options don't match requested options:\n"
          "Requested:\n%s\n\nActual:\n%s", interface, game_info.options)

    self._features = features.Features(game_info=game_info,
                                       action_space=action_space,
                                       use_feature_units=use_feature_units)
    if visualize:
      self._renderer_human = renderer_human.RendererHuman()
      self._renderer_human.init(game_info, static_data)
    else:
      self._renderer_human = None

    self._episode_count = 0
    self._obs = None
    self._state = environment.StepType.LAST  # Want to jump to `reset`.
    logging.info("Environment is ready.")

  def _launch_sp(self, interface):
    self._sc2_procs = [self._run_config.start()]
    self._controllers = [p.controller for p in self._sc2_procs]

    # Create the game.
    create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(
        map_path=self._map.path, map_data=self._map.data(self._run_config)))
    agent_race = Race.random
    for p in self._players:
      if isinstance(p, Agent):
        create.player_setup.add(type=sc_pb.Participant)
        agent_race = p.race
      else:
        create.player_setup.add(type=sc_pb.Computer, race=p.race,
                                difficulty=p.difficulty)
    if self._random_seed is not None:
      create.random_seed = self._random_seed
    self._controllers[0].create_game(create)

    join = sc_pb.RequestJoinGame(race=agent_race, options=interface)
    self._controllers[0].join_game(join)

  def _launch_mp(self, interface):
    # Reserve a whole bunch of ports for the weird multiplayer implementation.
    self._ports = [portpicker.pick_unused_port()
                   for _ in range(1 + self._num_players * 2)]
    assert len(self._ports) == len(set(self._ports))  # Ports must be unique.

    # Actually launch the game processes.
    self._sc2_procs = [self._run_config.start(extra_ports=self._ports)
                       for _ in range(self._num_players)]
    self._controllers = [p.controller for p in self._sc2_procs]

    # Save the maps so they can access it.
    self._parallel.run(
        (c.save_map, self._map.path, self._map.data(self._run_config))
        for c in self._controllers)

    # Create the game. Set the first instance as the host.
    create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(
        map_path=self._map.path))
    if self._random_seed is not None:
      create.random_seed = self._random_seed
    for p in self._players:
      if isinstance(p, Agent):
        create.player_setup.add(type=sc_pb.Participant)
      else:
        create.player_setup.add(type=sc_pb.Computer, race=p.race,
                                difficulty=p.difficulty)
    self._controllers[0].create_game(create)

    # Create the join request.
    join = sc_pb.RequestJoinGame(options=interface)
    join.shared_port = self._ports.pop()
    join.server_ports.game_port = self._ports.pop()
    join.server_ports.base_port = self._ports.pop()
    for _ in range(self._num_players - 1):
      join.client_ports.add(game_port=self._ports.pop(),
                            base_port=self._ports.pop())

    join_reqs = []
    for p in self._players:
      if isinstance(p, Agent):
        j = sc_pb.RequestJoinGame()
        j.CopyFrom(join)
        j.race = p.race
        join_reqs.append(j)

    # Join the game. This must be run in parallel because Join is a blocking
    # call to the game that waits until all clients have joined.
    self._parallel.run((c.join_game, join)
                       for c, join in zip(self._controllers, join_reqs))

    # Save them for restart.
    self._create_req = create
    self._join_reqs = join_reqs

  def observation_spec(self):
    """Look at Features for full specs."""
    return (self._features.observation_spec(),) * self._num_players

  def action_spec(self):
    """Look at Features for full specs."""
    return (self._features.action_spec(),) * self._num_players

  def _restart(self):
    if len(self._controllers) == 1:
      self._controllers[0].restart()
    else:
      self._parallel.run(c.leave for c in self._controllers)
      self._controllers[0].create_game(self._create_req)
      self._parallel.run((c.join_game, j)
                         for c, j in zip(self._controllers, self._join_reqs))

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
      logging.info(("Episode %s finished after %s game steps. "
                    "Outcome: %s, reward: %s, score: %s"),
                   self._episode_count, self._episode_steps, outcome, reward,
                   [o["score_cumulative"][0] for o in agent_obs])

    return tuple(environment.TimeStep(step_type=self._state,
                                      reward=r * self._score_multiplier,
                                      discount=discount, observation=o)
                 for r, o in zip(reward, agent_obs))

  def save_replay(self, replay_dir):
    replay_path = self._run_config.save_replay(
        self._controllers[0].save_replay(), replay_dir, self._map.name)
    logging.info("Wrote replay to: %s", replay_path)

  def close(self):
    logging.info("Environment Close")
    if hasattr(self, "_renderer_human") and self._renderer_human:
      self._renderer_human.close()
      self._renderer_human = None

    # Don't use parallel since it might be broken by an exception.
    if hasattr(self, "_controllers") and self._controllers:
      for c in self._controllers:
        c.quit()
      self._controllers = None
    if hasattr(self, "_sc2_procs") and self._sc2_procs:
      for p in self._sc2_procs:
        p.close()
      self._sc2_procs = None

    if hasattr(self, "_ports") and self._ports:
      for port in self._ports:
        portpicker.return_port(port)
      self._ports = None

    logging.info("%s", sw)
