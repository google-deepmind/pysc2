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

#ifndef PYSC2_ENV_CONVERTER_CC_GAME_DATA_RAW_ACTIONS_H_
#define PYSC2_ENV_CONVERTER_CC_GAME_DATA_RAW_ACTIONS_H_

#include <vector>

#include "absl/container/fixed_array.h"
#include "s2clientprotocol/raw.pb.h"
#include "s2clientprotocol/sc2api.pb.h"

namespace pysc2 {

enum RawFunctionType {
  NO_OP,
  RAW_CMD_PT,
  RAW_CMD_UNIT,
  RAW_CMD,
  RAW_MOVE_CAMERA,
  RAW_AUTOCAST,
};

struct RawFunction {
  std::string label;
  RawFunctionType type = NO_OP;
  int ability_id = 0;
  int general_id = 0;
};

// List of all raw functions supported by the converter.
const std::vector<RawFunction>& RawFunctions();

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_GAME_DATA_RAW_ACTIONS_H_
