#!/usr/bin/python
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Compare the observations from multiple binaries."""

from pysc2.lib import features
from pysc2.lib import np_util
from pysc2.lib import proto_diff

from s2clientprotocol import common_pb2


def image_differencer(path, proto_a, proto_b):
  """proto_diff differencer for PySC2 image data."""
  if path[-1] == "data" and len(path) >= 2:
    image_data_path = proto_diff.ProtoPath(path[:-1])
    image_data_a = image_data_path.get_field(proto_a)
    if isinstance(image_data_a, common_pb2.ImageData):
      image_data_b = image_data_path.get_field(proto_b)
      image_a = features.Feature.unpack_layer(image_data_a)
      image_b = features.Feature.unpack_layer(image_data_b)
      return np_util.summarize_array_diffs(image_a, image_b)

  return None
