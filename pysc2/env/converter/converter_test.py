# Copyright 2021 DeepMind Technologies Ltd. All rights reserved.
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

from absl.testing import absltest
from absl.testing import parameterized
import numpy as np
from pysc2.env.converter import converter
from pysc2.env.converter.proto import converter_pb2
from s2clientprotocol import common_pb2
from s2clientprotocol import raw_pb2
from s2clientprotocol import sc2api_pb2
from s2clientprotocol import spatial_pb2

NUM_ACTION_TYPES = 539
MAX_UNIT_COUNT = 16
NUM_UNIT_TYPES = 243
NUM_UNIT_FEATURES = 40
NUM_UPGRADES = 40
NUM_UPGRADE_TYPES = 86
MAX_UNIT_SELECTION_SIZE = 16
MAP_SIZE = 128
RAW_RESOLUTION = 128
MINIMAP_SIZE = 64
SCREEN_SIZE = 96


def _make_dummy_env_info():
  return converter_pb2.EnvironmentInfo(
      game_info=sc2api_pb2.ResponseGameInfo(
          player_info=[
              sc2api_pb2.PlayerInfo(
                  player_id=1, type=sc2api_pb2.PlayerType.Participant),
              sc2api_pb2.PlayerInfo(
                  player_id=2, type=sc2api_pb2.PlayerType.Participant),
          ],
          start_raw=raw_pb2.StartRaw(
              map_size=common_pb2.Size2DI(x=MAP_SIZE, y=MAP_SIZE))))


def _make_converter_settings_common(**kwargs):
  return converter_pb2.ConverterSettings(
      num_action_types=NUM_ACTION_TYPES,
      num_unit_types=NUM_UNIT_TYPES,
      num_upgrade_types=NUM_UPGRADE_TYPES,
      max_num_upgrades=NUM_UPGRADES,
      minimap=common_pb2.Size2DI(x=MINIMAP_SIZE, y=MINIMAP_SIZE),
      minimap_features=['height_map', 'visibility_map'],
      add_opponent_features=True,
      **kwargs)


def _make_converter_settings(mode: str):
  if mode == 'visual':
    return _make_converter_settings_common(
        visual_settings=converter_pb2.ConverterSettings.VisualSettings(
            screen=common_pb2.Size2DI(x=SCREEN_SIZE, y=SCREEN_SIZE),
            screen_features=['height_map', 'player_relative']))
  else:
    return _make_converter_settings_common(
        raw_settings=converter_pb2.ConverterSettings.RawSettings(
            resolution=common_pb2.Size2DI(x=RAW_RESOLUTION, y=RAW_RESOLUTION),
            num_unit_features=NUM_UNIT_FEATURES,
            max_unit_count=MAX_UNIT_COUNT,
            max_unit_selection_size=MAX_UNIT_SELECTION_SIZE,
            enable_action_repeat=True))


def _make_observation():
  return converter_pb2.Observation(
      player=sc2api_pb2.ResponseObservation(
          observation=sc2api_pb2.Observation(
              player_common=sc2api_pb2.PlayerCommon(player_id=1),
              feature_layer_data=spatial_pb2.ObservationFeatureLayer(
                  minimap_renders=spatial_pb2.FeatureLayersMinimap(
                      height_map=common_pb2.ImageData(
                          bits_per_pixel=8,
                          size=common_pb2.Size2DI(
                              x=MINIMAP_SIZE, y=MINIMAP_SIZE),
                          data=bytes(bytearray(MINIMAP_SIZE * MINIMAP_SIZE))),
                      visibility_map=common_pb2.ImageData(
                          bits_per_pixel=8,
                          size=common_pb2.Size2DI(
                              x=MINIMAP_SIZE, y=MINIMAP_SIZE),
                          data=bytes(bytearray(MINIMAP_SIZE * MINIMAP_SIZE)))),
                  renders=spatial_pb2.FeatureLayers(
                      height_map=common_pb2.ImageData(
                          bits_per_pixel=8,
                          size=common_pb2.Size2DI(x=SCREEN_SIZE, y=SCREEN_SIZE),
                          data=bytes(bytearray(SCREEN_SIZE * SCREEN_SIZE))),
                      player_relative=common_pb2.ImageData(
                          bits_per_pixel=8,
                          size=common_pb2.Size2DI(x=SCREEN_SIZE, y=SCREEN_SIZE),
                          data=bytes(bytearray(SCREEN_SIZE * SCREEN_SIZE))))))))


class RawConverterTest(absltest.TestCase):

  def test_action_spec(self):
    cvr = converter.Converter(
        settings=_make_converter_settings('raw'),
        environment_info=_make_dummy_env_info())

    action_spec = cvr.action_spec()
    self.assertCountEqual(action_spec.keys(), [
        'queued', 'repeat', 'target_unit_tag', 'unit_tags', 'world', 'delay',
        'function'
    ])

    for k, v in action_spec.items():
      self.assertEqual(k, v.name, msg=k)
      self.assertEqual(v.dtype, np.int32, msg=k)
      self.assertEqual(
          v.shape, (MAX_UNIT_SELECTION_SIZE,) if k == 'unit_tags' else (),
          msg=k)
      self.assertEqual(v.minimum, (1,) if k == 'delay' else (0,), msg=k)

    for k, v in {
        'queued': 1,
        'repeat': 2,
        'target_unit_tag': MAX_UNIT_COUNT - 1,
        'world': RAW_RESOLUTION * RAW_RESOLUTION - 1,
        'delay': 127,
        'function': NUM_ACTION_TYPES - 1
    }.items():
      self.assertEqual(action_spec[k].maximum, (v,), msg=k)

  def test_action_move_camera(self):
    cvr = converter.Converter(
        settings=_make_converter_settings('raw'),
        environment_info=_make_dummy_env_info())

    raw_move_camera = {'delay': 17, 'function': 168, 'world': 131}

    action = cvr.convert_action(raw_move_camera)

    expected = converter_pb2.Action(
        delay=17,
        request_action=sc2api_pb2.RequestAction(actions=[
            sc2api_pb2.Action(
                action_raw=raw_pb2.ActionRaw(
                    camera_move=raw_pb2.ActionRawCameraMove(
                        center_world_space=common_pb2.Point(x=3.5, y=126.5))))
        ]))

    self.assertEqual(expected.SerializeToString(), action.SerializeToString())

  def test_action_smart_unit(self):
    cvr = converter.Converter(
        settings=_make_converter_settings('raw'),
        environment_info=_make_dummy_env_info())

    raw_smart_unit = {
        'delay': 31,
        'function': 1,
        'queued': 0,
        'repeat': 0,
        'unit_tags': [4],
        'world': 5
    }
    action = cvr.convert_action(raw_smart_unit)

    expected = converter_pb2.Action(
        delay=31,
        request_action=sc2api_pb2.RequestAction(actions=[
            sc2api_pb2.Action(
                action_raw=raw_pb2.ActionRaw(
                    unit_command=raw_pb2.ActionRawUnitCommand(
                        ability_id=1,
                        unit_tags=(4,),
                        queue_command=False,
                        target_world_space_pos=common_pb2.Point2D(
                            x=5.5, y=127.5))))
        ]))

    self.assertEqual(expected.SerializeToString(), action.SerializeToString())


class VisualConverterTest(absltest.TestCase):

  def test_action_spec(self):
    cvr = converter.Converter(
        settings=_make_converter_settings('visual'),
        environment_info=_make_dummy_env_info())

    action_spec = cvr.action_spec()
    self.assertCountEqual(action_spec, [
        'build_queue_id', 'control_group_act', 'control_group_id', 'minimap',
        'queued', 'screen', 'screen2', 'select_add', 'select_point_act',
        'select_unit_act', 'select_unit_id', 'select_worker', 'unload_id',
        'delay', 'function'
    ])

    for k, v in action_spec.items():
      self.assertEqual(k, v.name, msg=k)
      self.assertEqual(v.dtype, np.int32, msg=k)
      self.assertEqual(v.shape, (), msg=k)
      self.assertEqual(v.minimum, (1,) if (k == 'delay') else (0,), msg=k)

    for k, v in {
        'build_queue_id': 9,
        'control_group_act': 4,
        'control_group_id': 9,
        'minimap': MINIMAP_SIZE * MINIMAP_SIZE - 1,
        'queued': 1,
        'screen': SCREEN_SIZE * SCREEN_SIZE - 1,
        'screen2': SCREEN_SIZE * SCREEN_SIZE - 1,
        'select_add': 1,
        'select_point_act': 3,
        'select_unit_act': 3,
        'select_unit_id': 499,
        'select_worker': 3,
        'unload_id': 499,
        'delay': 127,
        'function': NUM_ACTION_TYPES - 1
    }.items():
      self.assertEqual(action_spec[k].maximum, (v,), msg=k)

  def test_action_move_camera(self):
    cvr = converter.Converter(
        settings=_make_converter_settings('visual'),
        environment_info=_make_dummy_env_info())

    move_camera = {'delay': 17, 'function': 1, 'minimap': 6}
    action = cvr.convert_action(move_camera)

    expected = converter_pb2.Action(
        delay=17,
        request_action=sc2api_pb2.RequestAction(actions=[
            sc2api_pb2.Action(
                action_feature_layer=spatial_pb2.ActionSpatial(
                    camera_move=spatial_pb2.ActionSpatialCameraMove(
                        center_minimap=common_pb2.PointI(x=6, y=0))))
        ]))

    self.assertEqual(expected.SerializeToString(), action.SerializeToString())

  def test_action_smart_screen(self):
    cvr = converter.Converter(
        settings=_make_converter_settings('visual'),
        environment_info=_make_dummy_env_info())

    smart_screen = {
        'delay': np.int32(4),
        'function': np.int32(451),
        'queued': np.int32(1),
        'screen': np.int32(333)
    }

    action = cvr.convert_action(smart_screen)

    expected = converter_pb2.Action(
        delay=4,
        request_action=sc2api_pb2.RequestAction(actions=[
            sc2api_pb2.Action(
                action_feature_layer=spatial_pb2.ActionSpatial(
                    unit_command=spatial_pb2.ActionSpatialUnitCommand(
                        ability_id=1,
                        queue_command=True,
                        target_screen_coord=common_pb2.PointI(
                            x=333 % SCREEN_SIZE, y=333 // SCREEN_SIZE))))
        ]))

    self.assertEqual(expected.SerializeToString(), action.SerializeToString())


@parameterized.parameters(('visual',), ('raw',))
class ConverterTest(parameterized.TestCase):

  def test_construction(self, mode):
    converter.Converter(
        settings=_make_converter_settings(mode),
        environment_info=_make_dummy_env_info())

  def test_convert_action_delay(self, mode):
    cvr = converter.Converter(
        settings=_make_converter_settings(mode),
        environment_info=_make_dummy_env_info())

    for delay in range(1, 128):
      action = cvr.convert_action(dict(function=0, delay=delay))
      self.assertEqual(action.delay, delay)

  def test_observation_spec(self, mode):
    cvr = converter.Converter(
        settings=_make_converter_settings(mode),
        environment_info=_make_dummy_env_info())

    obs_spec = cvr.observation_spec()
    expected_fields = [
        'away_race_observed', 'away_race_requested', 'game_loop',
        'home_race_requested', 'minimap_height_map', 'minimap_visibility_map',
        'mmr', 'opponent_player', 'opponent_unit_counts_bow',
        'opponent_upgrades_fixed_length', 'player', 'unit_counts_bow',
        'upgrades_fixed_length'
    ]

    if mode == 'raw':
      expected_fields += ['raw_units']
    else:
      expected_fields += [
          'available_actions', 'screen_height_map', 'screen_player_relative'
      ]

    self.assertCountEqual(list(obs_spec), expected_fields)

    for k, v in obs_spec.items():
      self.assertEqual(k, v.name, msg=k)
      if k.startswith('minimap_') or k.startswith('screen_'):
        self.assertEqual(v.dtype, np.uint8, msg=k)
      else:
        self.assertEqual(v.dtype, np.int32, msg=k)
        if 'upgrades_fixed_length' not in k:
          self.assertFalse(hasattr(v, 'min'), msg=k)
          self.assertFalse(hasattr(v, 'max'), msg=k)

    for k, v in {
        'minimap_height_map': 255,
        'minimap_visibility_map': 3,
        'upgrades_fixed_length': NUM_UPGRADE_TYPES + 1,
        'opponent_upgrades_fixed_length': NUM_UPGRADE_TYPES + 1
    }.items():
      self.assertEqual(obs_spec[k].minimum, (0,), msg=k)
      self.assertEqual(obs_spec[k].maximum, (v,), msg=k)

    if mode == 'visual':
      for k, v in {
          'screen_height_map': 255,
          'screen_player_relative': 4
      }.items():
        self.assertEqual(obs_spec[k].minimum, (0,), msg=k)
        self.assertEqual(obs_spec[k].maximum, (v,), msg=k)

    for f in [
        'away_race_observed', 'away_race_requested', 'game_loop',
        'home_race_requested'
    ]:
      self.assertEqual(obs_spec[f].shape, (1,), msg=f)

    self.assertEqual(obs_spec['mmr'].shape, ())

    for k, v in {
        'player': 11,
        'opponent_player': 10,
        'unit_counts_bow': NUM_UNIT_TYPES,
        'opponent_unit_counts_bow': NUM_UNIT_TYPES,
        'upgrades_fixed_length': NUM_UPGRADES,
        'opponent_upgrades_fixed_length': NUM_UPGRADES
    }.items():
      self.assertEqual(obs_spec[k].shape, (v,), k)

    if mode == 'raw':
      self.assertEqual(obs_spec['raw_units'].shape,
                       (MAX_UNIT_COUNT, NUM_UNIT_FEATURES + 2))
    else:
      self.assertEqual(obs_spec['available_actions'].shape, (NUM_ACTION_TYPES,))

  def test_observation_matches_spec(self, mode):
    cvr = converter.Converter(
        settings=_make_converter_settings(mode),
        environment_info=_make_dummy_env_info())

    obs_spec = cvr.observation_spec()
    converted = cvr.convert_observation(_make_observation())

    for k, v in obs_spec.items():
      self.assertIn(k, converted)
      self.assertEqual(v.shape, converted[k].shape)

    for k in converted:
      self.assertIn(k, obs_spec)


if __name__ == '__main__':
  absltest.main()
