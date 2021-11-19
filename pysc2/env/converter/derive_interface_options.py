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

"""Derives SC2 interface options from converter settings."""

from pysc2.env.converter.proto import converter_pb2

from s2clientprotocol import common_pb2
from s2clientprotocol import sc2api_pb2


def from_settings(settings: converter_pb2.ConverterSettings):
  """Derives SC2 interface options from converter settings."""
  if settings.HasField('visual_settings'):
    resolution = settings.visual_settings.screen
  else:
    resolution = common_pb2.Size2DI(x=1, y=1)

  return sc2api_pb2.InterfaceOptions(
      feature_layer=sc2api_pb2.SpatialCameraSetup(
          width=settings.camera_width_world_units,
          allow_cheating_layers=False,
          resolution=resolution,
          minimap_resolution=settings.minimap,
          crop_to_playable_area=settings.crop_to_playable_area),
      raw=settings.HasField('raw_settings'),
      score=True,
      raw_affects_selection=True,
      show_cloaked=True,
      show_placeholders=True,
      show_burrowed_shadows=True,
      raw_crop_to_playable_area=settings.crop_to_playable_area)
