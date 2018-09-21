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
"""A Starcraft II environment for playing using remote SC2 instances."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
from absl import logging
import time

from pysc2 import maps
from pysc2 import run_configs
from pysc2.env import sc2_env
from pysc2.lib import remote_controller
from pysc2.lib import run_parallel

from s2clientprotocol import sc2api_pb2 as sc_pb


class RestartException(Exception):
  pass


class RemoteSC2Env(sc2_env.SC2Env):
  """A Remote Starcraft II environment for playing vs other agents or humans.

  Unlike SC2Env, this doesn't actually start any instances and only connects
  to a remote instance.

  This assumes a 2 player game, and works best with play_vs_agent.py.
  """

  def __init__(self,  # pylint: disable=invalid-name
               _only_use_kwargs=None,
               map_name=None,
               save_map=True,
               host="127.0.0.1",
               host_port=None,
               lan_port=None,
               race=None,
               name="<unknown>",
               agent_interface_format=None,
               discount=1.,
               visualize=False,
               step_mul=None,
               realtime=False,
               replay_dir=None,
               replay_prefix=None):
    """Create a SC2 Env that connects to a remote instance of the game.

    This assumes that the game is already up and running, and that it only
    needs to join the game - and leave once the game has ended. You need some
    other script to launch the SC2 process and call RequestCreateGame. Note
    that you must call close to leave the game when finished. Not doing so
    will lead to issues when attempting to create another game on the same
    SC2 process.

    This class assumes that the game is multiplayer. LAN ports may be
    specified either as a base port (from which the others will be implied),
    or as an explicit list.

    You must specify an agent_interface_format. See the `AgentInterfaceFormat`
    documentation for further detail.

    Args:
      _only_use_kwargs: Don't pass args, only kwargs.
      map_name: Name of a SC2 map. Run bin/map_list to get the full list of
          known maps. Alternatively, pass a Map instance. Take a look at the
          docs in maps/README.md for more information on available maps.
      save_map: Whether to save map data before joining the game.
      host: Host where the SC2 process we're connecting to is running.
      host_port: The WebSocket port for the SC2 process we're connecting to.
      lan_port: Either an explicit sequence of LAN ports corresponding to
          [server game port, ...base port, client game port, ...base port],
          or an int specifying base port - equivalent to specifying the
          sequence [lan_port, lan_port+1, lan_port+2, lan_port+3].
      race: Race for this agent.
      name: The name of this agent, for saving in the replay.
      agent_interface_format: AgentInterfaceFormat object describing the
          format of communication between the agent and the environment.
      discount: Returned as part of the observation.
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
      replay_dir: Directory to save a replay.
      replay_prefix: An optional prefix to use when saving replays.

    Raises:
      ValueError: if the race is invalid.
      ValueError: if the resolutions aren't specified correctly.
      ValueError: if lan_port is a sequence but its length != 4.
    """
    if _only_use_kwargs:
      raise ValueError("All arguments must be passed as keyword arguments.")

    if agent_interface_format is None:
      raise ValueError("Please specify agent_interface_format.")

    if not race:
      race = sc2_env.Race.random

    map_inst = map_name and maps.get(map_name)
    self._map_name = map_name

    self._num_agents = 1
    self._discount = discount
    self._step_mul = step_mul or (map_inst.step_mul if map_inst else 8)
    self._realtime = realtime
    self._last_step_time = None
    self._save_replay_episodes = 1 if replay_dir else 0
    self._next_replay_save_time = time.time() + 60.0
    self._replay_dir = replay_dir
    self._replay_prefix = replay_prefix

    self._score_index = -1  # Win/loss only.
    self._score_multiplier = 1
    self._episode_length = 0  # No limit.
    self._ensure_available_actions = False
    self._discount_zero_after_timeout = False

    self._run_config = run_configs.get()
    self._parallel = run_parallel.RunParallel()  # Needed for multiplayer.
    self._in_game = False

    interface = self._get_interface(
        agent_interface_format=agent_interface_format, require_raw=visualize)

    if isinstance(lan_port, collections.Sequence):
      if len(lan_port) != 4:
        raise ValueError("lan_port sequence must be of length 4")
      ports = lan_port[:]
    else:
      ports = [lan_port + p for p in range(4)]  # 2 * num players *in the game*.

    self._connect_remote(
        host, host_port, ports, race, name, map_inst, save_map, interface)

    self._finalize([agent_interface_format], [interface], visualize)

  def step(self, actions, step_mul=None):
    result = super(RemoteSC2Env, self).step(actions, step_mul)

    current_time = time.time()
    if self._realtime and current_time > self._next_replay_save_time:
      # Currently we don't get a player result when a realtime game ends,
      # which means no replay is saved. As a temporary workaround, save
      # a replay every minute of the game when playing remote.
      # TODO(b/115466611): player_results should be returned in realtime mode
      logging.info("Saving interim replay...")
      self.save_replay(self._replay_dir, self._replay_prefix)
      self._next_replay_save_time = current_time + 60.0

    return result

  def close(self):
    # Leave the game so that another may be created in the same SC2 process.
    if self._in_game:
      logging.info("Leaving game.")
      self._controllers[0].leave()
      self._in_game = False
      logging.info("Left game.")

    # We don't own the SC2 process, we shouldn't call quit in the super class.
    self._controllers = None

    super(RemoteSC2Env, self).close()

  def _connect_remote(self, host, host_port, lan_ports, race, name, map_inst,
                      save_map, interface):
    """Make sure this stays synced with bin/agent_remote.py."""
    # Connect!
    logging.info("Connecting...")
    self._controllers = [remote_controller.RemoteController(host, host_port)]
    logging.info("Connected")

    if map_inst and save_map:
      run_config = run_configs.get()
      self._controllers[0].save_map(map_inst.path, map_inst.data(run_config))

    # Create the join request.
    join = sc_pb.RequestJoinGame(options=interface)
    join.race = race
    join.player_name = name
    join.shared_port = 0  # unused
    join.server_ports.game_port = lan_ports.pop(0)
    join.server_ports.base_port = lan_ports.pop(0)
    join.client_ports.add(
        game_port=lan_ports.pop(0), base_port=lan_ports.pop(0))

    logging.info("Joining game.")
    self._controllers[0].join_game(join)
    self._in_game = True
    logging.info("Game joined.")

  def _restart(self):
    # Can't restart since it's not clear how you'd coordinate that with the
    # other players.
    raise RestartException("Can't restart")
