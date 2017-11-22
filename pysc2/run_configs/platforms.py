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
import os
import platform

from absl import flags

from pysc2.lib import sc_process
from pysc2.run_configs import lib

# https://github.com/Blizzard/s2client-proto/blob/master/buildinfo/versions.json
VERSIONS = {ver.game_version: ver for ver in [
    lib.Version("3.16.1", 55958, "5BD7C31B44525DAB46E64C4602A81DC2", None),
    lib.Version("3.17.0", 56787, "DFD1F6607F2CF19CB4E1C996B2563D9B", None),
    lib.Version("3.17.1", 56787, "3F2FCED08798D83B873B5543BEFA6C4B", None),
    lib.Version("3.17.2", 56787, "C690FC543082D35EA0AAA876B8362BEA", None),
    lib.Version("3.18.0", 57507, "1659EF34997DA3470FF84A14431E3A86", None),
    lib.Version("3.19.0", 58400, "2B06AEE58017A7DF2A3D452D733F1019", None),
    lib.Version("3.19.1", 58400, "D9B568472880CC4719D1B698C0D86984", None),
    lib.Version("4.0.0", 59587, "9B4FD995C61664831192B7DA46F8C1A1", None),
]}

flags.DEFINE_enum("sc2_version", None, sorted(VERSIONS.keys()),
                  "Which version of the game to use.")
FLAGS = flags.FLAGS


def _get_version(game_version):
  if game_version.count(".") == 1:
    game_version += ".0"
  if game_version not in VERSIONS:
    raise ValueError("Unknown game version: %s. Known versions: %s" % (
        game_version, sorted(VERSIONS.keys())))
  return VERSIONS[game_version]


def _read_execute_info(path, parents):
  """Read the ExecuteInfo.txt file and return the base directory."""
  path = os.path.join(path, "StarCraft II/ExecuteInfo.txt")
  if os.path.exists(path):
    with open(path, "rb") as f:  # Binary because the game appends a '\0' :(.
      for line in f:
        parts = [p.strip() for p in line.split("=")]
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

  def start(self, version=None, **kwargs):
    """Launch the game."""
    if not os.path.isdir(self.data_dir):
      raise lib.SC2LaunchError(
          "Expected to find StarCraft II installed at '%s'. If it's not "
          "installed, do that and run it once so auto-detection works. If "
          "auto-detection failed repeatedly, then set the SC2PATH environment "
          "variable with the correct location." % self.data_dir)

    version = version or FLAGS.sc2_version
    if isinstance(version, lib.Version) and not version.data_version:
      # This is for old replays that don't have the embedded data_version.
      version = _get_version(version.game_version)
    elif isinstance(version, str):
      version = _get_version(version)
    elif not version:
      versions_dir = os.path.join(self.data_dir, "Versions")
      build_version = max(int(v[4:]) for v in os.listdir(versions_dir)
                          if v.startswith("Base"))
      version = lib.Version(None, build_version, None, None)
    if version.build_version < VERSIONS["3.16.1"].build_version:
      raise lib.SC2LaunchError(
          "SC2 Binaries older than 3.16.1 don't support the api.")
    exec_path = os.path.join(
        self.data_dir, "Versions/Base%s" % version.build_version,
        self._exec_name)

    return sc_process.StarcraftProcess(
        self, exec_path=exec_path, data_version=version.data_version, **kwargs)


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

  def start(self, **kwargs):
    extra_args = kwargs.pop("extra_args", [])
    extra_args += [
        # Defaults on Ubuntu. These can be a full paths.
        "-eglpath", "libEGL.so.1",
        "-osmesapath", "libOSMesa.so.6",
    ]
    return super(Linux, self).start(extra_args=extra_args, **kwargs)
