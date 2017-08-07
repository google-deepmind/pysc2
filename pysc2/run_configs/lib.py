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

import datetime
import os

from pysc2.lib import sc_process



class SC2LaunchError(Exception):
  pass


class RunConfig(object):
  """Base class for different run configs."""

  def __init__(self, replay_dir, data_dir, tmp_dir, exec_path, cwd=None,
               env=None):
    """Initialize the runconfig with the various directories needed.

    Args:
      replay_dir: Where to find replays. Might not be accessible to SC2.
      data_dir: Where SC2 should find the data and battle.net cache.
      tmp_dir: The temporary directory. None is system default.
      exec_path: Where to find the SC2 binary.
      cwd: Where to set the current working directory.
      env: What to pass as the environment variables.
    """
    self.replay_dir = replay_dir
    self.data_dir = data_dir
    self.tmp_dir = tmp_dir
    self.exec_path = exec_path
    self.cwd = cwd
    self.env = env

  def map_data(self, map_name):
    """Return the map data for a map by name or path."""
    with open(os.path.join(self.data_dir, "Maps", map_name), "rb") as f:
      return f.read()

  def abs_replay_path(self, replay_path):
    """Return the absolute path to the replay, outside the sandbox."""
    return os.path.join(self.replay_dir, replay_path)

  def replay_data(self, replay_path):
    """Return the replay data given a path to the replay."""
    with open(self.abs_replay_path(replay_path), "rb") as f:
      return f.read()

  def replay_paths(self, replay_dir):
    """A generator yielding the full path to the replays under `replay_dir`."""
    replay_dir = self.abs_replay_path(replay_dir)
    if replay_dir.lower().endswith(".sc2replay"):
      yield replay_dir
      return
    for f in os.listdir(replay_dir):
      if f.lower().endswith(".sc2replay"):
        yield os.path.join(replay_dir, f)

  def save_replay(self, replay_data, replay_dir, map_name):
    """Save a replay to a directory, returning the path to the replay.

    Args:
      replay_data: The result of controller.save_replay(), ie the binary data.
      replay_dir: Where to save the replay. This can be absolute or relative.
      map_name: The map name, used as a prefix for the replay name.

    Returns:
      The full path where the replay is saved.
    """
    now = datetime.datetime.utcnow().replace(microsecond=0)
    replay_filename = "%s_%s.SC2Replay" % (
        os.path.splitext(os.path.basename(map_name))[0],
        now.isoformat("-").replace(":", "-"))
    replay_dir = self.abs_replay_path(replay_dir)
    if not os.path.exists(replay_dir):
      os.makedirs(replay_dir)
    replay_path = os.path.join(replay_dir, replay_filename)
    with open(replay_path, "wb") as f:
      f.write(replay_data)
    return replay_path

  def start(self, **kwargs):
    """Launch the game."""
    return sc_process.StarcraftProcess(self, **kwargs)

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

