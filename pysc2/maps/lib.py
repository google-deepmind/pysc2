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
"""The library and base Map for defining full maps.

To define your own map just import this library and subclass Map. It will be
automatically registered for creation by `get`.

  class NewMap(lib.Map):
    prefix = "map_dir"
    filename = "map_name"
    players = 3

You can build a hierarchy of classes to make your definitions less verbose.

To use a map, either import the map module and instantiate the map directly, or
import the maps lib and use `get`. Using `get` from this lib will work, but only
if you've imported the map module somewhere.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import logging
import os


class DuplicateMapException(Exception):
  pass


class NoMapException(Exception):
  pass


class Map(object):
  """Base map object to configure a map. To define a map just subclass this.

  Properties:
    directory: Directory for the map
    filename: Actual filename. You can skip the ".SC2Map" file ending.
    download: Where to download the map.
    game_steps_per_episode: Game steps per episode, independent of the step_mul.
        0 (default) means no limit.
    step_mul: How many game steps per agent step?
    score_index: Which score to give for this map. -1 means the win/loss
        reward. >=0 is the index into score_cumulative.
    score_multiplier: A score multiplier to allow make small scores good.
    players: Max number of players for this map.
  """
  directory = ""
  filename = None
  download = None
  game_steps_per_episode = 0
  step_mul = 8
  score_index = -1
  score_multiplier = 1
  players = None

  @property
  def path(self):
    """The full path to the map file: directory, filename and file ending."""
    if self.filename:
      map_path = os.path.join(self.directory, self.filename)
      if not map_path.endswith(".SC2Map"):
        map_path += ".SC2Map"
      return map_path

  def data(self, run_config):
    """Return the map data."""
    try:
      return run_config.map_data(self.path)
    except (IOError, OSError) as e:  # Catch both for python 2/3 compatibility.
      if self.download and hasattr(e, "filename"):
        logging.error("Error reading map '%s' from: %s", self.name, e.filename)
        logging.error("Download the map from: %s", self.download)
      raise

  @property
  def name(self):
    return self.__class__.__name__

  def __str__(self):
    return "\n".join([
        self.name,
        "    %s" % self.path,
        "    players: %s, score_index: %s, score_multiplier: %s" % (
            self.players, self.score_index, self.score_multiplier),
        "    step_mul: %s, game_steps_per_episode: %s" % (
            self.step_mul, self.game_steps_per_episode),
    ])

  @classmethod
  def all_subclasses(cls):
    """An iterator over all subclasses of `cls`."""
    for s in cls.__subclasses__():
      yield s
      for c in s.all_subclasses():
        yield c


def get_maps():
  """Get the full dict of maps {map_name: map_class}."""
  maps = {}
  for mp in Map.all_subclasses():
    if mp.filename:
      map_name = mp.__name__
      if map_name in maps:
        raise DuplicateMapException("Duplicate map found: " + map_name)
      maps[map_name] = mp
  return maps


def get(map_name):
  """Get an instance of a map by name. Errors if the map doesn't exist."""
  if isinstance(map_name, Map):
    return map_name

  # Get the list of maps. This isn't at module scope to avoid problems of maps
  # being defined after this module is imported.
  maps = get_maps()
  map_class = maps.get(map_name)
  if map_class:
    return map_class()
  raise NoMapException("Map doesn't exist: %s" % map_name)
