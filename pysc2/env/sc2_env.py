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
# pylint: disable=g-complex-comprehension

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
from absl import logging
import random
import time

import enum

from pysc2 import maps
from pysc2 import run_configs
from pysc2.env import environment
from pysc2.lib import actions as actions_lib
from pysc2.lib import features
from pysc2.lib import metrics
from pysc2.lib import portspicker
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


class BotBuild(enum.IntEnum):
  """Bot build strategies."""
  random = sc_pb.RandomBuild
  rush = sc_pb.Rush
  timing = sc_pb.Timing
  power = sc_pb.Power
  macro = sc_pb.Macro
  air = sc_pb.Air


# Re-export these names to make it easy to construct the environment.
ActionSpace = actions_lib.ActionSpace  # pylint: disable=invalid-name
Dimensions = features.Dimensions  # pylint: disable=invalid-name
AgentInterfaceFormat = features.AgentInterfaceFormat  # pylint: disable=invalid-name
parse_agent_interface_format = features.parse_agent_interface_format


def to_list(arg):
  return arg if isinstance(arg, list) else [arg]


def get_default(a, b):
  return b if a is None else a


class Agent(collections.namedtuple("Agent", ["race", "name"])):
  """Define an Agent. It can have a single race or a list of races."""

  def __new__(cls, race, name=None):
    return super(Agent, cls).__new__(cls, to_list(race), name or "<unknown>")


class Bot(collections.namedtuple("Bot", ["race", "difficulty", "build"])):
  """Define a Bot. It can have a single or list of races or builds."""

  def __new__(cls, race, difficulty, build=None):
    return super(Bot, cls).__new__(
        cls, to_list(race), difficulty, to_list(build or BotBuild.random))


_DelayedAction = collections.namedtuple(
    "DelayedAction", ["game_loop", "action"])

REALTIME_GAME_LOOP_SECONDS = 1 / 22.4
MAX_STEP_COUNT = 524000  # The game fails above 2^19=524288 steps.
NUM_ACTION_DELAY_BUCKETS = 10


class SC2Env(environment.Base):
  """A Starcraft II environment.

  The implementation details of the action and observation specs are in
  lib/features.py
  """

  def __init__(self,  # pylint: disable=invalid-name
               _only_use_kwargs=None,
               map_name=None,
               battle_net_map=False,
               players=None,
               agent_interface_format=None,
               discount=1.,
               discount_zero_after_timeout=False,
               visualize=False,
               step_mul=None,
               realtime=False,
               save_replay_episodes=0,
               replay_dir=None,
               replay_prefix=None,
               game_steps_per_episode=None,
               score_index=None,
               score_multiplier=None,
               random_seed=None,
               disable_fog=False,
               ensure_available_actions=True,
               version=None):
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
          docs in maps/README.md for more information on available maps. Can
          also be a list of map names or instances, in which case one will be
          chosen at random per episode.
      battle_net_map: Whether to use the battle.net versions of the map(s).
      players: A list of Agent and Bot instances that specify who will play.
      agent_interface_format: A sequence containing one AgentInterfaceFormat
        per agent, matching the order of agents specified in the players list.
        Or a single AgentInterfaceFormat to be used for all agents.
      discount: Returned as part of the observation.
      discount_zero_after_timeout: If True, the discount will be zero
          after the `game_steps_per_episode` timeout.
      visualize: Whether to pop up a window showing the camera and feature
          layers. This won't work without access to a window manager.
      step_mul: How many game steps per agent step (action/observation). None
          means use the map default.
      realtime: Whether to use realtime mode. In this mode the game simulation
          automatically advances (at 22.4 gameloops per second) rather than
          being stepped manually. The number of game loops advanced with each
          call to step() won't necessarily match the step_mul specified. The
          environment will attempt to honour step_mul, returning observations
          with that spacing as closely as possible. Game loops will be skipped
          if they cannot be retrieved and processed quickly enough.
      save_replay_episodes: Save a replay after this many episodes. Default of 0
          means don't save replays.
      replay_dir: Directory to save replays. Required with save_replay_episodes.
      replay_prefix: An optional prefix to use when saving replays.
      game_steps_per_episode: Game steps per episode, independent of the
          step_mul. 0 means no limit. None means use the map default.
      score_index: -1 means use the win/loss reward, >=0 is the index into the
          score_cumulative with 0 being the curriculum score. None means use
          the map default.
      score_multiplier: How much to multiply the score by. Useful for negating.
      random_seed: Random number seed to use when initializing the game. This
          lets you run repeatable games/tests.
      disable_fog: Whether to disable fog of war.
      ensure_available_actions: Whether to throw an exception when an
          unavailable action is passed to step().
      version: The version of SC2 to use, defaults to the latest.

    Raises:
      ValueError: if no map is specified.
      ValueError: if wrong number of players are requested for a map.
      ValueError: if the resolutions aren't specified correctly.
    """
    if _only_use_kwargs:
      raise ValueError("All arguments must be passed as keyword arguments.")

    if not players:
      raise ValueError("You must specify the list of players.")

    for p in players:
      if not isinstance(p, (Agent, Bot)):
        raise ValueError(
            "Expected players to be of type Agent or Bot. Got: %s." % p)

    num_players = len(players)
    self._num_agents = sum(1 for p in players if isinstance(p, Agent))
    self._players = players

    if not 1 <= num_players <= 2 or not self._num_agents:
      raise ValueError("Only 1 or 2 players with at least one agent is "
                       "supported at the moment.")

    if not map_name:
      raise ValueError("Missing a map name.")

    self._battle_net_map = battle_net_map
    self._maps = [maps.get(name) for name in to_list(map_name)]
    min_players = min(m.players for m in self._maps)
    max_players = max(m.players for m in self._maps)
    if self._battle_net_map:
      for m in self._maps:
        if not m.battle_net:
          raise ValueError("%s isn't known on Battle.net" % m.name)

    if max_players == 1:
      if self._num_agents != 1:
        raise ValueError("Single player maps require exactly one Agent.")
    elif not 2 <= num_players <= min_players:
      raise ValueError(
          "Maps support 2 - %s players, but trying to join with %s" % (
              min_players, num_players))

    if save_replay_episodes and not replay_dir:
      raise ValueError("Missing replay_dir")

    self._realtime = realtime
    self._last_step_time = None
    self._save_replay_episodes = save_replay_episodes
    self._replay_dir = replay_dir
    self._replay_prefix = replay_prefix
    self._random_seed = random_seed
    self._disable_fog = disable_fog
    self._ensure_available_actions = ensure_available_actions
    self._discount = discount
    self._discount_zero_after_timeout = discount_zero_after_timeout
    self._default_step_mul = step_mul
    self._default_score_index = score_index
    self._default_score_multiplier = score_multiplier
    self._default_episode_length = game_steps_per_episode

    self._run_config = run_configs.get(version=version)
    self._parallel = run_parallel.RunParallel()  # Needed for multiplayer.
    self._game_info = None

    if agent_interface_format is None:
      raise ValueError("Please specify agent_interface_format.")

    if isinstance(agent_interface_format, AgentInterfaceFormat):
      agent_interface_format = [agent_interface_format] * self._num_agents

    if len(agent_interface_format) != self._num_agents:
      raise ValueError(
          "The number of entries in agent_interface_format should "
          "correspond 1-1 with the number of agents.")

    self._action_delay_fns = [aif.action_delay_fn
                              for aif in agent_interface_format]

    self._interface_formats = agent_interface_format
    self._interface_options = [
        self._get_interface(interface_format, require_raw=visualize and i == 0)
        for i, interface_format in enumerate(agent_interface_format)]

    self._launch_game()
    self._create_join()

    self._finalize(visualize)

  def _finalize(self, visualize):
    self._delayed_actions = [collections.deque()
                             for _ in self._action_delay_fns]

    if visualize:
      self._renderer_human = renderer_human.RendererHuman()
      self._renderer_human.init(
          self._controllers[0].game_info(),
          self._controllers[0].data())
    else:
      self._renderer_human = None

    self._metrics = metrics.Metrics(self._map_name)
    self._metrics.increment_instance()

    self._last_score = None
    self._total_steps = 0
    self._episode_steps = 0
    self._episode_count = 0
    self._obs = [None] * self._num_agents
    self._agent_obs = [None] * self._num_agents
    self._state = environment.StepType.LAST  # Want to jump to `reset`.
    logging.info("Environment is ready")

  @staticmethod
  def _get_interface(agent_interface_format, require_raw):
    aif = agent_interface_format
    interface = sc_pb.InterfaceOptions(
        raw=(aif.use_feature_units or
             aif.use_unit_counts or
             aif.use_raw_units or
             require_raw),
        show_cloaked=aif.show_cloaked,
        show_burrowed_shadows=aif.show_burrowed_shadows,
        show_placeholders=aif.show_placeholders,
        raw_affects_selection=True,
        raw_crop_to_playable_area=aif.raw_crop_to_playable_area,
        score=True)

    if aif.feature_dimensions:
      interface.feature_layer.width = aif.camera_width_world_units
      aif.feature_dimensions.screen.assign_to(
          interface.feature_layer.resolution)
      aif.feature_dimensions.minimap.assign_to(
          interface.feature_layer.minimap_resolution)
      interface.feature_layer.crop_to_playable_area = aif.crop_to_playable_area
      interface.feature_layer.allow_cheating_layers = aif.allow_cheating_layers

    if aif.rgb_dimensions:
      aif.rgb_dimensions.screen.assign_to(interface.render.resolution)
      aif.rgb_dimensions.minimap.assign_to(interface.render.minimap_resolution)

    return interface

  def _launch_game(self):
    # Reserve a whole bunch of ports for the weird multiplayer implementation.
    if self._num_agents > 1:
      self._ports = portspicker.pick_unused_ports(self._num_agents * 2)
      logging.info("Ports used for multiplayer: %s", self._ports)
    else:
      self._ports = []

    # Actually launch the game processes.
    self._sc2_procs = [
        self._run_config.start(extra_ports=self._ports,
                               want_rgb=interface.HasField("render"))
        for interface in self._interface_options]
    self._controllers = [p.controller for p in self._sc2_procs]

    if self._battle_net_map:
      available_maps = self._controllers[0].available_maps()
      available_maps = set(available_maps.battlenet_map_names)
      unavailable = [m.name for m in self._maps
                     if m.battle_net not in available_maps]
      if unavailable:
        raise ValueError("Requested map(s) not in the battle.net cache: %s"
                         % ",".join(unavailable))

  def _create_join(self):
    """Create the game, and join it."""
    map_inst = random.choice(self._maps)
    self._map_name = map_inst.name

    self._step_mul = max(1, self._default_step_mul or map_inst.step_mul)
    self._score_index = get_default(self._default_score_index,
                                    map_inst.score_index)
    self._score_multiplier = get_default(self._default_score_multiplier,
                                         map_inst.score_multiplier)
    self._episode_length = get_default(self._default_episode_length,
                                       map_inst.game_steps_per_episode)
    if self._episode_length <= 0 or self._episode_length > MAX_STEP_COUNT:
      self._episode_length = MAX_STEP_COUNT

    # Create the game. Set the first instance as the host.
    create = sc_pb.RequestCreateGame(
        disable_fog=self._disable_fog,
        realtime=self._realtime)

    if self._battle_net_map:
      create.battlenet_map_name = map_inst.battle_net
    else:
      create.local_map.map_path = map_inst.path
      map_data = map_inst.data(self._run_config)
      if self._num_agents == 1:
        create.local_map.map_data = map_data
      else:
        # Save the maps so they can access it. Don't do it in parallel since SC2
        # doesn't respect tmpdir on windows, which leads to a race condition:
        # https://github.com/Blizzard/s2client-proto/issues/102
        for c in self._controllers:
          c.save_map(map_inst.path, map_data)
    if self._random_seed is not None:
      create.random_seed = self._random_seed
    for p in self._players:
      if isinstance(p, Agent):
        create.player_setup.add(type=sc_pb.Participant)
      else:
        create.player_setup.add(
            type=sc_pb.Computer, race=random.choice(p.race),
            difficulty=p.difficulty, ai_build=random.choice(p.build))
    self._controllers[0].create_game(create)

    # Create the join requests.
    agent_players = [p for p in self._players if isinstance(p, Agent)]
    sanitized_names = crop_and_deduplicate_names(p.name for p in agent_players)
    join_reqs = []
    for p, name, interface in zip(agent_players, sanitized_names,
                                  self._interface_options):
      join = sc_pb.RequestJoinGame(options=interface)
      join.race = random.choice(p.race)
      join.player_name = name
      if self._ports:
        join.shared_port = 0  # unused
        join.server_ports.game_port = self._ports[0]
        join.server_ports.base_port = self._ports[1]
        for i in range(self._num_agents - 1):
          join.client_ports.add(game_port=self._ports[i * 2 + 2],
                                base_port=self._ports[i * 2 + 3])
      join_reqs.append(join)

    # Join the game. This must be run in parallel because Join is a blocking
    # call to the game that waits until all clients have joined.
    self._parallel.run((c.join_game, join)
                       for c, join in zip(self._controllers, join_reqs))

    self._game_info = self._parallel.run(c.game_info for c in self._controllers)
    for g, interface in zip(self._game_info, self._interface_options):
      if g.options.render != interface.render:
        logging.warning(
            "Actual interface options don't match requested options:\n"
            "Requested:\n%s\n\nActual:\n%s", interface, g.options)

    self._features = [
        features.features_from_game_info(
            game_info=g, agent_interface_format=aif, map_name=self._map_name)
        for g, aif in zip(self._game_info, self._interface_formats)]

  @property
  def map_name(self):
    return self._map_name

  @property
  def game_info(self):
    """A list of ResponseGameInfo, one per agent."""
    return self._game_info

  def static_data(self):
    return self._controllers[0].data()

  def observation_spec(self):
    """Look at Features for full specs."""
    return tuple(f.observation_spec() for f in self._features)

  def action_spec(self):
    """Look at Features for full specs."""
    return tuple(f.action_spec() for f in self._features)

  def action_delays(self):
    """In realtime we track the delay observation -> action executed.

    Returns:
      A list per agent of action delays, where action delays are a list where
      the index in the list corresponds to the delay in game loops, the value
      at that index the count over the course of an episode.

    Raises:
      ValueError: If called when not in realtime mode.
    """
    if not self._realtime:
      raise ValueError("This method is only supported in realtime mode")

    return self._action_delays

  def _restart(self):
    if (len(self._players) == 1 and len(self._players[0].race) == 1 and
        len(self._maps) == 1):
      # Need to support restart for fast-restart of mini-games.
      self._controllers[0].restart()
    else:
      if len(self._controllers) > 1:
        self._parallel.run(c.leave for c in self._controllers)
      self._create_join()

  @sw.decorate
  def reset(self):
    """Start a new episode."""
    self._episode_steps = 0
    if self._episode_count:
      # No need to restart for the first episode.
      self._restart()

    self._episode_count += 1
    races = [Race(r).name
             for _, r in sorted(self._features[0].requested_races.items())]
    logging.info("Starting episode %s: [%s] on %s",
                 self._episode_count, ", ".join(races), self._map_name)
    self._metrics.increment_episode()

    self._last_score = [0] * self._num_agents
    self._state = environment.StepType.FIRST
    if self._realtime:
      self._last_step_time = time.time()
      self._last_obs_game_loop = None
      self._action_delays = [[0] * NUM_ACTION_DELAY_BUCKETS] * self._num_agents

    return self._observe(target_game_loop=0)

  @sw.decorate("step_env")
  def step(self, actions, step_mul=None):
    """Apply actions, step the world forward, and return observations.

    Args:
      actions: A list of actions meeting the action spec, one per agent, or a
          list per agent. Using a list allows multiple actions per frame, but
          will still check that they're valid, so disabling
          ensure_available_actions is encouraged.
      step_mul: If specified, use this rather than the environment's default.

    Returns:
      A tuple of TimeStep namedtuples, one per agent.
    """
    if self._state == environment.StepType.LAST:
      return self.reset()

    skip = not self._ensure_available_actions
    actions = [[f.transform_action(o.observation, a, skip_available=skip)
                for a in to_list(acts)]
               for f, o, acts in zip(self._features, self._obs, actions)]

    if not self._realtime:
      actions = self._apply_action_delays(actions)

    self._parallel.run((c.actions, sc_pb.RequestAction(actions=a))
                       for c, a in zip(self._controllers, actions))

    self._state = environment.StepType.MID
    return self._step(step_mul)

  def _step(self, step_mul=None):
    step_mul = step_mul or self._step_mul
    if step_mul <= 0:
      raise ValueError("step_mul should be positive, got {}".format(step_mul))

    target_game_loop = self._episode_steps + step_mul
    if not self._realtime:
      # Send any delayed actions that were scheduled up to the target game loop.
      current_game_loop = self._send_delayed_actions(
          up_to_game_loop=target_game_loop,
          current_game_loop=self._episode_steps)

      self._step_to(game_loop=target_game_loop,
                    current_game_loop=current_game_loop)

    return self._observe(target_game_loop=target_game_loop)

  def _apply_action_delays(self, actions):
    """Apply action delays to the requested actions, if configured to."""
    assert not self._realtime
    actions_now = []
    for actions_for_player, delay_fn, delayed_actions in zip(
        actions, self._action_delay_fns, self._delayed_actions):
      actions_now_for_player = []

      for action in actions_for_player:
        delay = delay_fn() if delay_fn else 1
        if delay > 1 and action.ListFields():  # Skip no-ops.
          game_loop = self._episode_steps + delay - 1

          # Randomized delays mean that 2 delay actions can be reversed.
          # Make sure that doesn't happen.
          if delayed_actions:
            game_loop = max(game_loop, delayed_actions[-1].game_loop)

          # Don't send an action this frame.
          delayed_actions.append(_DelayedAction(game_loop, action))
        else:
          actions_now_for_player.append(action)
      actions_now.append(actions_now_for_player)

    return actions_now

  def _send_delayed_actions(self, up_to_game_loop, current_game_loop):
    """Send any delayed actions scheduled for up to the specified game loop."""
    assert not self._realtime
    while True:
      if not any(self._delayed_actions):  # No queued actions
        return current_game_loop

      act_game_loop = min(d[0].game_loop for d in self._delayed_actions if d)
      if act_game_loop > up_to_game_loop:
        return current_game_loop

      self._step_to(act_game_loop, current_game_loop)
      current_game_loop = act_game_loop
      if self._controllers[0].status_ended:
        # We haven't observed and may have hit game end.
        return current_game_loop

      actions = []
      for d in self._delayed_actions:
        if d and d[0].game_loop == current_game_loop:
          delayed_action = d.popleft()
          actions.append(delayed_action.action)
        else:
          actions.append(None)
      self._parallel.run((c.act, a) for c, a in zip(self._controllers, actions))

  def _step_to(self, game_loop, current_game_loop):
    step_mul = game_loop - current_game_loop
    if step_mul < 0:
      raise ValueError("We should never need to step backwards")
    if step_mul > 0:
      with self._metrics.measure_step_time(step_mul):
        if not self._controllers[0].status_ended:  # May already have ended.
          self._parallel.run((c.step, step_mul) for c in self._controllers)

  def _get_observations(self, target_game_loop):
    # Transform in the thread so it runs while waiting for other observations.
    def parallel_observe(c, f):
      obs = c.observe(target_game_loop=target_game_loop)
      agent_obs = f.transform_obs(obs)
      return obs, agent_obs

    with self._metrics.measure_observation_time():
      self._obs, self._agent_obs = zip(*self._parallel.run(
          (parallel_observe, c, f)
          for c, f in zip(self._controllers, self._features)))

    game_loop = self._agent_obs[0].game_loop[0]
    if (game_loop < target_game_loop and
        not any(o.player_result for o in self._obs)):
      raise ValueError(
          ("The game didn't advance to the expected game loop. "
           "Expected: %s, got: %s") % (target_game_loop, game_loop))
    elif game_loop > target_game_loop and target_game_loop > 0:
      logging.warn("Received observation %d step(s) late: %d rather than %d.",
                   game_loop - target_game_loop, game_loop, target_game_loop)

    if self._realtime:
      # Track delays on executed actions.
      # Note that this will underestimate e.g. action sent, new observation
      # taken before action executes, action executes, observation taken
      # with action. This is difficult to avoid without changing the SC2
      # binary - e.g. send the observation game loop with each action,
      # return them in the observation action proto.
      if self._last_obs_game_loop is not None:
        for i, obs in enumerate(self._obs):
          for action in obs.actions:
            if action.HasField("game_loop"):
              delay = action.game_loop - self._last_obs_game_loop
              if delay > 0:
                num_slots = len(self._action_delays[i])
                delay = min(delay, num_slots - 1)  # Cap to num buckets.
                self._action_delays[i][delay] += 1
                break
      self._last_obs_game_loop = game_loop

  def _observe(self, target_game_loop):
    self._get_observations(target_game_loop)

    # TODO(tewalds): How should we handle more than 2 agents and the case where
    # the episode can end early for some agents?
    outcome = [0] * self._num_agents
    discount = self._discount
    episode_complete = any(o.player_result for o in self._obs)

    if episode_complete:
      self._state = environment.StepType.LAST
      discount = 0
      for i, o in enumerate(self._obs):
        player_id = o.observation.player_common.player_id
        for result in o.player_result:
          if result.player_id == player_id:
            outcome[i] = possible_results.get(result.result, 0)

    if self._score_index >= 0:  # Game score, not win/loss reward.
      cur_score = [o["score_cumulative"][self._score_index]
                   for o in self._agent_obs]
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

    self._total_steps += self._agent_obs[0].game_loop[0] - self._episode_steps
    self._episode_steps = self._agent_obs[0].game_loop[0]
    if self._episode_steps >= self._episode_length:
      self._state = environment.StepType.LAST
      if self._discount_zero_after_timeout:
        discount = 0.0
      if self._episode_steps >= MAX_STEP_COUNT:
        logging.info("Cut short to avoid SC2's max step count of 2^19=524288.")

    if self._state == environment.StepType.LAST:
      if (self._save_replay_episodes > 0 and
          self._episode_count % self._save_replay_episodes == 0):
        self.save_replay(self._replay_dir, self._replay_prefix)
      logging.info(("Episode %s finished after %s game steps. "
                    "Outcome: %s, reward: %s, score: %s"),
                   self._episode_count, self._episode_steps, outcome, reward,
                   [o["score_cumulative"][0] for o in self._agent_obs])

    def zero_on_first_step(value):
      return 0.0 if self._state == environment.StepType.FIRST else value
    return tuple(environment.TimeStep(
        step_type=self._state,
        reward=zero_on_first_step(r * self._score_multiplier),
        discount=zero_on_first_step(discount),
        observation=o) for r, o in zip(reward, self._agent_obs))

  def send_chat_messages(self, messages, broadcast=True):
    """Useful for logging messages into the replay."""
    self._parallel.run(
        (c.chat,
         message,
         sc_pb.ActionChat.Broadcast if broadcast else sc_pb.ActionChat.Team)
        for c, message in zip(self._controllers, messages))

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
      portspicker.return_ports(self._ports)
      self._ports = None

    self._game_info = None


def crop_and_deduplicate_names(names):
  """Crops and de-duplicates the passed names.

  SC2 gets confused in a multi-agent game when agents have the same
  name. We check for name duplication to avoid this, but - SC2 also
  crops player names to a hard character limit, which can again lead
  to duplicate names. To avoid this we unique-ify names if they are
  equivalent after cropping. Ideally SC2 would handle duplicate names,
  making this unnecessary.

  TODO(b/121092563): Fix this in the SC2 binary.

  Args:
    names: List of names.

  Returns:
    De-duplicated names cropped to 32 characters.
  """
  max_name_length = 32

  # Crop.
  cropped = [n[:max_name_length] for n in names]

  # De-duplicate.
  deduplicated = []
  name_counts = collections.Counter(n for n in cropped)
  name_index = collections.defaultdict(lambda: 1)
  for n in cropped:
    if name_counts[n] == 1:
      deduplicated.append(n)
    else:
      deduplicated.append("({}) {}".format(name_index[n], n))
      name_index[n] += 1

  # Crop again.
  recropped = [n[:max_name_length] for n in deduplicated]
  if len(set(recropped)) != len(recropped):
    raise ValueError("Failed to de-duplicate names")

  return recropped
