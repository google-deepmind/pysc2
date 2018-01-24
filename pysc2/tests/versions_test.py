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
"""Test that every version in run_configs.google actually runs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import logging

from absl.testing import absltest
from absl.testing import parameterized
from pysc2 import run_configs
from pysc2.run_configs.platforms import VERSIONS


def major_version(v):
  return ".".join(v.split(".")[:2])


class TestVersions(parameterized.TestCase):

  @parameterized.parameters(sorted(VERSIONS.items()))
  def test_versions(self, game_version, version):
    self.assertEqual(game_version, version.game_version)
    logging.info((" starting: %s " % game_version).center(80, "-"))
    with run_configs.get().start(version=game_version) as controller:
      ping = controller.ping()
      logging.info("expected: %s", version)
      logging.info("actual: %s", ", ".join(str(ping).strip().split("\n")))
      self.assertEqual(major_version(ping.game_version),
                       major_version(version.game_version))
      self.assertEqual(version.build_version, ping.base_build)
      self.assertEqual(version.data_version.lower(),
                       ping.data_version.lower())
    logging.info((" success: %s " % game_version).center(80, "-"))

if __name__ == "__main__":
  absltest.main()
