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
               host="127.0.0.1",
               host_port=None,
               lan_port=None,
               race=None,
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
               replay_dir=None,
               use_feature_units=False):
    """Create a SC2 Env that connects to a remote instance of the game.

    This assumes that the game is already up and running, and it only needs to
    join. You need some other script to launch the process and call
    RequestCreateGame. It also assumes that it's a multiplayer game, and that
    the ports are consecutive.

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
      host: Host where the server is running.
      host_port: The port for the host.
      lan_port: Where to connect to the other SC2 instance.
      race: Race for this agent.
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
      replay_dir: Directory to save a replay.
      use_feature_units: Whether to include feature unit data in observations.

    Raises:
      ValueError: if the agent_race, bot_race or difficulty are invalid.
      ValueError: if too many players are requested for a map.
      ValueError: if the resolutions aren't specified correctly.
    """
    if _only_use_kwargs:
      raise ValueError("All arguments must be passed as keyword arguments.")

    if not race:
      race = sc2_env.Race.random

    map_inst = map_name and maps.get(map_name)
    self._map_name = map_name

    self._num_agents = 1
    self._discount = discount
    self._step_mul = step_mul or (map_inst.step_mul if map_inst else 8)
    self._save_replay_episodes = 1 if replay_dir else 0
    self._replay_dir = replay_dir

    self._score_index = -1  # Win/loss only.
    self._score_multiplier = 1
    self._episode_length = 0  # No limit.

    self._run_config = run_configs.get()
    self._parallel = run_parallel.RunParallel()  # Needed for multiplayer.

    interface = self._get_interface(
        feature_screen_size, feature_screen_width, feature_screen_height,
        feature_minimap_size, feature_minimap_width, feature_minimap_height,
        rgb_screen_size, rgb_screen_width, rgb_screen_height, rgb_minimap_size,
        rgb_minimap_width, rgb_minimap_height, action_space,
        camera_width_world_units, use_feature_units, visualize)

    self._connect_remote(host, host_port, lan_port, race, map_inst, interface)

    self._finalize(interface, action_space, use_feature_units, visualize)

  def _connect_remote(self, host, host_port, lan_port, race, map_inst,
                      interface):
    """Make sure this stays synced with bin/play_vs_agent.py."""
    # Connect!
    logging.info("Connecting...")
    self._controllers = [remote_controller.RemoteController(host, host_port)]
    logging.info("Connected")

    # Create the join request.
    ports = [lan_port + p for p in range(4)]  # 2 * num players *in the game*.
    join = sc_pb.RequestJoinGame(options=interface)
    join.race = race
    join.shared_port = 0  # unused
    join.server_ports.game_port = ports.pop(0)
    join.server_ports.base_port = ports.pop(0)
    join.client_ports.add(game_port=ports.pop(0), base_port=ports.pop(0))

    if map_inst:
      run_config = run_configs.get()
      self._controllers[0].save_map(map_inst.path, map_inst.data(run_config))
    self._controllers[0].join_game(join)

  def _restart(self):
    # Can't restart since it's not clear how you'd coordinate that with the
    # other players.
    self._controllers[0].leave()
    raise RestartException("Can't restart")
