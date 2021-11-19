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

#ifndef PYSC2_ENV_CONVERTER_CC_RAW_ACTIONS_ENCODER_H_
#define PYSC2_ENV_CONVERTER_CC_RAW_ACTIONS_ENCODER_H_

#include <vector>

#include "absl/container/fixed_array.h"
#include "absl/container/flat_hash_map.h"
#include "absl/random/random.h"
#include "absl/status/statusor.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "s2clientprotocol/common.pb.h"
#include "s2clientprotocol/raw.pb.h"
#include "s2clientprotocol/sc2api.pb.h"

namespace pysc2 {

class RawActionsEncoder {
 public:
  RawActionsEncoder(const SC2APIProtocol::Size2DI& map_size, int max_unit_count,
                    int max_selection_size,
                    const SC2APIProtocol::Size2DI& raw_resolution,
                    int num_action_types, bool shuffle_unit_tags,
                    bool action_repeat);

  absl::StatusOr<SC2APIProtocol::RequestAction> Encode(
      const SC2APIProtocol::ResponseObservation& observation,
      const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>&
          drastic_action) const;

  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> Decode(
      const SC2APIProtocol::ResponseObservation& observation,
      const SC2APIProtocol::RequestAction& action) const;

  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> MakeFunctionCall(
      int function_id, int world, int queued, const std::vector<int>& unit_tags,
      int target_unit_tag, int repeat) const;

  // Maps from an agent-specified coordinate (single int) to a Point2D that
  // the game understands.
  SC2APIProtocol::Point2D AgentCoordsToWorldCoords(int target_pos) const;

  // Maps from a game-specified coordinate to the corresponding coordinate (int)
  // that an agent could have returned. Note that there is a loss of precision
  // here, as an agent coordinate aliases an entire region of the world space.
  int WorldCoordsToAgentCoords(const SC2APIProtocol::Point2D& position) const;

 private:
  SC2APIProtocol::Size2DI map_size_;
  int max_unit_count_;
  int max_selection_size_;
  SC2APIProtocol::Size2DI raw_resolution_;
  int num_action_types_;
  bool shuffle_unit_tags_;
  bool action_repeat_;
  mutable absl::BitGen bit_gen_;
};

void PrintAllActions();

int RawAbilityToGameId(int ability_id);

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_CC_RAW_ACTIONS_ENCODER_H_
