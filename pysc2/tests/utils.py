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
"""Unit test tools."""

import functools

from absl import logging
from absl.testing import absltest

from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import actions
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import portspicker
from pysc2.lib import run_parallel
from pysc2.lib import stopwatch

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import debug_pb2 as sc_debug
from s2clientprotocol import error_pb2 as sc_error
from s2clientprotocol import raw_pb2 as sc_raw
from s2clientprotocol import sc2api_pb2 as sc_pb


class TestCase(absltest.TestCase):
  """A test base class that enables stopwatch profiling."""

  def setUp(self):
    super(TestCase, self).setUp()
    stopwatch.sw.clear()
    stopwatch.sw.enable()

  def tearDown(self):
    super(TestCase, self).tearDown()
    s = str(stopwatch.sw)
    if s:
      logging.info("Stop watch profile:\n%s", s)
    stopwatch.sw.disable()


def get_units(obs, filter_fn=None, owner=None, unit_type=None, tag=None):
  """Return a dict of units that match the filter."""
  if unit_type and not isinstance(unit_type, (list, tuple)):
    unit_type = (unit_type,)
  out = {}
  for u in obs.observation.raw_data.units:
    if ((filter_fn is None or filter_fn(u)) and
        (owner is None or u.owner == owner) and
        (unit_type is None or u.unit_type in unit_type) and
        (tag is None or u.tag == tag)):
      out[u.tag] = u
  return out


def get_unit(*args, **kwargs):
  """Return the first unit that matches, or None."""
  try:
    return next(iter(get_units(*args, **kwargs).values()))
  except StopIteration:
    return None


def xy_locs(mask):
  """Mask should be a set of bools from comparison with a feature layer."""
  ys, xs = mask.nonzero()
  return [point.Point(x, y) for x, y in zip(xs, ys)]


def only_in_game(func):
  @functools.wraps(func)
  def decorator(self, *args, **kwargs):
    if self.in_game:  # pytype: disable=attribute-error
      return func(self, *args, **kwargs)
  return decorator


class GameReplayTestCase(TestCase):
  """Tests that run through a game, then verify it still works in a replay."""

  @staticmethod
  def setup(**kwargs):
    """A decorator to replace unittest.setUp so it can take args."""
    def decorator(func):  # pylint: disable=missing-docstring
      @functools.wraps(func)
      def _setup(self):  # pylint: disable=missing-docstring
        def test_in_game():
          print((" %s: Starting game " % func.__name__).center(80, "-"))
          self.start_game(**kwargs)
          func(self)

        def test_in_replay():
          self.start_replay()
          print((" %s: Starting replay " % func.__name__).center(80, "-"))
          func(self)

        try:
          test_in_game()
          test_in_replay()
        finally:
          self.close()
      return _setup
    return decorator

  def start_game(self, show_cloaked=True, disable_fog=False, players=2):
    """Start a multiplayer game with options."""
    self._disable_fog = disable_fog
    run_config = run_configs.get()
    self._parallel = run_parallel.RunParallel()  # Needed for multiplayer.
    map_inst = maps.get("Flat64")
    self._map_data = map_inst.data(run_config)

    self._ports = portspicker.pick_unused_ports(4) if players == 2 else []
    self._sc2_procs = [run_config.start(extra_ports=self._ports, want_rgb=False)
                       for _ in range(players)]
    self._controllers = [p.controller for p in self._sc2_procs]

    if players == 2:
      for c in self._controllers:  # Serial due to a race condition on Windows.
        c.save_map(map_inst.path, self._map_data)

    self._interface = sc_pb.InterfaceOptions()
    self._interface.raw = True
    self._interface.raw_crop_to_playable_area = True
    self._interface.show_cloaked = show_cloaked
    self._interface.score = False
    self._interface.feature_layer.width = 24
    self._interface.feature_layer.resolution.x = 64
    self._interface.feature_layer.resolution.y = 64
    self._interface.feature_layer.minimap_resolution.x = 64
    self._interface.feature_layer.minimap_resolution.y = 64

    create = sc_pb.RequestCreateGame(
        random_seed=1, disable_fog=self._disable_fog,
        local_map=sc_pb.LocalMap(map_path=map_inst.path))
    for _ in range(players):
      create.player_setup.add(type=sc_pb.Participant)
    if players == 1:
      create.local_map.map_data = self._map_data
      create.player_setup.add(type=sc_pb.Computer, race=sc_common.Random,
                              difficulty=sc_pb.VeryEasy)

    join = sc_pb.RequestJoinGame(race=sc_common.Protoss,
                                 options=self._interface)
    if players == 2:
      join.shared_port = 0  # unused
      join.server_ports.game_port = self._ports[0]
      join.server_ports.base_port = self._ports[1]
      join.client_ports.add(game_port=self._ports[2],
                            base_port=self._ports[3])

    self._controllers[0].create_game(create)
    self._parallel.run((c.join_game, join) for c in self._controllers)

    self._info = self._controllers[0].game_info()
    self._features = features.features_from_game_info(
        self._info, use_raw_units=True)

    self._map_size = point.Point.build(self._info.start_raw.map_size)
    print("Map size:", self._map_size)
    self.in_game = True
    self.step()  # Get into the game properly.

  def start_replay(self):
    """Switch from the game to a replay."""
    self.step(300)
    replay_data = self._controllers[0].save_replay()
    self._parallel.run(c.leave for c in self._controllers)
    for player_id, controller in enumerate(self._controllers):
      controller.start_replay(sc_pb.RequestStartReplay(
          replay_data=replay_data,
          map_data=self._map_data,
          options=self._interface,
          disable_fog=self._disable_fog,
          observed_player_id=player_id+1))
    self.in_game = False
    self.step()  # Get into the game properly.

  def close(self):  # Instead of tearDown.
    """Shut down the SC2 instances."""
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
    if hasattr(self, "_parallel") and self._parallel is not None:
      self._parallel.shutdown()
      self._parallel = None

  def step(self, count=4):
    return self._parallel.run((c.step, count) for c in self._controllers)

  def observe(self, disable_fog=False):
    return self._parallel.run((c.observe, disable_fog)  # pytype: disable=attribute-error
                              for c in self._controllers)  # pytype: disable=attribute-error

  @only_in_game
  def move_camera(self, x, y):
    action = sc_pb.Action()
    action.action_raw.camera_move.center_world_space.x = x
    action.action_raw.camera_move.center_world_space.y = y
    return self._parallel.run((c.act, action) for c in self._controllers)  # pytype: disable=attribute-error

  @only_in_game
  def raw_unit_command(self, player, ability_id, unit_tags, pos=None,
                       target=None):
    """Issue a raw unit command."""
    if isinstance(ability_id, str):
      ability_id = actions.FUNCTIONS[ability_id].ability_id
    action = sc_pb.Action()
    cmd = action.action_raw.unit_command
    cmd.ability_id = ability_id
    if isinstance(unit_tags, (list, tuple)):
      cmd.unit_tags.extend(unit_tags)
    else:
      cmd.unit_tags.append(unit_tags)
    if pos:
      cmd.target_world_space_pos.x = pos[0]
      cmd.target_world_space_pos.y = pos[1]
    elif target:
      cmd.target_unit_tag = target
    response = self._controllers[player].act(action)  # pytype: disable=attribute-error
    for result in response.result:
      self.assertEqual(result, sc_error.Success)

  @only_in_game
  def debug(self, player=0, **kwargs):
    self._controllers[player].debug([sc_debug.DebugCommand(**kwargs)])  # pytype: disable=attribute-error

  def god(self):
    """Stop the units from killing each other so we can observe them."""
    self.debug(0, game_state=sc_debug.god)
    self.debug(1, game_state=sc_debug.god)

  def create_unit(self, unit_type, owner, pos, quantity=1):
    if isinstance(pos, tuple):
      pos = sc_common.Point2D(x=pos[0], y=pos[1])
    elif isinstance(pos, sc_common.Point):
      pos = sc_common.Point2D(x=pos.x, y=pos.y)
    return self.debug(create_unit=sc_debug.DebugCreateUnit(
        unit_type=unit_type, owner=owner, pos=pos, quantity=quantity))

  def kill_unit(self, unit_tags):
    if not isinstance(unit_tags, (list, tuple)):
      unit_tags = [unit_tags]
    return self.debug(kill_unit=sc_debug.DebugKillUnit(tag=unit_tags))

  def set_energy(self, tag, energy):
    self.debug(unit_value=sc_debug.DebugSetUnitValue(
        unit_value=sc_debug.DebugSetUnitValue.Energy, value=energy,
        unit_tag=tag))

  def assert_point(self, proto_pos, pos):
    self.assertAlmostEqual(proto_pos.x, pos[0])
    self.assertAlmostEqual(proto_pos.y, pos[1])

  def assert_layers(self, layers, pos, **kwargs):
    for k, v in sorted(kwargs.items()):
      self.assertEqual(layers[k, pos.y, pos.x], v,
                       msg="%s[%s, %s]: expected: %s, got: %s" % (
                           k, pos.y, pos.x, v, layers[k, pos.y, pos.x]))

  def assert_unit(self, unit, **kwargs):
    self.assertTrue(unit)
    self.assertIsInstance(unit, sc_raw.Unit)
    for k, v in sorted(kwargs.items()):
      if k == "pos":
        self.assert_point(unit.pos, v)
      else:
        self.assertEqual(getattr(unit, k), v,
                         msg="%s: expected: %s, got: %s\n%s" % (
                             k, v, getattr(unit, k), unit))
