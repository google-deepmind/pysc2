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

#ifndef PYSC2_ENV_CONVERTER_CC_GENERAL_ORDER_IDS_H_
#define PYSC2_ENV_CONVERTER_CC_GENERAL_ORDER_IDS_H_

#include "dm_env_rpc/v1/dm_env_rpc.pb.h"

namespace pysc2 {

// The indices of order ids in the raw units tensor.
constexpr int kOrderId1 = 27;
constexpr int kOrderId2 = 28;
constexpr int kOrderId3 = 38;
constexpr int kOrderId4 = 39;

// There has been weirdness with what order IDs the game returns (sometimes it's
// the general version (like move), and sometimes it's the specific version
// (like move battlecruiser)). This makes order IDs consistent for an agent.
void GeneralOrderIds(dm_env_rpc::v1::Tensor* raw_units, int num_action_types);

int GeneralOrderId(int order_id, int num_action_types);

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_CC_GENERAL_ORDER_IDS_H_
