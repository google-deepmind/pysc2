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
"""Tests for image_differencer.py."""

from absl.testing import absltest
import numpy as np
from pysc2.lib import image_differencer
from pysc2.lib import proto_diff

from s2clientprotocol import common_pb2
from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import spatial_pb2


class ImageDifferencerTest(absltest.TestCase):

  def testFilteredOut(self):
    result = image_differencer.image_differencer(
        path=proto_diff.ProtoPath(("observation", "actions", 1)),
        proto_a=None,
        proto_b=None)
    self.assertIsNone(result)

  def testFilteredIn(self):
    a = sc_pb.ResponseObservation(
        observation=sc_pb.Observation(
            feature_layer_data=spatial_pb2.ObservationFeatureLayer(
                renders=spatial_pb2.FeatureLayers(
                    height_map=common_pb2.ImageData(
                        bits_per_pixel=32,
                        size=common_pb2.Size2DI(x=4, y=4),
                        data=np.array([[0, 0, 0, 0],
                                       [1, 0, 1, 0],
                                       [0, 0, 0, 1],
                                       [1, 1, 1, 1]], dtype=np.int32).tobytes()
                    )
                )
            )))
    b = sc_pb.ResponseObservation(
        observation=sc_pb.Observation(
            feature_layer_data=spatial_pb2.ObservationFeatureLayer(
                renders=spatial_pb2.FeatureLayers(
                    height_map=common_pb2.ImageData(
                        bits_per_pixel=32,
                        size=common_pb2.Size2DI(x=4, y=4),
                        data=np.array([[0, 0, 0, 0],
                                       [0, 1, 1, 0],
                                       [0, 0, 0, 1],
                                       [1, 1, 1, 0]], dtype=np.int32).tobytes()
                    )
                )
            )))

    result = image_differencer.image_differencer(
        path=proto_diff.ProtoPath((
            "observation",
            "feature_layer_data",
            "renders",
            "height_map",
            "data")),
        proto_a=a,
        proto_b=b)

    self.assertEqual(
        result,
        "3 element(s) changed - [1][0]: 1 -> 0; [1][1]: 0 -> 1; [3][3]: 1 -> 0")


if __name__ == "__main__":
  absltest.main()
