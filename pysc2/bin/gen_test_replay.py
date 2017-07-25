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
"""Generate some replays for testing map-reduce."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os


from pysc2 import run_configs
from pysc2.agents import random_agent
from pysc2.agents import scripted_agent
from pysc2.env import run_loop
from pysc2.env import sc2_env

from google.apputils import app


def main(unused_argv):
  guitar_dir = run_configs.get().abs_replay_path("guitar_test")
  if not os.path.isdir(guitar_dir):
    os.mkdir(guitar_dir)

  with sc2_env.SC2Env("TestEmpty", step_mul=10) as env:
    agent = random_agent.RandomAgent()
    run_loop.run_loop([agent], env, 50)
    env.save_replay(guitar_dir)

  with sc2_env.SC2Env("TestMNEasy", step_mul=10) as env:
    agent = random_agent.RandomAgent()
    run_loop.run_loop([agent], env, 25)
    env.save_replay(guitar_dir)

  with sc2_env.SC2Env("TestMNEasy", step_mul=10) as env:
    agent = scripted_agent.MNEasyWin()
    run_loop.run_loop([agent], env, 20)
    env.save_replay(guitar_dir)

  with sc2_env.SC2Env("TestMNEasy", step_mul=10) as env:
    agent = scripted_agent.MNEasyLose()
    run_loop.run_loop([agent], env, 20)
    env.save_replay(guitar_dir)


if __name__ == "__main__":
  app.run()
