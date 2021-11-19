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

import os

from absl import flags
from absl.testing import absltest
from absl.testing import parameterized
from pysc2.lib.replay import sc2_replay
from pysc2.lib.replay import sc2_replay_utils

from pysc2.lib import gfile
from pysc2.lib import resources

FLAGS = flags.FLAGS
PATH = "pysc2/lib/replay/test_data"


def _read_replay(name):
  replay_path = resources.GetResourceFilename(os.path.join(PATH, name))
  with gfile.Open(replay_path, mode="rb") as f:
    replay_data = f.read()
  return sc2_replay.SC2Replay(replay_data)


def _read_skips(name):
  skips_path = resources.GetResourceFilename(os.path.join(PATH, name))
  with gfile.Open(skips_path, mode="r") as f:
    return [int(i) for i in f.readlines()[0].split(",")]


class Sc2ReplayUtilsTest(parameterized.TestCase):

  @parameterized.parameters(
      ((f"replay_0{i}.SC2Replay", f"replay_0{i}.skips.txt")
       for i in range(1, 10)))
  def test_raw_action_skips(self, replay_name, skips_file):
    replay = _read_replay(replay_name)
    skips = _read_skips(skips_file)
    result = sc2_replay_utils.raw_action_skips(replay)
    self.assertEqual(result[1], skips)


if __name__ == "__main__":
  absltest.main()
