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
"""Utilities built on top of sc2_replay."""

import collections
import dataclasses
from typing import List, Mapping

from pysc2.lib.replay import sc2_replay


_EVENT_TYPES_TO_FILTER_OUT = frozenset([
    # Not related to actions.
    "SetSyncLoadingTime",
    "SetSyncPlayingTime",
    "TriggerSoundLengthSync",
    "UserFinishedLoadingSync",
    "UserOptions",

    # Always accompanied by a CommandManagerState, which we track.
    "CmdUpdateTargetPoint",

    # Of interest for the visual interface, but skipped for now as we are
    # targeting raw.
    "CameraSave",
    "ControlGroupUpdate",
    "SelectionDelta",
])


def _readable_event_type(full_event_type):
  return full_event_type[len("NNet.Game.S"):-5]


@dataclasses.dataclass
class EventData:
  game_loop: int
  event_type: str


def raw_action_skips(replay: sc2_replay.SC2Replay) -> Mapping[int, List[int]]:
  """Returns player id -> list, the game loops on which each player acted.

  Args:
    replay: An sc2_replay.SC2Replay instance.

  Note that these skips are specific to the raw interface - further work will
  be needed to support visual.
  """
  action_frames = collections.defaultdict(list)
  last_game_loop = None
  # Extract per-user events of interest.
  for event in replay.game_events():
    event_type = _readable_event_type(event["_event"])
    if event_type not in _EVENT_TYPES_TO_FILTER_OUT:
      game_loop = event["_gameloop"]
      last_game_loop = game_loop
      # As soon as anyone leaves, we stop tracking events.
      if event_type == "GameUserLeave":
        break

      user_id = event["_userid"]["m_userId"]
      player_id = user_id + 1
      if player_id < 1 or player_id > 2:
        raise ValueError(f"Unexpected player_id: {player_id}")
      if (action_frames[player_id] and
          action_frames[player_id][-1].game_loop == game_loop):
        # Later (non-camera) events on the same game loop take priority.
        if event_type != "CameraUpdate":
          action_frames[player_id][-1].event_type = event_type
      else:
        action_frames[player_id].append(EventData(game_loop, event_type))

  for player_id in action_frames:
    # Filter out repeated camera updates.
    filtered = []
    for v in action_frames[player_id]:
      if (v.event_type == "CameraUpdate" and filtered and
          filtered[-1].event_type == "CameraUpdate"):
        filtered[-1].game_loop = v.game_loop
      else:
        filtered.append(v)
    # If the last update is a camera move, remove it (only camera moves with a
    # raw action following them should be added).
    if filtered and filtered[-1].event_type == "CameraUpdate":
      filtered.pop()
    # Extract game loops.
    action_frames[player_id] = [v.game_loop for v in filtered]
    if not action_frames[player_id] or (action_frames[player_id][-1] !=
                                        last_game_loop):
      action_frames[player_id].append(last_game_loop)
  return action_frames
