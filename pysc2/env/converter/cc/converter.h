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

#ifndef PYSC2_ENV_CONVERTER_CC_CONVERTER_H_
#define PYSC2_ENV_CONVERTER_CC_CONVERTER_H_

#include <string>

#include "absl/container/flat_hash_map.h"
#include "absl/status/statusor.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "pysc2/env/converter/cc/raw_converter.h"
#include "pysc2/env/converter/cc/visual_converter.h"
#include "pysc2/env/converter/proto/converter.pb.h"
#include "s2clientprotocol/sc2api.pb.h"

namespace pysc2 {

// Marshalls data between SC2 protos and agent-friendly mappings.
// The Converter is stateful and relies on ConvertObservation and
// ConvertAction to be called in the right order. To reset the state of the
// Converter after an episode, a new instance should be created.
class Converter {
 public:
  Converter(const ConverterSettings& settings,
            const EnvironmentInfo& environment_info);

  // Returns the observation specification, in line with configuration.
  absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec> ObservationSpec()
      const;

  // Returns the action specification, in line with configuration.
  absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec> ActionSpec()
      const;

  // Converts an observation received from the SC2 binary to a string to
  // tensor map. Adds derived features according to the configuration of the
  // converter instance.
  absl::StatusOr<absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>>
  ConvertObservation(const Observation& observation);

  // Converts an action specified as a string to tensor map to a proto
  // suitable for sending to the SC2 binary.
  absl::StatusOr<pysc2::Action> ConvertAction(
      const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& action);

  // Converts an SC2 action to agent format.
  absl::StatusOr<absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>>
  DecodeAction(const SC2APIProtocol::RequestAction& action) const;

 private:
  ConverterSettings settings_;
  EnvironmentInfo environment_info_;

  std::unique_ptr<RawConverter> raw_converter_;
  std::unique_ptr<VisualConverter> visual_converter_;
  std::vector<int> minimap_field_indices_;
  std::vector<SC2APIProtocol::Race> requested_races_;
  SC2APIProtocol::Race away_race_observed_;

  dm_env_rpc::v1::Tensor MMR(const Observation& observation) const;
  dm_env_rpc::v1::Tensor HomeRaceRequested(
      const Observation& observation) const;
  dm_env_rpc::v1::Tensor AwayRaceRequested(
      const Observation& observation) const;
  dm_env_rpc::v1::Tensor AwayRaceObserved(const Observation& observation);
};

absl::StatusOr<Converter> MakeConverter(
    const ConverterSettings& settings, const EnvironmentInfo& environment_info);

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_CC_CONVERTER_H_
