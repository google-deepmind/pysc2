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
import time

import enum
import portpicker

from pysc2 import maps
from pysc2 import run_configs
from pysc2.env import environment
from pysc2.lib import actions as actions_lib
from pysc2.lib import features
from pysc2.lib import metrics
from pysc2.lib import renderer_human
from pysc2.lib import run_parallel
from pysc2.lib import stopwatch

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb

sw = stopwatch.sw


possible_results = {
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

# Re-export these names to make it easy to construct the environment.
ActionSpace = actions_lib.ActionSpace  # pylint: disable=invalid-name
Dimensions = features.Dimensions  # pylint: disable=invalid-name
AgentInterfaceFormat = features.AgentInterfaceFormat  # pylint: disable=invalid-name
parse_agent_interface_format = features.parse_agent_interface_format


Agent = collections.namedtuple("Agent", ["race"])
Bot = collections.namedtuple("Bot", ["race", "difficulty"])


def _pick_unused_ports(num_ports, retry_interval_secs=3, retry_attempts=5):
  """Returns a list of `num_ports` unused ports."""
  ports = set()
  for _ in range(retry_attempts):
    ports.update(
        portpicker.pick_unused_port() for _ in range(num_ports - len(ports)))
    ports.discard(None)  # portpicker returns None on error.
    if len(ports) == num_ports:
      return list(ports)
    # Duplicate ports can be returned, especially when insufficient ports are
    # free. Wait for more ports to be freed and retry.
    time.sleep(retry_interval_secs)

  # Could not obtain enough ports. Release what we do have.
  for port in ports:
    portpicker.return_port(port)
  raise RuntimeError("Unable to obtain %d unused ports." % num_ports)


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
      screen_size_px: Deprecated. Use agent_interface_formats instead.
      minimap_size_px: Deprecated. Use agent_interface_formats instead.
      agent_interface_format: A sequence containing one AgentInterfaceFormat
        per agent, matching the order of agents specified in the players list.
        Or a single AgentInterfaceFormat to be used for all agents.
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
      random_seed: Random number seed to use when initializing the game. This
          lets you run repeatable games/tests.
      disable_fog: Whether to disable fog of war.

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

    map_inst = maps.get(map_name)
    self._map_name = map_name

    if not players:
      players = list()
      players.append(Agent(Race.random))

      if not map_inst.players or map_inst.players >= 2:
        players.append(Bot(Race.random, Difficulty.very_easy))

    for p in players:
      if not isinstance(p, (Agent, Bot)):
        raise ValueError(
            "Expected players to be of type Agent or Bot. Got: %s." % p)

    num_players = len(players)
    self._num_agents = sum(1 for p in players if isinstance(p, Agent))
    self._players = players

    if not 1 <= num_players <= 2 or not self._num_agents:
      raise ValueError(
          "Only 1 or 2 players with at least one agent is "
          "supported at the moment.")

    if save_replay_episodes and not replay_dir:
      raise ValueError("Missing replay_dir")

    if map_inst.players and num_players > map_inst.players:
      raise ValueError(
          "Map only supports %s players, but trying to join with %s" % (
              map_inst.players, num_players))

    self._discount = discount
    self._step_mul = step_mul or map_inst.step_mul
    self._save_replay_episodes = save_replay_episodes
    self._replay_dir = replay_dir
    self._random_seed = random_seed
    self._disable_fog = disable_fog

    if score_index is None:
      self._score_index = map_inst.score_index
    else:
      self._score_index = score_index
    if score_multiplier is None:
      self._score_multiplier = map_inst.score_multiplier
    else:
      self._score_multiplier = score_multiplier

    self._episode_length = game_steps_per_episode
    if self._episode_length is None:
      self._episode_length = map_inst.game_steps_per_episode

    self._run_config = run_configs.get()
    self._parallel = run_parallel.RunParallel()  # Needed for multiplayer.

    if agent_interface_format is None:
      raise ValueError("Please specify agent_interface_format.")

    if isinstance(agent_interface_format, AgentInterfaceFormat):
      agent_interface_format = [agent_interface_format] * self._num_agents

    if len(agent_interface_format) != self._num_agents:
      raise ValueError(
          "The number of entries in agent_interface_format should "
          "correspond 1-1 with the number of agents.")

    interfaces = []
    for i, interface_format in enumerate(agent_interface_format):
      require_raw = visualize and (i == 0)
      interfaces.append(self._get_interface(interface_format, require_raw))

    if self._num_agents == 1:
      self._launch_sp(map_inst, interfaces[0])
    else:
      self._launch_mp(map_inst, interfaces)

    self._finalize(agent_interface_format, interfaces, visualize)

  def _finalize(self, agent_interface_formats, interfaces, visualize):
    game_info = self._parallel.run(c.game_info for c in self._controllers)
    if not self._map_name:
      self._map_name = game_info[0].map_name

    for g, interface in zip(game_info, interfaces):
      if g.options.render != interface.render:
        logging.warning(
            "Actual interface options don't match requested options:\n"
            "Requested:\n%s\n\nActual:\n%s", interface, g.options)

    self._features = [
        features.features_from_game_info(
            game_info=g,
            use_feature_units=agent_interface_format.use_feature_units,
            action_space=agent_interface_format.action_space,
            hide_specific_actions=agent_interface_format.hide_specific_actions)
        for g, agent_interface_format in zip(game_info, agent_interface_formats)
    ]

    if visualize:
      static_data = self._controllers[0].data()
      self._renderer_human = renderer_human.RendererHuman()
      self._renderer_human.init(game_info[0], static_data)
    else:
      self._renderer_human = None

    self._metrics = metrics.Metrics(self._map_name)
    self._metrics.increment_instance()

    self._last_score = None
    self._total_steps = 0
    self._episode_steps = 0
    self._episode_count = 0
    self._obs = None
    self._state = environment.StepType.LAST  # Want to jump to `reset`.
    logging.info("Environment is ready on map: %s", self._map_name)

  @staticmethod
  def _get_interface(agent_interface_format, require_raw):
    interface = sc_pb.InterfaceOptions(
        raw=(agent_interface_format.use_feature_units or require_raw),
        score=True)

    if agent_interface_format.feature_dimensions:
      interface.feature_layer.width = (
          agent_interface_format.camera_width_world_units)
      agent_interface_format.feature_dimensions.screen.assign_to(
          interface.feature_layer.resolution)
      agent_interface_format.feature_dimensions.minimap.assign_to(
          interface.feature_layer.minimap_resolution)

    if agent_interface_format.rgb_dimensions:
      agent_interface_format.rgb_dimensions.screen.assign_to(
          interface.render.resolution)
      agent_interface_format.rgb_dimensions.minimap.assign_to(
          interface.render.minimap_resolution)

    return interface

  def _launch_sp(self, map_inst, interface):
    self._sc2_procs = [self._run_config.start()]
    self._controllers = [p.controller for p in self._sc2_procs]

    # Create the game.
    create = sc_pb.RequestCreateGame(
        local_map=sc_pb.LocalMap(
            map_path=map_inst.path, map_data=map_inst.data(self._run_config)),
        disable_fog=self._disable_fog)
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

  def _launch_mp(self, map_inst, interfaces):
    # Reserve a whole bunch of ports for the weird multiplayer implementation.
    self._ports = _pick_unused_ports(self._num_agents * 2)

    # Actually launch the game processes.
    self._sc2_procs = [self._run_config.start(extra_ports=self._ports)
                       for _ in range(self._num_agents)]
    self._controllers = [p.controller for p in self._sc2_procs]

    # Save the maps so they can access it. Don't do it in parallel since SC2
    # doesn't respect tmpdir on windows, which leads to a race condition:
    # https://github.com/Blizzard/s2client-proto/issues/102
    for c in self._controllers:
      c.save_map(map_inst.path, map_inst.data(self._run_config))

    # Create the game. Set the first instance as the host.
    create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(
        map_path=map_inst.path), disable_fog=self._disable_fog)
    if self._random_seed is not None:
      create.random_seed = self._random_seed
    for p in self._players:
      if isinstance(p, Agent):
        create.player_setup.add(type=sc_pb.Participant)
      else:
        create.player_setup.add(type=sc_pb.Computer, race=p.race,
                                difficulty=p.difficulty)
    self._controllers[0].create_game(create)

    # Create the join requests.
    agent_players = (p for p in self._players if isinstance(p, Agent))
    join_reqs = []
    for agent_index, p in enumerate(agent_players):
      ports = self._ports[:]
      join = sc_pb.RequestJoinGame(options=interfaces[agent_index])
      join.shared_port = 0  # unused
      join.server_ports.game_port = ports.pop(0)
      join.server_ports.base_port = ports.pop(0)
      for _ in range(self._num_agents - 1):
        join.client_ports.add(game_port=ports.pop(0),
                              base_port=ports.pop(0))

      join.race = p.race
      join_reqs.append(join)

    # Join the game. This must be run in parallel because Join is a blocking
    # call to the game that waits until all clients have joined.
    self._parallel.run((c.join_game, join)
                       for c, join in zip(self._controllers, join_reqs))

    # Save them for restart.
    self._create_req = create
    self._join_reqs = join_reqs

  def observation_spec(self):
    """Look at Features for full specs."""
    return tuple(f.observation_spec() for f in self._features)

  def action_spec(self):
    """Look at Features for full specs."""
    return tuple(f.action_spec() for f in self._features)

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
    self._metrics.increment_episode()

    self._last_score = [0] * self._num_agents
    self._state = environment.StepType.FIRST
    return self._step()

  @sw.decorate("step_env")
  def step(self, actions):
    """Apply actions, step the world forward, and return observations."""
    if self._state == environment.StepType.LAST:
      return self.reset()

    self._parallel.run(
        (c.act, f.transform_action(o.observation, a))
        for c, f, o, a in zip(
            self._controllers, self._features, self._obs, actions))

    self._state = environment.StepType.MID
    return self._step()

  def _step(self):
    with self._metrics.measure_step_time(self._step_mul):
      self._parallel.run((c.step, self._step_mul) for c in self._controllers)

    with self._metrics.measure_observation_time():
      self._obs = self._parallel.run(c.observe for c in self._controllers)
      agent_obs = [f.transform_obs(o) for f, o in zip(
          self._features, self._obs)]

    # TODO(tewalds): How should we handle more than 2 agents and the case where
    # the episode can end early for some agents?
    outcome = [0] * self._num_agents
    discount = self._discount
    if any(o.player_result for o in self._obs):  # Episode over.
      self._state = environment.StepType.LAST
      discount = 0
      for i, o in enumerate(self._obs):
        player_id = o.observation.player_common.player_id
        for result in o.player_result:
          if result.player_id == player_id:
            outcome[i] = possible_results.get(result.result, 0)

    if self._score_index >= 0:  # Game score, not win/loss reward.
      cur_score = [o["score_cumulative"][self._score_index] for o in agent_obs]
      if self._episode_steps == 0:  # First reward is always 0.
        reward = [0] * self._num_agents
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

  def send_chat_messages(self, messages):
    """Useful for logging messages into the replay."""
    self._parallel.run(
        (c.chat, message) for c, message in zip(self._controllers, messages))

  def save_replay(self, replay_dir, prefix=None):
    if prefix is None:
      prefix = self._map_name
    replay_path = self._run_config.save_replay(
        self._controllers[0].save_replay(), replay_dir, prefix)
    logging.info("Wrote replay to: %s", replay_path)
    return replay_path

  def close(self):
    logging.info("Environment Close")
    if hasattr(self, "_metrics") and self._metrics:
      self._metrics.close()
      self._metrics = None
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
