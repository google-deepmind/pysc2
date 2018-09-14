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
"""Configs for how to run SC2 from a normal install on various platforms."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import copy
from absl import logging
import os
import platform
import subprocess
import sys

from absl import flags
import six

from pysc2.lib import sc_process
from pysc2.run_configs import lib


flags.DEFINE_enum("sc2_version", None, sorted(lib.VERSIONS.keys()),
                  "Which version of the game to use.")
flags.DEFINE_bool("sc2_dev_build", False,
                  "Use a dev build. Mostly useful for testing by Blizzard.")
FLAGS = flags.FLAGS


def _read_execute_info(path, parents):
  """Read the ExecuteInfo.txt file and return the base directory."""
  path = os.path.join(path, "StarCraft II/ExecuteInfo.txt")
  if os.path.exists(path):
    with open(path, "rb") as f:  # Binary because the game appends a '\0' :(.
      for line in f:
        parts = [p.strip() for p in line.decode("utf-8").split("=")]
        if len(parts) == 2 and parts[0] == "executable":
          exec_path = parts[1].replace("\\", "/")  # For windows compatibility.
          for _ in range(parents):
            exec_path = os.path.dirname(exec_path)
          return exec_path


class LocalBase(lib.RunConfig):
  """Base run config for public installs."""

  def __init__(self, base_dir, exec_name, cwd=None, env=None):
    base_dir = os.path.expanduser(base_dir)
    cwd = cwd and os.path.join(base_dir, cwd)
    super(LocalBase, self).__init__(
        replay_dir=os.path.join(base_dir, "Replays"),
        data_dir=base_dir, tmp_dir=None, cwd=cwd, env=env)
    self._exec_name = exec_name

  def start(self, version=None, want_rgb=True, **kwargs):
    """Launch the game."""
    del want_rgb  # Unused
    if not os.path.isdir(self.data_dir):
      raise sc_process.SC2LaunchError(
          "Expected to find StarCraft II installed at '%s'. If it's not "
          "installed, do that and run it once so auto-detection works. If "
          "auto-detection failed repeatedly, then set the SC2PATH environment "
          "variable with the correct location." % self.data_dir)

    version = version or FLAGS.sc2_version
    if isinstance(version, lib.Version) and not version.data_version:
      # This is for old replays that don't have the embedded data_version.
      version = self._get_version(version.game_version)
    elif isinstance(version, six.string_types):
      version = self._get_version(version)
    elif not version:
      version = self._get_version("latest")
    if version.build_version < lib.VERSIONS["3.16.1"].build_version:
      raise sc_process.SC2LaunchError(
          "SC2 Binaries older than 3.16.1 don't support the api.")
    if FLAGS.sc2_dev_build:
      version = version._replace(build_version=0)
    exec_path = os.path.join(
        self.data_dir, "Versions/Base%05d" % version.build_version,
        self._exec_name)

    if not os.path.exists(exec_path):
      raise sc_process.SC2LaunchError("No SC2 binary found at: %s" % exec_path)

    return sc_process.StarcraftProcess(
        self, exec_path=exec_path, version=version, **kwargs)

  def get_versions(self):
    versions_dir = os.path.join(self.data_dir, "Versions")
    version_prefix = "Base"
    versions_found = sorted(int(v[len(version_prefix):])
                            for v in os.listdir(versions_dir)
                            if v.startswith(version_prefix))
    if not versions_found:
      raise sc_process.SC2LaunchError(
          "No SC2 Versions found in %s" % versions_dir)
    known_versions = [v for v in lib.VERSIONS.values()
                      if v.build_version in versions_found]
    # Add one more with the max version. That one doesn't need a data version
    # since SC2 will find it in the .build.info file. This allows running
    # versions newer than what are known by pysc2, and so is the default.
    known_versions.append(
        lib.Version("latest", max(versions_found), None, None))
    return lib.version_dict(known_versions)


class Windows(LocalBase):
  """Run on Windows."""

  def __init__(self):
    exec_path = (os.environ.get("SC2PATH") or
                 _read_execute_info(os.path.expanduser("~/Documents"), 3) or
                 "C:/Program Files (x86)/StarCraft II")
    super(Windows, self).__init__(exec_path, "SC2_x64.exe", "Support64")

  @classmethod
  def priority(cls):
    if platform.system() == "Windows":
      return 1


class Cygwin(LocalBase):
  """Run on Cygwin. This runs the windows binary within a cygwin terminal."""

  def __init__(self):
    super(Cygwin, self).__init__(
        os.environ.get("SC2PATH",
                       "/cygdrive/c/Program Files (x86)/StarCraft II"),
        "SC2_x64.exe", "Support64")

  @classmethod
  def priority(cls):
    if sys.platform == "cygwin":
      return 1


class MacOS(LocalBase):
  """Run on MacOS."""

  def __init__(self):
    exec_path = (os.environ.get("SC2PATH") or
                 _read_execute_info(os.path.expanduser(
                     "~/Library/Application Support/Blizzard"), 6) or
                 "/Applications/StarCraft II")
    super(MacOS, self).__init__(exec_path, "SC2.app/Contents/MacOS/SC2")

  @classmethod
  def priority(cls):
    if platform.system() == "Darwin":
      return 1


class Linux(LocalBase):
  """Config to run on Linux."""

  known_mesa = [  # In priority order
      "libOSMesa.so",
      "libOSMesa.so.8",  # Ubuntu 16.04
      "libOSMesa.so.6",  # Ubuntu 14.04
  ]

  def __init__(self):
    base_dir = os.environ.get("SC2PATH", "~/StarCraftII")
    base_dir = os.path.expanduser(base_dir)
    env = copy.deepcopy(os.environ)
    env["LD_LIBRARY_PATH"] = ":".join(filter(None, [
        os.environ.get("LD_LIBRARY_PATH"),
        os.path.join(base_dir, "Libs/")]))
    super(Linux, self).__init__(base_dir, "SC2_x64", env=env)

  @classmethod
  def priority(cls):
    if platform.system() == "Linux":
      return 1

  def start(self, want_rgb=True, **kwargs):
    extra_args = kwargs.pop("extra_args", [])

    if want_rgb:
      # Figure out whether the various GL libraries exist since SC2 sometimes
      # fails if you ask to use a library that doesn't exist.
      libs = subprocess.check_output(["/sbin/ldconfig", "-p"]).decode()
      libs = {lib.strip().split()[0] for lib in libs.split("\n") if lib}
      if "libEGL.so" in libs:  # Prefer hardware rendering.
        extra_args += ["-eglpath", "libEGL.so"]
      else:
        for mesa_lib in self.known_mesa:  # Look for a software renderer.
          if mesa_lib in libs:
            extra_args += ["-osmesapath", mesa_lib]
            break
        else:
          logging.info(
              "No GL library found, so RGB rendering will be disabled. "
              "For software rendering install libosmesa.")

    return super(Linux, self).start(
        want_rgb=want_rgb, extra_args=extra_args, **kwargs)
