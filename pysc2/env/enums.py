# Copyright 2021 Google Inc. All Rights Reserved.
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
"""Enumerations used for configuring the SC2 environment."""

import enum

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb


class Race(enum.IntEnum):
  random = sc_common.Random
  protoss = sc_common.Protoss
  terran = sc_common.Terran
  zerg = sc_common.Zerg


class Difficulty(enum.IntEnum):
  """Bot difficulties."""
  very_easy = sc_pb.VeryEasy
  easy = sc_pb.Easy
  medium = sc_pb.Medium
  medium_hard = sc_pb.MediumHard
  hard = sc_pb.Hard
  harder = sc_pb.Harder
  very_hard = sc_pb.VeryHard
  cheat_vision = sc_pb.CheatVision
  cheat_money = sc_pb.CheatMoney
  cheat_insane = sc_pb.CheatInsane


class BotBuild(enum.IntEnum):
  """Bot build strategies."""
  random = sc_pb.RandomBuild
  rush = sc_pb.Rush
  timing = sc_pb.Timing
  power = sc_pb.Power
  macro = sc_pb.Macro
  air = sc_pb.Air
