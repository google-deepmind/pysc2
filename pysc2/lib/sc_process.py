# Copyright 2017-2018 Google Inc. All Rights Reserved.
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
import subprocess
import tempfile
import time

from absl import flags
from future.builtins import range  # pylint: disable=redefined-builtin

import portpicker
from pysc2.lib import remote_controller
from pysc2.lib import stopwatch

flags.DEFINE_bool("sc2_verbose", False, "Enable SC2 verbose logging.")
FLAGS = flags.FLAGS

sw = stopwatch.sw


class SC2LaunchError(Exception):
  pass


class StarcraftProcess(object):
  """Launch a starcraft server, initialize a controller, and later, clean up.

  This is best used from run_configs, which decides which version to run, and
  where to find it.

  It is important to call `close` or use it as a context manager, otherwise
  you'll likely leak temp files and SC2 processes.
  """

  def __init__(self, run_config, exec_path, version, full_screen=False,
               extra_args=None, verbose=False, host=None, port=None,
               connect=True, timeout_seconds=None, window_size=(640, 480),
               window_loc=(50, 50), **kwargs):
    """Launch the SC2 process.

    Args:
      run_config: `run_configs.lib.RunConfig` object.
      exec_path: Path to the binary to run.
      version: `run_configs.lib.Version` object.
      full_screen: Whether to launch the game window full_screen on win/mac.
      extra_args: List of additional args for the SC2 process.
      verbose: Whether to have the SC2 process do verbose logging.
      host: IP for the game to listen on for its websocket. This is
          usually "127.0.0.1", or "::1", but could be others as well.
      port: Port SC2 should listen on for the websocket.
      connect: Whether to create a RemoteController to connect.
      timeout_seconds: Timeout for the remote controller.
      window_size: Screen size if not full screen.
      window_loc: Screen location if not full screen.
      **kwargs: Extra arguments for _launch (useful for subclasses).
    """
    self._proc = None
    self._controller = None
    self._check_exists(exec_path)
    self._tmp_dir = tempfile.mkdtemp(prefix="sc-", dir=run_config.tmp_dir)
    self._host = host or "127.0.0.1"
    self._port = port or portpicker.pick_unused_port()
    self._version = version

    args = [
        exec_path,
        "-listen", self._host,
        "-port", str(self._port),
        "-dataDir", os.path.join(run_config.data_dir, ""),
        "-tempDir", os.path.join(self._tmp_dir, ""),
    ]
    if ":" in self._host:
      args += ["-ipv6"]
    if full_screen:
      args += ["-displayMode", "1"]
    else:
      args += [
          "-displayMode", "0",
          "-windowwidth", str(window_size[0]),
          "-windowheight", str(window_size[1]),
          "-windowx", str(window_loc[0]),
          "-windowy", str(window_loc[1]),
      ]

    if verbose or FLAGS.sc2_verbose:
      args += ["-verbose"]
    if self._version and self._version.data_version:
      args += ["-dataVersion", self._version.data_version.upper()]
    if extra_args:
      args += extra_args
    logging.info("Launching SC2: %s", " ".join(args))
    try:
      with sw("startup"):
        self._proc = self._launch(run_config, args, **kwargs)
        if connect:
          self._controller = remote_controller.RemoteController(
              self._host, self._port, self, timeout_seconds=timeout_seconds)
    except:
      self.close()
      raise

  @sw.decorate
  def close(self):
    """Shut down the game and clean up."""
    if hasattr(self, "_controller") and self._controller:
      self._controller.quit()
      self._controller.close()
      self._controller = None
    self._shutdown()
    if hasattr(self, "_port") and self._port:
      portpicker.return_port(self._port)
      self._port = None
    if hasattr(self, "_tmp_dir") and os.path.exists(self._tmp_dir):
      shutil.rmtree(self._tmp_dir)

  @property
  def controller(self):
    return self._controller

  @property
  def host(self):
    return self._host

  @property
  def port(self):
    return self._port

  @property
  def version(self):
    return self._version

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
      raise SC2LaunchError("Failed to launch: %s" % args)

  def _shutdown(self):
    """Terminate the sub-process."""
    if self._proc:
      ret = _shutdown_proc(self._proc, 3)
      logging.info("Shutdown with return code: %s", ret)
      self._proc = None

  @property
  def running(self):
    # poll returns None if it's running, otherwise the exit code.
    return self._proc and (self._proc.poll() is None)

  @property
  def pid(self):
    return self._proc.pid if self.running else None


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
