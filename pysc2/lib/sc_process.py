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
"""Launch the game and set up communication."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import logging
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

from future.builtins import range  # pylint: disable=redefined-builtin

import portpicker
from pysc2.lib import protocol
from pysc2.lib import remote_controller
from pysc2.lib import stopwatch
import websocket

from absl import flags

flags.DEFINE_bool("sc2_verbose", False, "Enable SC2 verbose logging.")
FLAGS = flags.FLAGS

sw = stopwatch.sw


class StarcraftProcess(object):
  """Launch a starcraft server, initialize a controller, and later, clean up.

  This is best used from run_configs.py. It is important to call `close`,
  otherwise you'll likely leak temp files and SC2 processes (chewing CPU).

  Usage:
    p = StarcraftProcess(run_config)
    p.controller.ping()
    p.close()
  or:
    with StarcraftProcess(run_config) as controller:
      controller.ping()
  """

  def __init__(self, run_config, full_screen=False, game_version=None,
               data_version=None, verbose=False, **kwargs):
    self._proc = None
    self._sock = None
    self._controller = None
    self._tmp_dir = tempfile.mkdtemp(prefix="sc-", dir=run_config.tmp_dir)
    self._port = portpicker.pick_unused_port()
    exec_path = run_config.exec_path(game_version)
    self._check_exists(exec_path)

    args = [
        exec_path,
        "-listen", "127.0.0.1",
        "-port", str(self._port),
        "-dataDir", os.path.join(run_config.data_dir, ""),
        "-tempDir", os.path.join(self._tmp_dir, ""),
        "-displayMode", "1" if full_screen else "0",
    ]
    if verbose or FLAGS.sc2_verbose:
      args += ["-verbose"]
    if data_version:
      args += ["-dataVersion", data_version.upper()]
    try:
      self._proc = self._launch(run_config, args, **kwargs)
      self._sock = self._connect(self._port)
      client = protocol.StarcraftProtocol(self._sock)
      self._controller = remote_controller.RemoteController(client)
      with sw("startup"):
        self._controller.ping()
    except:
      self.close()
      raise

  @sw.decorate
  def close(self):
    """Shut down the game and clean up."""
    self._shutdown()
    self._proc = None
    self._sock = None
    self._controller = None
    if hasattr(self, "_port") and self._port:
      portpicker.return_port(self._port)
      self._port = None
    if os.path.exists(self._tmp_dir):
      shutil.rmtree(self._tmp_dir)

  @property
  def controller(self):
    return self._controller

  def __enter__(self):
    return self.controller

  def __exit__(self, unused_exception_type, unused_exc_value, unused_traceback):
    self.close()

  def __del__(self):
    # Prefer using a context manager, but this cleans most other cases.
    self.close()

  def _check_exists(self, exec_path):
    if not os.path.isfile(exec_path):
      raise RuntimeError("Trying to run '%s', but it doesn't exist" % exec_path)
    if not os.access(exec_path, os.X_OK):
      raise RuntimeError(
          "Trying to run '%s', but it isn't executable." % exec_path)

  def _launch(self, run_config, args, **kwargs):
    """Launch the process and return the process object."""
    del kwargs
    try:
      with sw("popen"):
        return subprocess.Popen(args, cwd=run_config.cwd, env=run_config.env)
    except OSError:
      logging.exception("Failed to launch")
      sys.exit("Failed to launch: " + str(args))

  @sw.decorate
  def _connect(self, port):
    """Connect to the websocket, retrying as needed. Returns the socket."""
    was_running = False
    for i in range(120):
      is_running = self.running
      was_running = was_running or is_running
      if (i >= 30 or was_running) and not is_running:
        logging.warning(
            "SC2 isn't running, so bailing early on the websocket connection.")
        break
      logging.info("Connection attempt %s (running: %s)", i, is_running)
      time.sleep(1)
      try:
        return websocket.create_connection("ws://127.0.0.1:%s/sc2api" % port,
                                           timeout=2 * 60)  # 2 minutes
      except socket.error:
        pass  # SC2 hasn't started listening yet.
      except websocket.WebSocketException as err:
        if "Handshake Status 404" in str(err):
          pass  # SC2 is listening, but hasn't set up the /sc2api endpoint yet.
        else:
          raise
    sys.exit("Failed to create the socket.")

  def _shutdown(self):
    """Terminate the sub-process."""
    if self._proc:
      ret = _shutdown_proc(self._proc, 3)
      logging.info("Shutdown with return code: %s", ret)
      self._proc = None

  @property
  def running(self):
    return self._proc.poll() if self._proc else False


def _shutdown_proc(p, timeout):
  """Wait for a proc to shut down, then terminate or kill it after `timeout`."""
  freq = 10  # how often to check per second
  for _ in range(1 + timeout * freq):
    ret = p.poll()
    if ret is not None:
      logging.info("Shutdown gracefully.")
      return ret
    time.sleep(1 / freq)
  logging.warning("Killing the process.")
  p.kill()
  return p.wait()
