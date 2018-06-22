# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Creates SC2 processes and games for remote agents to connect into."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import portspicker

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


class VsAgent(object):
  """Host a remote agent vs remote agent game.

  Starts two SC2 processes, one for each of two remote agents to connect to.
  Call create_game, then have the agents connect to their respective port in
  host_ports, specifying lan_ports in the join game request.

  Agents should leave the game once it has finished, then another game can
  be created. Note that failure of either agent to leave prior to creating
  the next game will lead to SC2 crashing.

  Best used as a context manager for simple and timely resource release.

  **NOTE THAT** currently re-connecting to the same SC2 process is flaky.
  If you experience difficulties the workaround is to only create one game
  per instantiation of VsAgent.
  """

  def __init__(self):
    self._num_agents = 2
    self._run_config = run_configs.get()
    self._processes = []
    self._controllers = []
    self._saved_maps = set()

    # Reserve LAN ports.
    self._lan_ports = portspicker.pick_unused_ports(self._num_agents * 2)

    # Start SC2 processes.
    for _ in range(self._num_agents):
      process = self._run_config.start(extra_ports=self._lan_ports)
      self._processes.append(process)
      self._controllers.append(process.controller)

  def __enter__(self):
    return self

  def __exit__(self, exception_type, exception_value, traceback):
    self.close()

  def __del__(self):
    self.close()

  def create_game(self, map_name):
    """Create a game for the agents to join.

    Args:
      map_name: The map to use.
    """
    map_inst = maps.get(map_name)
    map_data = map_inst.data(self._run_config)
    if map_name not in self._saved_maps:
      for controller in self._controllers:
        controller.save_map(map_inst.path, map_data)
      self._saved_maps.add(map_name)

    # Form the create game message.
    create = sc_pb.RequestCreateGame(
        local_map=sc_pb.LocalMap(map_path=map_inst.path),
        disable_fog=False)

    # Set up for two agents.
    for _ in range(self._num_agents):
      create.player_setup.add(type=sc_pb.Participant)

    # Create the game.
    self._controllers[0].create_game(create)

  @property
  def hosts(self):
    """The hosts that the remote agents should connect to."""
    return [process.host for process in self._processes]

  @property
  def host_ports(self):
    """The WebSocket ports that the remote agents should connect to."""
    return [process.port for process in self._processes]

  @property
  def lan_ports(self):
    """The LAN ports which the remote agents should specify when joining."""
    return self._lan_ports

  def close(self):
    """Shutdown and free all resources."""
    for controller in self._controllers:
      controller.quit()
    self._controllers = []

    for process in self._processes:
      process.close()
    self._processes = []

    portspicker.return_ports(self._lan_ports)
    self._lan_ports = []


class VsBot(object):
  """Host a remote agent vs bot game.

  Starts a single SC2 process. Call create_game, then have the agent connect
  to host_port.

  The agent should leave the game once it has finished, then another game can
  be created. Note that failure of the agent to leave prior to creating
  the next game will lead to SC2 crashing.

  Best used as a context manager for simple and timely resource release.

  **NOTE THAT** currently re-connecting to the same SC2 process is flaky.
  If you experience difficulties the workaround is to only create one game
  per instantiation of VsBot.
  """

  def __init__(self):
    # Start the SC2 process.
    self._run_config = run_configs.get()
    self._process = self._run_config.start()
    self._controller = self._process.controller
    self._saved_maps = set()

  def __enter__(self):
    return self

  def __exit__(self, exception_type, exception_value, traceback):
    self.close()

  def __del__(self):
    self.close()

  def create_game(
      self,
      map_name,
      bot_difficulty=sc_pb.VeryEasy,
      bot_race=sc_common.Random,
      bot_first=False):
    """Create a game, one remote agent vs the specified bot.

    Args:
      map_name: The map to use.
      bot_difficulty: The difficulty of the bot to play against.
      bot_race: The race for the bot.
      bot_first: Whether the bot should be player 1 (else is player 2).
    """
    self._controller.ping()

    # Form the create game message.
    map_inst = maps.get(map_name)
    map_data = map_inst.data(self._run_config)
    if map_name not in self._saved_maps:
      self._controller.save_map(map_inst.path, map_data)
      self._saved_maps.add(map_name)

    create = sc_pb.RequestCreateGame(
        local_map=sc_pb.LocalMap(map_path=map_inst.path, map_data=map_data),
        disable_fog=False)

    # Set up for one bot, one agent.
    if not bot_first:
      create.player_setup.add(type=sc_pb.Participant)

    create.player_setup.add(
        type=sc_pb.Computer, race=bot_race, difficulty=bot_difficulty)

    if bot_first:
      create.player_setup.add(type=sc_pb.Participant)

    # Create the game.
    self._controller.create_game(create)

  @property
  def host(self):
    """The host that the remote agent should connect to."""
    return self._process.host

  @property
  def host_port(self):
    """The WebSocket port that the remote agent should connect to."""
    return self._process.port

  def close(self):
    """Shutdown and free all resources."""
    if self._controller is not None:
      self._controller.quit()
      self._controller = None
    if self._process is not None:
      self._process.close()
      self._process = None
