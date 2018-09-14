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
"""Test that every version in run_configs actually runs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import logging

from absl.testing import absltest
from pysc2 import maps
from pysc2 import run_configs

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


def major_version(v):
  return ".".join(v.split(".")[:2])


def log_center(s, *args):
  logging.info(((" " + s + " ") % args).center(80, "-"))


class TestVersions(absltest.TestCase):

  def test_version_numbers(self):
    run_config = run_configs.get()
    failures = []
    for game_version, version in sorted(run_config.get_versions().items()):
      try:
        self.assertEqual(game_version, version.game_version)
        log_center("starting version check: %s", game_version)
        with run_config.start(version=game_version,
                              want_rgb=False) as controller:
          ping = controller.ping()
          logging.info("expected: %s", version)
          logging.info("actual: %s", ", ".join(str(ping).strip().split("\n")))
          self.assertEqual(version.build_version, ping.base_build)
          if version.game_version != "latest":
            self.assertEqual(major_version(ping.game_version),
                             major_version(version.game_version))
            self.assertEqual(version.data_version.lower(),
                             ping.data_version.lower())
        log_center("success: %s", game_version)
      except:  # pylint: disable=bare-except
        log_center("failure: %s", game_version)
        logging.exception("Failed")
        failures.append(game_version)
    self.assertEmpty(failures)

  def test_versions_create_game(self):
    run_config = run_configs.get()
    failures = []
    for game_version in sorted(run_config.get_versions().keys()):
      try:
        log_center("starting create game: %s", game_version)
        with run_config.start(version=game_version,
                              want_rgb=False) as controller:
          interface = sc_pb.InterfaceOptions()
          interface.raw = True
          interface.score = True
          interface.feature_layer.width = 24
          interface.feature_layer.resolution.x = 84
          interface.feature_layer.resolution.y = 84
          interface.feature_layer.minimap_resolution.x = 64
          interface.feature_layer.minimap_resolution.y = 64

          map_inst = maps.get("Simple64")
          create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(
              map_path=map_inst.path, map_data=map_inst.data(run_config)))
          create.player_setup.add(type=sc_pb.Participant)
          create.player_setup.add(type=sc_pb.Computer, race=sc_common.Terran,
                                  difficulty=sc_pb.VeryEasy)
          join = sc_pb.RequestJoinGame(race=sc_common.Terran, options=interface)

          controller.create_game(create)
          controller.join_game(join)

          for _ in range(5):
            controller.step(16)
            controller.observe()

        log_center("success: %s", game_version)
      except:  # pylint: disable=bare-except
        logging.exception("Failed")
        log_center("failure: %s", game_version)
        failures.append(game_version)
    self.assertEmpty(failures)


if __name__ == "__main__":
  absltest.main()
