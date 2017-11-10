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
"""Dump out stats about all the actions that are in use in a set of replays."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import multiprocessing
import os
import signal
import sys
import threading
import time

from future.builtins import range  # pylint: disable=redefined-builtin
import six
from six.moves import queue

from pysc2 import run_configs
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import protocol
from pysc2.lib import remote_controller

from absl import app
from absl import flags
from pysc2.lib import gfile
from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb

import importlib
import json
import sys

FLAGS = flags.FLAGS
flags.DEFINE_integer("parallel", 1, "How many instances to run in parallel.")
flags.DEFINE_integer("step_mul", 8, "How many game steps per observation.")
flags.DEFINE_string("replays", None, "Path to a directory of replays.")
flags.DEFINE_string("parser", "pysc2.replay_parsers.base_parser.BaseParser",
                    "Which parser to use in scrapping replay data")
flags.DEFINE_string("data_dir", None,
                    "Path to directory to save replay data from replay parser")
flags.DEFINE_integer("screen_resolution", 16,
                     "Resolution for screen feature layers.")
flags.DEFINE_integer("minimap_resolution", 16,
                     "Resolution for minimap feature layers.")
flags.mark_flag_as_required("replays")

interface = sc_pb.InterfaceOptions()
interface.raw = True
interface.score = False
interface.feature_layer.width = 24
interface.feature_layer.resolution.x = FLAGS.screen_resolution
interface.feature_layer.resolution.y = FLAGS.screen_resolution
interface.feature_layer.minimap_resolution.x = FLAGS.minimap_resolution
interface.feature_layer.minimap_resolution.y = FLAGS.minimap_resolution

class ProcessStats(object):
  """Stats for a worker process."""

  def __init__(self, proc_id, parser_cls):
    self.proc_id = proc_id
    self.time = time.time()
    self.stage = ""
    self.replay = ""
    self.parser = parser_cls()

  def update(self, stage):
    self.time = time.time()
    self.stage = stage

  def __str__(self):
    return ("[%2d] replay: %10s, replays: %5d, steps: %7d, game loops: %7s, "
            "last: %12s, %3d s ago" % (
                self.proc_id, self.replay, self.parser.replays,
                self.parser.steps,
                self.parser.steps * FLAGS.step_mul, self.stage,
                time.time() - self.time))


class ReplayProcessor(multiprocessing.Process):
  """A Process that pulls replays and processes them."""

  def __init__(self, proc_id, run_config, replay_queue, stats_queue, parser_cls):
    super(ReplayProcessor, self).__init__()
    self.stats = ProcessStats(proc_id, parser_cls)
    self.run_config = run_config
    self.replay_queue = replay_queue
    self.stats_queue = stats_queue

  def run(self):
    signal.signal(signal.SIGTERM, lambda a, b: sys.exit())  # Exit quietly.
    self._update_stage("spawn")
    replay_name = "none"
    while True:
      self._print("Starting up a new SC2 instance.")
      self._update_stage("launch")
      try:
        with self.run_config.start() as controller:
          self._print("SC2 Started successfully.")
          ping = controller.ping()
          for _ in range(300):
            try:
              replay_path = self.replay_queue.get()
            except queue.Empty:
              self._update_stage("done")
              self._print("Empty queue, returning")
              return
            try:
              replay_name = os.path.basename(replay_path)
              self.stats.replay = replay_name
              self._print("Got replay: %s" % replay_path)
              self._update_stage("open replay file")
              replay_data = self.run_config.replay_data(replay_path)
              self._update_stage("replay_info")
              info = controller.replay_info(replay_data)
              self._print((" Replay Info %s " % replay_name).center(60, "-"))
              self._print(info)
              self._print("-" * 60)
              if self.stats.parser.valid_replay(info, ping):
                self.stats.parser.maps[info.map_name] += 1
                for player_info in info.player_info:
                  race_name = sc_common.Race.Name(
                      player_info.player_info.race_actual)
                  self.stats.parser.races[race_name] += 1
                map_data = None
                if info.local_map_path:
                  self._update_stage("open map file")
                  map_data = self.run_config.map_data(info.local_map_path)
                for player_id in [1, 2]:
                  self._print("Starting %s from player %s's perspective" % (
                      replay_name, player_id))
                  self.process_replay(controller, replay_data, map_data,
                                      player_id, info, replay_name)
              else:
                self._print("Replay is invalid.")
                self.stats.parser.invalid_replays.add(replay_name)
            finally:
              self.replay_queue.task_done()
          self._update_stage("shutdown")
      except (protocol.ConnectionError, protocol.ProtocolError,
              remote_controller.RequestError):
        self.stats.parser.crashing_replays.add(replay_name)
      except KeyboardInterrupt:
        return

  def _print(self, s):
    for line in str(s).strip().splitlines():
      print("[%s] %s" % (self.stats.proc_id, line))

  def _update_stage(self, stage):
    self.stats.update(stage)
    self.stats_queue.put(self.stats)

  def process_replay(self, controller, replay_data, map_data, player_id, info, replay_name):
    print(replay_name)
    """Process a single replay, updating the stats."""
    self._update_stage("start_replay")
    controller.start_replay(sc_pb.RequestStartReplay(
        replay_data=replay_data,
        map_data=map_data,
        options=interface,
        observed_player_id=player_id))

    feat = features.Features(controller.game_info())

    self.stats.parser.replays += 1
    self._update_stage("step")
    controller.step()
    data = []
    while True:
      self.stats.parser.steps += 1
      self._update_stage("observe")
      obs = controller.observe()
      # If parser.parse_step returns, whatever is returned is appended
      # to a data list, and this data list is saved to a json file
      # in the data_dir directory with filename = replay_name_player_id.json
      parsed_data = self.stats.parser.parse_step(obs,feat,info)
      if parsed_data:
        data.append(parsed_data)

      if obs.player_result:        
        # Save scraped replay data to file at end of replay if parser returns
        # and data_dir provided        
        if data:
          if FLAGS.data_dir:
            stripped_replay_name = replay_name.split(".")[0]
            data_file = os.path.join(FLAGS.data_dir,
                           stripped_replay_name + "_" + str(player_id) + '.json')
            with open(data_file,'w') as outfile:
              json.dump(data,outfile)
          else:
            print("Please provide a directory as data_dir to save scrapped data files")
        break

      self._update_stage("step")
      controller.step(FLAGS.step_mul)


def stats_printer(stats_queue, parser_cls):
  """A thread that consumes stats_queue and prints them every 10 seconds."""
  proc_stats = [ProcessStats(i,parser_cls) for i in range(FLAGS.parallel)]
  print_time = start_time = time.time()
  width = 107

  running = True
  while running:
    print_time += 10

    while time.time() < print_time:
      try:
        s = stats_queue.get(True, print_time - time.time())
        if s is None:  # Signal to print and exit NOW!
          running = False
          break
        proc_stats[s.proc_id] = s
      except queue.Empty:
        pass

    parser = parser_cls()
    for s in proc_stats:
      parser.merge(s.parser)

    print((" Summary %0d secs " % (print_time - start_time)).center(width, "="))
    print(parser)
    print(" Process stats ".center(width, "-"))
    print("\n".join(str(s) for s in proc_stats))
    print("=" * width)


def replay_queue_filler(replay_queue, replay_list):
  """A thread that fills the replay_queue with replay filenames."""
  for replay_path in replay_list:
    replay_queue.put(replay_path)


def main(unused_argv):
  """Dump stats about all the actions that are in use in a set of replays."""
  run_config = run_configs.get()

  parser_module, parser_name = FLAGS.parser.rsplit(".", 1)
  parser_cls = getattr(importlib.import_module(parser_module), parser_name)

  if not gfile.Exists(FLAGS.replays):
    sys.exit("{} doesn't exist.".format(FLAGS.replays))

  stats_queue = multiprocessing.Queue()
  stats_thread = threading.Thread(target=stats_printer, args=(stats_queue,parser_cls))
  stats_thread.start()
  try:
    # For some reason buffering everything into a JoinableQueue makes the
    # program not exit, so save it into a list then slowly fill it into the
    # queue in a separate thread. Grab the list synchronously so we know there
    # is work in the queue before the SC2 processes actually run, otherwise
    # The replay_queue.join below succeeds without doing any work, and exits.
    print("Getting replay list:", FLAGS.replays)
    replay_list = sorted(run_config.replay_paths(FLAGS.replays))
    print(len(replay_list), "replays found.\n")
    replay_queue = multiprocessing.JoinableQueue(FLAGS.parallel * 10)
    replay_queue_thread = threading.Thread(target=replay_queue_filler,
                                           args=(replay_queue, replay_list))
    replay_queue_thread.daemon = True
    replay_queue_thread.start()

    for i in range(FLAGS.parallel):
      p = ReplayProcessor(i, run_config, replay_queue, stats_queue, parser_cls)
      p.daemon = True
      p.start()
      time.sleep(1)  # Stagger startups, otherwise they seem to conflict somehow

    replay_queue.join()  # Wait for the queue to empty.
  except KeyboardInterrupt:
    print("Caught KeyboardInterrupt, exiting.")
  finally:
    stats_queue.put(None)  # Tell the stats_thread to print and exit.
    stats_thread.join()


if __name__ == "__main__":
  app.run(main)
