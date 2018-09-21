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
"""Play as a human against an agent by setting up a LAN game.

This needs to be called twice, once for the human, and once for the agent.

The human plays on the host. There you run it as:
$ python -m pysc2.bin.play_vs_agent --human --map <map> --remote <agent ip>

And on the machine the agent plays on:
$ python -m pysc2.bin.play_vs_agent --agent <import path>

The `--remote` arg is used to create an SSH tunnel to the remote agent's
machine, so can be dropped if it's running on the same machine.

SC2 is limited to only allow LAN games on localhost, so we need to forward the
ports between machines. SSH is used to do this with the `--remote` arg. If the
agent is on the same machine as the host, this arg can be dropped. SSH doesn't
forward UDP, so this also sets up a UDP proxy. As part of that it sets up a TCP
server that is also used as a settings server. Note that you won't have an
opportunity to give ssh a password, so you must use ssh keys for authentication.
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
import portpicker

from pysc2 import maps
from pysc2 import run_configs
from pysc2.env import lan_sc2_env
from pysc2.env import run_loop
from pysc2.env import sc2_env
from pysc2.lib import point_flag
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

flags.DEFINE_string("host", "127.0.0.1", "Game Host. Can be 127.0.0.1 or ::1")
flags.DEFINE_integer(
    "config_port", 14380,
    "Where to set/find the config port. The host starts a tcp server to share "
    "the config with the client, and to proxy udp traffic if played over an "
    "ssh tunnel. This sets that port, and is also the start of the range of "
    "ports used for LAN play.")
flags.DEFINE_string("remote", None,
                    "Where to set up the ssh tunnels to the client.")

flags.DEFINE_string("map", None, "Name of a map to use to play.")

flags.DEFINE_bool("human", False, "Whether to host a game as a human.")


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
  with lan_sc2_env.LanSC2Env(
      host=FLAGS.host,
      config_port=FLAGS.config_port,
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
    except lan_sc2_env.RestartException:
      pass
  logging.info("Done.")


def human():
  """Run a host which expects one player to connect remotely."""
  run_config = run_configs.get()

  map_inst = maps.get(FLAGS.map)

  if not FLAGS.rgb_screen_size or not FLAGS.rgb_minimap_size:
    logging.info("Use --rgb_screen_size and --rgb_minimap_size if you want rgb "
                 "observations.")

  ports = [FLAGS.config_port + p for p in range(5)]  # tcp + 2 * num_players
  if not all(portpicker.is_port_free(p) for p in ports):
    sys.exit("Need 5 free ports after the config port.")

  proc = None
  ssh_proc = None
  tcp_conn = None
  udp_sock = None
  try:
    proc = run_config.start(extra_ports=ports[1:], timeout_seconds=300,
                            host=FLAGS.host, window_loc=(50, 50))

    tcp_port = ports[0]
    settings = {
        "remote": FLAGS.remote,
        "game_version": proc.version.game_version,
        "realtime": FLAGS.realtime,
        "map_name": map_inst.name,
        "map_path": map_inst.path,
        "map_data": map_inst.data(run_config),
        "ports": {
            "server": {"game": ports[1], "base": ports[2]},
            "client": {"game": ports[3], "base": ports[4]},
        }
    }

    create = sc_pb.RequestCreateGame(
        realtime=settings["realtime"],
        local_map=sc_pb.LocalMap(map_path=settings["map_path"]))
    create.player_setup.add(type=sc_pb.Participant)
    create.player_setup.add(type=sc_pb.Participant)

    controller = proc.controller
    controller.save_map(settings["map_path"], settings["map_data"])
    controller.create_game(create)

    if FLAGS.remote:
      ssh_proc = lan_sc2_env.forward_ports(
          FLAGS.remote, proc.host, [settings["ports"]["client"]["base"]],
          [tcp_port, settings["ports"]["server"]["base"]])

    print("-" * 80)
    print("Join: play_vs_agent --host %s --config_port %s" % (proc.host,
                                                              tcp_port))
    print("-" * 80)

    tcp_conn = lan_sc2_env.tcp_server(
        lan_sc2_env.Addr(proc.host, tcp_port), settings)

    if FLAGS.remote:
      udp_sock = lan_sc2_env.udp_server(
          lan_sc2_env.Addr(proc.host, settings["ports"]["client"]["game"]))

      lan_sc2_env.daemon_thread(
          lan_sc2_env.tcp_to_udp,
          (tcp_conn, udp_sock,
           lan_sc2_env.Addr(proc.host, settings["ports"]["server"]["game"])))

      lan_sc2_env.daemon_thread(lan_sc2_env.udp_to_tcp, (udp_sock, tcp_conn))

    join = sc_pb.RequestJoinGame()
    join.shared_port = 0  # unused
    join.server_ports.game_port = settings["ports"]["server"]["game"]
    join.server_ports.base_port = settings["ports"]["server"]["base"]
    join.client_ports.add(game_port=settings["ports"]["client"]["game"],
                          base_port=settings["ports"]["client"]["base"])

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
  finally:
    if tcp_conn:
      tcp_conn.close()
    if proc:
      proc.close()
    if udp_sock:
      udp_sock.close()
    if ssh_proc:
      ssh_proc.terminate()
      for _ in range(5):
        if ssh_proc.poll() is not None:
          break
        time.sleep(1)
      if ssh_proc.poll() is None:
        ssh_proc.kill()
        ssh_proc.wait()


def entry_point():  # Needed so setup.py scripts work.
  app.run(main)


if __name__ == "__main__":
  app.run(main)
