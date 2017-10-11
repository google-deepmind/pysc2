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

from pysc2.run_configs import lib

from absl import flags

# https://github.com/Blizzard/s2client-proto/blob/master/buildinfo/versions.json
VERSIONS = {  # Map of game version to build and data versions.
    "3.16.1": (55958, "5BD7C31B44525DAB46E64C4602A81DC2"),
    "3.17.0": (56787, "DFD1F6607F2CF19CB4E1C996B2563D9B"),
    "3.17.1": (56787, "3F2FCED08798D83B873B5543BEFA6C4B"),
    "3.17.2": (56787, "C690FC543082D35EA0AAA876B8362BEA"),
    "3.18.0": (57507, "1659EF34997DA3470FF84A14431E3A86"),
    "3.19.0": (58400, "2B06AEE58017A7DF2A3D452D733F1019"),
}

flags.DEFINE_enum("sc2_version", None, sorted(VERSIONS.keys()),
                  "Which version of the game to use.")
FLAGS = flags.FLAGS


def get_version(game_version):
  if game_version.count(".") == 1:
    game_version += ".0"
  if game_version not in VERSIONS:
    raise ValueError("Unknown game version: %s. Known versions: %s" % (
        game_version, sorted(VERSIONS.keys())))
  return VERSIONS[game_version]


class LocalBase(lib.RunConfig):
  """Base run config for the deepmind file hierarchy."""

  def __init__(self, base_dir, exec_name, cwd=None, env=None):
    base_dir = os.path.expanduser(base_dir)
    cwd = cwd and os.path.join(base_dir, cwd)
    super(LocalBase, self).__init__(
        replay_dir=os.path.join(base_dir, "Replays"),
        data_dir=base_dir, tmp_dir=None, cwd=cwd, env=env)
    self._exec_name = exec_name

  def exec_path(self, game_version=None):
    """Get the exec_path for this platform. Possibly find the latest build."""
    build_version = get_version(game_version)[0] if game_version else None

    if not build_version:
      versions_dir = os.path.join(self.data_dir, "Versions")
      if not os.path.isdir(versions_dir):
        raise lib.SC2LaunchError(
            "Expected to find StarCraft II installed at '%s'. Either install "
            "it there or set the SC2PATH environment variable." % self.data_dir)
      build_version = max(int(v[4:]) for v in os.listdir(versions_dir)
                          if v.startswith("Base"))
      if build_version < 55958:
        raise lib.SC2LaunchError(
            "Your SC2 binary is too old. Upgrade to 3.16.1 or newer.")
    return os.path.join(
        self.data_dir, "Versions/Base%s" % build_version, self._exec_name)

  def start(self, game_version=None, data_version=None, **kwargs):
    """Launch the game."""
    game_version = game_version or FLAGS.sc2_version
    if game_version and not data_version:
      data_version = get_version(game_version)[1]
    return super(LocalBase, self).start(game_version=game_version,
                                        data_version=data_version, **kwargs)


class Windows(LocalBase):
  """Run on Windows."""

  def __init__(self):
    super(Windows, self).__init__(
        os.environ.get("SC2PATH", "C:/Program Files (x86)/StarCraft II"),
        "SC2_x64.exe", "Support64")

  @classmethod
  def priority(cls):
    if platform.system() == "Windows":
      return 1


class MacOS(LocalBase):
  """Run on MacOS."""

  def __init__(self):
    super(MacOS, self).__init__(
        os.environ.get("SC2PATH", "/Applications/StarCraft II"),
        "SC2.app/Contents/MacOS/SC2")

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

