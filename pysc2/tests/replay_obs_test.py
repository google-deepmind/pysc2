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

from absl.testing import absltest
from future.builtins import range  # pylint: disable=redefined-builtin

from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import actions
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import units
from pysc2.tests import utils

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb

_EMPTY = 0
printable_unit_types = {
    _EMPTY: '.',
    units.Neutral.MineralField: 'm',
    units.Neutral.MineralField750: 'm',
    units.Neutral.SpacePlatformGeyser: 'G',
    units.Neutral.VespeneGeyser: 'G',
    units.Terran.Barracks: 'B',
    units.Terran.CommandCenter: 'C',
    units.Terran.SCV: 's',
    units.Terran.Marine: 'M',
    units.Terran.SupplyDepot: 'D',
}


def identity_function(name, args):
  return lambda _: actions.FUNCTIONS[name](*args)


def any_point(unit_type, obs):
  unit_layer = obs.feature_screen.unit_type
  y, x = (unit_layer == unit_type).nonzero()
  if not y.any():
    return None, None
  return [x[-1], y[-1]]


def avg_point(unit_type, obs):
  unit_layer = obs.feature_screen.unit_type
  y, x = (unit_layer == unit_type).nonzero()
  if not y.any():
    return None, None
  return [int(x.mean()), int(y.mean())]


def select(func, unit_type):
  return lambda o: actions.FUNCTIONS.select_point('select', func(unit_type, o))


class Config(object):
  """Holds the configuration options."""

  def __init__(self):
    # Environment.
    self.map_name = 'Flat64'
    screen_resolution = point.Point(32, 32)
    minimap_resolution = point.Point(32, 32)
    self.camera_width = 24
    self.random_seed = 42

    self.interface = sc_pb.InterfaceOptions(
        raw=True, score=True,
        feature_layer=sc_pb.SpatialCameraSetup(width=self.camera_width))
    screen_resolution.assign_to(self.interface.feature_layer.resolution)
    minimap_resolution.assign_to(
        self.interface.feature_layer.minimap_resolution)

    # Hard code an action sequence.
    # TODO(petkoig): Consider whether the Barracks and Supply Depot positions
    # need to be dynamically determined.
    self.actions = {
        507: select(any_point, units.Terran.SCV),
        963: identity_function('Build_SupplyDepot_screen', ['now', [25, 15]]),
        1152: select(avg_point, units.Terran.CommandCenter),
        1320: identity_function('Train_SCV_quick', ['now']),
        1350: identity_function('Train_SCV_quick', ['now']),
        1393: identity_function('Train_SCV_quick', ['now']),
        1437: identity_function('Train_SCV_quick', ['now']),
        1522: select(any_point, units.Terran.SCV),
        1548: identity_function('Build_Barracks_screen', ['now', [25, 25]]),
        1752: select(avg_point, units.Terran.CommandCenter),
        1937: identity_function('Train_SCV_quick', ['now']),
        2400: select(avg_point, units.Terran.Barracks),
        2700: identity_function('Train_Marine_quick', ['now']),
        3300: select(any_point, units.Terran.Marine),
    }
    self.num_observations = max(self.actions.keys()) + 2
    self.player_id = 1


def _obs_string(obs):
  unit_type = obs.feature_screen.unit_type
  selected = obs.feature_screen.selected
  max_y, max_x = unit_type.shape
  out = ''
  for y in range(max_y):
    started = False
    for x in range(max_x):
      s = selected[y, x]
      u = unit_type[y, x]
      if started and not s:
        out += ')'
      elif not started and s:
        out += '('
      else:
        out += ' '
      out += printable_unit_types.get(u, str(u))
      started = s
    if started:
      out += ')'
    out += '\n'
  return out


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

    self._sc2_proc = run_config.start(
        want_rgb=self._config.interface.HasField('render'))
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
    f = features.features_from_game_info(game_info=controller.game_info())

    observations = {}
    last_actions = []
    for _ in range(config.num_observations):
      raw_obs = controller.observe()
      o = raw_obs.observation
      obs = f.transform_obs(raw_obs)

      if raw_obs.action_errors:
        print('action errors:', raw_obs.action_errors)

      if o.game_loop == 2:
        # Center camera is initiated automatically by the game and reported
        # at frame 2.
        last_actions = [actions.FUNCTIONS.move_camera.id]

      self.assertEqual(last_actions, list(obs.last_actions))

      unit_type = obs.feature_screen.unit_type
      observations[o.game_loop] = unit_type

      if o.game_loop in config.actions:
        func = config.actions[o.game_loop](obs)

        print((' loop: %s ' % o.game_loop).center(80, '-'))
        print(_obs_string(obs))
        scv_y, scv_x = (units.Terran.SCV == unit_type).nonzero()
        print('scv locations: ', sorted(list(zip(scv_x, scv_y))))
        print('available actions: ', list(sorted(obs.available_actions)))
        print('Making action: %s' % (func,))

        # Ensure action is available.
        # If a build action is available, we have managed to target an SCV.
        self.assertIn(func.function, obs.available_actions)

        if (func.function in
            (actions.FUNCTIONS.Build_SupplyDepot_screen.id,
             actions.FUNCTIONS.Build_Barracks_screen.id)):
          # Ensure we can build on that position.
          x, y = func.arguments[1]
          self.assertEqual(_EMPTY, unit_type[y, x])

        action = f.transform_action(o, func)
        last_actions = [func.function]
        controller.act(action)
      else:
        last_actions = []

      controller.step()

    replay_data = controller.save_replay()
    return replay_data, observations

  def _process_replay(self, controller, observations, config):
    f = features.features_from_game_info(game_info=controller.game_info())

    while True:
      o = controller.observe()
      obs = f.transform_obs(o)

      if o.player_result:  # end of game
        break

      unit_type = obs.feature_screen.unit_type
      self.assertEqual(
          tuple(observations[o.observation.game_loop].flatten()),
          tuple(unit_type.flatten()))

      self.assertIn(len(o.actions), (0, 1), 'Expected 0 or 1 action')

      if o.actions:
        func = f.reverse_action(o.actions[0])

        # Action is reported one frame later.
        executed = config.actions.get(o.observation.game_loop - 1, None)

        executed_func = executed(obs) if executed else None
        print('%4d Sent:     %s' % (o.observation.game_loop, executed_func))
        print('%4d Returned: %s' % (o.observation.game_loop, func))

        if o.observation.game_loop == 2:
          # Center camera is initiated automatically by the game and reported
          # at frame 2.
          self.assertEqual(actions.FUNCTIONS.move_camera.id, func.function)
          continue

        self.assertEqual(func.function, executed_func.function)
        if func.function != actions.FUNCTIONS.select_point.id:
          # select_point likes to return Toggle instead of Select.
          self.assertEqual(func.arguments, executed_func.arguments)
        self.assertEqual(func.function, obs.last_actions[0])

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
  absltest.main()
