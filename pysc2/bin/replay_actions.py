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

from absl import app
from absl import flags
from future.builtins import range  # pylint: disable=redefined-builtin
import queue
import six

from pysc2 import run_configs
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import protocol
from pysc2.lib import remote_controller

from pysc2.lib import gfile
from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb

FLAGS = flags.FLAGS
flags.DEFINE_integer("parallel", 1, "How many instances to run in parallel.")
flags.DEFINE_integer("step_mul", 8, "How many game steps per observation.")
flags.DEFINE_string("replays", None, "Path to a directory of replays.")
flags.mark_flag_as_required("replays")


size = point.Point(16, 16)
interface = sc_pb.InterfaceOptions(
    raw=True, score=False,
    feature_layer=sc_pb.SpatialCameraSetup(width=24))
size.assign_to(interface.feature_layer.resolution)
size.assign_to(interface.feature_layer.minimap_resolution)


def sorted_dict_str(d):
  return "{%s}" % ", ".join("%s: %s" % (k, d[k])
                            for k in sorted(d, key=d.get, reverse=True))


class ReplayStats(object):
  """Summary stats of the replays seen so far."""

  def __init__(self):
    self.replays = 0
    self.steps = 0
    self.camera_move = 0
    self.select_pt = 0
    self.select_rect = 0
    self.control_group = 0
    self.maps = collections.defaultdict(int)
    self.races = collections.defaultdict(int)
    self.unit_ids = collections.defaultdict(int)
    self.valid_abilities = collections.defaultdict(int)
    self.made_abilities = collections.defaultdict(int)
    self.valid_actions = collections.defaultdict(int)
    self.made_actions = collections.defaultdict(int)
    self.crashing_replays = set()
    self.invalid_replays = set()

  def merge(self, other):
    """Merge another ReplayStats into this one."""
    def merge_dict(a, b):
      for k, v in six.iteritems(b):
        a[k] += v

    self.replays += other.replays
    self.steps += other.steps
    self.camera_move += other.camera_move
    self.select_pt += other.select_pt
    self.select_rect += other.select_rect
    self.control_group += other.control_group
    merge_dict(self.maps, other.maps)
    merge_dict(self.races, other.races)
    merge_dict(self.unit_ids, other.unit_ids)
    merge_dict(self.valid_abilities, other.valid_abilities)
    merge_dict(self.made_abilities, other.made_abilities)
    merge_dict(self.valid_actions, other.valid_actions)
    merge_dict(self.made_actions, other.made_actions)
    self.crashing_replays |= other.crashing_replays
    self.invalid_replays |= other.invalid_replays

  def __str__(self):
    len_sorted_dict = lambda s: (len(s), sorted_dict_str(s))
    len_sorted_list = lambda s: (len(s), sorted(s))
    return "\n\n".join((
        "Replays: %s, Steps total: %s" % (self.replays, self.steps),
        "Camera move: %s, Select pt: %s, Select rect: %s, Control group: %s" % (
            self.camera_move, self.select_pt, self.select_rect,
            self.control_group),
        "Maps: %s\n%s" % len_sorted_dict(self.maps),
        "Races: %s\n%s" % len_sorted_dict(self.races),
        "Unit ids: %s\n%s" % len_sorted_dict(self.unit_ids),
        "Valid abilities: %s\n%s" % len_sorted_dict(self.valid_abilities),
        "Made abilities: %s\n%s" % len_sorted_dict(self.made_abilities),
        "Valid actions: %s\n%s" % len_sorted_dict(self.valid_actions),
        "Made actions: %s\n%s" % len_sorted_dict(self.made_actions),
        "Crashing replays: %s\n%s" % len_sorted_list(self.crashing_replays),
        "Invalid replays: %s\n%s" % len_sorted_list(self.invalid_replays),
    ))


class ProcessStats(object):
  """Stats for a worker process."""

  def __init__(self, proc_id):
    self.proc_id = proc_id
    self.time = time.time()
    self.stage = ""
    self.replay = ""
    self.replay_stats = ReplayStats()

  def update(self, stage):
    self.time = time.time()
    self.stage = stage

  def __str__(self):
    return ("[%2d] replay: %10s, replays: %5d, steps: %7d, game loops: %7s, "
            "last: %12s, %3d s ago" % (
                self.proc_id, self.replay, self.replay_stats.replays,
                self.replay_stats.steps,
                self.replay_stats.steps * FLAGS.step_mul, self.stage,
                time.time() - self.time))


def valid_replay(info, ping):
  """Make sure the replay isn't corrupt, and is worth looking at."""
  if (info.HasField("error") or
      info.base_build != ping.base_build or  # different game version
      info.game_duration_loops < 1000 or
      len(info.player_info) != 2):
    # Probably corrupt, or just not interesting.
    return False
  for p in info.player_info:
    if p.player_apm < 10 or p.player_mmr < 1000:
      # Low APM = player just standing around.
      # Low MMR = corrupt replay or player who is weak.
      return False
  return True


class ReplayProcessor(multiprocessing.Process):
  """A Process that pulls replays and processes them."""

  def __init__(self, proc_id, run_config, replay_queue, stats_queue):
    super(ReplayProcessor, self).__init__()
    self.stats = ProcessStats(proc_id)
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
              replay_name = os.path.basename(replay_path)[:10]
              self.stats.replay = replay_name
              self._print("Got replay: %s" % replay_path)
              self._update_stage("open replay file")
              replay_data = self.run_config.replay_data(replay_path)
              self._update_stage("replay_info")
              info = controller.replay_info(replay_data)
              self._print((" Replay Info %s " % replay_name).center(60, "-"))
              self._print(info)
              self._print("-" * 60)
              if valid_replay(info, ping):
                self.stats.replay_stats.maps[info.map_name] += 1
                for player_info in info.player_info:
                  race_name = sc_common.Race.Name(
                      player_info.player_info.race_actual)
                  self.stats.replay_stats.races[race_name] += 1
                map_data = None
                if info.local_map_path:
                  self._update_stage("open map file")
                  map_data = self.run_config.map_data(info.local_map_path)
                for player_id in [1, 2]:
                  self._print("Starting %s from player %s's perspective" % (
                      replay_name, player_id))
                  self.process_replay(controller, replay_data, map_data,
                                      player_id)
              else:
                self._print("Replay is invalid.")
                self.stats.replay_stats.invalid_replays.add(replay_name)
            finally:
              self.replay_queue.task_done()
          self._update_stage("shutdown")
      except (protocol.ConnectionError, protocol.ProtocolError,
              remote_controller.RequestError):
        self.stats.replay_stats.crashing_replays.add(replay_name)
      except KeyboardInterrupt:
        return

  def _print(self, s):
    for line in str(s).strip().splitlines():
      print("[%s] %s" % (self.stats.proc_id, line))

  def _update_stage(self, stage):
    self.stats.update(stage)
    self.stats_queue.put(self.stats)

  def process_replay(self, controller, replay_data, map_data, player_id):
    """Process a single replay, updating the stats."""
    self._update_stage("start_replay")
    controller.start_replay(sc_pb.RequestStartReplay(
        replay_data=replay_data,
        map_data=map_data,
        options=interface,
        observed_player_id=player_id))

    feat = features.features_from_game_info(controller.game_info())

    self.stats.replay_stats.replays += 1
    self._update_stage("step")
    controller.step()
    while True:
      self.stats.replay_stats.steps += 1
      self._update_stage("observe")
      obs = controller.observe()

      for action in obs.actions:
        act_fl = action.action_feature_layer
        if act_fl.HasField("unit_command"):
          self.stats.replay_stats.made_abilities[
              act_fl.unit_command.ability_id] += 1
        if act_fl.HasField("camera_move"):
          self.stats.replay_stats.camera_move += 1
        if act_fl.HasField("unit_selection_point"):
          self.stats.replay_stats.select_pt += 1
        if act_fl.HasField("unit_selection_rect"):
          self.stats.replay_stats.select_rect += 1
        if action.action_ui.HasField("control_group"):
          self.stats.replay_stats.control_group += 1

        try:
          func = feat.reverse_action(action).function
        except ValueError:
          func = -1
        self.stats.replay_stats.made_actions[func] += 1

      for valid in obs.observation.abilities:
        self.stats.replay_stats.valid_abilities[valid.ability_id] += 1

      for u in obs.observation.raw_data.units:
        self.stats.replay_stats.unit_ids[u.unit_type] += 1

      for ability_id in feat.available_actions(obs.observation):
        self.stats.replay_stats.valid_actions[ability_id] += 1

      if obs.player_result:
        break

      self._update_stage("step")
      controller.step(FLAGS.step_mul)


def stats_printer(stats_queue):
  """A thread that consumes stats_queue and prints them every 10 seconds."""
  proc_stats = [ProcessStats(i) for i in range(FLAGS.parallel)]
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

    replay_stats = ReplayStats()
    for s in proc_stats:
      replay_stats.merge(s.replay_stats)

    print((" Summary %0d secs " % (print_time - start_time)).center(width, "="))
    print(replay_stats)
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

  if not gfile.Exists(FLAGS.replays):
    sys.exit("{} doesn't exist.".format(FLAGS.replays))

  stats_queue = multiprocessing.Queue()
  stats_thread = threading.Thread(target=stats_printer, args=(stats_queue,))
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
      p = ReplayProcessor(i, run_config, replay_queue, stats_queue)
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
