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

#include "pysc2/env/converter/cc/general_order_ids.h"

#include <cstdint>

#include "absl/container/flat_hash_map.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "pysc2/env/converter/cc/game_data/raw_actions.h"
#include "pysc2/env/converter/cc/tensor_util.h"

namespace pysc2 {
namespace {

class OrderIdToGeneralLookup {
 public:
  OrderIdToGeneralLookup() {
    for (int i = 0; i < RawFunctions().size(); i++) {
      RawFunctionType type = RawFunctions().at(i).type;
      int ability_id = RawFunctions().at(i).ability_id;
      int general_id = RawFunctions().at(i).general_id;

      // This is a general ability if general_id is not set.
      if (general_id == 0) {
        auto general_pair = std::make_pair(type, ability_id);
        CHECK(general_to_general_game_id_.find(general_pair) ==
              general_to_general_game_id_.end())
            << "Found duplicate: " << type << ", " << ability_id;
        general_to_general_game_id_[general_pair] = i;
      }
    }

    for (int i = 0; i < RawFunctions().size(); i++) {
      RawFunctionType type = RawFunctions().at(i).type;
      int ability_id = RawFunctions().at(i).ability_id;
      int general_id = RawFunctions().at(i).general_id;

      // If this is a general ability, assign its ability_id to the general_id.
      if (general_id == 0) {
        general_id = ability_id;
      }
      auto general_pair = std::make_pair(type, general_id);

      game_id_to_general_game_id_[i] =
          general_to_general_game_id_[general_pair];
    }
  }

  int Lookup(int game_id) const {
    auto it = game_id_to_general_game_id_.find(game_id);
    if (it != game_id_to_general_game_id_.end()) {
      return it->second;
    } else {
      return 0;
    }
  }

 private:
  absl::flat_hash_map<std::pair<RawFunctionType, int>, int>
      general_to_general_game_id_;
  absl::flat_hash_map<int, int> game_id_to_general_game_id_;
};

const OrderIdToGeneralLookup& OrderIdToGeneral() {
  static auto* lookup_table = new OrderIdToGeneralLookup();
  return *lookup_table;
}

}  // namespace

int GeneralOrderId(int order_id, int num_action_types) {
  int general_order_id = OrderIdToGeneral().Lookup(order_id);
  if (general_order_id < num_action_types) {
    return general_order_id;
  } else {
    return 0;
  }
}

void GeneralOrderIds(dm_env_rpc::v1::Tensor* raw_units, int num_action_types) {
  int num_units = raw_units->shape(0);
  int num_features = raw_units->shape(1);
  MutableMatrix<int32_t> m(raw_units);
  for (int unit_id = 0; unit_id < num_units; unit_id++) {
    for (int feature_id : {kOrderId1, kOrderId2, kOrderId3, kOrderId4}) {
      if (num_features > feature_id) {
        m(unit_id, feature_id) =
            GeneralOrderId(m(unit_id, feature_id), num_action_types);
      }
    }
  }
}

}  // namespace pysc2
