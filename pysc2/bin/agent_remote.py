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
r"""Play an agent with an SC2 instance that isn't owned.

This can be used to play on the sc2ai.net ladder, as well as to play vs humans.

To play on ladder:
  $ python -m pysc2.bin.agent_remote --agent <import path> \
      --host_port <GamePort> --lan_port <StartPort>

To play vs humans:
  $ python -m pysc2.bin.agent_remote --human --map <MapName>
then copy the string it generates which is something similar to above

If you want to play remotely, you'll need to port forward (eg with ssh -L or -R)
the host_port from localhost on one machine to localhost on the other.

You can also set your race, observation options, etc by cmdline flags.

When playing vs humans it launches both instances on the human side. This means
you only need to port-forward a single port (ie the websocket betwen SC2 and the
agent), but you also need to transfer the entire observation, which is much
bigger than the actions transferred over the lan connection between the two SC2
instances. It also makes it easy to maintain version compatibility since they
are the same binary. Unfortunately it means higher cpu usage where the human is
playing, which on a Mac becomes problematic as OSX slows down the instance
running in the background. There can also be observation differences between
Mac/Win and Linux. For these reasons, prefer play_vs_agent which runs the
instance next to the agent, and tunnels the lan actions instead.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import getpass
import importlib
from absl import logging
import platform
import sys
import time

from absl import app
from absl import flags

from pysc2 import maps
from pysc2 import run_configs
from pysc2.env import remote_sc2_env
from pysc2.env import run_loop
from pysc2.env import sc2_env
from pysc2.lib import point_flag
from pysc2.lib import portspicker
from pysc2.lib import renderer_human

from s2clientprotocol import sc2api_pb2 as sc_pb

FLAGS = flags.FLAGS
flags.DEFINE_bool("render", platform.system() == "Linux",
                  "Whether to render with pygame.")
flags.DEFINE_bool("realtime", False, "Whether to run in realtime mode.")

flags.DEFINE_string("agent", "pysc2.agents.random_agent.RandomAgent",
                    "Which agent to run, as a python path to an Agent class.")
flags.DEFINE_string("agent_name", None,
                    "Name of the agent in replays. Defaults to the class name.")
flags.DEFINE_enum("agent_race", "random", sc2_env.Race._member_names_,  # pylint: disable=protected-access
                  "Agent's race.")

flags.DEFINE_float("fps", 22.4, "Frames per second to run the game.")
flags.DEFINE_integer("step_mul", 8, "Game steps per agent step.")

point_flag.DEFINE_point("feature_screen_size", "84",
                        "Resolution for screen feature layers.")
point_flag.DEFINE_point("feature_minimap_size", "64",
                        "Resolution for minimap feature layers.")
point_flag.DEFINE_point("rgb_screen_size", "256",
                        "Resolution for rendered screen.")
point_flag.DEFINE_point("rgb_minimap_size", "128",
                        "Resolution for rendered minimap.")
flags.DEFINE_enum("action_space", "FEATURES",
                  sc2_env.ActionSpace._member_names_,  # pylint: disable=protected-access
                  "Which action space to use. Needed if you take both feature "
                  "and rgb observations.")
flags.DEFINE_bool("use_feature_units", False,
                  "Whether to include feature units.")

flags.DEFINE_string("user_name", getpass.getuser(),
                    "Name of the human player for replays.")
flags.DEFINE_enum("user_race", "random", sc2_env.Race._member_names_,  # pylint: disable=protected-access
                  "User's race.")

flags.DEFINE_string("host", "127.0.0.1", "Game Host")
flags.DEFINE_integer("host_port", None, "Host port")
flags.DEFINE_integer("lan_port", None, "Host port")

flags.DEFINE_string("map", None, "Name of a map to use to play.")

flags.DEFINE_bool("human", False, "Whether to host a game as a human.")

flags.DEFINE_integer("timeout_seconds", 300,
                     "Time in seconds for the remote agent to connect to the "
                     "game before an exception is raised.")


def main(unused_argv):
  if FLAGS.human:
    human()
  else:
    agent()


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
      name=FLAGS.agent_name or agent_name,
      race=sc2_env.Race[FLAGS.agent_race],
      step_mul=FLAGS.step_mul,
      agent_interface_format=sc2_env.parse_agent_interface_format(
          feature_screen=FLAGS.feature_screen_size,
          feature_minimap=FLAGS.feature_minimap_size,
          rgb_screen=FLAGS.rgb_screen_size,
          rgb_minimap=FLAGS.rgb_minimap_size,
          action_space=FLAGS.action_space,
          use_feature_units=FLAGS.use_feature_units),
      visualize=FLAGS.render) as env:
    agents = [agent_cls()]
    logging.info("Connected, starting run_loop.")
    try:
      run_loop.run_loop(agents, env)
    except remote_sc2_env.RestartException:
      pass
  logging.info("Done.")


def human():
  """Run a host which expects one player to connect remotely."""
  run_config = run_configs.get()

  map_inst = maps.get(FLAGS.map)

  if not FLAGS.rgb_screen_size or not FLAGS.rgb_minimap_size:
    logging.info("Use --rgb_screen_size and --rgb_minimap_size if you want rgb "
                 "observations.")

  ports = portspicker.pick_contiguous_unused_ports(4)  # 2 * num_players
  host_proc = run_config.start(extra_ports=ports, host=FLAGS.host,
                               timeout_seconds=FLAGS.timeout_seconds,
                               window_loc=(50, 50))
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
  print("Join host: agent_remote --map %s --host %s --host_port %s "
        "--lan_port %s" % (FLAGS.map, FLAGS.host, client_proc.port, ports[0]))
  print("-" * 80)
  sys.stdout.flush()

  join = sc_pb.RequestJoinGame()
  join.shared_port = 0  # unused
  join.server_ports.game_port = ports.pop(0)
  join.server_ports.base_port = ports.pop(0)
  join.client_ports.add(game_port=ports.pop(0), base_port=ports.pop(0))

  join.race = sc2_env.Race[FLAGS.user_race]
  join.player_name = FLAGS.user_name
  if FLAGS.render:
    join.options.raw = True
    join.options.score = True
    if FLAGS.feature_screen_size and FLAGS.feature_minimap_size:
      fl = join.options.feature_layer
      fl.width = 24
      FLAGS.feature_screen_size.assign_to(fl.resolution)
      FLAGS.feature_minimap_size.assign_to(fl.minimap_resolution)
    if FLAGS.rgb_screen_size and FLAGS.rgb_minimap_size:
      FLAGS.rgb_screen_size.assign_to(join.options.render.resolution)
      FLAGS.rgb_minimap_size.assign_to(join.options.render.minimap_resolution)
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

  portspicker.return_ports(ports)


def entry_point():  # Needed so setup.py scripts work.
  app.run(main)


if __name__ == "__main__":
  app.run(main)
