// Copyright 2021 DeepMind Technologies Ltd. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#ifndef PYSC2_ENV_CONVERTER_GAME_DATA_VISUAL_ACTIONS_H_
#define PYSC2_ENV_CONVERTER_GAME_DATA_VISUAL_ACTIONS_H_

#include <vector>

#include "absl/container/flat_hash_map.h"
#include "s2clientprotocol/sc2api.pb.h"

namespace pysc2 {

using ActionId = int;
using AbilityId = int;
using GeneralId = int;

// Those elements with explicit numbering should not be changed as they
// correspond to particular ActionIds.
enum FunctionType {
  no_op = 0,
  move_camera = 1,
  select_point = 2,
  select_rect = 3,
  select_control_group = 4,
  select_unit = 5,
  select_idle_worker = 6,
  select_army = 7,
  select_warp_gates = 8,
  select_larva = 9,
  unload = 10,
  build_queue = 11,
  cmd_screen,
  cmd_minimap,
  cmd_quick,
  autocast,
};

struct Function {
  ActionId action_id;
  std::string label;
  FunctionType type = no_op;
  int ability_id = 0;
  int general_id = 0;
};

// List of all visual functions supported by the converter.
const std::vector<Function>& VisualFunctions();

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_GAME_DATA_VISUAL_ACTIONS_H_
