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


class Agent(collections.namedtuple("Agent", ["race", "name"])):

  def __new__(cls, race, name=None):
    return super(Agent, cls).__new__(cls, race, name or "<unknown>")


class Bot(collections.namedtuple("Bot", ["race", "difficulty", "build"])):

  def __new__(cls, race, difficulty, build=None):
    return super(Bot, cls).__new__(
        cls, race, difficulty, build or BotBuild.random)


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
               players=None,
               agent_race=None,  # deprecated
               bot_race=None,  # deprecated
               difficulty=None,  # deprecated
               screen_size_px=None,  # deprecated
               minimap_size_px=None,  # deprecated
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
               ensure_available_actions=True):
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
      players = [Agent(Race.random)]

    if len(players) == 1 and (not map_inst.players or map_inst.players >= 2):
      # Make sure 2p+ maps have an opponent.
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
    self._realtime = realtime
    self._last_step_time = None
    self._save_replay_episodes = save_replay_episodes
    self._replay_dir = replay_dir
    self._replay_prefix = replay_prefix
    self._random_seed = random_seed
    self._disable_fog = disable_fog
    self._ensure_available_actions = ensure_available_actions
    self._discount_zero_after_timeout = discount_zero_after_timeout

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
    if self._episode_length == 0 or self._episode_length > MAX_STEP_COUNT:
      self._episode_length = MAX_STEP_COUNT

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

    self._action_delay_fns = [aif.action_delay_fn
                              for aif in agent_interface_format]

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

    self._delayed_actions = [collections.deque()
                             for _ in self._action_delay_fns]

    self._features = [
        features.features_from_game_info(
            game_info=g,
            use_feature_units=agent_interface_format.use_feature_units,
            use_raw_units=agent_interface_format.use_raw_units,
            raw_resolution=agent_interface_format.raw_resolution,
            use_raw_actions=agent_interface_format.use_raw_actions,
            max_selected_units=agent_interface_format.max_selected_units,
            use_unit_counts=agent_interface_format.use_unit_counts,
            use_camera_position=agent_interface_format.use_camera_position,
            action_space=agent_interface_format.action_space,
            hide_specific_actions=agent_interface_format.hide_specific_actions,
            add_cargo_to_units=agent_interface_format.add_cargo_to_units,
            send_observation_proto=agent_interface_format.send_observation_proto
        )
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
    self._obs = [None] * len(interfaces)
    self._agent_obs = [None] * len(interfaces)
    self._state = environment.StepType.LAST  # Want to jump to `reset`.
    logging.info("Environment is ready on map: %s", self._map_name)

  @staticmethod
  def _get_interface(agent_interface_format, require_raw):
    interface = sc_pb.InterfaceOptions(
        raw=(agent_interface_format.use_feature_units or
             agent_interface_format.use_unit_counts or
             agent_interface_format.use_raw_units or
             require_raw),
        show_cloaked=agent_interface_format.show_cloaked,
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
    self._sc2_procs = [self._run_config.start(
        want_rgb=interface.HasField("render"))]
    self._controllers = [p.controller for p in self._sc2_procs]

    # Create the game.
    create = sc_pb.RequestCreateGame(
        local_map=sc_pb.LocalMap(
            map_path=map_inst.path, map_data=map_inst.data(self._run_config)),
        disable_fog=self._disable_fog,
        realtime=self._realtime)
    agent = Agent(Race.random)
    for p in self._players:
      if isinstance(p, Agent):
        create.player_setup.add(type=sc_pb.Participant)
        agent = p
      else:
        create.player_setup.add(type=sc_pb.Computer, race=p.race,
                                difficulty=p.difficulty, ai_build=p.build)
    if self._random_seed is not None:
      create.random_seed = self._random_seed
    self._controllers[0].create_game(create)

    join = sc_pb.RequestJoinGame(
        options=interface, race=agent.race, player_name=agent.name)
    self._controllers[0].join_game(join)

  def _launch_mp(self, map_inst, interfaces):
    # Reserve a whole bunch of ports for the weird multiplayer implementation.
    self._ports = portspicker.pick_unused_ports(self._num_agents * 2)
    logging.info("Ports used for multiplayer: %s", self._ports)

    # Actually launch the game processes.
    self._sc2_procs = [
        self._run_config.start(extra_ports=self._ports,
                               want_rgb=interface.HasField("render"))
        for interface in interfaces]
    self._controllers = [p.controller for p in self._sc2_procs]

    # Save the maps so they can access it. Don't do it in parallel since SC2
    # doesn't respect tmpdir on windows, which leads to a race condition:
    # https://github.com/Blizzard/s2client-proto/issues/102
    for c in self._controllers:
      c.save_map(map_inst.path, map_inst.data(self._run_config))

    # Create the game. Set the first instance as the host.
    create = sc_pb.RequestCreateGame(
        local_map=sc_pb.LocalMap(
            map_path=map_inst.path),
        disable_fog=self._disable_fog,
        realtime=self._realtime)
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
    agent_players = [p for p in self._players if isinstance(p, Agent)]
    sanitized_names = crop_and_deduplicate_names(p.name for p in agent_players)
    join_reqs = []
    for agent_index, (p, name) in enumerate(
        zip(agent_players, sanitized_names)):
      ports = self._ports[:]
      join = sc_pb.RequestJoinGame(options=interfaces[agent_index])
      join.shared_port = 0  # unused
      join.server_ports.game_port = ports.pop(0)
      join.server_ports.base_port = ports.pop(0)
      for _ in range(self._num_agents - 1):
        join.client_ports.add(game_port=ports.pop(0),
                              base_port=ports.pop(0))

      join.race = p.race
      join.player_name = name
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
    if self._realtime:
      self._last_step_time = time.time()
      self._last_act_game_loop = [None] * self._num_agents
      self._action_delays = [[0] * NUM_ACTION_DELAY_BUCKETS] * self._num_agents

    return self._observe(target_game_loop=0)

  @sw.decorate("step_env")
  def step(self, actions, step_mul=None):
    """Apply actions, step the world forward, and return observations.

    Args:
      actions: A list of actions meeting the action spec, one per agent.
      step_mul: If specified, use this rather than the environment's default.

    Returns:
      A tuple of TimeStep namedtuples, one per agent.
    """
    if self._state == environment.StepType.LAST:
      return self.reset()

    skip = not self._ensure_available_actions
    actions = [f.transform_action(o.observation, a, skip_available=skip)
               for f, o, a in zip(self._features, self._obs, actions)]

    if not self._realtime:
      actions = self._apply_action_delays(actions)

    self._parallel.run((c.act, a) for c, a in zip(self._controllers, actions))

    self._state = environment.StepType.MID

    if self._realtime:
      for i, (action, obs) in enumerate(zip(actions, self._obs)):
        if action.ListFields() and self._last_act_game_loop[i] is None:
          self._last_act_game_loop[i] = obs.observation.game_loop

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
    for action, delay_fn, delayed_actions in zip(
        actions, self._action_delay_fns, self._delayed_actions):
      delay = delay_fn() if delay_fn else 1
      if delay > 1 and action.ListFields():  # Skip no-ops.
        game_loop = self._episode_steps + delay - 1

        # Randomized delays mean that 2 delay actions can be reversed.
        # Make sure that doesn't happen.
        if delayed_actions:
          game_loop = max(game_loop, delayed_actions[-1].game_loop)

        delayed_actions.append(_DelayedAction(game_loop, action))
        actions_now.append(None)  # Don't send an action this frame.
      else:
        actions_now.append(action)

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
      logging.warn("Received observation %d step(s) early: %d rather than %d.",
                   target_game_loop - game_loop, game_loop, target_game_loop)
      raise ValueError("The game didn't advance to the expected game loop")
    elif game_loop > target_game_loop and target_game_loop > 0:
      logging.warn("Received observation %d step(s) late: %d rather than %d.",
                   game_loop - target_game_loop, game_loop, target_game_loop)

    if self._realtime:
      # Track delays on executed actions.
      for i, obs in enumerate(self._obs):
        for action in obs.actions:
          if action.HasField("game_loop") and (
              self._last_act_game_loop[i] is not None):

            delay = action.game_loop - self._last_act_game_loop[i]

            # Delay zero is impossible (in that an action cannot possibly
            # execute on the same game loop as the observation which was used
            # to generate it), but we can see a delay of zero in this logic -
            # when another action is issued before an in-flight action is
            # executed. It is non-trivial to link issued to executed actions,
            # hence we simply ignore zero delays here.
            if delay:
              num_slots = len(self._action_delays[i])
              delay = min(delay, num_slots - 1)  # Cap to num buckets.
              self._action_delays[i][delay] += 1
              self._last_act_game_loop[i] = None

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
      portspicker.return_ports(self._ports)
      self._ports = None


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
