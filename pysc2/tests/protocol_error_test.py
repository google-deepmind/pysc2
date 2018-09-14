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
"""Verify that we blow up if SC2 thinks we did something wrong."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest
from pysc2 import run_configs
from pysc2.lib import protocol
from pysc2.lib import remote_controller
from pysc2.tests import utils

from s2clientprotocol import sc2api_pb2 as sc_pb


class TestProtocolError(utils.TestCase):
  """Verify that we blow up if SC2 thinks we did something wrong."""

  def test_error(self):
    with run_configs.get().start(want_rgb=False) as controller:
      with self.assertRaises(remote_controller.RequestError):
        controller.create_game(sc_pb.RequestCreateGame())  # Missing map, etc.

      with self.assertRaises(protocol.ProtocolError):
        controller.join_game(sc_pb.RequestJoinGame())  # No game to join.


if __name__ == "__main__":
  absltest.main()
