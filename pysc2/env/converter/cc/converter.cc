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

#include "pysc2/env/converter/cc/converter.h"

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "glog/logging.h"
#include "absl/status/status.h"
#include "absl/status/statusor.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "pysc2/env/converter/cc/convert_obs.h"
#include "pysc2/env/converter/cc/features.h"
#include "pysc2/env/converter/cc/raw_actions_encoder.h"
#include "pysc2/env/converter/cc/raw_converter.h"
#include "pysc2/env/converter/cc/tensor_util.h"
#include "pysc2/env/converter/cc/unit_lookups.h"
#include "pysc2/env/converter/proto/converter.pb.h"
#include "s2clientprotocol/common.pb.h"
#include "s2clientprotocol/sc2api.pb.h"
#include "s2clientprotocol/spatial.pb.h"

namespace pysc2 {

namespace {

constexpr int kMaxActionDelay = 127;

}  // namespace

absl::StatusOr<Converter> MakeConverter(
    const ConverterSettings& settings,
    const EnvironmentInfo& environment_info) {
  int non_observers = 0;
  for (const auto& player_info : environment_info.game_info().player_info()) {
    if (player_info.type() != SC2APIProtocol::PlayerType::Observer) {
      non_observers += 1;
    }
  }
  if (non_observers != 2) {
    return absl::InvalidArgumentError(
        absl::StrCat("The converter requires the game to be configured with 2 "
                     "non-observer players. Specifed: ",
                     non_observers));
  }

  if (!settings.has_visual_settings() && !settings.has_raw_settings()) {
    return absl::InvalidArgumentError(
        "Please specify either visual or raw settings.");
  }

  if (settings.num_action_types() < 539) {
    return absl::InvalidArgumentError(absl::StrCat(
        "Please specify the number of action types which you would like "
        "to be made visible. We don't support less than 539 action "
        "types, visual or raw. Specified: ",
        settings.num_action_types()));
  }
  if (settings.num_unit_types() < 217) {
    return absl::InvalidArgumentError(absl::StrCat(
        "Please specify the number of unit types which you would like to "
        "be made visible. We don't support less than 217 unit types. "
        "Specified: ",
        settings.num_unit_types()));
  }
  if (settings.num_upgrade_types() < 86) {
    return absl::InvalidArgumentError(absl::StrCat(
        "Please specify the number of upgrade types which you would like to "
        "be made visible. We don't support less than 86 upgrade types. "
        "Specified: ",
        settings.num_upgrade_types()));
  }
  if (settings.max_num_upgrades() <= 0) {
    return absl::InvalidArgumentError(
        "Please specify the maximum number of upgrades, which equates to the "
        "length of the `upgrades_fixed_length` observation. We use 40 "
        "typically.");
  }
  if (settings.minimap_features_size() || settings.has_visual_settings()) {
    if (settings.minimap().x() <= 0) {
      return absl::InvalidArgumentError(
          "Please specify the width of the minimap.");
    }
    if (settings.minimap().y() <= 0) {
      return absl::InvalidArgumentError(
          "Please specify the height of the minimap.");
    }
    if (settings.minimap().x() != settings.minimap().y()) {
      return absl::InvalidArgumentError(
          absl::StrCat("Only a square minimap is supported currently, but ",
                       settings.minimap().x(), "x", settings.minimap().y(),
                       " was specified"));
    }
  }

  if (settings.has_visual_settings()) {
    const auto& visual = settings.visual_settings();
    if (visual.screen().x() <= 0) {
      return absl::InvalidArgumentError(
          "Please specify the width of the screen.");
    }
    if (visual.screen().y() <= 0) {
      return absl::InvalidArgumentError(
          "Please specify the height of the screen.");
    }
    if (visual.screen().x() != visual.screen().y()) {
      return absl::InvalidArgumentError(absl::StrCat(
          "Only a square screen is supported currently, but ",
          visual.screen().x(), "x", visual.screen().y(), " was specified"));
    }
  } else {
    const auto& raw = settings.raw_settings();
    if (raw.num_unit_features() < 39) {
      return absl::InvalidArgumentError(absl::StrCat(
          "Please specify the number of features to output for each raw "
          "unit. Note that we don't support any less than 30 raw unit "
          "features. Specified: ",
          raw.num_unit_features()));
    }
    if (raw.max_unit_selection_size() < 16) {
      return absl::InvalidArgumentError(absl::StrCat(
          "Please specify the maximum number of units that may be controlled "
          "by the agent in a single action. Specified: ",
          raw.max_unit_selection_size()));
    }
  }

  return Converter(settings, environment_info);
}

Converter::Converter(const ConverterSettings& settings,
                     const EnvironmentInfo& environment_info)
    : settings_(settings),
      environment_info_(environment_info),
      away_race_observed_(SC2APIProtocol::Race::Random) {
  if (settings_.has_raw_settings()) {
    raw_converter_ = std::make_unique<RawConverter>(settings, environment_info);
  } else {
    visual_converter_ = std::make_unique<VisualConverter>(settings);
  }

  // Cache requested races.
  for (const auto& player_info : environment_info.game_info().player_info()) {
    if (player_info.type() != SC2APIProtocol::PlayerType::Observer) {
      requested_races_.push_back(player_info.race_requested());
    }
  }
  CHECK_EQ(requested_races_.size(), 2) << "Must have 2 non-observer players.";
}

absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec>
Converter::ObservationSpec() const {
  absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec> spec;
  if (raw_converter_) {
    spec = raw_converter_->ObservationSpec();
  } else {
    spec = visual_converter_->ObservationSpec();
  }

  spec["game_loop"] = Int32TensorSpec("game_loop", {1});
  spec["player"] = Int32TensorSpec("player", {kNumPlayerFeatures});
  spec["home_race_requested"] = Int32TensorSpec("home_race_requested", {1});
  spec["away_race_requested"] = Int32TensorSpec("away_race_requested", {1});
  spec["away_race_observed"] = Int32TensorSpec("away_race_observed", {1});
  spec["upgrades_fixed_length"] = TensorSpec(
      "upgrades_fixed_length", dm_env_rpc::v1::DataType::INT32,
      {settings_.max_num_upgrades()}, 0, settings_.num_upgrade_types() + 1);
  spec["unit_counts_bow"] =
      Int32TensorSpec("unit_counts_bow", {settings_.num_unit_types()});

  spec["mmr"] = Int32ScalarSpec("mmr");

  const auto& minimap_features = settings_.minimap_features();
  for (size_t i = 0; i < minimap_features.size(); ++i) {
    const std::string& feature = minimap_features[i];
    auto name = absl::StrCat("minimap_", feature);
    auto range = GetMinimapFeatureScale(feature).value();
    spec[name] = TensorSpec(name, dm_env_rpc::v1::DataType::UINT8,
                            {settings_.minimap().x(), settings_.minimap().y()},
                            0, range - 1);
  }

  if (settings_.add_opponent_features()) {
    spec["opponent_player"] = Int32TensorSpec("opponent_player", {10});
    spec["opponent_unit_counts_bow"] = Int32TensorSpec(
        "opponent_unit_counts_bow", {settings_.num_unit_types()});
    spec["opponent_upgrades_fixed_length"] = TensorSpec(
        "opponent_upgrades_fixed_length", dm_env_rpc::v1::DataType::INT32,
        {settings_.max_num_upgrades()}, 0, settings_.num_upgrade_types() + 1);
  }

  if (settings_.supervised()) {
    spec["action/delay"] =
        TensorSpec("delay", dm_env_rpc::v1::INT32, {}, 1, kMaxActionDelay);
  }
  return spec;
}

absl::StatusOr<absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>>
Converter::ConvertObservation(const Observation& observation) {
  auto result = raw_converter_
                    ? raw_converter_->ConvertObservation(observation)
                    : visual_converter_->ConvertObservation(observation);
  if (!result.ok()) {
    return result;
  }
  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& output = *result;

  const SC2APIProtocol::Observation& obs = observation.player().observation();

  output["game_loop"] = GameLoop(obs);
  output["player"] = MapPlayerIdToOne(PlayerCommon(obs));
  output["home_race_requested"] = HomeRaceRequested(observation);
  output["away_race_requested"] = AwayRaceRequested(observation);
  output["away_race_observed"] = AwayRaceObserved(observation);
  output["upgrades_fixed_length"] =
      UpgradesUint8FixedLength(Upgrades(obs), settings_.max_num_upgrades());
  output["unit_counts_bow"] = AddUnitCountsBowData(
      UnitToUint8Matrix<int64_t>(UnitCounts(obs, true, false), 0),
      settings_.num_unit_types(), true);

  const auto& minimap_features = settings_.minimap_features();
  if (!minimap_features.empty()) {
    const SC2APIProtocol::FeatureLayersMinimap& layers =
        obs.feature_layer_data().minimap_renders();
    if (minimap_field_indices_.empty()) {
      minimap_field_indices_ = FeatureLayerFieldIndices(
          std::vector<std::string>(minimap_features.cbegin(),
                                   minimap_features.cend()),
          layers);
    }
    for (size_t i = 0; i < minimap_features.size(); ++i) {
      output[absl::StrCat("minimap_", minimap_features.at(i))] =
          FeatureLayer8bit(layers, minimap_field_indices_[i],
                           minimap_features.at(i));
    }
  }

  if (settings_.add_opponent_features()) {
    const auto& opponent_obs = observation.opponent().observation();
    dm_env_rpc::v1::Tensor opponent_player_original =
        PlayerCommon(opponent_obs);
    dm_env_rpc::v1::Tensor opponent_player = ZeroVector<int32_t>(10);
    MutableVector<int32_t> v(&opponent_player);
    for (int i = 0; i < 10; ++i) {
      v(i) = opponent_player_original.int32s().array(i + 1);
    }
    output["opponent_player"] = opponent_player;
    output["opponent_unit_counts_bow"] = AddUnitCountsBowData(
        UnitToUint8Matrix<int64_t>(UnitCounts(opponent_obs, true, false), 0),
        settings_.num_unit_types(), true);
    output["opponent_upgrades_fixed_length"] = UpgradesUint8FixedLength(
        Upgrades(opponent_obs), settings_.max_num_upgrades());
  }

  if (settings_.supervised()) {
    if (!observation.has_force_action_delay()) {
      return absl::InvalidArgumentError(
          "Need force_action_delay to be present in the observation "
          "when supervised is enabled.");
    }
    int delay = observation.force_action_delay();
    if (delay == 0) {
      return absl::FailedPreconditionError("Must never happen");
    }
    output["action/delay"] = MakeTensor(delay);
  }

  output["mmr"] = MMR(observation);
  return result;
}

absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec>
Converter::ActionSpec() const {
  absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec> spec;
  if (raw_converter_) {
    spec = raw_converter_->ActionSpec();
  } else {
    spec = visual_converter_->ActionSpec();
  }
  spec["delay"] =
      TensorSpec("delay", dm_env_rpc::v1::INT32, {}, 1, kMaxActionDelay);
  return spec;
}

absl::StatusOr<pysc2::Action> Converter::ConvertAction(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& action) {
  auto converted_or = raw_converter_ ? raw_converter_->ConvertAction(action)
                                     : visual_converter_->ConvertAction(action);
  if (!converted_or.ok()) {
    return converted_or.status();
  }
  pysc2::Action converted;
  *converted.mutable_request_action() = *std::move(converted_or);

  auto delay_iter = action.find("delay");
  if (delay_iter == action.cend()) {
    return absl::InvalidArgumentError(
        "Please specify delay - the number of game loops to wait before "
        "receiving the next observation.");
  }
  converted.set_delay(ToScalar(delay_iter->second));
  return converted;
}

absl::StatusOr<absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>>
Converter::DecodeAction(const SC2APIProtocol::RequestAction& action) const {
  if (raw_converter_) {
    return raw_converter_->DecodeAction(action);
  } else {
    return visual_converter_->DecodeAction(action);
  }
}

dm_env_rpc::v1::Tensor Converter::MMR(const Observation& observation) const {
  int player_id =
      observation.player().observation().player_common().player_id();
  int mmr;
  if (environment_info_.has_replay_info()) {
    // Use default MMR of 3500 when not available in the replay_info.
    for (const auto& info : environment_info_.replay_info().player_info()) {
      if (player_id == info.player_info().player_id()) {
        mmr = info.player_mmr();
        break;
      }
    }
  } else {
    mmr = settings_.mmr();
  }

  dm_env_rpc::v1::Tensor tensor;
  tensor.mutable_int32s()->add_array(mmr);
  return tensor;
}

dm_env_rpc::v1::Tensor Converter::HomeRaceRequested(
    const Observation& observation) const {
  int player_id =
      observation.player().observation().player_common().player_id();
  CHECK(player_id == 1 || player_id == 2) << "- player_id is " << player_id;
  return MakeTensor(std::vector<int>({requested_races_[player_id - 1]}));
}

dm_env_rpc::v1::Tensor Converter::AwayRaceRequested(
    const Observation& observation) const {
  int player_id =
      observation.player().observation().player_common().player_id();
  CHECK(player_id == 1 || player_id == 2) << "- player_id is " << player_id;
  return MakeTensor(std::vector<int>({requested_races_[2 - player_id]}));
}

dm_env_rpc::v1::Tensor Converter::AwayRaceObserved(
    const Observation& observation) {
  dm_env_rpc::v1::Tensor away_race_observed;

  if (away_race_observed_ == SC2APIProtocol::Race::Random) {
    // Look for enemy unit
    for (const auto& u :
         observation.player().observation().raw_data().units()) {
      if (u.alliance() == SC2APIProtocol::Enemy) {
        away_race_observed_ = UnitTypeToRace(u.unit_type());
        break;
      }
    }
  }
  return MakeTensor(std::vector<int>({away_race_observed_}));
}

}  // namespace pysc2
