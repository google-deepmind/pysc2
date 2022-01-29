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
"""Test the apm values of various actions."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random

from absl import app
from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import actions
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import units

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import error_pb2 as sc_error
from s2clientprotocol import sc2api_pb2 as sc_pb


def get_units(obs, filter_fn=None, owner=None, unit_type=None, tag=None):
  """Return a dict of units that match the filter."""
  if unit_type and not isinstance(unit_type, (list, tuple)):
    unit_type = (unit_type,)
  return {u.tag: u for u in obs.observation.raw_data.units
          if ((filter_fn is None or filter_fn(u)) and
              (owner is None or u.owner == owner) and
              (unit_type is None or u.unit_type in unit_type) and
              (tag is None or u.tag == tag))}


def get_unit(*args, **kwargs):
  """Return the first unit that matches, or None."""
  try:
    return next(iter(get_units(*args, **kwargs).values()))
  except StopIteration:
    return None


def _xy_locs(mask):
  """Mask should be a set of bools from comparison with a feature layer."""
  ys, xs = mask.nonzero()
  return [point.Point(x, y) for x, y in zip(xs, ys)]


class Env(object):
  """Test the apm values of various actions."""

  def __init__(self):
    run_config = run_configs.get()
    map_inst = maps.get("Flat64")
    self._map_path = map_inst.path
    self._map_data = map_inst.data(run_config)

    self._sc2_proc = run_config.start(want_rgb=False)
    self._controller = self._sc2_proc.controller
    self._summary = []
    self._features = None  # type: features.Features

  def close(self):
    self._controller.quit()
    self._sc2_proc.close()

    print(" apm name")
    for name, info in self._summary:
      print("%4d %s" % (info.player_info[0].player_apm, name))

  def __enter__(self):
    return self

  def __exit__(self, unused_exception_type, unused_exc_value, unused_traceback):
    self.close()

  def __del__(self):
    self.close()

  def step(self, count=22):
    self._controller.step(count)
    return self._controller.observe()

  def fl_obs(self, obs):
    return self._features.transform_obs(obs)

  def raw_unit_command(self, ability_id, unit_tags, pos=None, target=None):
    """Send a raw unit command."""
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
    response = self._controller.act(action)
    for result in response.result:
      assert result == sc_error.Success

  def fl_action(self, obs, act, *args):
    return self._controller.act(self._features.transform_action(
        obs.observation, actions.FUNCTIONS[act](*args), skip_available=True))

  def check_apm(self, name):
    """Set up a game, yield, then check the apm in the replay."""
    interface = sc_pb.InterfaceOptions(raw=True, score=False)
    interface.feature_layer.width = 24
    interface.feature_layer.resolution.x = 64
    interface.feature_layer.resolution.y = 64
    interface.feature_layer.minimap_resolution.x = 64
    interface.feature_layer.minimap_resolution.y = 64

    create = sc_pb.RequestCreateGame(
        random_seed=1, local_map=sc_pb.LocalMap(map_path=self._map_path,
                                                map_data=self._map_data))
    create.player_setup.add(type=sc_pb.Participant)
    create.player_setup.add(type=sc_pb.Computer, race=sc_common.Protoss,
                            difficulty=sc_pb.VeryEasy)

    join = sc_pb.RequestJoinGame(race=sc_common.Protoss, options=interface)

    self._controller.create_game(create)
    self._controller.join_game(join)

    self._info = self._controller.game_info()
    self._features = features.features_from_game_info(
        self._info, use_feature_units=True, use_raw_units=True)
    self._map_size = point.Point.build(self._info.start_raw.map_size)

    for i in range(60):
      yield i, self.step()

    data = self._controller.save_replay()
    replay_info = self._controller.replay_info(data)
    self._summary.append((name, replay_info))


def main(unused_argv):
  env = Env()

  def rand_fl_coord():
    return (point.Point.unit_rand() * 64).floor()

  def rand_world_coord():
    return (point.Point.unit_rand() * 20).floor() + 20

  def random_probe_loc(obs):
    return random.choice(_xy_locs(
        env.fl_obs(obs).feature_screen.unit_type == units.Protoss.Probe))

  def random_probe_tag(obs):
    return random.choice(get_units(obs, unit_type=units.Protoss.Probe).keys())

  for i, obs in env.check_apm("no-op"):
    pass

  for i, obs in env.check_apm("fl stop, single probe"):
    if i == 0:
      env.fl_action(obs, "select_point", "select", random_probe_loc(obs))
    env.fl_action(obs, "Stop_quick", "now")

  for i, obs in env.check_apm("fl smart, single probe, random location"):
    if i == 0:
      env.fl_action(obs, "select_point", "select", random_probe_loc(obs))
    env.fl_action(obs, "Smart_screen", "now", rand_fl_coord())

  for i, obs in env.check_apm("fl move, single probe, random location"):
    if i == 0:
      env.fl_action(obs, "select_point", "select", random_probe_loc(obs))
    env.fl_action(obs, "Move_screen", "now", rand_fl_coord())

  for i, obs in env.check_apm("fl stop, random probe"):
    env.fl_action(obs, "select_point", "select", random_probe_loc(obs))
    env.fl_action(obs, "Stop_quick", "now")

  for i, obs in env.check_apm("fl move, random probe, random location"):
    env.fl_action(obs, "select_point", "select", random_probe_loc(obs))
    env.fl_action(obs, "Move_screen", "now", rand_fl_coord())

  for i, obs in env.check_apm("raw stop, random probe"):
    env.raw_unit_command("Stop_quick", random_probe_tag(obs))

  for i, obs in env.check_apm("raw move, random probe, random location"):
    env.raw_unit_command("Move_screen", random_probe_tag(obs),
                         rand_world_coord())

  probe = None
  for i, obs in env.check_apm("raw move, single probe, random location"):
    if not probe:
      probe = random_probe_tag(obs)
    env.raw_unit_command("Move_screen", probe, rand_world_coord())


if __name__ == "__main__":
  app.run(main)
