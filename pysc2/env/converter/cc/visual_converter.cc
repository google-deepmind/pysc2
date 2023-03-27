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

#include "pysc2/env/converter/cc/visual_converter.h"

#include <cstdint>
#include <map>
#include <string>

#include "absl/container/flat_hash_set.h"
#include "absl/status/status.h"
#include "absl/status/statusor.h"
#include "absl/strings/str_cat.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "pysc2/env/converter/cc/convert_obs.h"
#include "pysc2/env/converter/cc/features.h"
#include "pysc2/env/converter/cc/tensor_util.h"
#include "pysc2/env/converter/cc/visual_actions.h"
#include "pysc2/env/converter/proto/converter.pb.h"
#include "s2clientprotocol/common.pb.h"
#include "s2clientprotocol/sc2api.pb.h"
#include "s2clientprotocol/spatial.pb.h"
#include "s2clientprotocol/ui.pb.h"

namespace pysc2 {
namespace {

constexpr int kNumControlGroups = 10;
constexpr int kNumBuildQueueSlots = 10;
constexpr int kRandomBigNumber = 500;

dm_env_rpc::v1::Tensor AvailableActions(const SC2APIProtocol::Observation& obs,
                                        int num_action_types) {
  dm_env_rpc::v1::Tensor output = ZeroVector<int32_t>(num_action_types);
  MutableVector<int32_t> v(&output);

  // Determine which UI actions are available.
  v(no_op) = 1;
  v(move_camera) = 1;
  v(select_point) = 1;
  v(select_rect) = 1;
  v(select_control_group) = 1;
  if (obs.ui_data().has_multi()) {
    v(select_unit) = 1;
  }
  if (obs.player_common().idle_worker_count() > 0) {
    v(select_idle_worker) = 1;
  }
  if (obs.player_common().army_count() > 0) {
    v(select_army) = 1;
  }
  if (obs.player_common().warp_gate_count() > 0) {
    v(select_warp_gates) = 1;
  }
  if (obs.player_common().larva_count() > 0) {
    v(select_larva) = 1;
  }
  if (obs.ui_data().has_cargo()) {
    v(unload) = 1;
  }
  if (obs.ui_data().has_production()) {
    v(build_queue) = 1;
  }

  // Convert available abilities to action ids.
  absl::flat_hash_set<ActionId> available_actions;
  for (const auto& available_ability : obs.abilities()) {
    int ability_id = available_ability.ability_id();
    bool requires_point = available_ability.requires_point();
    bool found_applicable = false;
    for (const VisualAction& action : GetActionsForAbility(ability_id)) {
      if (action.IsApplicable(requires_point)) {
        if (action.general_id() == 0) {
          available_actions.insert(action.action_id());
          found_applicable = true;
        } else {
          for (const VisualAction& general_action :
               GetActionsForAbility(action.general_id())) {
            if (general_action.action_type() == action.action_type()) {
              available_actions.insert(general_action.action_id());
              found_applicable = true;
              break;
            }
          }
        }
      }
    }
    CHECK(found_applicable)
        << "Failed to find applicable action for " << available_ability;
  }
  for (auto action_id : available_actions) {
    if (action_id < num_action_types) {
      v(action_id) = 1;
    }
  }

  return output;
}

}  // namespace

VisualConverter::VisualConverter(const ConverterSettings& settings)
    : settings_(settings), screen_field_indices_() {}

absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec>
VisualConverter::ObservationSpec() const {
  absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec> spec;
  spec["available_actions"] =
      TensorSpec("available_actions", dm_env_rpc::v1::DataType::INT32,
                 {settings_.num_action_types()});

  const auto& visual = settings_.visual_settings();
  const auto& screen_features = visual.screen_features();
  for (size_t i = 0; i < screen_features.size(); ++i) {
    const std::string& feature = screen_features[i];
    auto name = absl::StrCat("screen_", feature);
    auto range = GetScreenFeatureScale(feature).value();
    spec[name] =
        TensorSpec(name, dm_env_rpc::v1::DataType::UINT8,
                   {visual.screen().x(), visual.screen().y()}, 0, range - 1);
  }

  if (settings_.supervised()) {
    for (const auto& [k, v] : ActionSpec()) {
      std::string label = absl::StrCat("action/", k);
      spec[label] = v;
      spec[label].set_name(label);
    }
  }
  return spec;
}

absl::StatusOr<absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>>
VisualConverter::ConvertObservation(const Observation& observation) {
  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> output;

  const SC2APIProtocol::Observation& obs = observation.player().observation();
  const auto& visual = settings_.visual_settings();
  output["available_actions"] =
      AvailableActions(obs, settings_.num_action_types());

  const auto& screen_features = visual.screen_features();
  if (!screen_features.empty()) {
    const SC2APIProtocol::FeatureLayers& layers =
        obs.feature_layer_data().renders();
    if (screen_field_indices_.empty()) {
      screen_field_indices_ = FeatureLayerFieldIndices(
          std::vector<std::string>(screen_features.cbegin(),
                                   screen_features.cend()),
          layers);
    }

    for (size_t i = 0; i < screen_features.size(); ++i) {
      output[absl::StrCat("screen_", screen_features.at(i))] = FeatureLayer8bit(
          layers, screen_field_indices_[i], screen_features.at(i));
    }
  }

  if (settings_.supervised()) {
    if (!observation.has_force_action()) {
      return absl::InvalidArgumentError(
          "Need force_action to be present in the observation "
          "when supervised is enabled.");
    }
    auto action_or = DecodeAction(observation.force_action());
    if (!action_or.ok()) {
      return action_or.status();
    }
    const auto& action = *action_or;

    int func_id = ToScalar(action.at("function"));
    if (func_id < 0) {
      return absl::InvalidArgumentError(
          absl::StrCat("`function` must be >= 0, instead was ", func_id));
    }
    if (func_id >= settings_.num_action_types()) {
      return absl::InvalidArgumentError(absl::StrCat(
          "`function` must be < num_action_types, instead was ", func_id));
    }

    for (const auto& [k, v] : action) {
      output[absl::StrCat("action/", k)] = v;
    }

    const auto& available_actions =
        output.at("available_actions").int32s().array();
    if (available_actions.Get(func_id) != 1) {
      LOG(INFO) << "Action " << func_id << " was not found among available "
                << "ones! Marking as available.";
      *output["available_actions"].mutable_int32s()->mutable_array()->Mutable(
          func_id) = 1;
    }
  }
  return output;
}

absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec>
VisualConverter::ActionSpec() const {
  absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec> spec;
  const auto& visual = settings_.visual_settings();
  spec["function"] = Int32ScalarSpec("function", settings_.num_action_types());
  spec["screen"] =
      Int32ScalarSpec("screen", visual.screen().x() * visual.screen().y());
  spec["minimap"] = Int32ScalarSpec(
      "minimap", settings_.minimap().x() * settings_.minimap().y());
  spec["screen2"] =
      Int32ScalarSpec("screen2", visual.screen().x() * visual.screen().y());
  spec["queued"] = Int32ScalarSpec("queued", 2);
  spec["control_group_act"] = Int32ScalarSpec(
      "control_group_act",
      // -1 because we zero index, +1 because Int32ScalarSpec subtracts one.
      SC2APIProtocol::ActionControlGroup::ControlGroupAction_MAX);
  spec["control_group_id"] =
      Int32ScalarSpec("control_group_id", kNumControlGroups);
  spec["select_point_act"] = Int32ScalarSpec(
      "select_point_act",
      // -1 because we zero index, +1 because Int32ScalarSpec subtracts one.
      SC2APIProtocol::ActionSpatialUnitSelectionPoint::Type_MAX);
  spec["select_add"] = Int32ScalarSpec("select_add", 2);
  spec["select_unit_act"] = Int32ScalarSpec(
      "select_unit_act",
      // -1 because we zero index, +1 because Int32ScalarSpec subtracts one.
      SC2APIProtocol::ActionMultiPanel::Type_MAX);
  spec["select_unit_id"] = Int32ScalarSpec("select_unit_id", kRandomBigNumber);
  spec["select_worker"] = Int32ScalarSpec(
      "select_worker",
      // -1 because we zero index, +1 because Int32ScalarSpec subtracts one.
      SC2APIProtocol::ActionSelectIdleWorker::Type_MAX);
  spec["build_queue_id"] =
      Int32ScalarSpec("build_queue_id", kNumBuildQueueSlots);
  spec["unload_id"] = Int32ScalarSpec("unload_id", kRandomBigNumber);
  return spec;
}

absl::StatusOr<SC2APIProtocol::RequestAction> VisualConverter::ConvertAction(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& action) {
  auto function = action.find("function");
  if (function == action.cend()) {
    return absl::InvalidArgumentError(
        "`function` must be specified for visual actions");
  }
  SC2APIProtocol::RequestAction request_action;
  int func_id = ToScalar(function->second);
  const VisualAction& func = GetAction(func_id);
  if (func.action_type() == no_op) {
    return request_action;
  }

  // Encode action proto.
  ActionContext action_context = {settings_.visual_settings().screen().x(),
                                  settings_.minimap().x(),
                                  settings_.num_action_types()};
  if (action.size() > 1) {
    *request_action.add_actions() = func.Encode(action, action_context);
  }
  return request_action;
}

absl::StatusOr<absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>>
VisualConverter::DecodeAction(
    const SC2APIProtocol::RequestAction& action) const {
  pysc2::ActionContext action_context = {
      settings_.visual_settings().screen().x(), settings_.minimap().x(),
      settings_.num_action_types()};

  return pysc2::Decode(action, action_context);
}

}  // namespace pysc2
