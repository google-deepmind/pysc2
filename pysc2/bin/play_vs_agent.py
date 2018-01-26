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
"""Play as a human against an agent."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import importlib
import platform
import threading
import time

from absl import app
from absl import flags
import portpicker

from pysc2 import maps
from pysc2 import run_configs
from pysc2.env import environment
from pysc2.env import sc2_env
from pysc2.lib import features
from pysc2.lib import renderer_human

from s2clientprotocol import sc2api_pb2 as sc_pb

FLAGS = flags.FLAGS
flags.DEFINE_bool("render", platform.system() == "Linux",
                  "Whether to render with pygame.")
flags.DEFINE_bool("realtime", False, "Whether to run in realtime mode.")

flags.DEFINE_string("agent", "pysc2.agents.random_agent.RandomAgent",
                    "Which agent to run, as a python path to an Agent class.")
flags.DEFINE_enum("agent_race", "random", sc2_env.Race._member_names_,  # pylint: disable=protected-access
                  "Agent's race.")

flags.DEFINE_integer("step_mul", 8, "Game steps per agent step.")

flags.DEFINE_integer("feature_screen_size", 84,
                     "Resolution for screen feature layers.")
flags.DEFINE_integer("feature_minimap_size", 64,
                     "Resolution for minimap feature layers.")
flags.DEFINE_integer("rgb_screen_size", 256,
                     "Resolution for rendered screen.")
flags.DEFINE_integer("rgb_minimap_size", 128,
                     "Resolution for rendered minimap.")

flags.DEFINE_enum("user_race", "random", sc2_env.Race._member_names_,  # pylint: disable=protected-access
                  "User's race.")

flags.DEFINE_string("map", None, "Name of a map to use to play.")
flags.mark_flag_as_required("map")


def human_runner(controller, join):
  """Run the human agent in a thread."""
  j = sc_pb.RequestJoinGame()
  j.CopyFrom(join)
  j.race = sc2_env.Race[FLAGS.user_race]
  if FLAGS.render:
    j.options.raw = True
    j.options.feature_layer.width = 24
    j.options.feature_layer.resolution.x = 64
    j.options.feature_layer.resolution.y = 64
    j.options.feature_layer.minimap_resolution.x = 64
    j.options.feature_layer.minimap_resolution.y = 64
    # j.options.render.resolution.x = 256
    # j.options.render.resolution.y = 192
    # j.options.render.minimap_resolution.x = 128
    # j.options.render.minimap_resolution.y = 128
  controller.join_game(j)

  if FLAGS.render:
    renderer = renderer_human.RendererHuman(render_feature_grid=False)
    renderer.run(run_configs.get(), controller, max_episodes=1)
  else:  # Still step forward so the Mac/Windows renderer works.
    try:
      while True:
        frame_start_time = time.time()
        if not FLAGS.realtime:
          controller.step(FLAGS.step_mul)
        obs = controller.observe()

        if obs.player_result:
          break
        time.sleep(max(0, frame_start_time - time.time() + 1 / 22.4))
    except KeyboardInterrupt:
      pass
  controller.quit()


def agent_runner(controller, join):
  """Run the agent in a thread."""
  agent_module, agent_name = FLAGS.agent.rsplit(".", 1)
  agent_cls = getattr(importlib.import_module(agent_module), agent_name)
  agent = agent_cls()

  interface = sc_pb.InterfaceOptions()
  interface.raw = True
  interface.score = True
  interface.feature_layer.width = 24
  interface.feature_layer.resolution.x = FLAGS.feature_screen_size
  interface.feature_layer.resolution.y = FLAGS.feature_screen_size
  interface.feature_layer.minimap_resolution.x = FLAGS.feature_minimap_size
  interface.feature_layer.minimap_resolution.y = FLAGS.feature_minimap_size
  # if FLAGS.rgb_screen_size and FLAGS.rgb_minimap_size:
  #   if FLAGS.rgb_screen_size < FLAGS.rgb_minimap_size:
  #     sys.exit("Screen size can't be smaller than minimap size.")
  #   interface.render.resolution.x = FLAGS.rgb_screen_size
  #   interface.render.resolution.y = FLAGS.rgb_screen_size
  #   interface.render.minimap_resolution.x = FLAGS.rgb_minimap_size
  #   interface.render.minimap_resolution.y = FLAGS.rgb_minimap_size

  j = sc_pb.RequestJoinGame()
  j.CopyFrom(join)
  j.options.CopyFrom(interface)
  j.race = sc2_env.Race[FLAGS.agent_race]
  controller.join_game(j)

  feats = features.Features(game_info=controller.game_info())
  agent.setup(feats.observation_spec(), feats.action_spec())

  state = environment.StepType.FIRST
  reward = 0
  discount = 1
  while True:
    frame_start_time = time.time()
    if not FLAGS.realtime:
      controller.step(FLAGS.step_mul)
    obs = controller.observe()
    if obs.player_result:  # Episode over.
      state = environment.StepType.LAST
      discount = 0

    agent_obs = feats.transform_obs(obs.observation)

    timestep = environment.TimeStep(
        step_type=state, reward=reward, discount=discount,
        observation=agent_obs)

    action = agent.step(timestep)
    if state == environment.StepType.LAST:
      break
    controller.act(feats.transform_action(obs.observation, action))

    if FLAGS.realtime:
      time.sleep(max(0, frame_start_time - time.time() + FLAGS.step_mul / 22.4))
  controller.quit()


def main(unused_argv):
  """Run SC2 to play a game or a replay."""
  run_config = run_configs.get()

  map_inst = maps.get(FLAGS.map)

  ports = [portpicker.pick_unused_port() for _ in range(5)]
  sc2_procs = [run_config.start(extra_ports=ports) for _ in range(2)]
  controllers = [p.controller for p in sc2_procs]

  for c in controllers:
    c.save_map(map_inst.path, map_inst.data(run_config))

  create = sc_pb.RequestCreateGame(
      realtime=FLAGS.realtime, local_map=sc_pb.LocalMap(map_path=map_inst.path))
  create.player_setup.add(type=sc_pb.Participant)
  create.player_setup.add(type=sc_pb.Participant)

  controllers[0].create_game(create)

  join = sc_pb.RequestJoinGame()
  join.shared_port = ports.pop()
  join.server_ports.game_port = ports.pop()
  join.server_ports.base_port = ports.pop()
  join.client_ports.add(game_port=ports.pop(), base_port=ports.pop())

  threads = [
      threading.Thread(target=human_runner, args=(controllers[0], join)),
      threading.Thread(target=agent_runner, args=(controllers[1], join)),
  ]
  for t in threads:
    t.start()
  for t in threads:
    t.join()


def entry_point():  # Needed so setup.py scripts work.
  app.run(main)


if __name__ == "__main__":
  app.run(main)
