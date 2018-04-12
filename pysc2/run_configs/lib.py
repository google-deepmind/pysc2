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

