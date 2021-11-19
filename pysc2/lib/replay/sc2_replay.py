# Copyright 2021 DeepMind Technologies Ltd. All rights reserved.
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
"""Utility functions for loading replay data using the s2protocol library."""

import io
import json
import types

import mpyq
from s2protocol import versions as s2versions
import tree


def _convert_to_str(s):
  if isinstance(s, bytes):
    return bytes.decode(s)
  else:
    return s


def _convert_all_to_str(structure):
  if isinstance(structure, types.GeneratorType):
    return tree.map_structure(_convert_to_str, list(structure))
  else:
    return tree.map_structure(_convert_to_str, structure)


class SC2Replay(object):
  """Helper class for loading and extracting data using s2protocol library."""

  def __init__(self, replay_data):
    """Construct SC2Replay helper for extracting data from a replay."""
    (self._header, self._metadata, self._extracted,
     self._protocol) = _extract(replay_data)

  def details(self):
    details_key = b"replay.details"
    if details_key not in self._extracted:
      details_key = b"replay.details.backup"

    return _convert_all_to_str(
        self._protocol.decode_replay_details(self._extracted[details_key]))

  def init_data(self):
    return _convert_all_to_str(
        self._protocol.decode_replay_initdata(
            self._extracted[b"replay.initData"]))

  def tracker_events(self, filter_fn=None):
    """Yield tracker events from the replay in s2protocol format."""
    for event in _convert_all_to_str(
        self._protocol.decode_replay_tracker_events(
            self._extracted[b"replay.tracker.events"])):
      if not filter_fn or filter_fn(event):
        yield event

  def game_events(self, filter_fn=None):
    """Yield game events from the replay in s2protocol format."""
    for event in _convert_all_to_str(
        self._protocol.decode_replay_game_events(
            self._extracted[b"replay.game.events"])):
      if not filter_fn or filter_fn(event):
        yield event

  def message_events(self, filter_fn=None):
    """Yield message events from the replay in s2protocol format."""
    for event in _convert_all_to_str(
        self._protocol.decode_replay_message_events(
            self._extracted[b"replay.message.events"])):
      if not filter_fn or filter_fn(event):
        yield event

  def attributes_events(self, filter_fn=None):
    """Yield attribute events from the replay in s2protocol format."""
    for event in _convert_all_to_str(
        self._protocol.decode_replay_attributes_events(
            self._extracted[b"replay.attributes.events"])):
      if not filter_fn or filter_fn(event):
        yield event

  @property
  def metadata(self):
    return self._metadata

  @property
  def protocol(self):
    return self._protocol


def _extract(contents):
  """Extract a replay using s2protocol."""
  replay_io = io.BytesIO()
  replay_io.write(contents)
  replay_io.seek(0)
  archive = mpyq.MPQArchive(replay_io)
  extracted = archive.extract()
  metadata = json.loads(
      bytes.decode(extracted[b"replay.gamemetadata.json"], "utf-8"))
  contents = archive.header["user_data_header"]["content"]
  header = s2versions.latest().decode_replay_header(contents)
  base_build = header["m_version"]["m_baseBuild"]
  protocol = s2versions.build(base_build)
  if protocol is None:
    raise ValueError("Could not load protocol {} for replay".format(base_build))
  return header, metadata, extracted, protocol
