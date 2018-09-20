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
"""Configs for various ways to run starcraft."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import datetime
import os

from pysc2.lib import gfile


class Version(collections.namedtuple("Version", [
    "game_version", "build_version", "data_version", "binary"])):
  """Represents a single version of the game."""
  __slots__ = ()


def version_dict(versions):
  return {ver.game_version: ver for ver in versions}


# https://github.com/Blizzard/s2client-proto/blob/master/buildinfo/versions.json
# Generate with bin/gen_versions.py
VERSIONS = version_dict([
    Version("3.13.0", 52910, "8D9FEF2E1CF7C6C9CBE4FBCA830DDE1C", None),
    Version("3.14.0", 53644, "CA275C4D6E213ED30F80BACCDFEDB1F5", None),
    Version("3.15.0", 54518, "BBF619CCDCC80905350F34C2AF0AB4F6", None),
    Version("3.15.1", 54518, "6EB25E687F8637457538F4B005950A5E", None),
    Version("3.16.0", 55505, "60718A7CA50D0DF42987A30CF87BCB80", None),
    Version("3.16.1", 55958, "5BD7C31B44525DAB46E64C4602A81DC2", None),
    Version("3.17.0", 56787, "DFD1F6607F2CF19CB4E1C996B2563D9B", None),
    Version("3.17.1", 56787, "3F2FCED08798D83B873B5543BEFA6C4B", None),
    Version("3.17.2", 56787, "C690FC543082D35EA0AAA876B8362BEA", None),
    Version("3.18.0", 57507, "1659EF34997DA3470FF84A14431E3A86", None),
    Version("3.19.0", 58400, "2B06AEE58017A7DF2A3D452D733F1019", None),
    Version("3.19.1", 58400, "D9B568472880CC4719D1B698C0D86984", None),
    Version("4.0.0", 59587, "9B4FD995C61664831192B7DA46F8C1A1", None),
    Version("4.0.2", 59587, "B43D9EE00A363DAFAD46914E3E4AF362", None),
    Version("4.1.0", 60196, "1B8ACAB0C663D5510941A9871B3E9FBE", None),
    Version("4.1.1", 60321, "5C021D8A549F4A776EE9E9C1748FFBBC", None),
    Version("4.1.2", 60321, "33D9FE28909573253B7FC352CE7AEA40", None),
    Version("4.1.3", 60321, "F486693E00B2CD305B39E0AB254623EB", None),
    Version("4.1.4", 60321, "2E2A3F6E0BAFE5AC659C4D39F13A938C", None),
    Version("4.2.0", 62347, "C0C0E9D37FCDBC437CE386C6BE2D1F93", None),
    Version("4.2.1", 62848, "29BBAC5AFF364B6101B661DB468E3A37", None),
    Version("4.2.2", 63454, "3CB54C86777E78557C984AB1CF3494A0", None),
    Version("4.2.3", 63454, "5E3A8B21E41B987E05EE4917AAD68C69", None),
    Version("4.2.4", 63454, "7C51BC7B0841EACD3535E6FA6FF2116B", None),
    Version("4.3.0", 64469, "C92B3E9683D5A59E08FC011F4BE167FF", None),
    Version("4.3.1", 65094, "E5A21037AA7A25C03AC441515F4E0644", None),
    Version("4.3.2", 65384, "B6D73C85DFB70F5D01DEABB2517BF11C", None),
    Version("4.4.0", 65895, "BF41339C22AE2EDEBEEADC8C75028F7D", None),
    Version("4.4.1", 66668, "C094081D274A39219061182DBFD7840F", None),
    Version("4.5.0", 67188, "2ACF84A7ECBB536F51FC3F734EC3019F", None),
    Version("4.5.1", 67188, "6D239173B8712461E6A7C644A5539369", None),
    Version("4.6.0", 67926, "7DE59231CBF06F1ECE9A25A27964D4AE", None),
])


class RunConfig(object):
  """Base class for different run configs."""

  def __init__(self, replay_dir, data_dir, tmp_dir, cwd=None, env=None):
    """Initialize the runconfig with the various directories needed.

    Args:
      replay_dir: Where to find replays. Might not be accessible to SC2.
      data_dir: Where SC2 should find the data and battle.net cache.
      tmp_dir: The temporary directory. None is system default.
      cwd: Where to set the current working directory.
      env: What to pass as the environment variables.
    """
    self.replay_dir = replay_dir
    self.data_dir = data_dir
    self.tmp_dir = tmp_dir
    self.cwd = cwd
    self.env = env

  def map_data(self, map_name):
    """Return the map data for a map by name or path."""
    with gfile.Open(os.path.join(self.data_dir, "Maps", map_name), "rb") as f:
      return f.read()

  def abs_replay_path(self, replay_path):
    """Return the absolute path to the replay, outside the sandbox."""
    return os.path.join(self.replay_dir, replay_path)

  def replay_data(self, replay_path):
    """Return the replay data given a path to the replay."""
    with gfile.Open(self.abs_replay_path(replay_path), "rb") as f:
      return f.read()

  def replay_paths(self, replay_dir):
    """A generator yielding the full path to the replays under `replay_dir`."""
    replay_dir = self.abs_replay_path(replay_dir)
    if replay_dir.lower().endswith(".sc2replay"):
      yield replay_dir
      return
    for f in gfile.ListDir(replay_dir):
      if f.lower().endswith(".sc2replay"):
        yield os.path.join(replay_dir, f)

  def save_replay(self, replay_data, replay_dir, prefix=None):
    """Save a replay to a directory, returning the path to the replay.

    Args:
      replay_data: The result of controller.save_replay(), ie the binary data.
      replay_dir: Where to save the replay. This can be absolute or relative.
      prefix: Optional prefix for the replay filename.

    Returns:
      The full path where the replay is saved.

    Raises:
      ValueError: If the prefix contains the path seperator.
    """
    if not prefix:
      replay_filename = ""
    elif os.path.sep in prefix:
      raise ValueError("Prefix '%s' contains '%s', use replay_dir instead." % (
          prefix, os.path.sep))
    else:
      replay_filename = prefix + "_"
    now = datetime.datetime.utcnow().replace(microsecond=0)
    replay_filename += "%s.SC2Replay" % now.isoformat("-").replace(":", "-")
    replay_dir = self.abs_replay_path(replay_dir)
    if not gfile.Exists(replay_dir):
      gfile.MakeDirs(replay_dir)
    replay_path = os.path.join(replay_dir, replay_filename)
    with gfile.Open(replay_path, "wb") as f:
      f.write(replay_data)
    return replay_path

  def start(self, version=None, **kwargs):
    """Launch the game. Find the version and run sc_process.StarcraftProcess."""
    raise NotImplementedError()

  @classmethod
  def all_subclasses(cls):
    """An iterator over all subclasses of `cls`."""
    for s in cls.__subclasses__():
      yield s
      for c in s.all_subclasses():
        yield c

  @classmethod
  def name(cls):
    return cls.__name__

  @classmethod
  def priority(cls):
    """None means this isn't valid. Run the one with the max priority."""
    return None

  def get_versions(self):
    """Return a dict of all versions that can be run."""
    return VERSIONS

  def _get_version(self, game_version):
    versions = self.get_versions()
    if game_version.count(".") == 1:
      game_version += ".0"
    if game_version not in versions:
      raise ValueError("Unknown game version: %s. Known versions: %s" % (
          game_version, sorted(versions.keys())))
    return versions[game_version]

