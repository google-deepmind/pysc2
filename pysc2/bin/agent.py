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
"""Run an agent."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import importlib
import threading

from future.builtins import range  # pylint: disable=redefined-builtin

from pysc2 import maps
from pysc2.env import available_actions_printer
from pysc2.env import run_loop
from pysc2.env import sc2_env
from pysc2.lib import point
from pysc2.lib import stopwatch

from pysc2.lib import app
import gflags as flags


FLAGS = flags.FLAGS
flags.DEFINE_bool("render", True, "Whether to render with pygame.")
flags.DEFINE_string("resolution", "64,64", "Resolution for feature layers.")

flags.DEFINE_integer("max_agent_steps", 2500, "Total agent steps.")
flags.DEFINE_integer("game_steps_per_episode", 0, "Game steps per episode.")
flags.DEFINE_integer("step_mul", 8, "Game steps per agent step.")

flags.DEFINE_string("agent", "pysc2.agents.random_agent.RandomAgent",
                    "Which agent to run")
flags.DEFINE_enum("agent_race", None, sc2_env.races.keys(), "Agent's race.")
flags.DEFINE_enum("bot_race", None, sc2_env.races.keys(), "Bot's race.")
flags.DEFINE_enum("difficulty", None, sc2_env.difficulties.keys(),
                  "Bot's strength.")

flags.DEFINE_bool("profile", False, "Whether to turn on code profiling.")
flags.DEFINE_bool("trace", False, "Whether to trace the code execution.")
flags.DEFINE_integer("parallel", 1, "How many instances to run in parallel.")

flags.DEFINE_bool("save_replay", False, "Whether to save a replay at the end.")

flags.DEFINE_string("map", None, "Name of a map to use.")
flags.mark_flag_as_required("map")


def run_thread(agent_cls, map_name, visualize):
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
    agent = agent_cls()
    run_loop.run_loop([agent], env, FLAGS.max_agent_steps)
    if FLAGS.save_replay:
      env.save_replay("random")


def _main(unused_argv):
  """Run an agent."""
  stopwatch.sw.enabled = FLAGS.profile or FLAGS.trace
  stopwatch.sw.trace = FLAGS.trace

  maps.get(FLAGS.map)  # Assert the map exists.

  agent_module, agent_name = FLAGS.agent.rsplit(".", 1)
  agent_cls = getattr(importlib.import_module(agent_module), agent_name)

  threads = []
  for i in range(FLAGS.parallel):
    t = threading.Thread(target=run_thread, args=(
        agent_cls, FLAGS.map, FLAGS.render and i == 0))
    threads.append(t)
    t.start()

  for t in threads:
    t.join()

  if FLAGS.profile:
    print(stopwatch.sw)


def main():  # Needed so setup.py scripts work.
  app.really_start(_main)


if __name__ == "__main__":
  main()
