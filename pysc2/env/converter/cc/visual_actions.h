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

#ifndef PYSC2_ENV_CONVERTER_CC_VISUAL_ACTIONS_H_
#define PYSC2_ENV_CONVERTER_CC_VISUAL_ACTIONS_H_

#include <string>

#include "absl/container/flat_hash_map.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "pysc2/env/converter/cc/game_data/visual_actions.h"
#include "s2clientprotocol/sc2api.pb.h"

namespace pysc2 {

using ActionId = int;
using AbilityId = int;
using GeneralId = int;

// Context for the encoding and decoding of actions.
struct ActionContext {
  int screen_width;
  int minimap_width;
  int num_functions;
};

class VisualAction {
 public:
  VisualAction(ActionId action_id, absl::string_view tag,
               FunctionType action_type, AbilityId ability_id = 0,
               GeneralId general_id = 0);

  ActionId action_id() const { return action_id_; }
  FunctionType action_type() const { return action_type_; }
  AbilityId ability_id() const { return ability_id_; }
  GeneralId general_id() const { return general_id_; }

  bool IsApplicable(bool requires_point) const;

  // Encodes this action, parameterized by the specified args, into a proto.
  SC2APIProtocol::Action Encode(
      const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& args,
      const ActionContext& action_context) const;

 private:
  std::string tag_;
  FunctionType action_type_;
  ActionId action_id_;
  AbilityId ability_id_;
  GeneralId general_id_;
};

// Gets action directly by action id.
const VisualAction& GetAction(ActionId action_id);

// Gets vector of actions which have the specified ability id.
const std::vector<VisualAction>& GetActionsForAbility(AbilityId ability_id);

// Decodes a proto-specified action into the equivalent agent action.
absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> Decode(
    const SC2APIProtocol::RequestAction& request_action,
    const ActionContext& action_context);

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_CC_VISUAL_ACTIONS_H_
