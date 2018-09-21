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
"""A Starcraft II environment for playing LAN games vs humans.

Check pysc2/bin/play_vs_agent.py for documentation.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import binascii
import collections
import hashlib
import json
from absl import logging
import os
import socket
import struct
import subprocess
import threading
import time

from future.builtins import range  # pylint: disable=redefined-builtin
from pysc2 import run_configs
from pysc2.env import sc2_env
from pysc2.lib import run_parallel
import whichcraft

from s2clientprotocol import sc2api_pb2 as sc_pb


class Addr(collections.namedtuple("Addr", ["ip", "port"])):

  def __str__(self):
    ip = "[%s]" % self.ip if ":" in self.ip else self.ip
    return "%s:%s" % (ip, self.port)


def daemon_thread(target, args):
  t = threading.Thread(target=target, args=args)
  t.daemon = True
  t.start()
  return t


def udp_server(addr):
  family = socket.AF_INET6 if ":" in addr.ip else socket.AF_INET
  sock = socket.socket(family, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
  sock.bind(addr)
  return sock


def tcp_server(tcp_addr, settings):
  """Start up the tcp server, send the settings."""
  family = socket.AF_INET6 if ":" in tcp_addr.ip else socket.AF_INET
  sock = socket.socket(family, socket.SOCK_STREAM, socket.IPPROTO_TCP)
  sock.bind(tcp_addr)
  sock.listen(1)
  logging.info("Waiting for connection on %s", tcp_addr)
  conn, addr = sock.accept()
  logging.info("Accepted connection from %s", Addr(*addr))

  # Send map_data independently for py2/3 and json encoding reasons.
  write_tcp(conn, settings["map_data"])
  send_settings = {k: v for k, v in settings.items() if k != "map_data"}
  logging.debug("settings: %s", send_settings)
  write_tcp(conn, json.dumps(send_settings).encode())
  return conn


def tcp_client(tcp_addr):
  """Connect to the tcp server, and return the settings."""
  family = socket.AF_INET6 if ":" in tcp_addr.ip else socket.AF_INET
  sock = socket.socket(family, socket.SOCK_STREAM, socket.IPPROTO_TCP)
  for i in range(300):
    logging.info("Connecting to: %s, attempt %d", tcp_addr, i)
    try:
      sock.connect(tcp_addr)
      break
    except socket.error:
      time.sleep(1)
  else:
    sock.connect(tcp_addr)  # One last try, but don't catch this error.
  logging.info("Connected.")

  map_data = read_tcp(sock)
  settings_str = read_tcp(sock)
  if not settings_str:
    raise socket.error("Failed to read")
  settings = json.loads(settings_str.decode())
  logging.info("Got settings. map_name: %s.", settings["map_name"])
  logging.debug("settings: %s", settings)
  settings["map_data"] = map_data
  return sock, settings


def log_msg(prefix, msg):
  logging.debug("%s: len: %s, hash: %s, msg: 0x%s", prefix, len(msg),
                hashlib.md5(msg).hexdigest()[:6], binascii.hexlify(msg[:25]))


def udp_to_tcp(udp_sock, tcp_conn):
  while True:
    msg, _ = udp_sock.recvfrom(2**16)
    log_msg("read_udp", msg)
    if not msg:
      return
    write_tcp(tcp_conn, msg)


def tcp_to_udp(tcp_conn, udp_sock, udp_to_addr):
  while True:
    msg = read_tcp(tcp_conn)
    if not msg:
      return
    log_msg("write_udp", msg)
    udp_sock.sendto(msg, udp_to_addr)


def read_tcp(conn):
  read_size = read_tcp_size(conn, 4)
  if not read_size:
    return
  size = struct.unpack("@I", read_size)[0]
  msg = read_tcp_size(conn, size)
  log_msg("read_tcp", msg)
  return msg


def read_tcp_size(conn, size):
  """Read `size` number of bytes from `conn`, retrying as needed."""
  chunks = []
  bytes_read = 0
  while bytes_read < size:
    chunk = conn.recv(size - bytes_read)
    if not chunk:
      if bytes_read > 0:
        logging.warning("Incomplete read: %s of %s.", bytes_read, size)
      return
    chunks.append(chunk)
    bytes_read += len(chunk)
  return b"".join(chunks)


def write_tcp(conn, msg):
  log_msg("write_tcp", msg)
  conn.sendall(struct.pack("@I", len(msg)))
  conn.sendall(msg)


def forward_ports(remote_host, local_host, local_listen_ports,
                  remote_listen_ports):
  """Forwards ports such that multiplayer works between machines.

  Args:
    remote_host: Where to ssh to.
    local_host: "127.0.0.1" or "::1".
    local_listen_ports: Which ports to listen on locally to forward remotely.
    remote_listen_ports: Which ports to listen on remotely to forward locally.

  Returns:
    The ssh process.

  Raises:
    ValueError: if it can't find ssh.
  """
  if ":" in local_host and not local_host.startswith("["):
    local_host = "[%s]" % local_host

  ssh = whichcraft.which("ssh") or whichcraft.which("plink")
  if not ssh:
    raise ValueError("Couldn't find an ssh client.")

  args = [ssh, remote_host]
  for local_port in local_listen_ports:
    args += ["-L", "%s:%s:%s:%s" % (local_host, local_port,
                                    local_host, local_port)]
  for remote_port in remote_listen_ports:
    args += ["-R", "%s:%s:%s:%s" % (local_host, remote_port,
                                    local_host, remote_port)]

  logging.info("SSH port forwarding: %s", " ".join(args))
  return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          stdin=subprocess.PIPE, close_fds=(os.name == "posix"))


class RestartException(Exception):
  pass


class LanSC2Env(sc2_env.SC2Env):
  """A Starcraft II environment for playing vs humans over LAN.

  This owns a single instance, and expects to join a game hosted by some other
  script, likely play_vs_agent.py.
  """

  def __init__(self,  # pylint: disable=invalid-name
               _only_use_kwargs=None,
               host="127.0.0.1",
               config_port=None,
               race=None,
               name="<unknown>",
               agent_interface_format=None,
               discount=1.,
               visualize=False,
               step_mul=None,
               realtime=False,
               replay_dir=None,
               replay_prefix=None):
    """Create a SC2 Env that connects to a remote instance of the game.

    This assumes that the game is already up and running, and it only needs to
    join. You need some other script to launch the process and call
    RequestCreateGame. It also assumes that it's a multiplayer game, and that
    the ports are consecutive.

    You must pass a resolution that you want to play at. You can send either
    feature layer resolution or rgb resolution or both. If you send both you
    must also choose which to use as your action space. Regardless of which you
    choose you must send both the screen and minimap resolutions.

    For each of the 4 resolutions, either specify size or both width and
    height. If you specify size then both width and height will take that value.

    Args:
      _only_use_kwargs: Don't pass args, only kwargs.
      host: Which ip to use. Either ipv4 or ipv6 localhost.
      config_port: Where to find the config port.
      race: Race for this agent.
      name: The name of this agent, for saving in the replay.
      agent_interface_format: AgentInterfaceFormat object describing the
          format of communication between the agent and the environment.
      discount: Returned as part of the observation.
      visualize: Whether to pop up a window showing the camera and feature
          layers. This won't work without access to a window manager.
      step_mul: How many game steps per agent step (action/observation). None
          means use the map default.
      realtime: Whether to use realtime mode. In this mode the game simulation
          automatically advances (at 22.4 gameloops per second) rather than
          being stepped manually. The number of game loops advanced with each
          call to step() won't necessarily match the step_mul specified. The
          environment will attempt to honour step_mul, returning observations
          with that spacing as closely as possible. Game loops will be skipped
          if they cannot be retrieved and processed quickly enough.
      replay_dir: Directory to save a replay.
      replay_prefix: An optional prefix to use when saving replays.

    Raises:
      ValueError: if the race is invalid.
      ValueError: if the resolutions aren't specified correctly.
      ValueError: if the host or port are invalid.
    """
    if _only_use_kwargs:
      raise ValueError("All arguments must be passed as keyword arguments.")

    if host not in ("127.0.0.1", "::1"):
      raise ValueError("Bad host arguments. Must be a localhost")
    if not config_port:
      raise ValueError("Must pass a config_port.")

    if agent_interface_format is None:
      raise ValueError("Please specify agent_interface_format.")

    if not race:
      race = sc2_env.Race.random

    self._num_agents = 1
    self._discount = discount
    self._step_mul = step_mul or 8
    self._realtime = realtime
    self._last_step_time = None
    self._save_replay_episodes = 1 if replay_dir else 0
    self._replay_dir = replay_dir
    self._replay_prefix = replay_prefix

    self._score_index = -1  # Win/loss only.
    self._score_multiplier = 1
    self._episode_length = 0  # No limit.
    self._ensure_available_actions = False
    self._discount_zero_after_timeout = False

    self._run_config = run_configs.get()
    self._parallel = run_parallel.RunParallel()  # Needed for multiplayer.

    interface = self._get_interface(
        agent_interface_format=agent_interface_format, require_raw=visualize)

    self._launch_remote(host, config_port, race, name, interface)

    self._finalize([agent_interface_format], [interface], visualize)

  def _launch_remote(self, host, config_port, race, name, interface):
    """Make sure this stays synced with bin/play_vs_agent.py."""
    self._tcp_conn, settings = tcp_client(Addr(host, config_port))

    self._map_name = settings["map_name"]

    if settings["remote"]:
      self._udp_sock = udp_server(
          Addr(host, settings["ports"]["server"]["game"]))

      daemon_thread(tcp_to_udp,
                    (self._tcp_conn, self._udp_sock,
                     Addr(host, settings["ports"]["client"]["game"])))

      daemon_thread(udp_to_tcp, (self._udp_sock, self._tcp_conn))

    extra_ports = [
        settings["ports"]["server"]["game"],
        settings["ports"]["server"]["base"],
        settings["ports"]["client"]["game"],
        settings["ports"]["client"]["base"],
    ]

    self._sc2_procs = [self._run_config.start(
        extra_ports=extra_ports, host=host, version=settings["game_version"],
        window_loc=(700, 50), want_rgb=interface.HasField("render"))]
    self._controllers = [p.controller for p in self._sc2_procs]

    # Create the join request.
    join = sc_pb.RequestJoinGame(options=interface)
    join.race = race
    join.player_name = name
    join.shared_port = 0  # unused
    join.server_ports.game_port = settings["ports"]["server"]["game"]
    join.server_ports.base_port = settings["ports"]["server"]["base"]
    join.client_ports.add(game_port=settings["ports"]["client"]["game"],
                          base_port=settings["ports"]["client"]["base"])

    self._controllers[0].save_map(settings["map_path"], settings["map_data"])
    self._controllers[0].join_game(join)

  def _restart(self):
    # Can't restart since it's not clear how you'd coordinate that with the
    # other players.
    raise RestartException("Can't restart")

  def close(self):
    if hasattr(self, "_tcp_conn") and self._tcp_conn:
      self._tcp_conn.close()
      self._tcp_conn = None
    if hasattr(self, "_udp_sock") and self._udp_sock:
      self._udp_sock.close()
      self._udp_sock = None
    super(LanSC2Env, self).close()
