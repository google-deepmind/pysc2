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
from absl import logging
import platform
import time

from absl import app
from absl import flags
import portpicker

from pysc2 import maps
from pysc2 import run_configs
from pysc2.env import remote_sc2_env
from pysc2.env import run_loop
from pysc2.env import sc2_env
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

flags.DEFINE_float("fps", 22.4, "Frames per second to run the game.")
flags.DEFINE_integer("step_mul", 8, "Game steps per agent step.")

flags.DEFINE_integer("feature_screen_size", 84,
                     "Resolution for screen feature layers.")
flags.DEFINE_integer("feature_minimap_size", 64,
                     "Resolution for minimap feature layers.")
flags.DEFINE_integer("rgb_screen_size", 256,
                     "Resolution for rendered screen.")
flags.DEFINE_integer("rgb_minimap_size", 128,
                     "Resolution for rendered minimap.")
flags.DEFINE_enum("action_space", "FEATURES",
                  sc2_env.ActionSpace._member_names_,  # pylint: disable=protected-access
                  "Which action space to use. Needed if you take both feature "
                  "and rgb observations.")
flags.DEFINE_bool("use_feature_units", False,
                  "Whether to include feature units.")

flags.DEFINE_enum("user_race", "random", sc2_env.Race._member_names_,  # pylint: disable=protected-access
                  "User's race.")

flags.DEFINE_string("host", "127.0.0.1", "Game Host")
flags.DEFINE_integer("host_port", None, "Host port")
flags.DEFINE_integer("lan_port", None, "Host port")

flags.DEFINE_string("map", None, "Name of a map to use to play.")


def main(unused_argv):
  """Run SC2 to play a game or a replay."""

  if FLAGS.host_port:
    agent()
  else:
    host()


def agent():
  """Run the agent, connecting to a (remote) host started independently."""
  agent_module, agent_name = FLAGS.agent.rsplit(".", 1)
  agent_cls = getattr(importlib.import_module(agent_module), agent_name)

  logging.info("Starting agent:")
  with remote_sc2_env.RemoteSC2Env(
      map_name=FLAGS.map,
      host=FLAGS.host,
      host_port=FLAGS.host_port,
      lan_port=FLAGS.lan_port,
      race=sc2_env.Race[FLAGS.agent_race],
      step_mul=FLAGS.step_mul,
      feature_screen_size=FLAGS.feature_screen_size,
      feature_minimap_size=FLAGS.feature_minimap_size,
      rgb_screen_size=FLAGS.rgb_screen_size,
      rgb_minimap_size=FLAGS.rgb_minimap_size,
      action_space=(FLAGS.action_space and
                    sc2_env.ActionSpace[FLAGS.action_space]),
      use_feature_units=FLAGS.use_feature_units,
      visualize=FLAGS.render) as env:
    agents = [agent_cls()]
    logging.info("Connected, starting run_loop.")
    try:
      run_loop.run_loop(agents, env)
    except remote_sc2_env.RestartException:
      pass
  logging.info("Done.")


def host():
  """Run a host which expects one player to connect remotely."""
  run_config = run_configs.get()

  map_inst = maps.get(FLAGS.map)

  if not FLAGS.rgb_screen_size or not FLAGS.rgb_minimap_size:
    logging.info("Use --rgb_screen_size and --rgb_minimap_size if you want rgb "
                 "observations.")

  while True:
    start_port = portpicker.pick_unused_port()
    ports = [start_port + p for p in range(4)]  # 2 * num_players
    if all(portpicker.is_port_free(p) for p in ports):
      break

  host_proc = run_config.start(extra_ports=ports, host=FLAGS.host,
                               timeout_seconds=300, window_loc=(50, 50))
  client_proc = run_config.start(extra_ports=ports, host=FLAGS.host,
                                 connect=False, window_loc=(700, 50))

  create = sc_pb.RequestCreateGame(
      realtime=FLAGS.realtime, local_map=sc_pb.LocalMap(map_path=map_inst.path))
  create.player_setup.add(type=sc_pb.Participant)
  create.player_setup.add(type=sc_pb.Participant)

  controller = host_proc.controller
  controller.save_map(map_inst.path, map_inst.data(run_config))
  controller.create_game(create)

  print("-" * 80)
  print("Join host: play_vs_agent --map %s --host %s --host_port %s "
        "--lan_port %s" % (FLAGS.map, FLAGS.host, client_proc.port, start_port))
  print("-" * 80)

  join = sc_pb.RequestJoinGame()
  join.shared_port = 0  # unused
  join.server_ports.game_port = ports.pop(0)
  join.server_ports.base_port = ports.pop(0)
  join.client_ports.add(game_port=ports.pop(0), base_port=ports.pop(0))

  join.race = sc2_env.Race[FLAGS.user_race]
  if FLAGS.render:
    join.options.raw = True
    join.options.score = True
    if FLAGS.feature_screen_size and FLAGS.feature_minimap_size:
      fl = join.options.feature_layer
      fl.width = 24
      fl.resolution.x = FLAGS.feature_screen_size
      fl.resolution.y = FLAGS.feature_screen_size
      fl.minimap_resolution.x = FLAGS.feature_minimap_size
      fl.minimap_resolution.y = FLAGS.feature_minimap_size
    if FLAGS.rgb_screen_size and FLAGS.rgb_minimap_size:
      join.options.render.resolution.x = FLAGS.rgb_screen_size
      join.options.render.resolution.y = FLAGS.rgb_screen_size
      join.options.render.minimap_resolution.x = FLAGS.rgb_minimap_size
      join.options.render.minimap_resolution.y = FLAGS.rgb_minimap_size
  controller.join_game(join)

  if FLAGS.render:
    renderer = renderer_human.RendererHuman(
        fps=FLAGS.fps, render_feature_grid=False)
    renderer.run(run_configs.get(), controller, max_episodes=1)
  else:  # Still step forward so the Mac/Windows renderer works.
    try:
      while True:
        frame_start_time = time.time()
        if not FLAGS.realtime:
          controller.step()
        obs = controller.observe()

        if obs.player_result:
          break
        time.sleep(max(0, frame_start_time - time.time() + 1 / FLAGS.fps))
    except KeyboardInterrupt:
      pass

  for p in [host_proc, client_proc]:
    p.close()


def entry_point():  # Needed so setup.py scripts work.
  app.run(main)


if __name__ == "__main__":
  app.run(main)
