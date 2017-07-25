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

import logging
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

import portpicker
from pysc2.lib import protocol
from pysc2.lib import remote_controller
from pysc2.lib import stopwatch
import websocket


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

  def __init__(self, run_config, **kwargs):
    self._proc = None
    self._sock = None
    self._controller = None
    self._tmp_dir = tempfile.mkdtemp(prefix="sc-", dir=run_config.tmp_dir)
    self._port = portpicker.pick_unused_port()
    self._check_exists(run_config.exec_path)

    args = [
        run_config.exec_path,
        "-listen", "127.0.0.1",
        "-port", str(self._port),
        "-dataDir", run_config.data_dir + "/",
        "-tempDir", self._tmp_dir + "/",
        "-displayMode", "0",  # On windows/mac run in a window, not fullscreen.
    ]
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
    if not os.path.isfile(exec_path) or not os.access(exec_path, os.X_OK):
      raise RuntimeError(
          "Trying to run '%s', but it doesn't exist or isn't executable." %
          exec_path)

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
    was_running = self.running
    for i in xrange(120):
      was_running = was_running or self.running
      if (i >= 30 or was_running) and not self.running:
        logging.warning("SC2 isn't even running, so bailing early on the "
                        "websocket connection.")
        break
      logging.info("Connection attempt %s", i)
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
  for _ in xrange(1 + timeout * freq):
    ret = p.poll()
    if ret is not None:
      logging.info("Shutdown gracefully.")
      return ret
    time.sleep(1 / freq)
  for attempt in xrange(3):
    # We would like SC2 to shut down cleanly, but become forceful if needed.
    logging.warning("Terminating attempt %s...", attempt)
    p.terminate()
    for _ in xrange(1 + timeout * freq):
      ret = p.poll()
      if ret is not None:
        logging.warning("Terminated.")
        return ret
      time.sleep(1 / freq)
  logging.warning("Killing the process.")
  p.kill()
  return p.wait()
