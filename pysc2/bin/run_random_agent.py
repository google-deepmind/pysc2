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
"""Run the random agent."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import threading


from pysc2.agents import random_agent
from pysc2.env import available_actions_printer
from pysc2.env import run_loop
from pysc2.env import sc2_env
from pysc2.lib import flag_utils
from pysc2.lib import point
from pysc2.lib import stopwatch

from google.apputils import app
import gflags as flags


FLAGS = flags.FLAGS
flags.DEFINE_integer("max_agent_steps", 1000, "Total agent steps.")
flags.DEFINE_integer("game_steps_per_episode", 0, "Game steps per episode.")
flags.DEFINE_integer("step_mul", 20, "Game steps per agent step.")
flags.DEFINE_enum("agent_race", None, sc2_env.races.keys(), "Agent's race.")
flags.DEFINE_enum("bot_race", None, sc2_env.races.keys(), "Bot's race.")
flags.DEFINE_enum("difficulty", None, sc2_env.difficulties.keys(),
                  "Bot's strength.")
flags.DEFINE_bool("visualize", True, "Whether to show the visualization.")
flags.DEFINE_string("resolution", "64,64", "Resolution for feature layers.")
flags.DEFINE_bool("profile", False, "Whether to turn on code profiling.")
flags.DEFINE_bool("trace", False, "Whether to trace the code execution.")
flags.DEFINE_integer("parallel", 1, "How many instances to run in parallel.")
flags.DEFINE_bool("save_replay", False, "Whether to save a replay at the end.")
flags.DEFINE_string("map", None, "Name of a map/replay to use.")


def run_thread(map_name, visualize):
  resolution = point.Point(*(int(i) for i in FLAGS.resolution.split(",")))
  with sc2_env.SC2Env(
      map_name,
      agent_race=FLAGS.agent_race,
      bot_race=FLAGS.bot_race,
      difficulty=FLAGS.difficulty,
      step_mul=FLAGS.step_mul,
      visualize=visualize,
      game_steps_per_episode=FLAGS.game_steps_per_episode,
      screen_size_px=resolution,
      minimap_size_px=resolution) as env:
    env = available_actions_printer.AvailableActionsPrinter(env)
    agent = random_agent.RandomAgent()
    run_loop.run_loop([agent], env, FLAGS.max_agent_steps)
    if FLAGS.save_replay:
      env.save_replay("random")


def main(argv):
  """Run the random agent."""
  stopwatch.sw.enabled = FLAGS.profile or FLAGS.trace
  stopwatch.sw.trace = FLAGS.trace

  map_name = flag_utils.positional_flag("Map name", FLAGS.map, argv)

  threads = []
  for i in xrange(FLAGS.parallel):
    t = threading.Thread(target=run_thread, args=(
        map_name, FLAGS.visualize and i == 0))
    threads.append(t)
    t.start()

  for t in threads:
    t.join()

  if FLAGS.profile:
    print(stopwatch.sw)


if __name__ == "__main__":
  app.run()
