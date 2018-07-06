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

import time

from absl import app
from future.builtins import range  # pylint: disable=redefined-builtin

import psutil

from pysc2 import maps
from pysc2 import run_configs

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


def main(unused_argv):
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
  proc = run_config.start()
  process = psutil.Process(proc.pid)

  def add(s):
    cpu = process.cpu_times().user
    mem = process.memory_info().rss / 2 ** 20  # In Mb
    timeline.append((time.time() - start, cpu, mem, s))

    if mem > 2000:
      raise Exception("2gb mem limit exceeded")

  try:
    add("Started")

    controller = proc.controller
    map_inst = maps.get("Simple64")
    create = sc_pb.RequestCreateGame(
        realtime=False, disable_fog=False,
        local_map=sc_pb.LocalMap(map_path=map_inst.path,
                                 map_data=map_inst.data(run_config)))
    create.player_setup.add(type=sc_pb.Participant)
    create.player_setup.add(type=sc_pb.Computer, race=sc_common.Random,
                            difficulty=sc_pb.CheatInsane)
    join = sc_pb.RequestJoinGame(race=sc_common.Random, options=interface)
    controller.create_game(create)

    add("Created")

    controller.join_game(join)

    add("Joined")

    for _ in range(30):

      for i in range(2000):
        controller.step(16)
        obs = controller.observe()
        if obs.player_result:
          add("Lost")
          break
        if i % 100 == 0:
          add(i)

      controller.restart()
      add("Restarted")
    add("Done")
  except KeyboardInterrupt:
    pass
  finally:
    proc.close()

  print("Timeline:")
  for t in timeline:
    print("[%7.3f] cpu: %5.1f s, mem: %4d M; %s" % t)


if __name__ == "__main__":
  app.run(main)
