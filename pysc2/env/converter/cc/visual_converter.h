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

#ifndef PYSC2_ENV_CONVERTER_CC_VISUAL_CONVERTER_H_
#define PYSC2_ENV_CONVERTER_CC_VISUAL_CONVERTER_H_

#include <map>
#include <string>
#include <vector>

#include "absl/container/flat_hash_map.h"
#include "absl/status/statusor.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "pysc2/env/converter/proto/converter.pb.h"
#include "s2clientprotocol/sc2api.pb.h"

namespace pysc2 {

class VisualConverter {
 public:
  explicit VisualConverter(const ConverterSettings& settings);

  absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec> ObservationSpec()
      const;
  absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec> ActionSpec()
      const;

  absl::StatusOr<absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>>
  ConvertObservation(const Observation& observation);

  absl::StatusOr<SC2APIProtocol::RequestAction> ConvertAction(
      const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& action);

  absl::StatusOr<absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>>
  DecodeAction(const SC2APIProtocol::RequestAction& action) const;

 private:
  const ConverterSettings settings_;
  const EnvironmentInfo environment_info_;

  std::vector<int> screen_field_indices_;
};

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_CC_VISUAL_CONVERTER_H_
