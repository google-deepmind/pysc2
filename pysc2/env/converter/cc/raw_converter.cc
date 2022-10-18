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

#include "pysc2/env/converter/cc/raw_converter.h"

#include <memory>

#include "absl/status/status.h"
#include "absl/strings/str_cat.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "pysc2/env/converter/cc/convert_obs.h"
#include "pysc2/env/converter/cc/game_data/uint8_lookup.h"
#include "pysc2/env/converter/cc/general_order_ids.h"
#include "pysc2/env/converter/cc/map_util.h"
#include "pysc2/env/converter/cc/tensor_util.h"
#include "s2clientprotocol/common.pb.h"
#include "s2clientprotocol/sc2api.pb.h"

namespace pysc2 {
namespace {

constexpr int kMaxActionRepeat = 2;

}  // namespace

RawConverter::RawConverter(const ConverterSettings& settings,
                           const EnvironmentInfo& environment_info)
    : settings_(settings),
      environment_info_(environment_info),
      raw_actions_encoder_(environment_info.game_info().start_raw().map_size(),
                           settings.raw_settings().max_unit_count(),
                           settings.raw_settings().max_unit_selection_size(),
                           settings.raw_settings().resolution(),
                           settings.num_action_types(),
                           settings.raw_settings().shuffle_unit_tags(),
                           settings.raw_settings().enable_action_repeat()),
      current_observation_(),
      last_unit_tags_(),
      last_target_unit_tag_(-1),
      raw_camera_() {}

absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec>
RawConverter::ObservationSpec() const {
  absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec> spec;
  const auto& raw = settings_.raw_settings();
  spec["raw_units"] =
      RawUnitsSpec(raw.max_unit_count(), settings_.num_unit_types(),
                   raw.num_unit_features(), settings_.num_action_types());

  if (raw.use_camera_position()) {
    spec["camera_position"] =
        TensorSpec("camera_position", dm_env_rpc::v1::DataType::INT32, {2});
    spec["camera_size"] =
        TensorSpec("camera_size", dm_env_rpc::v1::DataType::INT32, {2});
  }
  if (raw.camera()) {
    spec["camera"] =
        TensorSpec("camera", dm_env_rpc::v1::DataType::INT32,
                   {raw.resolution().y(), raw.resolution().x()}, 0, 1);
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
RawConverter::ConvertObservation(const Observation& observation) {
  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> output;

  // Cache the latest observation.
  current_observation_ = observation.player();

  const auto& raw = settings_.raw_settings();
  const auto& map_size = environment_info_.game_info().start_raw().map_size();
  const SC2APIProtocol::Observation& obs = observation.player().observation();

  if (!raw_camera_ && raw.use_virtual_camera()) {
    // Seed the virtual camera with the true initial camera position.
    auto& camera = obs.raw_data().player().camera();
    if (raw.has_virtual_camera_dimensions()) {
      auto& dims = raw.virtual_camera_dimensions();
      if (!dims.has_left() || !dims.has_right() || !dims.has_top() ||
          !dims.has_bottom()) {
        return absl::InvalidArgumentError(absl::StrCat(
            "virtual_camera_dimensions must be fully specified, instead was: ",
            dims.DebugString()));
      }
      raw_camera_ =
          std::make_unique<RawCamera>(camera.x(), camera.y(), dims.left(),
                                      dims.right(), dims.top(), dims.bottom());
    } else {
      float width =
          static_cast<float>(settings_.camera_width_world_units()) / 2;
      raw_camera_ = std::make_unique<RawCamera>(camera.x(), camera.y(), width,
                                                width, width, width);
    }
  }

  if (raw.use_camera_position()) {
    output["camera_position"] =
        CameraPosition(obs, map_size, raw.resolution(), raw_camera_.get());
    output["camera_size"] = CameraSize(raw.resolution(), map_size,
                                       settings_.camera_width_world_units());
  }
  if (raw.camera()) {
    if (raw.use_virtual_camera()) {
      output["camera"] = raw_camera_->RenderCamera(map_size, raw.resolution());
    } else {
      output["camera"] = SeparateCamera(
          output["camera_position"], output["camera_size"], raw.resolution());
    }
  }

  output["raw_units"] = RawUnitsToUint8(
      RawUnitsFullVec(last_unit_tags_, last_target_unit_tag_, obs.raw_data(),
                      raw.max_unit_count(), true, map_size, raw.resolution(),
                      settings_.num_unit_types(), raw.num_unit_features(),
                      raw.mask_offscreen_enemies(),
                      settings_.num_action_types(), raw.add_effects_to_units(),
                      raw.add_cargo_to_units(), raw_camera_.get()),
      raw.num_unit_features());

  if (settings_.supervised()) {
    if (!observation.has_force_action_delay()) {
      return absl::InvalidArgumentError(
          "Need force_action_delay to be present in the observation "
          "when supervised is enabled.");
    }
    const auto& action = raw_actions_encoder_.Decode(
        observation.player(), observation.force_action());

    int func_id = ToScalar(action.at("function"));
    if (func_id < 0) {
      return absl::InvalidArgumentError(
          absl::StrCat("`function` must be >= 0, but is ", func_id));
    }
    if (func_id >= settings_.num_action_types()) {
      return absl::InvalidArgumentError(
          absl::StrCat("`function` must be < num_action_types (",
                       settings_.num_action_types(), "), but is ", func_id));
    }

    for (const auto& [k, v] : action) {
      output[absl::StrCat("action/", k)] = v;
    }
  }

  return output;
}

absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec>
RawConverter::ActionSpec() const {
  absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec> spec;
  const auto& raw = settings_.raw_settings();
  spec["function"] = Int32ScalarSpec("function", settings_.num_action_types());
  spec["unit_tags"] =
      TensorSpec("unit_tags", dm_env_rpc::v1::DataType::INT32,
                 {raw.max_unit_selection_size()}, 0, raw.max_unit_count());
  spec["target_unit_tag"] =
      Int32ScalarSpec("target_unit_tag", raw.max_unit_count());
  spec["world"] =
      Int32ScalarSpec("world", raw.resolution().x() * raw.resolution().y());
  spec["queued"] = Int32ScalarSpec("queued", 2);
  if (settings_.raw_settings().enable_action_repeat()) {
    spec["repeat"] = Int32ScalarSpec("repeat", kMaxActionRepeat + 1);
  }
  return spec;
}

absl::StatusOr<SC2APIProtocol::RequestAction> RawConverter::ConvertAction(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& action) {
  auto result = raw_actions_encoder_.Encode(current_observation_, action);
  if (!result.ok()) {
    return result;
  }
  const SC2APIProtocol::RequestAction& output = *result;

  // Ignore no-ops and non-unit commands (e.g. raw camera moves).
  if (output.actions_size() &&
      output.actions(0).action_raw().has_unit_command()) {
    last_unit_tags_.clear();
    const auto& unit_command = output.actions()[0].action_raw().unit_command();
    for (int64_t u : unit_command.unit_tags()) {
      last_unit_tags_.insert(u);
    }
    if (unit_command.has_target_unit_tag()) {
      last_target_unit_tag_ = unit_command.target_unit_tag();
    } else {
      last_target_unit_tag_ = -1;
    }
  }

  if (raw_camera_) {
    if (output.actions_size() > 0 && output.actions(0).has_action_raw() &&
        output.actions(0).action_raw().has_camera_move()) {
      // Update the virtual camera so that it always tracks what an agent
      // would see, even during supervised learning.
      const auto& pos =
          output.actions(0).action_raw().camera_move().center_world_space();
      raw_camera_->Move(pos.x(), pos.y());
    }
    VLOG(1) << "Camera is now at (" << raw_camera_->X() << ", "
            << raw_camera_->Y() << ")";
  }

  return result;
}

absl::StatusOr<absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>>
RawConverter::DecodeAction(const SC2APIProtocol::RequestAction& action) const {
  return raw_actions_encoder_.Decode(current_observation_, action);
}

}  // namespace pysc2
