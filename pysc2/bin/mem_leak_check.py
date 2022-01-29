#!/usr/bin/python
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
"""Test for memory leaks."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# pylint: disable=g-import-not-at-top

import collections
import random
import sys
import time

from absl import app
from absl import flags
from future.builtins import range  # pylint: disable=redefined-builtin

try:
  import psutil
except ImportError:
  sys.exit(
      "`psutil` library required to track memory. This can be installed with:\n"
      "$ pip install psutil\n"
      "and needs the python-dev headers installed, for example:\n"
      "$ apt install python-dev")

from pysc2 import maps
from pysc2 import run_configs
from pysc2.lib import protocol

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb

# pylint: enable=g-import-not-at-top

races = {
    "random": sc_common.Random,
    "protoss": sc_common.Protoss,
    "terran": sc_common.Terran,
    "zerg": sc_common.Zerg,
}


flags.DEFINE_integer("mem_limit", 2000, "Max memory usage in Mb.")
flags.DEFINE_integer("episodes", 200, "Max number of episodes.")
flags.DEFINE_enum("race", "random", races.keys(), "Which race to play as.")
flags.DEFINE_list("map", "Catalyst", "Which map(s) to test on.")
FLAGS = flags.FLAGS


class Timestep(collections.namedtuple(
    "Timestep", ["episode", "time", "cpu", "memory", "name"])):

  def __str__(self):
    return "[%3d: %7.3f] cpu: %5.1f s, mem: %4d Mb; %s" % self


def main(unused_argv):
  for m in FLAGS.map:  # Verify they're all valid.
    maps.get(m)

  interface = sc_pb.InterfaceOptions()
  interface.raw = True
  interface.score = True
  interface.feature_layer.width = 24
  interface.feature_layer.resolution.x = 84
  interface.feature_layer.resolution.y = 84
  interface.feature_layer.minimap_resolution.x = 64
  interface.feature_layer.minimap_resolution.y = 64

  timeline = []

  start = time.time()
  run_config = run_configs.get()
  proc = run_config.start(want_rgb=interface.HasField("render"))
  process = psutil.Process(proc.pid)
  episode = 1

  def add(s):
    cpu_times = process.cpu_times()
    cpu = cpu_times.user + cpu_times.system
    mem = process.memory_info().rss / 2 ** 20  # In Mb
    step = Timestep(episode, time.time() - start, cpu, mem, s)
    print(step)
    timeline.append(step)
    if mem > FLAGS.mem_limit:
      raise MemoryError("%s Mb mem limit exceeded" % FLAGS.mem_limit)

  try:
    add("Started process")

    controller = proc.controller
    for _ in range(FLAGS.episodes):
      map_inst = maps.get(random.choice(FLAGS.map))
      create = sc_pb.RequestCreateGame(
          realtime=False, disable_fog=False, random_seed=episode,
          local_map=sc_pb.LocalMap(map_path=map_inst.path,
                                   map_data=map_inst.data(run_config)))
      create.player_setup.add(type=sc_pb.Participant)
      create.player_setup.add(type=sc_pb.Computer, race=races[FLAGS.race],
                              difficulty=sc_pb.CheatInsane)
      join = sc_pb.RequestJoinGame(race=races[FLAGS.race], options=interface)

      controller.create_game(create)
      add("Created game on %s" % map_inst.name)
      controller.join_game(join)
      add("Joined game")
      for i in range(2000):
        controller.step(16)
        obs = controller.observe()
        if obs.player_result:
          add("Lost on step %s" % i)
          break
        if i > 0 and i % 100 == 0:
          add("Step %s" % i)
      episode += 1
    add("Done")
  except KeyboardInterrupt:
    pass
  except (MemoryError, protocol.ConnectionError) as e:
    print(e)
  finally:
    proc.close()

  print("Timeline:")
  for t in timeline:
    print(t)


if __name__ == "__main__":
  app.run(main)
