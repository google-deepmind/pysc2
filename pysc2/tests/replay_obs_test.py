#!/usr/bin/python
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
"""Test that a game and replay have equivalent observations and actions.

Here we verify that the observations processed by replays match the original
observations of the gameplay.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from future.builtins import range  # pylint: disable=redefined-builtin
import six

from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import actions
from pysc2.lib import features
from pysc2.lib import point
from pysc2.tests import utils

from absl.testing import absltest as basetest
from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb

# TODO(tewalds): define unit types in static data?
_EMPTY = 0
_COMMANDCENTER = 18
_SUPPLYDEPOT = 19
_BARRACKS = 21
_SCV = 45
_MINERALFIELD = 341
_GEYSER = 343
_MINERALFIELD750 = 483

printable_unit_types = {
    _EMPTY: '.',
    _COMMANDCENTER: 'C',
    _SUPPLYDEPOT: 'D',
    _BARRACKS: 'B',
    _SCV: 's',
    _MINERALFIELD: 'M',
    _GEYSER: 'G',
    _MINERALFIELD750: 'm',
}


class Config(object):
  """Holds the configuration options."""

  def __init__(self):
    # Environment.
    self.map_name = 'NewkirkPrecinct'
    self.screen_size_px = (32, 32)
    self.minimap_size_px = (32, 32)
    self.camera_width = 24
    self.random_seed = 42

    self.interface = sc_pb.InterfaceOptions(
        raw=True, score=True,
        feature_layer=sc_pb.SpatialCameraSetup(width=self.camera_width))
    resolution = point.Point(*self.screen_size_px)
    resolution.assign_to(self.interface.feature_layer.resolution)
    minimap_resolution = point.Point(*self.minimap_size_px)
    minimap_resolution.assign_to(
        self.interface.feature_layer.minimap_resolution)

    # Feature layer with the unit types.
    self.unit_type_id = features.SCREEN_FEATURES.unit_type.index
    self.num_observations = 3000
    self.player_id = 1

    # Hard code an action sequence.
    # TODO(petkoig): This is very brittle. A random seed reduces flakiness, but
    # isn't guaranteed to give the same actions between game versions. The pixel
    # coords should be computed at run-time, maybe with a trigger type system in
    # case build times also change.
    self.action_sequence = {
        507: ('select_point', [[1], [9, 18]]),  # Target an SCV.
        963: ('Build_SupplyDepot_screen', [[0], [4, 19]]),
        1152: ('select_point', [[0], [15, 13]]),  # Select the Command Center.
        1320: ('Train_SCV_quick', [[0]]),
        1350: ('Train_SCV_quick', [[0]]),
        1393: ('Train_SCV_quick', [[0]]),
        1437: ('Train_SCV_quick', [[0]]),
        1564: ('Train_SCV_quick', [[0]]),
        1602: ('Train_SCV_quick', [[0]]),
        1822: ('select_idle_worker', [[2]]),
        2848: ('Build_Barracks_screen', [[0], [22, 22]])
    }

    self.actions = {
        frame: self.action_to_function_call(*action)
        for frame, action in six.iteritems(self.action_sequence)
    }

  def action_to_function_call(self, name, args):
    return actions.FunctionCall(getattr(actions.FUNCTIONS, name).id, args)


def _layer_string(layer):
  return '\n'.join(' '.join(printable_unit_types.get(v, str(v))
                            for v in row) for row in layer)


class GameController(object):
  """Wrapper class for interacting with the game in play/replay mode."""

  def __init__(self, config):
    """Constructs the game controller object.

    Args:
      config: Interface configuration options.
    """
    self._config = config
    self._sc2_proc = None
    self._controller = None

    self._initialize()

  def _initialize(self):
    """Initialize play/replay connection."""
    run_config = run_configs.get()
    self._map_inst = maps.get(self._config.map_name)
    self._map_data = self._map_inst.data(run_config)

    self._sc2_proc = run_config.start()
    self._controller = self._sc2_proc.controller

  def start_replay(self, replay_data):
    start_replay = sc_pb.RequestStartReplay(
        replay_data=replay_data,
        map_data=self._map_data,
        options=self._config.interface,
        disable_fog=False,
        observed_player_id=self._config.player_id)
    self._controller.start_replay(start_replay)

  def create_game(self):
    create = sc_pb.RequestCreateGame(
        random_seed=self._config.random_seed,
        local_map=sc_pb.LocalMap(
            map_path=self._map_inst.path, map_data=self._map_data))
    create.player_setup.add(type=sc_pb.Participant)
    create.player_setup.add(
        type=sc_pb.Computer,
        race=sc_common.Terran,
        difficulty=sc_pb.VeryEasy)
    join = sc_pb.RequestJoinGame(
        race=sc_common.Terran,
        options=self._config.interface)

    self._controller.create_game(create)
    self._controller.join_game(join)

  @property
  def controller(self):
    return self._controller

  def close(self):
    """Close the controller connection."""
    if self._controller:
      self._controller.quit()
      self._controller = None
    if self._sc2_proc:
      self._sc2_proc.close()
      self._sc2_proc = None

  def __enter__(self):
    return self

  def __exit__(self, exception_type, exception_value, traceback):
    self.close()


class ReplayObsTest(utils.TestCase):

  def _get_replay_data(self, controller, config):
    """Runs a replay to get the replay data."""
    f = features.Features(controller.game_info())

    observations = {}
    for _ in range(config.num_observations):
      o = controller.observe().observation
      obs = f.transform_obs(o)

      unit_type = obs['screen'][config.unit_type_id]
      observations[o.game_loop] = unit_type

      if o.game_loop in config.actions:
        func = config.actions[o.game_loop]
        print(str(func))
        print(_layer_string(unit_type))
        scv_y, scv_x = (_SCV == unit_type).nonzero()
        print('scv locations: ', zip(scv_x, scv_y))

        # Ensure action is available.
        # If a build action is available, we have managed to target an SCV.
        self.assertIn(func.function, obs['available_actions'])

        if (config.actions[o.game_loop].function ==
            actions.FUNCTIONS.select_point.id):
          # Ensure we have selected an SCV or the command center.
          x, y = func.arguments[1]
          self.assertIn(unit_type[y, x], (_SCV, _COMMANDCENTER))
        elif (config.actions[o.game_loop].function in
              (actions.FUNCTIONS.Build_SupplyDepot_screen.id,
               actions.FUNCTIONS.Build_Barracks_screen.id)):
          # Ensure we can build on that position.
          x, y = func.arguments[1]
          self.assertEqual(_EMPTY, unit_type[y, x])

        action = f.transform_action(o, func)
        controller.act(action)

      controller.step()

    replay_data = controller.save_replay()
    return replay_data, observations

  def _process_replay(self, controller, observations, config):
    f = features.Features(controller.game_info())

    while True:
      o = controller.observe()
      obs = f.transform_obs(o.observation)

      if o.player_result:  # end of game
        break

      unit_type = obs['screen'][config.unit_type_id]
      self.assertEqual(
          tuple(observations[o.observation.game_loop].flatten()),
          tuple(unit_type.flatten()))

      self.assertIn(len(o.actions), (0, 1), 'Expected 0 or 1 action')

      if o.actions:
        func = f.reverse_action(o.actions[0])
        print('Action ', func.function)

        if o.observation.game_loop == 2:
          # Center camera is initiated automatically by the game and reported
          # at frame 2.
          self.assertEqual(actions.FUNCTIONS.move_camera.id, func.function)
          continue

        # Action is reported one frame later.
        executed = config.actions.get(o.observation.game_loop - 1, None)
        if not executed:
          self.assertEqual(
              actions.FUNCTIONS.move_camera.id, func.function,
              'A camera move to center the idle worker is expected.')
          continue

        print('Parsed and executed funcs: ', func, executed)
        self.assertEqual(func.function, executed.function)
        self.assertEqual(func.arguments, executed.arguments)

      controller.step()

    return observations

  def test_replay_observations_match(self):
    config = Config()

    with GameController(config) as game_controller:
      game_controller.create_game()
      replay_data, observations = self._get_replay_data(
          game_controller.controller, config)

      game_controller.start_replay(replay_data)
      self._process_replay(game_controller.controller, observations, config)


if __name__ == '__main__':
  basetest.main()
